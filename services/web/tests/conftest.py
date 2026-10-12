import ipaddress
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import tldextract

import project

# tldextract downloads the public suffix list the first time it runs. The tests use the snapshot bundled
# with tldextract instead, and don't read or write its cache.
OFFLINE_TLDEXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

# Fake hostnames for the lookup tests, so nothing goes out to the internet. public.test points at the local
# test server, which the public_test_server fixture lets through the public-address check, and private.test
# points at a private address that stays blocked.
FAKE_HOSTS = {
    "public.test": "127.0.0.1",
    "private.test": "10.0.0.1",
}


class Handler(BaseHTTPRequestHandler):
    # Path -> (status code, reason phrase, headers), set by the test through TestServer.route
    routes = {}

    def do_GET(self):
        status, reason, headers = self.routes.get(self.path.split("?")[0], (404, "Not Found", {}))
        self.send_response(status, reason)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args):
        pass


class TestServer:
    __test__ = False

    def __init__(self, port):
        self.port = port

    def url(self, path, host="public.test"):
        return "http://" + host + ":" + str(self.port) + path

    def route(self, path, status, reason=None, headers=None):
        Handler.routes[path] = (status, reason, headers or {})


@pytest.fixture(autouse=True)
def offline_tldextract(monkeypatch):
    monkeypatch.setattr(tldextract, "extract", OFFLINE_TLDEXTRACT)


@pytest.fixture
def fake_dns(monkeypatch):
    real_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        if host in FAKE_HOSTS:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (FAKE_HOSTS[host], port))]
        return real_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


@pytest.fixture
def public_test_server(monkeypatch, fake_dns):
    # Treat 127.0.0.1 as public so the lookup can reach the test server. Every other loopback or private
    # address is still blocked.
    real_is_public_address = project.is_public_address
    monkeypatch.setattr(
        project,
        "is_public_address",
        lambda ip: ip == ipaddress.ip_address("127.0.0.1") or real_is_public_address(ip),
    )

    Handler.routes = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    # A short poll interval, so shutdown doesn't wait the default half second after each test
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()

    yield TestServer(server.server_address[1])

    server.shutdown()
    thread.join()
    server.server_close()


@pytest.fixture
def no_lookups(monkeypatch):
    # Replace the network lookup with a stub that only echoes the URL, for tests of the page and grouping
    monkeypatch.setattr(project, "get_url_headers", lambda url: "[lookup " + url + "]")


@pytest.fixture
def client():
    return project.app.test_client()
