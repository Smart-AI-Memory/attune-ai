"""Deterministic projector: master file -> .help kinds + docs pages.

Part of the help-docs-single-source pilot (T2). Reads one
hand-authored "master file" per feature
(``content/features/<feature>.md`` in the consumer repo) and renders
it to the 10 non-faq ``.help`` kinds plus the 3 ``docs/`` feature
pages. No LLM, no AST render, no meta-templates: the master file's
named H2 sections are sliced and concatenated per a fixed projection
map, then wrapped with the same frontmatter/footer the generator
writes so attune-help's HelpEngine and the staleness machinery read
them unchanged (DD2/R4).

``faq`` is intentionally excluded (D7): the FAQ is a sourced
source-of-truth produced by the (still unbuilt) FAQ Generator from
four channels, not projected verbatim from the master file (D6).

See ``docs/specs/help-docs-single-source/`` in attune-ai
(design.md, decisions.md D6/D7/D8, t2-projector-build.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

from attune.authoring.fact_check import Finding, check_polished_file
from attune.authoring.source_introspection import compute_scaffold_hash

# ---------------------------------------------------------------------------
# Projection map — the contract (design.md), faq excluded per D7
# ---------------------------------------------------------------------------

#: ``.help`` kind -> source H2 sections, in render order. A kind is
#: rendered only when *all* of its sections are present in the master
#: file; a missing section skips the kinds that depend on it.
HELP_KIND_SECTIONS: dict[str, list[str]] = {
    "concept": ["Overview", "Concepts"],
    "reference": ["Reference"],
    "task": ["Tasks"],
    "quickstart": ["Quickstart"],
    "comparison": ["Comparison"],
    "error": ["Failure modes"],
    "troubleshooting": ["Failure modes"],
    "warning": ["Failure modes"],
    "note": ["Overview", "Concepts", "Notes & tips"],
    "tip": ["Notes & tips"],
    # "faq" intentionally excluded — D7 (FAQ Generator unbuilt)
}

#: ``docs/`` page (project-doc kind) -> source H2 sections.
#: ``tutorial`` is intentionally excluded (attune-ai decision D10): a
#: guided tutorial resists pure section projection — the projected
#: version is just the ``Tasks`` list verbatim, duplicating the how-to
#: — so tutorials stay hand-authored.
DOCS_PAGE_SECTIONS: dict[str, list[str]] = {
    "how-to": ["Quickstart", "Tasks", "Reference"],
    "architecture": ["Overview", "Concepts", "Design & extension"],
    "reference": ["Reference"],
}

#: Hub page (D11 / Variant 1). The "Start here" hero points to the
#: first present of these kinds; the remaining present site pages among
#: ``_HUB_CARD_ORDER`` form the card grid. ``tutorial`` is hero-only
#: (never a card) and ``concept`` is excluded entirely — it is a
#: ``.help`` kind with no site page.
_HUB_HERO_ORDER: tuple[str, ...] = ("tutorial", "how-to", "reference")
_HUB_CARD_ORDER: tuple[str, ...] = ("how-to", "reference", "architecture")

#: Human label + one-line blurb per site page kind, used by the hub's
#: hero callout and card grid.
_HUB_KIND_LABEL: dict[str, str] = {
    "tutorial": "Tutorial",
    "how-to": "How-to guide",
    "reference": "Reference",
    "architecture": "Architecture",
}
_HUB_KIND_BLURB: dict[str, str] = {
    "tutorial": "a guided, start-to-finish walkthrough",
    "how-to": "task recipes for common goals",
    "reference": "the full API and option reference",
    "architecture": "how it works and how to extend it",
}

#: Fallback ``docs/`` subdirectory per docs kind, used only when the
#: master file's ``nav.mkdocs`` mapping does not pin an explicit path.
#: Mirrors the generator's ``_PROJECT_DOC_KIND_SUBDIRS`` (note the
#: ``tutorial`` -> ``tutorials`` pluralization).
_DOCS_KIND_SUBDIRS: dict[str, str] = {
    "how-to": "how-to",
    "tutorial": "tutorials",
    "architecture": "architecture",
    "reference": "reference",
}

#: The 7 frontmatter keys attune-help's HelpEngine reads for a
#: ``.help`` template (output contract, DD2/R4). Kept here so the
#: projector and its test assert the same set, and so it matches the
#: generator's ``_render_template`` frontmatter exactly.
HELP_FRONTMATTER_KEYS = (
    "type",
    "name",
    "feature",
    "depth",
    "generated_at",
    "source_hash",
    "status",
)


@dataclass
class MasterFile:
    """A parsed master file.

    Attributes:
        feature: Feature name (from frontmatter ``feature``, else the
            file stem).
        frontmatter: The YAML frontmatter as a dict.
        sections: Ordered ``H2 title -> body markdown`` map, in the
            order the sections appear in the file.
    """

    feature: str
    frontmatter: dict
    sections: dict[str, str]


@dataclass
class ProjectedOutput:
    """One planned (or written) output — a ``.help`` kind or docs page.

    Carries the rendered ``content`` so callers (and the dry-run
    path) can inspect frontmatter/footer without touching disk.
    """

    kind: str
    target: str  # "help" | "docs"
    path: Path
    content: str


@dataclass
class ProjectionResult:
    written: list[Path] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    outputs: list[ProjectedOutput] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_master_file(path: str | Path) -> MasterFile:
    """Parse a master file into frontmatter + ordered H2 sections.

    Tolerates missing sections — the master-file schema lets a
    feature omit any section it doesn't need.
    """
    path = Path(path)
    post = frontmatter.load(str(path))
    meta = dict(post.metadata)
    sections = _split_h2_sections(post.content)
    feature = str(meta.get("feature") or path.stem)
    return MasterFile(feature=feature, frontmatter=meta, sections=sections)


def _split_h2_sections(body: str) -> dict[str, str]:
    """Split a markdown body into an ordered ``{H2 title: body}`` map.

    Only ``## `` headings *outside* fenced code blocks start a new
    section; a ``## `` line inside a ``` or ``~~~`` fence is body text,
    not a heading. Content before the first H2 is dropped (the
    master-file schema has no pre-section preamble). ``###`` and deeper
    headings stay inside their section's body.
    """
    sections: dict[str, str] = {}
    title: str | None = None
    lines: list[str] = []
    in_fence = False
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            if title is not None:
                sections[title] = "\n".join(lines).strip("\n")
            title = line[3:].strip()
            lines = []
            continue
        if title is not None:
            lines.append(line)
    if title is not None:
        sections[title] = "\n".join(lines).strip("\n")
    return sections


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def project_feature(
    master_path: str | Path,
    project_root: str | Path,
    help_dir: str | Path,
    *,
    skip_kinds: tuple[str, ...] = ("faq",),
    dry_run: bool = False,
) -> ProjectionResult:
    """Project a feature's master file to ``.help`` kinds + docs pages.

    Renders the 10 non-faq ``.help`` kinds to
    ``<help_dir>/templates/<feature>/<kind>.md`` (YAML frontmatter)
    and the 3 ``docs/`` pages to their ``nav.mkdocs`` paths under
    ``<project_root>/docs/`` (HTML-comment footer). ``source_hash`` is
    a single ``compute_scaffold_hash`` over the master file, shared by
    every output so they stay in lockstep.

    Also emits a Variant-1 **hub page** to
    ``<project_root>/docs/features/<feature>.md`` (kind ``"hub"``, D11):
    a "Start here" hero + a card grid over the feature's declared
    ``nav.mkdocs`` site pages. A feature with no ``nav.mkdocs`` pages
    records a ``"hub (no docs pages)"`` skip rather than emitting one.

    A kind whose source sections are not all present is recorded in
    ``result.skipped`` rather than written — never an error. With
    ``dry_run=True`` nothing is written; ``result.outputs`` still holds
    the full rendered content for inspection and ``result.written`` is
    empty.
    """
    master = parse_master_file(master_path)
    project_root = Path(project_root)
    help_dir = Path(help_dir)
    master_text = Path(master_path).read_text(encoding="utf-8")
    source_hash = compute_scaffold_hash(master_text)
    generated_help = datetime.now(timezone.utc).isoformat()
    generated_docs = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    result = ProjectionResult()

    title = _feature_title(master)

    for kind, titles in HELP_KIND_SECTIONS.items():
        if kind in skip_kinds:
            continue
        missing = [t for t in titles if t not in master.sections]
        if missing:
            result.skipped.append(f"{kind} (missing: {', '.join(missing)})")
            continue
        body = _join_sections(master, titles)
        content = _wrap_help(master.feature, kind, source_hash, generated_help, body, title=title)
        out_path = help_dir / "templates" / master.feature / f"{kind}.md"
        result.outputs.append(ProjectedOutput(kind, "help", out_path, content))

    for kind, titles in DOCS_PAGE_SECTIONS.items():
        if kind in skip_kinds:
            continue
        missing = [t for t in titles if t not in master.sections]
        if missing:
            result.skipped.append(f"docs/{kind} (missing: {', '.join(missing)})")
            continue
        body = _join_sections(master, titles)
        content = _wrap_docs(master.feature, kind, source_hash, generated_docs, body)
        out_path = _docs_output_path(master, kind, project_root)
        result.outputs.append(ProjectedOutput(kind, "docs", out_path, content))

    if "hub" not in skip_kinds:
        hub_content = _render_hub(master)
        if hub_content is None:
            result.skipped.append("hub (no docs pages)")
        else:
            hub_path = project_root / "docs" / "features" / f"{master.feature}.md"
            result.outputs.append(ProjectedOutput("hub", "docs", hub_path, hub_content))

    if not dry_run:
        for out in result.outputs:
            out.path.parent.mkdir(parents=True, exist_ok=True)
            out.path.write_text(out.content, encoding="utf-8")
            result.written.append(out.path)

    return result


def _join_sections(master: MasterFile, titles: list[str]) -> str:
    """Concatenate the named sections, each under its ``## `` heading."""
    parts: list[str] = []
    for title in titles:
        body = master.sections.get(title)
        if not body:
            continue
        parts.append(f"## {title}\n\n{body}")
    return "\n\n".join(parts)


