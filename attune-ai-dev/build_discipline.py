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
import sys
from pathlib import Path

try:
    from markdown_it import MarkdownIt
except ImportError:  # pragma: no cover - build-time dependency
    sys.stderr.write("markdown-it-py is required: pip install markdown-it-py\n")
    raise SystemExit(1) from None

HERE = Path(__file__).resolve().parent
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

  <style>
    :root {{
      --primary: #004ac6;
      --bg: #f8f9ff;
      --ink: #0b1c30;
      --muted: #434655;
      --rule: #c3c6d7;
      --surface-low: #eff4ff;
      --surface-high: #dce9ff;
      --draft: #8a5a00;
      --draft-bg: #fff4e0;
      --draft-rule: #f0d49a;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0b1c30;
        --ink: #e8ecf5;
        --muted: #b7c8e1;
        --rule: #38485d;
        --surface-low: #132438;
        --surface-high: #213145;
        --primary: #6ea1ff;
        --draft: #f0c674;
        --draft-bg: #2a2310;
        --draft-rule: #4a3d18;
      }}
    }}

    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--ink); }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
      font-size: 18px;
      line-height: 1.65;
      -webkit-font-smoothing: antialiased;
    }}

    .draft-banner {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: var(--draft-bg);
      color: var(--draft);
      border-bottom: 1px solid var(--draft-rule);
      text-align: center;
      padding: 0.6rem 1rem;
      font-size: 0.85rem;
      font-weight: 600;
      letter-spacing: 0.02em;
    }}
    .draft-banner a {{ color: var(--draft); text-decoration: underline; }}

    article {{
      max-width: 42rem;
      margin: 0 auto;
      padding: 3.5rem 1.5rem 5rem;
    }}

    .home-link {{
      display: inline-block;
      margin-bottom: 2.5rem;
      color: var(--muted);
      text-decoration: none;
      font-size: 0.9rem;
    }}
    .home-link:hover {{ color: var(--primary); }}

    article h1 {{
      font-family: "Manrope", -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 2.6rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.1;
      margin: 0 0 1rem;
    }}
    article h2 {{
      font-family: "Manrope", -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 1.7rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.2;
      margin: 3.5rem 0 1rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--rule);
    }}
    article h3 {{
      font-size: 1.25rem;
      font-weight: 700;
      margin: 2.25rem 0 0.75rem;
    }}
    article h1 + blockquote {{
      margin-top: 0;
      font-size: 1.2rem;
      color: var(--muted);
    }}
    article p {{ margin: 0 0 1.3rem; }}
    article a {{ color: var(--primary); }}
    article strong {{ font-weight: 700; }}
    article em {{ font-style: italic; }}

    article blockquote {{
      margin: 1.5rem 0;
      padding: 0.5rem 0 0.5rem 1.25rem;
      border-left: 3px solid var(--primary);
      color: var(--muted);
      font-style: italic;
    }}
    article blockquote p {{ margin: 0 0 0.5rem; }}

    article ul, article ol {{ margin: 0 0 1.3rem; padding-left: 1.4rem; }}
    article li {{ margin: 0 0 0.5rem; }}

    article code {{
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, Menlo, monospace;
      font-size: 0.88em;
      background: var(--surface-high);
      padding: 0.12em 0.4em;
      border-radius: 4px;
    }}
    article pre {{
      background: var(--surface-low);
      border: 1px solid var(--rule);
      border-radius: 8px;
      padding: 1rem 1.25rem;
      overflow-x: auto;
      margin: 0 0 1.5rem;
      font-size: 0.85rem;
      line-height: 1.5;
    }}
    article pre code {{ background: none; padding: 0; }}

    article table {{
      width: 100%;
      border-collapse: collapse;
      margin: 0 0 1.5rem;
      font-size: 0.92rem;
    }}
    article th, article td {{
      text-align: left;
      padding: 0.55rem 0.75rem;
      border-bottom: 1px solid var(--rule);
      vertical-align: top;
    }}
    article th {{ font-weight: 700; }}

    article hr {{
      border: none;
      border-top: 1px solid var(--rule);
      margin: 2.5rem 0;
    }}

    footer {{
      max-width: 42rem;
      margin: 0 auto;
      padding: 2rem 1.5rem 4rem;
      border-top: 1px solid var(--rule);
      color: var(--muted);
      font-size: 0.85rem;
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.5rem;
    }}
    footer a {{ color: var(--muted); text-decoration: none; }}
    footer a:hover {{ color: var(--ink); }}

    @media (max-width: 480px) {{
      body {{ font-size: 17px; }}
      article {{ padding: 2.5rem 1.25rem 3rem; }}
      article h1 {{ font-size: 2rem; }}
      article h2 {{ font-size: 1.4rem; }}
    }}
  </style>
</head>
<body>
  <div class="draft-banner">
    {draft_label} &middot; final edits in progress &middot;
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


def render(draft_label: str) -> str:
    """Render the source markdown into the branded HTML page."""
    if not SOURCE.is_file():
        raise SystemExit(f"source not found: {SOURCE}")

    md_text = SOURCE.read_text(encoding="utf-8")

    md = MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table")
    body_html = md.render(md_text)

    return TEMPLATE.format(
        title=PAGE_TITLE,
        desc=PAGE_DESC,
        canonical=CANONICAL,
        draft_label=draft_label,
        body=body_html,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Discipline article page.")
    parser.add_argument(
        "--draft-label",
        default="Draft v4",
        help="Draft marker shown in the banner (default: 'Draft v4').",
    )
    args = parser.parse_args()

    html = render(args.draft_label)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
