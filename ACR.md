---
rating: B3b
spec: "0.1"
updated: 2026-10-11
---

# AI Code Rating

**ACR B3b** (Maintainer: Experienced · AI Share: 51–75% · Oversight: Reviewed)

This project is rated with [AI Code Rating](https://aicoderating.com/spec/0.1/), spec version 0.1.

## How AI Was Used

The maintainer wrote HTTP Header Lookup by hand in 2024 and 2025: the Flask app, the page template, and the Docker setup. In 2026 an AI coding agent fixed security problems (escaping the results HTML and blocking lookups of private addresses), updated Python and the dependencies, fixed bugs in how redirects, statuses, and IP addresses were shown, moved the page's CSS from a CDN to a local build step, and added automatic dark mode, accessibility fixes, and a pytest test suite. The maintainer chose the changes and the look, including the dark mode and badge colours, and read all of the code the AI wrote. The AI tested its changes by running the app in Docker and with screenshots, and the test suite now checks the security fixes and lookup results.

The AI's changes are also reviewed by a second AI, and the two go back and forth until it doesn't find any more issues. That doesn't change the oversight level. Commits are marked with `Co-Authored-By: Claude Code` and, where Codex reviewed them, `Reviewed-By: Codex`.