def _render_hub(master: MasterFile) -> str | None:
    """Render the Variant-1 feature hub page (D11), or ``None``.

    The hub is the single front door + discovery surface for a feature
    (``docs/features/<feature>.md``). It leads with a "Start here" hero
    callout pointing to the first present of (tutorial, how-to,
    reference), then a Material card grid of the feature's remaining
    present site pages among (how-to, reference, architecture). The hero
    kind is not repeated as a card, and ``concept`` is excluded — it is a
    ``.help`` kind with no published page.

    Returns ``None`` when the master declares no ``nav.mkdocs`` site
    pages (the caller records a skip, never an error). Deterministic
    string render using only Material extensions attune-ai enables
    (``attr_list`` + ``md_in_html`` grid cards, ``admonition``) — no
    LLM, no AST (D3/D8).
    """
    nav = (master.frontmatter.get("nav") or {}).get("mkdocs") or {}
    present = [k for k in (*_HUB_HERO_ORDER, *_HUB_CARD_ORDER) if nav.get(k)]
    if not present:
        return None

    hero = next((k for k in _HUB_HERO_ORDER if k in present), None)
    cards = [k for k in _HUB_CARD_ORDER if k in present and k != hero]

    title = master.feature.replace("-", " ").replace("_", " ").title()
    lines: list[str] = [f"# {title}", ""]
    summary = master.frontmatter.get("summary")
    if summary and str(summary).strip():
        lines += [str(summary).strip(), ""]

    if hero is not None:
        lines += [
            '!!! tip "Start here"',
            "",
            f"    [{_HUB_KIND_LABEL[hero]}](../{nav[hero]}.md) — {_HUB_KIND_BLURB[hero]}.",
            "",
        ]

    if cards:
        lines += ['<div class="grid cards" markdown>', ""]
        for kind in cards:
            blurb = _HUB_KIND_BLURB[kind]
            label = _HUB_KIND_LABEL[kind]
            lines += [
                f"-   __{label}__",
                "",
                "    ---",
                "",
                f"    {blurb[0].upper()}{blurb[1:]}.",
                "",
                f"    [Open the {label.lower()}](../{nav[kind]}.md)",
                "",
            ]
        lines += ["</div>", ""]

    return "\n".join(lines).rstrip("\n") + "\n"


