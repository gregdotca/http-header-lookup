import socket

import pytest

from project import badge, get_badge_colour, get_url_headers


@pytest.mark.parametrize(
    "status, reason, expected",
    [
        (200, "OK", '<span class="badge-green">200 OK</span>'),
        (204, "No Content", '<span class="badge-green">204 NO CONTENT</span>'),
        (304, "Not Modified", '<span class="badge-orange">304 NOT MODIFIED</span>'),
        (403, "Forbidden", '<span class="badge-red">403 FORBIDDEN</span>'),
        (404, "Not Found", '<span class="badge-red">404 NOT FOUND</span>'),
        (503, "Service Unavailable", '<span class="badge-red">503 SERVICE UNAVAILABLE</span>'),
    ],
)
def test_final_status_badge(public_test_server, status, reason, expected):
    public_test_server.route("/", status, reason)

    result = get_url_headers(public_test_server.url("/"))

    assert result == public_test_server.url("/") + expected + "<BR><BR>"


def test_every_redirect_in_the_chain_is_shown(public_test_server):
    codes = [301, 302, 303, 307, 308]
    for number, code in enumerate(codes):
        public_test_server.route("/" + str(number), code, headers={"Location": "/" + str(number + 1)})
    public_test_server.route("/" + str(len(codes)), 200, "OK")

    result = get_url_headers(public_test_server.url("/0"))

    for number, code in enumerate(codes):
        assert '<span class="badge-orange">' + str(code) + "&gt;</span> /" + str(number + 1) in result
    assert result.endswith('<span class="badge-green">200 OK</span><BR><BR>')


def test_failed_lookup(public_test_server):
    # Hold a port that's bound but not listening, so connections to it are refused and nothing else can take it
    with socket.socket() as unused:
        unused.bind(("127.0.0.1", 0))
        port = unused.getsockname()[1]

        result = get_url_headers("http://public.test:" + str(port) + "/")

    assert '<span class="badge-red">HEADER LOOKUP FAILED</span>' in result


def test_malformed_url_lookup_fails_cleanly():
    assert "HEADER LOOKUP FAILED" in get_url_headers("http://[abc")


def test_url_is_escaped():
    result = get_url_headers('http://[abc"><script>alert(1)</script>')

    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_location_header_is_escaped(public_test_server):
    public_test_server.route("/", 302, headers={"Location": "/next?<script>alert(1)</script>"})
    public_test_server.route("/next", 200, "OK")

    result = get_url_headers(public_test_server.url("/"))

    assert "<script>" not in result
    assert "/next?&lt;script&gt;alert(1)&lt;/script&gt;" in result


def test_reason_phrase_is_escaped(public_test_server):
    public_test_server.route("/", 200, "<img src=x onerror=alert(1)>")

    result = get_url_headers(public_test_server.url("/"))

    assert "<IMG" not in result
    assert "200 &lt;IMG SRC=X ONERROR=ALERT(1)&gt;" in result


@pytest.mark.parametrize(
    "status, colour",
    [("success", "green"), ("info", "orange"), ("failure", "red"), ("other", "yellow")],
)
def test_badge_colours(status, colour):
    assert get_badge_colour(status) == colour


def test_badge_escapes_its_text():
    assert badge("success", "<b>") == '<span class="badge-green">&lt;b&gt;</span>'
