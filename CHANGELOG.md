# Changelog

## 2026-10-11

- Blocked lookups of private, loopback, link-local, and other non-public addresses in `services/web/project/__init__.py` (server-side request forgery, SSRF). The app fetched any URL it was given, so anyone using the public demo could make the server probe `localhost`, the Docker network, or cloud metadata endpoints such as `169.254.169.254`, directly or through a redirect or a hostname that resolves to a private address. urllib3's connection function is now replaced with one that resolves the host once, refuses non-public addresses, and connects to the checked IP, so redirects and DNS rebinding can't get around it. Lookups also ignore proxy settings from the environment (`HTTP_PROXY` and similar variables), because a proxy would connect to the target itself and only the proxy's address would be checked. Blocked lookups show a "BLOCKED: NOT A PUBLIC ADDRESS" badge. `CLAUDE.md` describes the hook, and now also says that values added to the results HTML must be escaped.
- Fixed a cross-site scripting (XSS) hole in `services/web/project/__init__.py`. The results are built as raw HTML and rendered with `|safe`, but the entered URLs, the base domains, and the `Location` headers and reason phrases sent back by the sites being looked up were inserted unescaped. A site could redirect with a `Location` header containing a `<script>` tag, and it would run in the browser of anyone who looked that site up. These values now go through `html.escape`.
- Updated the Usage text in `README.md` to say the app shows HTTP status codes and redirects, since it doesn't display response header values.
- Added `CLAUDE.md` with run and lint commands, the local dev/prod environment swap, and an overview of how a lookup request is processed, so Claude Code can work in the repo without rediscovering them.
- Updated the copyright notices in `LICENSE` and `README.md` from `2024` to `2024-2026` and added the contact email, to match the standard notice format.
- Fixed the install URL in `README.md` from `https://` to `http://`. Gunicorn serves plain HTTP on port 8092 with no TLS, so the `https://` link failed with a connection error.
- Added this changelog.
