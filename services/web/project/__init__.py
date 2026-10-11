#!/usr/bin/env python3
import html
import ipaddress
import socket
from urllib.parse import urlsplit

from flask import Flask, render_template, request
import requests
import tldextract
import urllib3.util.connection

app = Flask(__name__, static_folder="assets")

APP_TITLE = "HTTP Header Lookup"


class BlockedAddressError(Exception):
    pass


def is_public_address(ip):
    # Treat IPv4-mapped IPv6 addresses (::ffff:127.0.0.1) as the IPv4 address they contain
    ip = getattr(ip, "ipv4_mapped", None) or ip
    return ip.is_global and not ip.is_multicast


create_connection = urllib3.util.connection.create_connection


def create_public_connection(address, *args, **kwargs):
    # Refuse to connect to private, loopback, and other non-public addresses, so the lookup can't be
    # used to probe the server's own network. This runs for every connection, including each redirect
    # hop. The host is resolved once and the checked IP is connected to directly, so a second DNS lookup
    # can't swap in a private address. TLS still uses the hostname for SNI and certificate checks.
    host, port = address
    addresses = []

    for info in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        ip = info[4][0]
        if not is_public_address(ipaddress.ip_address(ip)):
            raise BlockedAddressError(host)
        addresses.append(ip)

    error = None
    for ip in dict.fromkeys(addresses):
        try:
            return create_connection((ip, port), *args, **kwargs)
        except OSError as e:
            error = e

    raise error


# urllib3 (used by requests) opens every connection through this function
urllib3.util.connection.create_connection = create_public_connection


@app.route("/")
def home():
    return render_template("home.html", app_title=APP_TITLE, page_body="", sort_results=0)


@app.route("/", methods=["POST"])
def home_post():
    # Cleanup the form input and return a list of URLs (original with whitespace removed and a clean list)
    try:
        post_data_clean, url_list_clean = cleanup_url_list(request.form["url_list"])
    except Exception:
        return display_homepage("", "There was an error cleaning the URL list, please try again.", 0)

    # Expand the URL list to include all possible variations (www, non-www, http, https)
    # This only applies to domains, complete URLs are left as-is
    url_list_expanded = expand_url_list(url_list_clean)

    # Remove duplicates
    url_list_unique = list(dict.fromkeys(url_list_expanded))

    # Determine if the user wants to sort the results
    try:
        sort_results = int(request.form["sort_results"])
    except Exception:
        sort_results = 0

    # Process the URL list and return the HTML to display in the homepage's body
    page_body = process_url_list(url_list_unique, sort_results)

    return display_homepage(post_data_clean, page_body, sort_results)


def cleanup_url_list(url_list):
    url_list_raw = ""
    url_list_clean = []

    for url in url_list.split():
        url_list_clean.append(url)
        url_list_raw += url + "\n"

    return url_list_raw, url_list_clean


def expand_url_list(url_list):
    url_list_expanded = []

    # Expand the URL list to include all possible variations (www, non-www, http, https)
    for url in url_list:

        # If it's already a complete URL just add it to the list
        if url.startswith("http://") or url.startswith("https://"):

            url_list_expanded.append(url)

        # Bare IPv6 addresses need brackets in a URL, and IP addresses don't have a www. variation
        elif is_ip_address(url) and ":" in url:

            url_list_expanded.append("http://[" + url + "]")
            url_list_expanded.append("https://[" + url + "]")

        elif is_ip_address(get_host("http://" + url)):

            url_list_expanded.append("http://" + url)
            url_list_expanded.append("https://" + url)

        # Otherwise add all possible variations
        else:

            url_list_expanded.append("http://" + url)
            url_list_expanded.append("http://www." + url)
            url_list_expanded.append("https://" + url)
            url_list_expanded.append("https://www." + url)

    # Remove duplicates
    url_list_unique = list(dict.fromkeys(url_list_expanded))

    return url_list_unique


def process_url_list(url_list, sort_results):
    page_body = ""

    try:

        # Group the URLs by base domain, keeping the order they were entered in
        url_groups = {}
        for url in url_list:
            url_groups.setdefault(get_base_domain(url), []).append(url)

        base_domains = list(url_groups)

        # Sort the base domains and URLs (if applicable)
        if sort_results == 1:
            base_domains.sort()

        # Create a list of HTTP header lookups to display in the homepage's body, grouped by domain
        for domain in base_domains:

            page_body += "<h2 class=\"mb-3 font-bold\">" + html.escape(domain) + "</h2>"

            urls = url_groups[domain]
            if sort_results == 1:
                urls = sorted(urls)

            for url in urls:
                page_body += get_url_headers(url)

            page_body += "<BR>"

    except Exception:

        page_body += "There was an error processing the URL list, please try again."

    return page_body


def get_base_domain(url):
    # IP addresses and hosts without a public suffix (such as localhost) have no base domain, so they're
    # grouped by their host instead
    return tldextract.extract(url).top_domain_under_public_suffix or get_host(url) or url


def get_host(url):
    # urlsplit raises ValueError for some malformed URLs (such as an unclosed "["), so return None for those
    try:
        return urlsplit(url).hostname
    except ValueError:
        return None


def is_ip_address(host):
    try:
        ipaddress.ip_address(host)
        return True
    except (TypeError, ValueError):
        return False


def get_url_headers(url):
    result = html.escape(url)

    try:

        # Ignore proxy settings from the environment: with a proxy, create_public_connection would only
        # check the proxy's address, and the proxy could still connect to a private one
        with requests.Session() as session:
            session.trust_env = False
            response = session.get(url, timeout=8)

        # The history only holds the redirects that were followed (301, 302, 303, 307, 308)
        for resp in response.history:

            location = html.escape(resp.headers.get("Location", ""))
            result += badge("info", str(resp.status_code) + ">") + " " + location

        result += status_badge(response)

        result += "<BR><BR>"

    except BlockedAddressError:

        result += badge("failure", "BLOCKED: NOT A PUBLIC ADDRESS") + "<BR><BR>"

    except Exception:

        result += badge("failure", "HEADER LOOKUP FAILED") + "<BR><BR>"

    return result


def display_homepage(form_input, page_body, sort_results):
    return render_template(
        "home.html",
        app_title=APP_TITLE,
        url_list=form_input,
        page_body=page_body,
        sort_results=sort_results,
    )


def status_badge(response):
    status_code = response.status_code

    if status_code < 300:
        badge_type = "success"
    elif status_code < 400:
        badge_type = "info"
    else:
        badge_type = "failure"

    return badge(badge_type, str(status_code) + " " + str(response.reason or "").upper())


def badge(status, text):
    return '<span class="badge-' + get_badge_colour(status) + '">' + html.escape(text) + "</span>"


def get_badge_colour(status):
    if status == "success":
        colour = "green"
    elif status == "info":
        colour = "orange"
    elif status == "failure":
        colour = "red"
    else:
        colour = "yellow"

    return colour


if __name__ == "__main__":
    app.run()
