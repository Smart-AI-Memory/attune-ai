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
    .start-here {
      border: 1px solid var(--primary); border-radius: 12px;
      background: var(--surface-low); padding: 1.1rem 1.3rem; margin: 0 0 1.75rem;
    }
    .start-here .sh-label {
      display: block; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em;
      text-transform: uppercase; color: var(--primary); margin-bottom: 0.6rem;
    }
    .start-here .sh-links { display: flex; flex-wrap: wrap; gap: 1.5rem; }
    .start-here .sh-item { text-decoration: none; color: var(--primary); font-weight: 700; }
    .start-here .sh-item:hover { text-decoration: underline; }
    .start-here .sh-item .sh-sub {
      display: block; color: var(--muted); font-size: 0.85rem; font-weight: 400;
    }
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
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <link rel="icon" href="/favicon.ico" sizes="32x32" />
  <script defer src="/_vercel/insights/script.js"></script>
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


_ANCHOR_RE = re.compile(r'<a\s+href="([^"]*)"([^>]*)>')
_KEEP_PREFIX_RE = re.compile(r"^(/|https?://|#|mailto:|tel:)")


def _neutralize_relative_links(body_html: str) -> str:
    """Strip ``href`` from corpus-relative anchors.

    The corpus markdown cross-references sibling templates with relative
    paths (``tasks/use-x.md``, ``concepts/y.md``, ``../specs/z/``) that have
    no equivalent in the published, flat-routed site (``/help/<feature>/<kind>``).
    Such links would 404 on click. Absolute (``/...``) and external
    (``https://``) links are preserved; relative ones keep their text but
    lose the dead href.
    """

    def repl(match: re.Match[str]) -> str:
        href, rest = match.group(1), match.group(2)
        if _KEEP_PREFIX_RE.match(href):
            return match.group(0)
        return f"<a{rest}>"

    return _ANCHOR_RE.sub(repl, body_html)


def _write_text(path: Path, text: str) -> None:
    """Write text with per-line trailing whitespace stripped + one final
    newline, so the generated files don't fight the trailing-whitespace /
    end-of-file pre-commit hooks on every rebuild."""
    cleaned = "\n".join(line.rstrip() for line in text.splitlines())
    path.write_text(cleaned + "\n", encoding="utf-8")


def _config():
    from attune.ops.config import Config, attune_home

    return Config(project_root=REPO_ROOT, attune_home=attune_home())


SITE_URL = "https://attune-ai.dev"

# Hand-authored narrative pages (tutorials, how-tos) live in the mkdocs
# docs site — a SEPARATE surface from this .help corpus, which projects
# only reference-style kinds. Without a bridge, the help system hides the
# hand-authored content entirely. Each feature page leads with a "Start
# here" hero linking to its tutorial / how-to when one exists (matched by
# slug against docs/{tutorials,how-to}/<feature>.md). Tutorial is listed
# first (preferred entry point). See docs/specs/help-docs-single-source/.
DOCS_URL = "https://smartaimemory.com/framework-docs"
_NARRATIVE_KINDS = (
    ("tutorials", "Tutorial", "a guided, start-to-finish walkthrough"),
    ("how-to", "How-to guide", "task recipes for common goals"),
)

# Some help-feature slugs differ from their narrative doc's slug. This
# curated map bridges those; each entry is hand-verified to point at the
# same-topic page. Exact-slug matches need no entry. Features with no
# entry and no exact match simply get no hero (no narrative authored yet).
_NARRATIVE_ALIASES = {
    "telemetry": {"how-to": "telemetry-and-signals"},
    "code-quality": {"how-to": "triage-code-quality"},
    "security-audit": {"how-to": "security-architecture"},
    "memory": {"how-to": "unified-memory-system"},
    "orchestration": {"how-to": "multi-agent-coordination"},
}


def _narrative_hero(feature: str) -> str:
    """Return a 'Start here' hero linking to hand-authored narrative docs.

    Matches ``feature`` against ``docs/tutorials/<slug>.md`` and
    ``docs/how-to/<slug>.md`` (slug = the feature name, or the
    ``_NARRATIVE_ALIASES`` override). Returns ``''`` when neither exists.
    """
    aliases = _NARRATIVE_ALIASES.get(feature, {})
    items = []
    for subdir, label, sub in _NARRATIVE_KINDS:
        slug = aliases.get(subdir, feature)
        if (REPO_ROOT / "docs" / subdir / f"{slug}.md").is_file():
            url = f"{DOCS_URL}/{subdir}/{slug}/"
            items.append(
                f'<a class="sh-item" href="{url}">{html.escape(label)}'
                f'<span class="sh-sub">{html.escape(sub)}</span></a>'
            )
    if not items:
        return ""
    return (
        '    <div class="start-here">\n'
        '      <span class="sh-label">Start here</span>\n'
        f'      <div class="sh-links">{"".join(items)}</div>\n'
        "    </div>\n"
    )


def _page(*, title: str, desc: str, crumbs: str, body: str, canonical: str) -> str:
    return (
        PAGE.replace("__TITLE__", html.escape(title, quote=True))
        .replace("__DESC__", html.escape(desc, quote=True))
        .replace("__CANONICAL__", html.escape(canonical, quote=True))
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
    body_html = _neutralize_relative_links(md.render(rec.body))
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
        canonical=f"{SITE_URL}/help/{feature}/{kind}",
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


def _build_feature_page(out: Path, feat, md: MarkdownIt) -> None:
    feature = feat.name
    tabs = "".join(f'<a href="/help/{feature}/{k}">{html.escape(k)}</a>' for k in feat.kinds)
    cards = "".join(
        f'<a class="feature-card" href="/help/{feature}/{k}">'
        f'<span class="fc-name">{html.escape(k)}</span></a>'
        for k in feat.kinds
    )
    body = (
        f'  <main class="help-home">\n'
        f"    <h1>{html.escape(_title_case(feature))}</h1>\n"
        f"{_narrative_hero(feature)}"
        f'    <p class="lede">{len(feat.kinds)} of {len(feat.kinds) + len(feat.missing_kinds)} '
        f"help kinds available.</p>\n"
        f'    <div class="kind-tabs">{tabs}</div>\n'
        f'    <div class="feature-grid">{cards}</div>\n'
        f"  </main>"
    )
    crumbs = _crumbs(("attune-ai", "/"), ("Help", "/help"), (_title_case(feature), None))
    page = _page(
        title=_title_case(feature),
        desc=f"{_title_case(feature)} — help, tasks, reference, and troubleshooting.",
        crumbs=crumbs,
        body=body,
        canonical=f"{SITE_URL}/help/{feature}",
    )
    (out / feature).mkdir(parents=True, exist_ok=True)
    _write_text(out / feature / "index.html", page)


def _build_landing(out: Path, features, helpd) -> None:
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
        canonical=f"{SITE_URL}/help",
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

    search_index: list[dict] = []
    n_pages = 0
    for feat in features:
        _build_feature_page(out, feat, md)
        for kind in feat.kinds:
            entry = _build_kind_page(out, helpd_mod, cfg, feat.name, kind, md)
            if entry:
                search_index.append(entry)
                n_pages += 1

    _build_landing(out, features, helpd_mod)
    (out / "search-index.json").write_text(
        json.dumps(search_index, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    _write_text(out / "search.js", SEARCH_JS)

    print(
        f"built {len(features)} features, {n_pages} kind pages, "
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
