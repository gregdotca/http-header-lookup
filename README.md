HTTP Header Lookup
------------------

[![ACR B3b](https://img.shields.io/badge/ACR-B3b-2140B5)](ACR.md)

## Demo

https://headers.greg.ca

## Installation

- Clone the repository
- Run "docker-compose up -d"
- Load http://IP_ADDRESS:8092 in your web browser

## Usage

Enter a list of domains and/or complete URLs and their HTTP status codes and redirects will be displayed. If you only enter a domain, the four common variations will be checked and displayed (www, non-www, http, https).

## Running the Tests

```bash
cd services/web
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

The tests don't need Docker or internet access.

## License

MIT License

Copyright (c) 2024-2026 Greg Chetcuti <greg@chetcuti.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
