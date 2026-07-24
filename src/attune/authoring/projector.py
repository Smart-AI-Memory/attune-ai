"""Deterministic projector: master file -> .help kinds + docs pages.

Part of the help-docs-single-source pilot (T2). Reads one
hand-authored "master file" per feature
(``content/features/<feature>.md`` in the consumer repo) and renders
it to the 11 ``.help`` kinds plus the 3 ``docs/`` feature pages. No
LLM, no AST render, no meta-templates: the master file's named H2
sections are sliced and concatenated per a fixed projection map, then
wrapped with the same frontmatter/footer the generator writes so
attune-help's HelpEngine and the staleness machinery read them
unchanged (DD2/R4).

``faq`` is the one transform (FG1 Phase 1, channel 4 only): the
``## FAQ seeds`` section's Q/A bullets are parsed and re-rendered as
an H2-per-question FAQ page rather than copied verbatim. The dynamic
channels (unmatched queries, telemetry, GitHub issues — D6) stay
deferred until real user signal exists.

See ``docs/specs/archive/help-docs-single-source/`` in attune-ai
(design.md, decisions.md D6/D7/D8, follow-ups.md FG1,
t2-projector-build.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import frontmatter

from attune.authoring.fact_check import Finding, check_polished_file
from attune.authoring.source_introspection import compute_scaffold_hash

# ---------------------------------------------------------------------------
# Projection map — the contract (design.md)
# ---------------------------------------------------------------------------

#: ``.help`` kind -> source H2 sections, in render order. A kind is
#: rendered only when *all* of its sections are present in the master
#: file; a missing section skips the kinds that depend on it. Every
#: kind is a verbatim section copy except ``faq``, which transforms
#: its seeds section (see ``_render_faq``, FG1 Phase 1).
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
    "faq": ["FAQ seeds"],
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
    #: Planned outputs whose on-disk file already matches modulo the
    #: ``generated_at`` stamp — left untouched so re-projection is
    #: idempotent (no timestamp churn in diffs).
    unchanged: list[Path] = field(default_factory=list)


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
    skip_kinds: tuple[str, ...] = (),
    dry_run: bool = False,
) -> ProjectionResult:
    """Project a feature's master file to ``.help`` kinds + docs pages.

    Renders the 11 ``.help`` kinds to
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
        if kind == "faq":
            body = _render_faq(master.sections["FAQ seeds"], result.warnings)
            if not body:
                result.skipped.append("faq (no parseable Q/A seeds)")
                continue
            slug_title = master.feature.replace("-", " ").replace("_", " ").title()
            kind_title = f"{slug_title} FAQ"
        else:
            body = _join_sections(master, titles)
            kind_title = title
        if kind == "concept" and (video := _video_meta(master)) is not None:
            url, video_title = video
            body = f"**Watch:** [{video_title}]({url})\n\n{body}"
        content = _wrap_help(
            master.feature, kind, source_hash, generated_help, body, title=kind_title
        )
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
            if out.path.exists():
                existing = out.path.read_text(encoding="utf-8")
                if normalize_generated_stamps(existing) == normalize_generated_stamps(out.content):
                    result.unchanged.append(out.path)
                    continue
            out.path.write_text(out.content, encoding="utf-8")
            result.written.append(out.path)

    return result


#: ``generated_at`` carriers in projected outputs: the ``.help`` YAML
#: frontmatter line and the docs-page HTML-comment footer field.
_FRONTMATTER_GENERATED_AT_RE = re.compile(r"^generated_at: .*$", re.M)
_FOOTER_GENERATED_AT_RE = re.compile(r" generated_at=[^ >]+")


def normalize_generated_stamps(text: str) -> str:
    """Return ``text`` with every ``generated_at`` stamp neutralized.

    Projection output is deterministic except for the render
    timestamp. Comparing two renders through this normalizer answers
    "same content?" — used by the idempotent write path (skip
    rewriting a file whose only difference would be the timestamp)
    and by the projection drift gate.
    """
    text = _FRONTMATTER_GENERATED_AT_RE.sub("generated_at: <stamp>", text)
    return _FOOTER_GENERATED_AT_RE.sub(" generated_at=<stamp>", text)


