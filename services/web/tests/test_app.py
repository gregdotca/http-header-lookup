import project
from project import process_url_list


def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "<title>HTTP Header Lookup" in response.text
    assert 'name="url_list"' in response.text


def test_home_page_is_not_in_quirks_mode(client):
    response = client.get("/")

    assert response.text.startswith("<!doctype html>")
    assert '<html lang="en">' in response.text
    assert 'name="viewport"' in response.text


def test_post_without_url_list_shows_error(client):
    response = client.post("/", data={})

    assert response.status_code == 200
    assert "There was an error cleaning the URL list, please try again." in response.text


def test_post_looks_up_every_variation(client, no_lookups):
    response = client.post("/", data={"url_list": "example.com\nhttps://example.org/page"})

    assert response.status_code == 200
    for url in [
        "http://example.com",
        "http://www.example.com",
        "https://example.com",
        "https://www.example.com",
        "https://example.org/page",
    ]:
        assert "[lookup " + url + "]" in response.text
    assert "http://https://" not in response.text


def test_post_accepts_the_maximum_number_of_entries(client, no_lookups):
    entries = ["site" + str(i) + ".com" for i in range(project.MAX_ENTRIES)]

    response = client.post("/", data={"url_list": "\n".join(entries)})

    for entry in entries:
        assert "[lookup https://" + entry + "]" in response.text


def test_post_counts_repeated_entries_once(client, no_lookups):
    entries = ["site" + str(i) + ".com" for i in range(project.MAX_ENTRIES)]

    response = client.post("/", data={"url_list": "\n".join(entries + entries)})

    assert "[lookup https://site0.com]" in response.text
    assert "at a time" not in response.text


def test_post_refuses_too_many_entries(client, monkeypatch):
    def fail(url):
        raise AssertionError("looked up " + url)

    monkeypatch.setattr(project, "get_url_headers", fail)
    entries = ["site" + str(i) + ".com" for i in range(project.MAX_ENTRIES + 1)]

    response = client.post("/", data={"url_list": "\n".join(entries), "sort_results": "1"})

    assert response.status_code == 200
    assert "Enter up to 10 domains or URLs at a time (you entered 11)." in response.text
    # The list and the sort setting are kept, so the visitor can shorten the list and try again
    assert "site10.com" in response.text
    assert 'value="1" checked' in response.text


def test_post_escapes_input(client, no_lookups, monkeypatch):
    # Use the real escaping in the results, while still skipping the network lookup
    monkeypatch.setattr(project, "get_url_headers", lambda url: project.badge("success", url))

    response = client.post("/", data={"url_list": "<script>alert(1)</script>"})

    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_post_keeps_the_sort_checkbox_ticked(client, no_lookups):
    response = client.post("/", data={"url_list": "example.com", "sort_results": "1"})

    assert 'value="1" checked' in response.text


def test_post_ignores_invalid_sort_value(client, no_lookups):
    response = client.post("/", data={"url_list": "example.com", "sort_results": "abc"})

    assert response.status_code == 200
    assert 'value="1" checked' not in response.text


def headings(page_body):
    return [part.split("</h2>")[0] for part in page_body.split('<h2 class="mb-3 font-bold">')[1:]]


def test_results_grouped_by_base_domain_in_entry_order(no_lookups):
    urls = ["https://www.zeta.com", "http://8.8.8.8", "https://alpha.com/b", "https://zeta.com/a", "https://alpha.com/a"]

    page_body = process_url_list(urls, 0)

    assert headings(page_body) == ["zeta.com", "8.8.8.8", "alpha.com"]
    assert page_body.index("[lookup https://www.zeta.com]") < page_body.index("[lookup https://zeta.com/a]")
    assert page_body.index("[lookup https://alpha.com/b]") < page_body.index("[lookup https://alpha.com/a]")


def test_results_sorted(no_lookups):
    urls = ["https://zeta.com", "https://alpha.com/b", "https://alpha.com/a"]

    page_body = process_url_list(urls, 1)

    assert headings(page_body) == ["alpha.com", "zeta.com"]
    assert page_body.index("[lookup https://alpha.com/a]") < page_body.index("[lookup https://alpha.com/b]")


def test_heading_is_escaped(no_lookups):
    page_body = process_url_list(["http://[<b>"], 0)

    assert headings(page_body) == ["[&lt;b&gt;"]


def test_processing_error_shows_message(monkeypatch):
    def fail(url):
        raise RuntimeError()

    monkeypatch.setattr(project, "get_base_domain", fail)

    assert process_url_list(["https://example.com"], 0) == "There was an error processing the URL list, please try again."