def _feature_title(master: MasterFile) -> str:
    """Human-readable H1 title for a feature's projected pages.

    Prefers the master file's frontmatter ``summary`` (the one-line
    feature description authors write); falls back to the title-cased
    feature slug, matching ``_wrap_docs``.
    """
    summary = master.frontmatter.get("summary")
    if summary and str(summary).strip():
        return str(summary).strip()
    return master.feature.replace("-", " ").replace("_", " ").title()


def _wrap_help(
    feature: str,
    kind: str,
    source_hash: str,
    generated_at: str,
    body: str,
    *,
    title: str,
) -> str:
    """Wrap a body with the ``.help`` YAML frontmatter the generator emits.

    The 7-key block matches ``generator._render_template`` exactly so
    attune-help's HelpEngine reads projected templates unchanged. An H1
    ``# {title}`` is prepended ahead of the body (mirroring
    ``_wrap_docs``) so downstream readers that key off the first H1 —
    e.g. attune-ai's ops dashboard ``_title_from_content`` — recover a
    real card title instead of degrading to ``<feature> / <kind>``.
    """
    name = f"{feature}-{kind}"
    block = (
        f"---\n"
        f"type: {kind}\n"
        f"name: {name}\n"
        f"feature: {feature}\n"
        f"depth: {kind}\n"
        f"generated_at: {generated_at}\n"
        f"source_hash: {source_hash}\n"
        f"status: generated\n"
        f"---\n"
    )
    result = f"{block}\n# {title}\n\n{body}"
    if not result.endswith("\n"):
        result += "\n"
    return result


