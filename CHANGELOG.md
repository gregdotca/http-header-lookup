# Changelog

## 2026-10-11

- Added `CLAUDE.md` with run and lint commands, the local dev/prod environment swap, and an overview of how a lookup request is processed, so Claude Code can work in the repo without rediscovering them.
- Updated the copyright notices in `LICENSE` and `README.md` from `2024` to `2024-2026` and added the contact email, to match the standard notice format.
- Fixed the install URL in `README.md` from `https://` to `http://`. Gunicorn serves plain HTTP on port 8092 with no TLS, so the `https://` link failed with a connection error.
- Added this changelog.
