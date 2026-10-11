# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

HTTP Header Lookup is a single-page Flask app (demo: https://headers.greg.ca). A user pastes a list of domains and/or full URLs, and the app fetches each one and shows its status code and redirect chain as coloured badges.

## Commands

Production (the committed config): gunicorn behind Docker on host port 8092.

```bash
docker-compose up -d --build        # build and run at http://localhost:8092
docker-compose logs -f web
```

Lint (this runs inside the production Docker build, so a lint failure breaks the build):

```bash
cd services/web && flake8 --ignore=E501,W503,F401 .
```

There is no test suite. `test.py` in the repo root is an untracked scratch script, not a test.

### Dev vs. prod environment swap

The dev setup is local-only: `docker-compose.DEV.yml`, `services/web/Dockerfile.DEV`, `to-dev.sh`, and `to-prod.sh` are listed in `.git/info/exclude`, not committed. `./to-dev.sh` renames files so the dev versions become `docker-compose.yml` and `services/web/Dockerfile` (the prod ones become `*.PROD`); `./to-prod.sh` swaps them back. The dev config runs Flask's debug server on port 5000 with `services/web/` bind-mounted for live reload.

If `docker-compose.PROD.yml` exists, the dev environment is active, and the dev `docker-compose.yml` and `Dockerfile` will show up as modifications to the tracked files. Switch back with `./to-prod.sh` before committing. In a clone without these local files, there's nothing to swap.

## Architecture

All server logic is in `services/web/project/__init__.py`; `services/web/manage.py` only wraps `app` in a `FlaskGroup` for gunicorn (`manage:app`) and the dev server.

POST `/` flow:
1. `cleanup_url_list` splits the textarea on whitespace.
2. `expand_url_list` turns each bare domain into four URLs (http/https × with/without `www.`); full `http(s)://` URLs pass through unchanged.
3. `get_base_domains` groups the URLs by registrable domain using `tldextract`. Grouping matches URLs to a domain by checking for `"." + domain` or `"/" + domain` in the URL, so `example.com` doesn't match `anotherexample.com`.
4. `get_url_headers` fetches the URL with a `requests.Session` (follows redirects; the 8s timeout applies to each connection attempt and to each wait for data, not to DNS resolution or the whole lookup) and walks `response.history` to render each hop as a badge.

Outbound connections are restricted to public addresses. At import, `project/__init__.py` replaces `urllib3.util.connection.create_connection` (the function urllib3, and so requests, opens every socket with) with `create_public_connection`. That function resolves the host once, raises `BlockedAddressError` if any address fails `is_public_address`, and connects to the checked IP itself. Because the check happens at connect time, it covers every redirect hop and DNS rebinding. Any new outbound HTTP code goes through it too, and `get_url_headers` catches the error to show a "BLOCKED" badge. `get_url_headers` fetches with a `requests.Session` that has `trust_env = False`. With a proxy from `HTTP_PROXY` and similar variables, the hook would only check the proxy's address, so any new fetch code needs the same setting.

The result is built as a raw HTML string and rendered in `services/web/project/templates/home.html` with `{{ page_body|safe }}`, so the template doesn't escape it. Any user input or value from a remote server added to it must go through `html.escape`. Use the standard library's `html.escape` and not `markupsafe.escape`: adding a `Markup` object to a plain string escapes the whole string, including the HTML already in it.

Frontend: `home.html` loads Tailwind and daisyUI from jsDelivr (`bumblebee` theme), plus jQuery from `services/web/project/assets/` (Flask's `static_folder` is `assets`). The `.badge-*` CSS classes in the template must match the colours returned by `get_badge_colour`.

`services/web/project/templates/custom.headers` is gitignored and included into `<head>` with `ignore missing`. It holds deployment-specific HTML, such as analytics snippets.
