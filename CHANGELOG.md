# Changelog

## 2026-10-11

- Fixed a cross-site scripting (XSS) hole in `services/web/project/__init__.py`. The results are built as raw HTML and rendered with `|safe`, but the entered URLs, the base domains, and the `Location` headers and reason phrases sent back by the sites being looked up were inserted unescaped. A site could redirect with a `Location` header containing a `<script>` tag, and it would run in the browser of anyone who looked that site up. These values now go through `html.escape`.
- Updated the Usage text in `README.md` to say the app shows HTTP status codes and redirects, since it doesn't display response header values.
- Added `CLAUDE.md` with run and lint commands, the local dev/prod environment swap, and an overview of how a lookup request is processed, so Claude Code can work in the repo without rediscovering them.
- Updated the copyright notices in `LICENSE` and `README.md` from `2024` to `2024-2026` and added the contact email, to match the standard notice format.
- Fixed the install URL in `README.md` from `https://` to `http://`. Gunicorn serves plain HTTP on port 8092 with no TLS, so the `https://` link failed with a connection error.
- Added this changelog.