def _wrap_docs(feature: str, kind: str, source_hash: str, generated_at: str, body: str) -> str:
    """Wrap a body with an H1 title and the ``attune-generated`` footer.

    The footer format matches ``generator._render_project_doc_template``
    so the staleness machinery (``parse_doc_footer``) reads it unchanged.
    """
    title = feature.replace("-", " ").replace("_", " ").title()
    footer = (
        f"\n<!-- attune-generated:"
        f" source_hash={source_hash}"
        f" feature={feature}"
        f" kind={kind}"
        f" generated_at={generated_at} -->"
    )
    result = f"# {title}\n\n{body}\n{footer}"
    if not result.endswith("\n"):
        result += "\n"
    return result


def _docs_output_path(master: MasterFile, kind: str, project_root: Path) -> Path:
    """Resolve a docs page's output path.

    Prefers the master file's ``nav.mkdocs[kind]`` (relative to
    ``docs/``, no extension); falls back to ``docs/<subdir>/<feature>.md``.
    """
    nav = (master.frontmatter.get("nav") or {}).get("mkdocs") or {}
    rel = nav.get(kind)
    if rel:
        return project_root / "docs" / f"{rel}.md"
    subdir = _DOCS_KIND_SUBDIRS.get(kind, kind)
    return project_root / "docs" / subdir / f"{master.feature}.md"


# ---------------------------------------------------------------------------
# Validation (warn-only for the pilot — DD4/R3)
# ---------------------------------------------------------------------------


def validate_master_file(master_path: str | Path, project_root: str | Path) -> list[Finding]:
    """Fact-check a master file, returning findings (warn-only).

    Runs the static fact-check pass (``python_refs`` / ``cli_refs`` /
    ``md_links`` / ``numeric_refs``) over the master file and, as an
    extra warning, flags whether ``import_repair`` would rewrite any
    example import to its canonical module path. The pilot never raises
    on findings — the caller decides what to do with them.
    """
    master_path = Path(master_path)
    project_root = Path(project_root)
    report = check_polished_file(master_path, project_root=project_root)
    findings = list(report.findings)
    repair_finding = _check_import_repair(master_path, project_root)
    if repair_finding is not None:
        findings.append(repair_finding)
    return findings


def _check_import_repair(master_path: Path, project_root: Path) -> Finding | None:
    """Return a warning Finding if ``import_repair`` would change the file.

    Build-time projection repairs mis-pathed example imports on every
    write; here we surface the same signal read-only against the master
    file. Best-effort: any failure (unresolved ``source_globs``, no
    matched sources) degrades to ``None``, matching the generator's
    opportunistic fact-check contract.
    """
    try:
        from attune.authoring.fact_check.import_repair import (
            build_symbol_module_map,
            repair_imports,
        )
        from attune.authoring.source_introspection import _extract_source_info

        meta = frontmatter.load(str(master_path)).metadata
        globs = meta.get("source_globs") or []
        matched: list[str] = []
        for pattern in globs:
            for candidate in project_root.glob(pattern):
                if candidate.is_file() and candidate.suffix == ".py":
                    matched.append(candidate.relative_to(project_root).as_posix())
        if not matched:
            return None
        source_info = _extract_source_info(matched, project_root)
        symbol_map = build_symbol_module_map(source_info)
        text = master_path.read_text(encoding="utf-8")
        if repair_imports(text, symbol_map) != text:
            return Finding(
                check="check_python_refs",
                severity="warning",
                location="(whole file)",
                message=(
                    "import_repair would rewrite one or more example imports to "
                    "their canonical module path; fix them in the master file."
                ),
            )
    except Exception:  # noqa: BLE001
        # INTENTIONAL: opportunistic, like the generator's fact-check
        # gate — a missing extra or unresolved glob must not break
        # validation.
        return None
    return None
