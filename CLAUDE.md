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

Without Docker, the CSS needs the [Tailwind standalone CLI](https://github.com/tailwindlabs/tailwindcss/releases):

```bash
cd services/web
tailwindcss -i project/styles/app.css -o project/assets/app.css --watch &
FLASK_APP=project/__init__.py flask --debug run
```

Lint (this runs inside the production Docker build, so a lint failure breaks the build):

```bash
cd services/web && flake8 --ignore=E501,W503,F401 .
```

There is no test suite. `test.py` in the repo root is an untracked scratch script, not a test.

### Dev vs. prod environment swap

The dev setup is local-only: `docker-compose.DEV.yml`, `services/web/Dockerfile.DEV`, `to-dev.sh`, and `to-prod.sh` are listed in `.git/info/exclude`, not committed. `./to-dev.sh` renames files so the dev versions become `docker-compose.yml` and `services/web/Dockerfile` (the prod ones become `*.PROD`); `./to-prod.sh` swaps them back. The dev config runs Flask's debug server on port 5000 with `services/web/` bind-mounted for live reload. Alongside it, `tailwindcss --watch=always` rebuilds `project/assets/app.css` into the mounted directory (`--watch=always` because the container's stdin is closed), so that file is root-owned on the host.

If `docker-compose.PROD.yml` exists, the dev environment is active, and the dev `docker-compose.yml` and `Dockerfile` will show up as modifications to the tracked files. Switch back with `./to-prod.sh` before committing. In a clone without these local files, there's nothing to swap.

## Architecture

All server logic is in `services/web/project/__init__.py`; `services/web/manage.py` only wraps `app` in a `FlaskGroup` for gunicorn (`manage:app`) and the dev server.

POST `/` flow:
1. `cleanup_url_list` splits the textarea on whitespace.
2. `expand_url_list` turns each bare domain into four URLs (http/https × with/without `www.`) and each bare IP address into two (http/https); full `http(s)://` URLs pass through unchanged.
3. `process_url_list` groups the URLs by `get_base_domain`, which is the registrable domain from `tldextract`, or the host itself for IP addresses and hosts like `localhost` that have no public suffix. URLs that can't be parsed (such as an unclosed `[`) are grouped by what's left after removing the scheme and `www.`, so all the variations of one entry stay in one group.
4. `get_url_headers` fetches the URL with a `requests.Session` (follows redirects; the 8s timeout applies to each connection attempt and to each wait for data, not to DNS resolution or the whole lookup) and renders each redirect in `response.history` as an orange badge with its `Location`, then the final status from `status_badge` (2xx green, 3xx orange, 4xx and 5xx red).

Outbound connections are restricted to public addresses. At import, `project/__init__.py` replaces `urllib3.util.connection.create_connection` (the function urllib3, and so requests, opens every socket with) with `create_public_connection`. That function resolves the host once, raises `BlockedAddressError` if any address fails `is_public_address`, and connects to the checked IP itself. Because the check happens at connect time, it covers every redirect hop and DNS rebinding. Any new outbound HTTP code goes through it too, and `get_url_headers` catches the error to show a "BLOCKED" badge. `get_url_headers` fetches with a `requests.Session` that has `trust_env = False`. With a proxy from `HTTP_PROXY` and similar variables, the hook would only check the proxy's address, so any new fetch code needs the same setting.

The result is built as a raw HTML string and rendered in `services/web/project/templates/home.html` with `{{ page_body|safe }}`, so the template doesn't escape it. Any user input or value from a remote server added to it must go through `html.escape`. Use the standard library's `html.escape` and not `markupsafe.escape`: adding a `Markup` object to a plain string escapes the whole string, including the HTML already in it.

Frontend: Tailwind 4 and daisyUI 5 are built at Docker build time, not loaded from a CDN. The Tailwind standalone CLI (version and per-architecture SHA-256s pinned as `ARG`s in the Dockerfile builder stage) compiles `services/web/project/styles/app.css` into `project/assets/app.css` (gitignored), which the final stage copies in. daisyUI is the vendored plugin `project/styles/daisyui-<version>.mjs`, with only the `bumblebee` (light) and `business` (dark) themes enabled. `app.css` uses `source(none)` and scans only `project/templates/` and `project/__init__.py`, because `process_url_list` outputs Tailwind classes in its HTML. A class used anywhere else, such as only from JavaScript, won't be in the build. To upgrade either tool, update the Dockerfile `ARG`s (and `Dockerfile.DEV`), or replace the `.mjs` file and its reference in `app.css`.

Dark mode is automatic only, with no toggle, JavaScript, or `data-theme` attribute. `bumblebee --default, business --prefersdark` in `project/styles/app.css` puts `business` inside `@media (prefers-color-scheme: dark)` on `:root:not([data-theme])`, so adding `data-theme` to `<html>` would lock the page to one theme. A `color-scheme` meta tag at the top of `<head>` tells the browser about both modes before the CSS loads. Use daisyUI theme colours (`base-content`, `base-200`, and so on), not hard-coded colour classes, so both modes keep working. Tailwind's `dark:` variant uses the same media query, so per-mode tweaks go there (the Lookup button is `btn-accent dark:btn-primary`, because business's accent is orange). Dark-mode overrides of theme variables live in an unlayered rule at the end of `app.css`: a darker `--color-primary` for the button, and bumblebee's `--radius-*` corner sizes so both modes match. Being unlayered, it beats daisyUI's layered theme.

Static files are served from `project/assets/` at `/assets/...` (Flask's `static_folder`; use `url_for('static', ...)`). jQuery and the favicon are vendored there. The `.badge-*` rules in `project/styles/app.css` must match the colours returned by `get_badge_colour`. They're fixed colours in both modes, chosen so white text passes WCAG AA (4.5:1), so check the contrast if you change them.

`services/web/project/templates/custom.headers` is gitignored and included into `<head>` with `ignore missing`. It holds deployment-specific HTML, such as analytics snippets.