def check_projection_drift(
    project_root: str | Path,
    help_dir: str | Path,
    masters_dir: str | Path | None = None,
) -> list[str]:
    """Compare a dry-run projection of every master against disk.

    The drift gate for single-sourced features: re-renders each
    ``<masters_dir>/*.md`` master in memory and diffs every planned
    output against the committed file, ignoring ``generated_at``
    stamps. Returns one finding per drifted output — empty means the
    corpus is in lockstep with its masters (the guarantee `status:
    manual` features otherwise lack, since they are exempt from the
    LLM-freshness staleness check by design).

    Findings name the master, the output path, and whether the file
    is missing or differs, so the fix is always the one-liner
    ``python scripts/project_features.py <feature>``.
    """
    project_root = Path(project_root)
    help_dir = Path(help_dir)
    masters = Path(masters_dir) if masters_dir else project_root / "content" / "features"
    findings: list[str] = []
    for master in sorted(masters.glob("*.md")):
        result = project_feature(master, project_root, help_dir, dry_run=True)
        for out in result.outputs:
            rel = (
                out.path.relative_to(project_root)
                if out.path.is_relative_to(project_root)
                else out.path
            )
            if not out.path.exists():
                findings.append(f"{master.stem}: {rel} missing — re-run projection")
                continue
            on_disk = out.path.read_text(encoding="utf-8")
            if normalize_generated_stamps(on_disk) != normalize_generated_stamps(out.content):
                findings.append(f"{master.stem}: {rel} differs from its master — re-run projection")
    return findings


#: The two accepted seed-bullet shapes (FG1 Phase 1). Bold-Q is the
#: dominant corpus shape; italic-question is the known variant
#: (elicitation-forms.md). Checked in this order — the bold pattern
#: must win so ``**Q:**`` is never read as an italic span.
_SEED_BOLD_RE = re.compile(r"\*\*Q:?\*\*\s*(.+?)\s*\*\*A:?\*\*\s*(.+)", re.S)
_SEED_ITALIC_RE = re.compile(r"\*([^*].*?)\*\s*(.+)", re.S)


def _render_faq(seeds_body: str, warnings: list[str]) -> str:
    """Transform a ``## FAQ seeds`` section into an FAQ body.

    The one non-verbatim projection (FG1 Phase 1, channel 4 only):
    drops the section's leading blockquote disclaimer (channel-4
    framing for authors, not user-facing FAQ content), parses each
    ``- `` bullet as a Q/A seed in either accepted shape::

        - **Q:** question **A:** answer
        - *question* answer

    and renders one ``## question`` heading + answer paragraph per
    seed. A bullet matching neither shape records a projection
    warning and is skipped — never an error. Returns ``""`` when no
    seed parses (the caller records a skip).
    """
    bullets: list[str] = []
    for line in seeds_body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        if line.startswith("- "):
            bullets.append(line[2:].strip())
        elif line[:1].isspace() and bullets:
            bullets[-1] += "\n" + stripped
        else:
            warnings.append(f"faq: unrecognized FAQ seeds line skipped: {stripped[:60]!r}")

    parts: list[str] = []
    for bullet in bullets:
        match = _SEED_BOLD_RE.match(bullet) or _SEED_ITALIC_RE.match(bullet)
        if match is None:
            first_line = bullet.splitlines()[0]
            warnings.append(f"faq: unparseable Q/A seed skipped: {first_line[:60]!r}")
            continue
        question = " ".join(match.group(1).split())
        answer = match.group(2).strip()
        parts.append(f"## {question}\n\n{answer}")
    return "\n\n".join(parts)


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

    if (video := _video_meta(master)) is not None:
        url, video_title = video
        lines += [f"**Watch:** [{video_title}]({url})", ""]

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


def _video_meta(master: MasterFile) -> tuple[str, str] | None:
    """Return ``(url, title)`` from frontmatter ``video``, or ``None``.

    Accepts a bare URL string or a ``{url, title}`` mapping. A mapping
    without a ``url`` projects nothing (the field is optional and
    advisory — never an error).
    """
    raw = master.frontmatter.get("video")
    if isinstance(raw, str) and raw.strip():
        return raw.strip(), "Watch the video"
    if isinstance(raw, dict):
        url = str(raw.get("url") or "").strip()
        if url:
            title = str(raw.get("title") or "").strip() or "Watch the video"
            return url, title
    return None


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
