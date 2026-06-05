#!/usr/bin/env python3
"""Render the ``.help/`` corpus into static help pages under ``help/``.

Re-runnable: regenerates ``attune-ai-dev/help/`` from the project's
``.help/templates/`` corpus. Reuses the ops dashboard's corpus loader
(``attune.ops.help_data``) and the same ``markdown-it-py`` renderer +
``brand.css`` the discipline page uses — no third parser/renderer
(see ``docs/specs/public-help-site/`` D1).

Build-time only: imports ``attune`` (installed in CI/dev). Vercel
serves the committed HTML as-is and never runs this script.

Usage:
    python build_help.py            # build into ./help/
    python build_help.py --check    # build to a temp dir, diff, fail on drift

XSS-safe: markdown rendered with ``html=False``; the corpus is
author-controlled but defense in depth is kept.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

try:
    from markdown_it import MarkdownIt
except ImportError:  # pragma: no cover - build-time dependency
    sys.stderr.write("markdown-it-py is required: pip install markdown-it-py\n")
    raise SystemExit(1) from None

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
BRAND_CSS = (HERE / "brand.css").read_text(encoding="utf-8")

# Help-specific layout on top of the shared brand tokens. Uses the
# same CSS variables (--primary, --rule, --surface-low/high, --muted).
HELP_CSS = """
    .help-nav {
      max-width: 60rem; margin: 0 auto;
      display: flex; align-items: center; justify-content: space-between;
      gap: 1rem; padding: 1.25rem 1.5rem; font-size: 0.9rem;
    }
    .help-nav .crumbs a { color: var(--muted); text-decoration: none; }
    .help-nav .crumbs a:hover { color: var(--primary); }
    .help-nav .crumbs .sep { color: var(--rule); margin: 0 0.4rem; }
    .help-nav .api-link { color: var(--primary); text-decoration: none; font-weight: 600; }
    main.help-home { max-width: 60rem; margin: 0 auto; padding: 1rem 1.5rem 5rem; }
    .help-home h1 {
      font-family: "Manrope", -apple-system, sans-serif;
      font-size: 2.4rem; font-weight: 800; letter-spacing: -0.03em;
      margin: 1rem 0 0.5rem;
    }
    .help-home .lede { color: var(--muted); font-size: 1.15rem; margin: 0 0 2rem; }
    .search-wrap { margin: 0 0 2.5rem; }
    #help-search {
      width: 100%; font-size: 1.05rem; padding: 0.85rem 1.1rem;
      border: 1px solid var(--rule); border-radius: 10px;
      background: var(--surface-low); color: var(--ink);
    }
    #help-search:focus { outline: 2px solid var(--primary); border-color: var(--primary); }
    #search-results { list-style: none; margin: 0.75rem 0 0; padding: 0; }
    #search-results li { margin: 0 0 0.4rem; }
    #search-results a {
      display: block; padding: 0.6rem 0.8rem; border-radius: 8px;
      text-decoration: none; color: var(--ink); border: 1px solid transparent;
    }
    #search-results a:hover { background: var(--surface-low); border-color: var(--rule); }
    #search-results .r-kind { color: var(--muted); font-size: 0.85rem; }
    #search-results .r-snip { color: var(--muted); font-size: 0.9rem; display: block; margin-top: 0.15rem; }
    .section-h {
      font-family: "Manrope", -apple-system, sans-serif;
      font-size: 1.3rem; font-weight: 700; margin: 2.5rem 0 1rem;
      padding-top: 1.25rem; border-top: 1px solid var(--rule);
    }
    .intent-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: 1rem; }
    .intent-card {
      display: block; padding: 1.1rem 1.2rem; border: 1px solid var(--rule);
      border-radius: 12px; text-decoration: none; color: var(--ink);
      background: var(--surface-low);
    }
    .intent-card:hover { border-color: var(--primary); }
    .intent-card .it-title { display: block; font-weight: 700; font-size: 1.05rem; }
    .intent-card .it-sub { display: block; color: var(--muted); font-size: 0.9rem; margin-top: 0.2rem; }
    .feature-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr)); gap: 0.85rem; }
    .feature-card {
      display: block; padding: 0.9rem 1.1rem; border: 1px solid var(--rule);
      border-radius: 10px; text-decoration: none; color: var(--ink);
    }
    .feature-card:hover { border-color: var(--primary); background: var(--surface-low); }
    .feature-card .fc-name { display: block; font-weight: 700; }
    .feature-card .fc-meta { display: block; color: var(--muted); font-size: 0.82rem; margin-top: 0.2rem; }
    .kind-tabs { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0 0 2rem; }
    .kind-tabs a {
      padding: 0.35rem 0.75rem; border: 1px solid var(--rule); border-radius: 999px;
      text-decoration: none; color: var(--muted); font-size: 0.88rem;
    }
    .kind-tabs a:hover { border-color: var(--primary); color: var(--primary); }
    .kind-tabs a.current { background: var(--primary); color: #fff; border-color: var(--primary); }
    @media (max-width: 480px) {
      .help-home h1 { font-size: 1.9rem; }
    }
"""

# A short human label for each intent group.
INTENT_LABELS = {
    "do": ("Do something", "tasks &amp; quickstarts"),
    "solve": ("Solve a problem", "troubleshooting, errors, FAQ"),
    "understand": ("Understand a concept", "how it works"),
    "lookup": ("Look something up", "reference"),
}

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>__TITLE__</title>
  <meta name="description" content="__DESC__" />
  <meta property="og:title" content="__TITLE__" />
  <meta property="og:description" content="__DESC__" />
  <meta property="og:type" content="website" />
  <link rel="canonical" href="__CANONICAL__" />
  <style>__CSS__</style>
</head>
<body>
  <nav class="help-nav">
    <span class="crumbs">__CRUMBS__</span>
    <a class="api-link" href="https://smartaimemory.com/framework-docs/"
      >API &amp; contributor docs &rarr;</a>
  </nav>
__BODY__
  <footer>
    <span>Smart AI Memory</span>
    <span><a href="https://github.com/Smart-AI-Memory/attune-ai">GitHub</a>
      &nbsp;&middot;&nbsp;
      <a href="https://pypi.org/project/attune-ai/">PyPI</a></span>
  </footer>
</body>
</html>
"""


def _md() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table")


def _write_text(path: Path, text: str) -> None:
    """Write text with per-line trailing whitespace stripped + one final
    newline, so the generated files don't fight the trailing-whitespace /
    end-of-file pre-commit hooks on every rebuild."""
    cleaned = "\n".join(line.rstrip() for line in text.splitlines())
    path.write_text(cleaned + "\n", encoding="utf-8")


def _config():
    from attune.ops.config import Config, attune_home

    return Config(project_root=REPO_ROOT, attune_home=attune_home())


def _page(*, title: str, desc: str, crumbs: str, body: str) -> str:
    return (
        PAGE.replace("__TITLE__", html.escape(title, quote=True))
        .replace("__DESC__", html.escape(desc, quote=True))
        .replace("__CANONICAL__", "https://attune-ai.dev/help")
        .replace("__CSS__", BRAND_CSS + HELP_CSS)
        .replace("__CRUMBS__", crumbs)
        .replace("__BODY__", body)
    )


def _crumbs(*parts: tuple[str, str | None]) -> str:
    """Build a breadcrumb trail from (label, href|None) pairs."""
    out = []
    for label, href in parts:
        label_e = html.escape(label)
        if href:
            out.append(f'<a href="{href}">{label_e}</a>')
        else:
            out.append(f"<span>{label_e}</span>")
    return '<span class="sep">&rsaquo;</span>'.join(out)


def _title_case(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def _first_para(body: str, *, max_chars: int = 200) -> str:
    """Plain-text first paragraph of a markdown body (for search snippets)."""
    for block in body.split("\n\n"):
        line = " ".join(block.split())
        if line and not line.startswith("#"):
            return line[:max_chars]
    return ""


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------


def _build_kind_page(out: Path, helpd, cfg, feature: str, kind: str, md: MarkdownIt) -> dict | None:
    rec = helpd.get_template(cfg, feature, kind)
    if rec is None:
        return None
    body_html = md.render(rec.body)
    title = rec.title or _title_case(feature)
    page_body = f'  <article class="markdown-body">\n{body_html}\n  </article>'
    crumbs = _crumbs(
        ("attune-ai", "/"),
        ("Help", "/help"),
        (_title_case(feature), f"/help/{feature}"),
        (kind, None),
    )
    page = _page(
        title=f"{title} — {kind}",
        desc=_first_para(rec.body) or f"{title} {kind} reference.",
        crumbs=crumbs,
        body=page_body,
    )
    _write_text(out / feature / f"{kind}.html", page)
    return {
        "title": title,
        "feature": feature,
        "kind": kind,
        "url": f"/help/{feature}/{kind}",
        "keywords": " ".join(
            sorted({feature, kind, *title.lower().split(), *_first_para(rec.body).lower().split()})
        ),
        "snippet": _first_para(rec.body, max_chars=160),
    }


def _build_feature_page(out: Path, feat, md: MarkdownIt, guides: list[Guide] = ()) -> None:
    feature = feat.name
    tabs = "".join(f'<a href="/help/{feature}/{k}">{html.escape(k)}</a>' for k in feat.kinds)
    cards = "".join(
        f'<a class="feature-card" href="/help/{feature}/{k}">'
        f'<span class="fc-name">{html.escape(k)}</span></a>'
        for k in feat.kinds
    )
    # Migrated hand-written guides (tutorial / how-to) for this feature.
    guides_block = ""
    if guides:
        gtabs = "".join(
            f'<a href="{g.url}">{html.escape(g.source)}</a>'
            for g in sorted(guides, key=lambda g: g.source)
        )
        guides_block = (
            '    <div class="section-h">Guides</div>\n'
            f'    <div class="kind-tabs">{gtabs}</div>\n'
        )
    body = (
        f'  <main class="help-home">\n'
        f"    <h1>{html.escape(_title_case(feature))}</h1>\n"
        f'    <p class="lede">{len(feat.kinds)} of {len(feat.kinds) + len(feat.missing_kinds)} '
        f"help kinds available.</p>\n"
        f'    <div class="kind-tabs">{tabs}</div>\n'
        f'    <div class="feature-grid">{cards}</div>\n'
        f"{guides_block}"
        f"  </main>"
    )
    crumbs = _crumbs(("attune-ai", "/"), ("Help", "/help"), (_title_case(feature), None))
    page = _page(
        title=_title_case(feature),
        desc=f"{_title_case(feature)} — help, tasks, reference, and troubleshooting.",
        crumbs=crumbs,
        body=body,
    )
    (out / feature).mkdir(parents=True, exist_ok=True)
    _write_text(out / feature / "index.html", page)


def _build_landing(
    out: Path, features, helpd, *, has_guides: bool = False, has_install: bool = False
) -> None:
    intent_cards = ""
    for intent, (label, sub) in INTENT_LABELS.items():
        # Link to the first feature that has a kind in this intent group.
        kinds = helpd.INTENT_GROUPS.get(intent, ())
        target = next(
            (f"/help/{f.name}/{k}" for f in features for k in kinds if k in f.kinds),
            "/help",
        )
        intent_cards += (
            f'<a class="intent-card" href="{target}">'
            f'<span class="it-title">{label}</span>'
            f'<span class="it-sub">{sub}</span></a>'
        )
    feature_cards = "".join(
        f'<a class="feature-card" href="/help/{f.name}">'
        f'<span class="fc-name">{html.escape(_title_case(f.name))}</span>'
        f'<span class="fc-meta">{len(f.kinds)} kinds</span></a>'
        for f in features
    )
    quick = []
    if has_install:
        quick.append(
            '<a class="intent-card" href="/help/installation">'
            '<span class="it-title">Install attune</span>'
            '<span class="it-sub">pip, providers, Redis</span></a>'
        )
    if has_guides:
        quick.append(
            '<a class="intent-card" href="/help/guides">'
            '<span class="it-title">Guides</span>'
            '<span class="it-sub">cross-cutting tutorials &amp; how-tos</span></a>'
        )
    quick_block = (
        '    <div class="section-h">Start here</div>\n'
        f'    <div class="intent-row">{"".join(quick)}</div>\n'
        if quick
        else ""
    )
    body = (
        '  <main class="help-home">\n'
        "    <h1>attune help</h1>\n"
        '    <p class="lede">Learn, do, solve, and look things up — generated from the '
        "live attune codebase.</p>\n"
        '    <div class="search-wrap">\n'
        '      <input id="help-search" type="search" placeholder="Search help…" '
        'autocomplete="off" />\n'
        '      <ul id="search-results"></ul>\n'
        "    </div>\n"
        f"{quick_block}"
        '    <div class="section-h">Browse by what you need</div>\n'
        f'    <div class="intent-row">{intent_cards}</div>\n'
        '    <div class="section-h">All features</div>\n'
        f'    <div class="feature-grid">{feature_cards}</div>\n'
        '    <script src="/help/search.js" defer></script>\n'
        "  </main>"
    )
    crumbs = _crumbs(("attune-ai", "/"), ("Help", None))
    page = _page(
        title="attune help",
        desc="Browse and search the attune help corpus — tasks, concepts, "
        "reference, and troubleshooting for every feature.",
        crumbs=crumbs,
        body=body,
    )
    _write_text(out / "index.html", page)


SEARCH_JS = """// Client-side help search over the static index (no server).
(function () {
  var input = document.getElementById("help-search");
  var results = document.getElementById("search-results");
  if (!input || !results) return;
  var index = [];
  fetch("/help/search-index.json").then(function (r) { return r.json(); })
    .then(function (data) { index = data; });
  function tokens(s) { return s.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean); }
  function render(hits) {
    results.innerHTML = hits.map(function (h) {
      return '<li><a href="' + h.url + '"><strong>' + h.title +
        '</strong> <span class="r-kind">' + h.feature + " / " + h.kind +
        '</span><span class="r-snip">' + (h.snippet || "") + "</span></a></li>";
    }).join("");
  }
  input.addEventListener("input", function () {
    var q = tokens(input.value);
    if (!q.length) { results.innerHTML = ""; return; }
    var scored = index.map(function (it) {
      var feat = (it.feature || "").toLowerCase();
      var title = (it.title || "").toLowerCase();
      var kw = (it.keywords || "").toLowerCase();
      // Weight: feature-name match >> title match > body keyword.
      var score = q.reduce(function (acc, t) {
        return acc + (feat.indexOf(t) >= 0 ? 3 : 0) +
          (title.indexOf(t) >= 0 ? 2 : 0) + (kw.indexOf(t) >= 0 ? 1 : 0);
      }, 0);
      return { it: it, score: score };
    }).filter(function (x) { return x.score > 0; });
    // Sort by score desc, then prefer concept/quickstart kinds, then title.
    var order = { concept: 0, quickstart: 1, task: 2, reference: 3 };
    scored.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      var ak = order[a.it.kind] === undefined ? 9 : order[a.it.kind];
      var bk = order[b.it.kind] === undefined ? 9 : order[b.it.kind];
      return ak - bk;
    });
    render(scored.slice(0, 20).map(function (x) { return x.it; }));
  });
})();
"""


# ---------------------------------------------------------------------------
# Hand-written guide migration (docs/tutorials + docs/how-to)  [PR-B]
#
# The MIGRATION SET below is config, not logic — prune it in review.
# See docs/specs/public-help-site/pr-b-plan.md for the rationale.
# ---------------------------------------------------------------------------

# (source-label, dir-relative-to-repo-root) — both dirs are scanned.
GUIDE_DIRS: tuple[tuple[str, str], ...] = (
    ("tutorial", "docs/tutorials"),
    ("how-to", "docs/how-to"),
)

# Stems that STAY in mkdocs (maintainer/internal) or are stubs the
# generated landing replaces. Matched by filename stem (any dir).
GUIDE_EXCLUDE_STEMS: frozenset[str] = frozenset(
    {
        "help-system-maintenance",  # maintainer: corpus freshness
        "learning-and-patterns",  # maintainer: session evaluator
        "index",  # stub landing pages (replaced)
        "installation",  # handled separately via INSTALL_SOURCE
    }
)

# Topic-based feature merges for guides whose stem doesn't equal a
# feature slug exactly (judgment calls — confirm in review). Keys are
# normalized stems (lowercased, underscores->hyphens).
GUIDE_FEATURE_MAP: dict[str, str] = {
    "security-architecture": "security-audit",
    "unified-memory-system": "memory",
    "memory-graph": "memory",
    "meta-orchestration-tutorial": "orchestration",
    "agent-factory": "agents",
    "triage-code-quality": "code-quality",
    "resilience-patterns": "resilience",
    "telemetry-and-signals": "telemetry",
}

# Install guide migrated as a standalone /help/installation page.
INSTALL_SOURCE = "docs/getting-started/installation.md"


class Guide(NamedTuple):
    source: str  # "tutorial" | "how-to"
    slug: str  # normalized stem
    title: str
    body: str  # markdown, frontmatter + mkdocs-isms stripped
    feature: str | None  # matched feature slug, or None (orphan)
    url: str


def _strip_frontmatter(text: str) -> str:
    m = re.match(r"\A---\s*\n.*?\n---\s*\n(.*)\Z", text, re.DOTALL)
    return m.group(1) if m else text


def _doc_title(body: str, slug: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return _title_case(slug)


_TAB_RE = re.compile(r'^={3,}\s+"(.+?)"\s*$')


def _strip_mkdocs_isms(text: str) -> tuple[str, int]:
    """Convert mkdocs-specific markup that markdown-it can't parse:
    admonitions (``!!!`` / ``???``), fenced divs (``:::``), and
    ``pymdownx.tabbed`` tabs (``=== "Title"`` with a 4-space-indented
    body). Tabs become ``#### Title`` headings with their bodies
    de-indented so fenced code inside them renders. Counts what it
    touched so anything unexpected surfaces in the build log."""
    out_lines: list[str] = []
    touched = 0
    in_tab = False
    for line in text.splitlines():
        s = line.lstrip()
        m = _TAB_RE.match(s)
        if m:
            touched += 1
            out_lines.extend([f"#### {m.group(1)}", ""])
            in_tab = True
            continue
        if s.startswith(":::"):
            touched += 1
            continue  # drop fenced-div markers
        if s.startswith("!!! ") or s.startswith("??? "):
            touched += 1
            label = s.split('"')[1] if '"' in s else s.split(maxsplit=2)[1].title()
            out_lines.append(f"**{label}**")
            in_tab = False
            continue
        if in_tab:
            if line.strip() == "":
                out_lines.append("")
                continue
            if line.startswith("    "):
                out_lines.append(line[4:])  # de-indent one tab level
                continue
            in_tab = False  # dedented content ends the tab block
        out_lines.append(line)
    return "\n".join(out_lines), touched


def _collect_guides(
    repo_root: Path, feature_slugs: set[str]
) -> tuple[dict[str, list[Guide]], list[Guide], int]:
    """Scan the guide dirs → (by_feature, orphans, mkdocs_isms_touched)."""
    by_feature: dict[str, list[Guide]] = {}
    orphans: list[Guide] = []
    isms = 0
    for source, rel in GUIDE_DIRS:
        d = repo_root / rel
        if not d.is_dir():
            continue
        for md_path in sorted(d.glob("*.md")):
            stem = md_path.stem
            if stem in GUIDE_EXCLUDE_STEMS:
                continue
            norm = stem.lower().replace("_", "-")
            raw = md_path.read_text(encoding="utf-8", errors="replace")
            body, touched = _strip_mkdocs_isms(_strip_frontmatter(raw))
            isms += touched
            title = _doc_title(body, norm)
            if norm in feature_slugs:
                feature = norm
            elif norm in GUIDE_FEATURE_MAP:
                feature = GUIDE_FEATURE_MAP[norm]
            else:
                feature = None
            if feature:
                url = f"/help/{feature}/{source}"
            else:
                url = f"/help/guides/{norm}"
            guide = Guide(source, norm, title, body, feature, url)
            if feature:
                by_feature.setdefault(feature, []).append(guide)
            else:
                orphans.append(guide)
    return by_feature, orphans, isms


def _guide_search_entry(guide: Guide) -> dict:
    return {
        "title": guide.title,
        "feature": guide.feature or "guides",
        "kind": guide.source,
        "url": guide.url,
        "keywords": " ".join(
            sorted({guide.feature or "guides", guide.source, *guide.title.lower().split()})
        ),
        "snippet": _first_para(guide.body, max_chars=160),
    }


def _build_guide_page(out: Path, guide: Guide, md: MarkdownIt) -> dict:
    body_html = md.render(guide.body)
    page_body = f'  <article class="markdown-body">\n{body_html}\n  </article>'
    if guide.feature:
        crumbs = _crumbs(
            ("attune-ai", "/"),
            ("Help", "/help"),
            (_title_case(guide.feature), f"/help/{guide.feature}"),
            (guide.source, None),
        )
        dest = out / guide.feature / f"{guide.source}.html"
    else:
        crumbs = _crumbs(
            ("attune-ai", "/"),
            ("Help", "/help"),
            ("Guides", "/help/guides"),
            (guide.title, None),
        )
        dest = out / "guides" / f"{guide.slug}.html"
    page = _page(
        title=f"{guide.title} — {guide.source}",
        desc=_first_para(guide.body) or guide.title,
        crumbs=crumbs,
        body=page_body,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    _write_text(dest, page)
    return _guide_search_entry(guide)


def _build_guides_index(out: Path, orphans: list[Guide]) -> None:
    cards = "".join(
        f'<a class="feature-card" href="{g.url}">'
        f'<span class="fc-name">{html.escape(g.title)}</span>'
        f'<span class="fc-meta">{g.source}</span></a>'
        for g in sorted(orphans, key=lambda g: g.title.lower())
    )
    body = (
        '  <main class="help-home">\n'
        "    <h1>Guides</h1>\n"
        '    <p class="lede">Cross-cutting tutorials and how-tos that '
        "span more than one feature.</p>\n"
        f'    <div class="feature-grid">{cards}</div>\n'
        "  </main>"
    )
    crumbs = _crumbs(("attune-ai", "/"), ("Help", "/help"), ("Guides", None))
    page = _page(
        title="Guides — attune help",
        desc="Cross-cutting tutorials and how-tos for attune.",
        crumbs=crumbs,
        body=body,
    )
    (out / "guides").mkdir(parents=True, exist_ok=True)
    _write_text(out / "guides" / "index.html", page)


def _build_install_page(out: Path, repo_root: Path, md: MarkdownIt) -> dict | None:
    src = repo_root / INSTALL_SOURCE
    if not src.is_file():
        return None
    raw = src.read_text(encoding="utf-8", errors="replace")
    body_md, _ = _strip_mkdocs_isms(_strip_frontmatter(raw))
    title = _doc_title(body_md, "installation")
    body_html = md.render(body_md)
    page = _page(
        title=f"{title} — attune help",
        desc=_first_para(body_md) or "Install and configure attune-ai.",
        crumbs=_crumbs(("attune-ai", "/"), ("Help", "/help"), ("Installation", None)),
        body=f'  <article class="markdown-body">\n{body_html}\n  </article>',
    )
    _write_text(out / "installation.html", page)
    return {
        "title": title,
        "feature": "installation",
        "kind": "guide",
        "url": "/help/installation",
        "keywords": "install installation setup pip configure redis getting started",
        "snippet": _first_para(body_md, max_chars=160),
    }


def build(out: Path, cfg=None) -> int:
    helpd_mod = __import__("attune.ops.help_data", fromlist=["help_data"])
    cfg = cfg if cfg is not None else _config()
    md = _md()

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    features = helpd_mod.list_features(cfg)
    if not features:
        sys.stderr.write(f"no features found under {helpd_mod.corpus_root(cfg)}\n")
        return 1

    # Second source (PR-B): hand-written tutorials + how-tos.
    feature_slugs = {f.name for f in features}
    guides_by_feature, orphan_guides, isms = _collect_guides(cfg.project_root, feature_slugs)

    search_index: list[dict] = []
    n_pages = 0
    for feat in features:
        feat_guides = guides_by_feature.get(feat.name, [])
        _build_feature_page(out, feat, md, feat_guides)
        for kind in feat.kinds:
            entry = _build_kind_page(out, helpd_mod, cfg, feat.name, kind, md)
            if entry:
                search_index.append(entry)
                n_pages += 1
        for guide in feat_guides:
            search_index.append(_build_guide_page(out, guide, md))

    for guide in orphan_guides:
        search_index.append(_build_guide_page(out, guide, md))
    if orphan_guides:
        _build_guides_index(out, orphan_guides)

    install_entry = _build_install_page(out, cfg.project_root, md)
    if install_entry:
        search_index.append(install_entry)

    n_guides = sum(len(v) for v in guides_by_feature.values()) + len(orphan_guides)
    _build_landing(
        out,
        features,
        helpd_mod,
        has_guides=bool(orphan_guides),
        has_install=install_entry is not None,
    )
    (out / "search-index.json").write_text(
        json.dumps(search_index, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    _write_text(out / "search.js", SEARCH_JS)

    if isms:
        print(f"  note: stripped {isms} mkdocs admonition/fence markers from guides")
    print(
        f"built {len(features)} features, {n_pages} kind pages, "
        f"{n_guides} guides ({len(orphan_guides)} orphan), "
        f"{len(search_index)} search entries -> {out}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the public help site.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Build to a temp dir and diff against help/; exit 1 on drift.",
    )
    args = parser.parse_args()

    target = HERE / "help"
    if not args.check:
        return build(target)

    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / "help"
        rc = build(scratch)
        if rc != 0:
            return rc
        # Compare file sets + contents.
        drift = _diff_trees(target, scratch)
        if drift:
            sys.stderr.write("help/ is out of date — run build_help.py:\n")
            for line in drift:
                sys.stderr.write(f"  {line}\n")
            return 1
        print("help/ is up to date")
        return 0


def _diff_trees(a: Path, b: Path) -> list[str]:
    if not a.exists():
        return ["help/ does not exist"]
    a_files = {p.relative_to(a) for p in a.rglob("*") if p.is_file()}
    b_files = {p.relative_to(b) for p in b.rglob("*") if p.is_file()}
    drift = []
    for missing in sorted(b_files - a_files):
        drift.append(f"missing: {missing}")
    for extra in sorted(a_files - b_files):
        drift.append(f"stale: {extra}")
    for common in sorted(a_files & b_files):
        if (a / common).read_bytes() != (b / common).read_bytes():
            drift.append(f"changed: {common}")
    return drift


if __name__ == "__main__":
    raise SystemExit(main())
