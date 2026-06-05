#!/usr/bin/env python3
"""Generate ``sitemap.xml`` for attune-ai.dev from the built HTML tree.

Re-runnable: ``python build_sitemap.py`` (run AFTER build_help.py /
build_discipline.py so all pages exist). Emits clean-URL canonical
entries matching the site's ``cleanUrls: true`` + ``trailingSlash: false``
Vercel config — i.e. ``/help/foo/bar`` (no ``.html``), ``/help`` for an
``index.html``, and ``/`` for the root.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SITE = "https://attune-rag.dev"
OUT = HERE / "sitemap.xml"

# Dirs that are not user-facing content.
_SKIP_PARTS = {"_vercel"}


def _url_path(rel: str) -> str:
    """Map a repo-relative ``*.html`` path to its served clean URL path."""
    stem = rel[:-5] if rel.endswith(".html") else rel  # drop .html
    if stem == "index":
        return "/"
    if stem.endswith("/index"):
        stem = stem[: -len("/index")]
    return "/" + stem


def main() -> int:
    paths = set()
    for f in sorted(HERE.rglob("*.html")):
        rel = f.relative_to(HERE).as_posix()
        if any(part in _SKIP_PARTS for part in Path(rel).parts):
            continue
        paths.add(_url_path(rel))

    urls = sorted(paths, key=lambda p: (p != "/", p))
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for p in urls:
        loc = SITE if p == "/" else SITE + p
        lines.append(f"  <url><loc>{escape(loc)}</loc></url>")
    lines.append("</urlset>")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(urls)} urls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
