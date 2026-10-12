import socket
import threading
import time

import pytest

import project
from project import Lookup, LookupCancelledError, create_public_connection, get_url_headers, look_up_urls, process_url_list


def test_lookups_run_in_parallel(monkeypatch):
    # The barrier only opens once every lookup is running at the same time. One after another, the first
    # lookup would wait 5 seconds and break it, and every result would be "[failed]".
    barrier = threading.Barrier(project.MAX_PARALLEL_LOOKUPS, timeout=5)

    def lookup(url):
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            return "[failed]"
        return "[" + url + "]"

    monkeypatch.setattr(project, "get_url_headers", lookup)
    urls = ["https://example" + str(number) + ".com" for number in range(project.MAX_PARALLEL_LOOKUPS)]

    assert look_up_urls(urls) == {url: "[" + url + "]" for url in urls}


def test_results_keep_their_order(monkeypatch):
    # The first URL finishes last, but is still shown first
    def lookup(url):
        time.sleep(0.2 if url.endswith("a.com") else 0)
        return "[" + url + "]"

    monkeypatch.setattr(project, "get_url_headers", lookup)

    page_body = process_url_list(["https://a.com", "https://b.com", "https://c.com"], 0)

    assert page_body.index("[https://a.com]") < page_body.index("[https://b.com]") < page_body.index("[https://c.com]")


def test_time_limit(monkeypatch):
    release = threading.Event()

    def lookup(url):
        if "slow" in url:
            release.wait(5)
        return "[" + url + "]"

    monkeypatch.setattr(project, "get_url_headers", lookup)
    monkeypatch.setattr(project, "LOOKUP_TIME_LIMIT", 0.3)

    start = time.monotonic()
    try:
        results = look_up_urls(["https://fast.com", "https://slow.com/<b>"])
    finally:
        release.set()

    assert time.monotonic() - start < 2
    assert results["https://fast.com"] == "[https://fast.com]"
    assert results["https://slow.com/<b>"] == (
        'https://slow.com/&lt;b&gt;<span class="badge-red">TIME LIMIT REACHED</span><BR><BR>'
    )


def test_lookups_not_started_by_the_time_limit_are_cancelled(monkeypatch):
    release = threading.Event()
    started = []

    def lookup(url):
        started.append(url)
        release.wait(5)
        return "[" + url + "]"

    monkeypatch.setattr(project, "get_url_headers", lookup)
    monkeypatch.setattr(project, "MAX_PARALLEL_LOOKUPS", 1)
    monkeypatch.setattr(project, "LOOKUP_TIME_LIMIT", 0.2)

    try:
        results = look_up_urls(["https://one.com", "https://two.com"])
    finally:
        release.set()

    assert started == ["https://one.com"]
    assert "TIME LIMIT REACHED" in results["https://one.com"]
    assert "TIME LIMIT REACHED" in results["https://two.com"]


def test_site_that_never_responds(public_test_server, monkeypatch):
    # A socket that's listening but never accepts: the connection opens, and no response ever comes
    monkeypatch.setattr(project, "LOOKUP_TIMEOUT", 0.3)

    with socket.socket() as silent:
        silent.bind(("127.0.0.1", 0))
        silent.listen()
        port = silent.getsockname()[1]

        start = time.monotonic()
        result = get_url_headers("http://public.test:" + str(port) + "/")

    assert time.monotonic() - start < 2
    assert "HEADER LOOKUP FAILED" in result


@pytest.fixture
def trickle_server(public_test_server):
    # A server that sends the start of a response, then one more byte every 50ms until the test ends
    stop = threading.Event()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()

    def serve(start):
        listener.settimeout(5)
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        with conn:
            try:
                conn.sendall(start)
                while not stop.wait(0.05):
                    conn.sendall(b"a")
            except OSError:
                pass

    threads = []

    def run(start):
        thread = threading.Thread(target=serve, args=(start,), daemon=True)
        thread.start()
        threads.append(thread)
        return "http://public.test:" + str(listener.getsockname()[1]) + "/"

    yield run

    stop.set()
    listener.close()
    for thread in threads:
        thread.join()


def test_time_limit_stops_a_lookup_that_never_ends(trickle_server, monkeypatch):
    # The headers never finish, but each byte arrives well inside LOOKUP_TIMEOUT
    url = trickle_server(b"HTTP/1.1 200 OK\r\nX-Slow: ")
    real_get_url_headers = project.get_url_headers
    finished = threading.Event()

    def lookup(url):
        try:
            return real_get_url_headers(url)
        finally:
            finished.set()

    monkeypatch.setattr(project, "get_url_headers", lookup)
    monkeypatch.setattr(project, "LOOKUP_TIME_LIMIT", 0.3)

    results = look_up_urls([url])

    assert "TIME LIMIT REACHED" in results[url]
    # The lookup's connection was closed, so its thread doesn't keep running in the background
    assert finished.wait(2)


def test_body_is_not_downloaded(trickle_server):
    # Sent at one byte per 50ms, the body would take 5 seconds
    url = trickle_server(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n")

    start = time.monotonic()
    result = get_url_headers(url)

    assert time.monotonic() - start < 2
    assert '<span class="badge-green">200 OK</span>' in result


def test_cancelled_lookup_opens_no_connections(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *args: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))],
    )
    attempts = []
    monkeypatch.setattr(project, "create_connection", lambda address, *args, **kwargs: attempts.append(address))
    lookup = Lookup()
    lookup.cancel()
    monkeypatch.setattr(project.current, "lookup", lookup, raising=False)

    with pytest.raises(LookupCancelledError):
        create_public_connection(("example.com", 80))
    assert attempts == []


def test_socket_opened_after_cancel_is_closed():
    lookup = Lookup()
    lookup.cancel()

    with socket.socket() as sock:
        with pytest.raises(LookupCancelledError):
            lookup.add(sock)
        assert sock.fileno() == -1
