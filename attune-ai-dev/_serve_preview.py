#!/usr/bin/env python3
"""Dev-only static server with Vercel-style clean-URL fallback.

NOT part of the build or the deploy — local preview only. Serves the
attune-ai-dev/ directory, resolving extensionless paths to <path>.html
or <path>/index.html the way Vercel's clean-URLs config does in prod.
"""

from __future__ import annotations

import http.server
import os
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "8780"))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def translate_path(self, path):
        local = Path(super().translate_path(path))
        if local.is_file() or local.is_dir():
            return str(local)
        html = local.with_suffix(".html")
        if html.is_file():
            return str(html)
        return str(local)


if __name__ == "__main__":
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"preview on http://127.0.0.1:{PORT}/help/")
        httpd.serve_forever()
