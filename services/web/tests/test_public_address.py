import ipaddress
import socket

import pytest
import urllib3.util.connection

import project
from project import BlockedAddressError, create_public_connection, get_url_headers, is_public_address


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",  # cloud metadata endpoint
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fe80::1",
        "fd00::1",
        "::ffff:127.0.0.1",
        "::ffff:10.0.0.1",
        "ff0e::1",  # global-scope multicast, which ipaddress counts as global
    ],
)
def test_non_public_addresses(ip):
    assert not is_public_address(ipaddress.ip_address(ip))


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "2001:4860:4860::8888", "::ffff:8.8.8.8"])
def test_public_addresses(ip):
    assert is_public_address(ipaddress.ip_address(ip))


def test_urllib3_uses_the_public_connection_hook():
    assert urllib3.util.connection.create_connection is create_public_connection


def fake_getaddrinfo(monkeypatch, *ips):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *args: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in ips],
    )


@pytest.fixture
def connections(monkeypatch):
    # Record the addresses create_public_connection connects to, instead of opening sockets
    attempts = []

    def create_connection(address, *args, **kwargs):
        attempts.append(address)
        return "socket for " + address[0]

    monkeypatch.setattr(project, "create_connection", create_connection)
    return attempts


def test_connects_to_the_checked_ip(monkeypatch, connections):
    fake_getaddrinfo(monkeypatch, "8.8.8.8")

    assert create_public_connection(("example.com", 443)) == "socket for 8.8.8.8"
    assert connections == [("8.8.8.8", 443)]


def test_blocks_if_any_address_is_private(monkeypatch, connections):
    fake_getaddrinfo(monkeypatch, "8.8.8.8", "10.0.0.1")

    with pytest.raises(BlockedAddressError):
        create_public_connection(("example.com", 80))
    assert connections == []


def test_tries_the_next_address_after_a_failure(monkeypatch):
    fake_getaddrinfo(monkeypatch, "8.8.8.8", "8.8.8.8", "1.1.1.1")
    attempts = []

    def create_connection(address, *args, **kwargs):
        attempts.append(address)
        if address[0] == "8.8.8.8":
            raise ConnectionRefusedError()
        return "socket"

    monkeypatch.setattr(project, "create_connection", create_connection)

    assert create_public_connection(("example.com", 80)) == "socket"
    # The duplicate address is only tried once
    assert attempts == [("8.8.8.8", 80), ("1.1.1.1", 80)]


def test_raises_the_last_error_if_every_address_fails(monkeypatch):
    fake_getaddrinfo(monkeypatch, "8.8.8.8")

    def create_connection(address, *args, **kwargs):
        raise ConnectionRefusedError()

    monkeypatch.setattr(project, "create_connection", create_connection)

    with pytest.raises(ConnectionRefusedError):
        create_public_connection(("example.com", 80))


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1", "http://localhost", "http://[::1]", "http://169.254.169.254/latest/meta-data/"],
)
def test_lookup_of_private_address_is_blocked(url):
    assert "BLOCKED: NOT A PUBLIC ADDRESS" in get_url_headers(url)


def test_hostname_resolving_to_private_address_is_blocked(fake_dns):
    assert "BLOCKED: NOT A PUBLIC ADDRESS" in get_url_headers("http://private.test/")


def test_redirect_to_private_address_is_blocked(public_test_server):
    public_test_server.route("/", 302, headers={"Location": "http://private.test/admin"})

    result = get_url_headers(public_test_server.url("/"))

    assert "BLOCKED: NOT A PUBLIC ADDRESS" in result


def test_proxy_environment_variables_are_ignored(public_test_server, monkeypatch):
    # With the proxy, the request would go to 10.0.0.1 and be blocked. Ignoring it, the lookup goes direct.
    for name in ["NO_PROXY", "no_proxy"]:
        monkeypatch.delenv(name, raising=False)
    for name in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
        monkeypatch.setenv(name, "http://10.0.0.1:3128")
    public_test_server.route("/", 200, "OK")

    assert '<span class="badge-green">200 OK</span>' in get_url_headers(public_test_server.url("/"))
