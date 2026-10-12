import pytest

from project import cleanup_url_list, expand_url_list, get_base_domain, is_ip_address


def test_cleanup_url_list_splits_on_any_whitespace():
    raw, urls = cleanup_url_list("  example.com\n\n\texample.org   https://example.net/a \r\n")

    assert urls == ["example.com", "example.org", "https://example.net/a"]
    assert raw == "example.com\nexample.org\nhttps://example.net/a\n"


def test_cleanup_url_list_empty():
    assert cleanup_url_list(" \n ") == ("", [])


def test_expand_domain_to_four_variations():
    assert expand_url_list(["example.com"]) == [
        "http://example.com",
        "http://www.example.com",
        "https://example.com",
        "https://www.example.com",
    ]


@pytest.mark.parametrize("url", ["http://example.com/path?q=1", "https://www.example.com"])
def test_expand_leaves_full_urls_alone(url):
    assert expand_url_list([url]) == [url]


@pytest.mark.parametrize(
    "entry, expected",
    [
        ("8.8.8.8", ["http://8.8.8.8", "https://8.8.8.8"]),
        ("8.8.8.8:8080", ["http://8.8.8.8:8080", "https://8.8.8.8:8080"]),
        ("2001:4860:4860::8888", ["http://[2001:4860:4860::8888]", "https://[2001:4860:4860::8888]"]),
        ("[2001:db8::1]:8080", ["http://[2001:db8::1]:8080", "https://[2001:db8::1]:8080"]),
    ],
)
def test_expand_ip_address_without_www(entry, expected):
    assert expand_url_list([entry]) == expected


def test_expand_removes_duplicates():
    assert expand_url_list(["example.com", "http://example.com", "example.com"]) == [
        "http://example.com",
        "http://www.example.com",
        "https://example.com",
        "https://www.example.com",
    ]


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.example.com/", "example.com"),
        ("http://deep.sub.example.co.uk/a", "example.co.uk"),
        # A domain in the path doesn't change the group
        ("https://example.com/redirect/example.org", "example.com"),
        ("http://8.8.8.8", "8.8.8.8"),
        ("http://[2001:db8::1]:8080", "2001:db8::1"),
        ("http://localhost:5000", "localhost"),
    ],
)
def test_get_base_domain(url, expected):
    assert get_base_domain(url) == expected


def test_get_base_domain_groups_malformed_variations_together():
    variations = expand_url_list(["[abc"])

    assert len(variations) == 4
    assert {get_base_domain(url) for url in variations} == {"[abc"}


@pytest.mark.parametrize(
    "value, expected",
    [("8.8.8.8", True), ("::1", True), ("example.com", False), ("", False), (None, False)],
)
def test_is_ip_address(value, expected):
    assert is_ip_address(value) is expected
