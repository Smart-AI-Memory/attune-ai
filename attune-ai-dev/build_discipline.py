#!/usr/bin/env python3
"""Render the Discipline article markdown into a branded static HTML page.

Re-runnable: edit `discipline/COLLABORATION_DISCIPLINE.md`, run this
script, and `discipline/index.html` regenerates. Brand tokens match
the landing page (attune-ai-dev/index.html) and smartaimemory.com.

Usage:
    python build_discipline.py [--draft-label "Draft v4"]

XSS-safe: markdown is rendered with html=False, so raw HTML in the
source is escaped rather than evaluated (defense in depth even though
the source is author-controlled).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from markdown_it import MarkdownIt
except ImportError:  # pragma: no cover - build-time dependency
    sys.stderr.write("markdown-it-py is required: pip install markdown-it-py\n")
    raise SystemExit(1) from None

HERE = Path(__file__).resolve().parent
BRAND_CSS = (HERE / "brand.css").read_text(encoding="utf-8")
SOURCE = HERE / "discipline" / "COLLABORATION_DISCIPLINE.md"
OUTPUT = HERE / "discipline" / "index.html"

PAGE_TITLE = "The Discipline of Agent Collaboration"
PAGE_DESC = (
    "A counter-thesis to vibe coding. Six mutual disciplines that turn "
    "AI-agent collaboration into work that ships, persists, and "
    "coordinates across packages."
)
CANONICAL = "https://attune-ai.dev/discipline"

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title}</title>
  <meta name="description" content="{desc}" />

  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:type" content="article" />
  <meta property="og:image" content="https://attune-ai.dev/og.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="canonical" href="{canonical}" />

  <style>{brand_css}</style>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="icon" href="/favicon.ico" sizes="32x32" />
  <script defer src="/_vercel/insights/script.js"></script>
</head>
<body>
  <div class="draft-banner">
    {banner_line}
    <a href="/">attune-ai.dev</a>
  </div>
  <article>
    <a class="home-link" href="/">&larr; attune-ai</a>
{body}
  </article>
  <footer>
    <span>Smart AI Memory</span>
    <span><a href="https://github.com/Smart-AI-Memory/attune-ai">GitHub</a>
      &nbsp;&middot;&nbsp;
      <a href="https://pypi.org/project/attune-ai/">PyPI</a></span>
  </footer>
</body>
</html>
"""


_ANCHOR_RE = re.compile(r'<a\s+href="([^"]*)"([^>]*)>')
_KEEP_PREFIX_RE = re.compile(r"^(/|https?://|#|mailto:|tel:)")


def _neutralize_relative_links(body_html: str) -> str:
    """Strip ``href`` from relative anchors that have no published target.

    The article's markdown links to repo-relative paths (``../specs/...``)
    that don't exist on the static site and would 404 on click. Absolute and
    external links are preserved; relative ones keep their text, lose the href.
    """

    def repl(match: re.Match[str]) -> str:
        href, rest = match.group(1), match.group(2)
        if _KEEP_PREFIX_RE.match(href):
            return match.group(0)
        return f"<a{rest}>"

    return _ANCHOR_RE.sub(repl, body_html)


def render(draft_label: str, published_label: str | None = None) -> str:
    """Render the source markdown into the branded HTML page.

    Args:
        draft_label: Draft marker (e.g. "Draft v5"); banner reads
            "<label> · final edits in progress".
        published_label: When set (e.g. "Revised 2026-07-02"), publish
            mode — the banner drops "final edits in progress" and shows
            only this label.
    """
    if not SOURCE.is_file():
        raise SystemExit(f"source not found: {SOURCE}")

    md_text = SOURCE.read_text(encoding="utf-8")

    md = MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table")
    body_html = _neutralize_relative_links(md.render(md_text))

    if published_label:
        banner_line = f"{published_label} &middot;"
    else:
        banner_line = f"{draft_label} &middot; final edits in progress &middot;"

    return TEMPLATE.format(
        brand_css=BRAND_CSS,
        title=PAGE_TITLE,
        desc=PAGE_DESC,
        canonical=CANONICAL,
        banner_line=banner_line,
        body=body_html,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Discipline article page.")
    parser.add_argument(
        "--draft-label",
        default="Draft v4",
        help="Draft marker shown in the banner (default: 'Draft v4').",
    )
    parser.add_argument(
        "--published",
        metavar="LABEL",
        default=None,
        help=(
            "Publish mode: replace the draft banner with this label "
            '(e.g. "Revised 2026-07-02") and drop "final edits in progress".'
        ),
    )
    args = parser.parse_args()

    html = render(args.draft_label, published_label=args.published)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
