"""Tests for the deterministic master-file projector (T2).

See ``docs/specs/help-docs-single-source/t2-projector-build.md`` in
attune-ai. The fixture mirrors attune-ai's
``content/features/spec-engine.md`` (merged in attune-ai #960) so the
test is hermetic and runnable in attune-author CI.
"""

from __future__ import annotations

from pathlib import Path

from attune.authoring.projector import (
    DOCS_PAGE_SECTIONS,
    HELP_FRONTMATTER_KEYS,
    HELP_KIND_SECTIONS,
    parse_master_file,
    project_feature,
    validate_master_file,
)

FIXTURE = Path(__file__).parent / "fixtures" / "spec-engine.md"

#: The 10 H2 sections the spec-engine master file declares, in order.
MASTER_SECTIONS = [
    "Overview",
    "Concepts",
    "Quickstart",
    "Tasks",
    "Reference",
    "Comparison",
    "Failure modes",
    "FAQ seeds",
    "Notes & tips",
    "Design & extension",
]


def _parse_help_frontmatter(content: str) -> dict[str, str]:
    """Pull the leading ``---`` frontmatter block into a flat dict."""
    assert content.startswith("---\n")
    _, block, _ = content.split("---\n", 2)
    out: dict[str, str] = {}
    for line in block.strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def _help_body(content: str) -> str:
    """Return the markdown body after the leading ``---`` frontmatter."""
    assert content.startswith("---\n")
    _, _, body = content.split("---\n", 2)
    return body.lstrip("\n")


# --- parse_master_file ------------------------------------------------------


def test_parse_master_file_yields_all_sections():
    master = parse_master_file(FIXTURE)
    assert master.feature == "spec-engine"
    assert list(master.sections.keys()) == MASTER_SECTIONS
    assert len(master.sections) == 10
    # Bodies are captured, not just headings.
    assert "spec engine" in master.sections["Overview"].lower()
    assert "| Type |" in master.sections["Concepts"]


def test_parse_ignores_h2_inside_code_fences():
    # The Tasks section is heavy with fenced python; none of its
    # in-fence lines should have spawned phantom sections.
    master = parse_master_file(FIXTURE)
    assert list(master.sections.keys()) == MASTER_SECTIONS


# --- project_feature: planning ---------------------------------------------


def test_dry_run_plans_eleven_help_kinds_and_three_docs(tmp_path):
    result = project_feature(FIXTURE, tmp_path, tmp_path / ".help", dry_run=True)
    help_outputs = [o for o in result.outputs if o.target == "help"]
    docs_outputs = [o for o in result.outputs if o.target == "docs" and o.kind != "hub"]
    hub_outputs = [o for o in result.outputs if o.kind == "hub"]

    assert len(help_outputs) == 11
    assert len(docs_outputs) == 3
    # The hub is additive — exactly one per feature with docs pages.
    assert len(hub_outputs) == 1
    assert {o.kind for o in help_outputs} == set(HELP_KIND_SECTIONS)
    assert {o.kind for o in docs_outputs} == set(DOCS_PAGE_SECTIONS)
    # faq IS planned when "## FAQ seeds" is present (FG1 Phase 1).
    assert "faq" in {o.kind for o in help_outputs}
    # tutorial is never projected (D10) — hand-authored.
    assert "tutorial" not in {o.kind for o in docs_outputs}
    # dry-run writes nothing.
    assert result.written == []
    assert not any(tmp_path.rglob("*.md"))


def test_help_frontmatter_has_seven_keys_and_depth_equals_kind(tmp_path):
    result = project_feature(FIXTURE, tmp_path, tmp_path / ".help", dry_run=True)
    for out in result.outputs:
        if out.target != "help":
            continue
        fm = _parse_help_frontmatter(out.content)
        assert set(fm) == set(HELP_FRONTMATTER_KEYS)
        assert fm["depth"] == out.kind
        assert fm["type"] == out.kind
        assert fm["name"] == f"spec-engine-{out.kind}"
        assert fm["feature"] == "spec-engine"
        assert fm["status"] == "generated"
        assert fm["source_hash"]  # non-empty


def test_help_body_opens_with_h1_title(tmp_path):
    # Every projected .help body must open with an `# H1` so attune-ai's
    # ops dashboard (_title_from_content) recovers a real card title
    # instead of degrading to "<feature> / <kind>" (P1).
    result = project_feature(FIXTURE, tmp_path, tmp_path / ".help", dry_run=True)
    help_outputs = [o for o in result.outputs if o.target == "help"]
    assert help_outputs
    for out in help_outputs:
        body = _help_body(out.content)
        first_line = body.splitlines()[0]
        assert first_line.startswith("# ")
        assert not first_line.startswith("## ")
        if out.kind == "faq":
            # The faq H1 is "<Feature> FAQ", matching the hand-authored
            # FAQ pages it replaces (FG1 Phase 1).
            assert first_line == "# Spec Engine FAQ"
        else:
            # The H1 is the feature summary (frontmatter), not the slug.
            assert first_line == "# Spec-driven development with approval loops"


def test_docs_pages_carry_footer(tmp_path):
    result = project_feature(FIXTURE, tmp_path, tmp_path / ".help", dry_run=True)
    # The hub is a nav surface, not a staleness-tracked projection — it
    # carries no footer (asserted separately).
    docs = [o for o in result.outputs if o.target == "docs" and o.kind != "hub"]
    assert docs
    for out in docs:
        assert "<!-- attune-generated:" in out.content
        assert "feature=spec-engine" in out.content
        assert f"kind={out.kind}" in out.content
        # No YAML frontmatter on docs pages.
        assert not out.content.startswith("---\n")


# --- project_feature: writing ----------------------------------------------


def test_project_feature_writes_to_disk(tmp_path):
    help_dir = tmp_path / ".help"
    result = project_feature(FIXTURE, tmp_path, help_dir, dry_run=False)

    assert len(result.written) == 15
    assert (help_dir / "templates" / "spec-engine" / "concept.md").exists()
    assert (help_dir / "templates" / "spec-engine" / "reference.md").exists()
    # docs land at their nav.mkdocs paths.
    assert (tmp_path / "docs" / "how-to" / "spec-engine.md").exists()
    assert (tmp_path / "docs" / "architecture" / "spec-engine.md").exists()
    assert (tmp_path / "docs" / "reference" / "spec-engine.md").exists()
    # the additive Variant-1 hub page (D11).
    assert (tmp_path / "docs" / "features" / "spec-engine.md").exists()
    # faq IS written from the FAQ seeds section (FG1 Phase 1).
    assert (help_dir / "templates" / "spec-engine" / "faq.md").exists()
    # tutorial is hand-authored (D10).
    assert not (tmp_path / "docs" / "tutorials" / "spec-engine.md").exists()


# --- project_feature: faq transform (FG1 Phase 1) ---------------------------


def _faq_output(result):
    faqs = [o for o in result.outputs if o.kind == "faq"]
    assert len(faqs) == 1
    return faqs[0]


def test_faq_renders_h2_per_question_and_drops_disclaimer(tmp_path):
    # The fixture's FAQ seeds section: a blockquote disclaimer + six
    # bold-Q bullets. The projected faq has one H2 per question and no
    # trace of the channel-4 disclaimer.
    result = project_feature(FIXTURE, tmp_path, tmp_path / ".help", dry_run=True)
    body = _help_body(_faq_output(result).content)

    assert body.splitlines()[0] == "# Spec Engine FAQ"
    assert "## What is the spec engine?" in body
    assert "## How do quality gates work?" in body
    assert body.count("\n## ") == 6
    # Disclaimer and bullet scaffolding are gone.
    assert "Channel-4 input" not in body
    assert "**Q:**" not in body
    assert "**A:**" not in body
    assert ">" not in body.split("\n## ")[0]
    # Answers survive with their content intact.
    assert "read_spec(plan_path)" in body


def test_faq_parses_both_bullet_shapes(tmp_path):
    # Bold-Q (the corpus-dominant shape) and italic-question (the
    # elicitation-forms variant) both parse; a malformed bullet is
    # skipped with a warning, never an error.
    master = tmp_path / "shapes.md"
    master.write_text(
        "---\n"
        "feature: shapes\n"
        "summary: x\n"
        "---\n\n"
        "## FAQ seeds\n\n"
        "> disclaimer to drop\n\n"
        "- **Q:** Bold question?\n"
        "  **A:** Bold answer\n"
        "  spanning two lines.\n"
        "- *Italic question?* Italic answer.\n"
        "- malformed seed with no shape\n",
        encoding="utf-8",
    )

    result = project_feature(master, tmp_path, tmp_path / ".help", dry_run=True)
    body = _help_body(_faq_output(result).content)

    assert "## Bold question?" in body
    assert "Bold answer\nspanning two lines." in body
    assert "## Italic question?" in body
    assert "Italic answer." in body
    assert "malformed" not in body
    assert any("unparseable" in w for w in result.warnings)


def test_faq_skipped_when_no_seed_parses(tmp_path):
    # A seeds section with no parseable Q/A records a skip (with
    # warnings for the bad bullets) rather than writing an empty faq.
    master = tmp_path / "empty.md"
    master.write_text(
        "---\nfeature: empty\nsummary: x\n---\n\n"
        "## FAQ seeds\n\n> only a disclaimer\n\n- not a q/a bullet\n",
        encoding="utf-8",
    )

    result = project_feature(master, tmp_path, tmp_path / ".help", dry_run=False)

    assert "faq (no parseable Q/A seeds)" in result.skipped
    assert not any(o.kind == "faq" for o in result.outputs)


# --- tolerate missing sections ---------------------------------------------


def test_missing_section_skips_only_dependent_outputs(tmp_path):
    # A minimal master with only Overview, Concepts, and Notes & tips:
    # concept/note/tip render; every output depending on an absent
    # section is skipped — never an error.
    master = tmp_path / "tiny.md"
    master.write_text(
        "---\n"
        "feature: tiny\n"
        "summary: x\n"
        "---\n\n"
        "## Overview\n\nthe overview\n\n"
        "## Concepts\n\nthe concepts\n\n"
        "## Notes & tips\n\nthe notes\n",
        encoding="utf-8",
    )

    result = project_feature(master, tmp_path, tmp_path / ".help", dry_run=True)
    rendered = {o.kind for o in result.outputs}

    assert rendered == {"concept", "note", "tip"}
    # Dependent outputs are recorded as skipped, with the missing
    # section named — including faq (no "## FAQ seeds" section).
    assert any(s.startswith("faq") for s in result.skipped)
    assert any(s.startswith("reference") for s in result.skipped)
    assert any(s.startswith("comparison") for s in result.skipped)
    assert any(s.startswith("error") for s in result.skipped)
    assert any(s.startswith("docs/how-to") for s in result.skipped)
    assert any(s.startswith("docs/architecture") for s in result.skipped)


# --- project_feature: hub page (D11 / Variant 1) ---------------------------


def _hub_content(result) -> str:
    """Return the single hub output's rendered content."""
    hubs = [o for o in result.outputs if o.kind == "hub"]
    assert len(hubs) == 1
    return hubs[0].content


def _degraded_master(tmp_path) -> Path:
    """A master that declares how-to/reference/architecture but NO
    tutorial — exercising the degraded how-to-hero branch (`models`)."""
    master = tmp_path / "models.md"
    master.write_text(
        "---\n"
        "feature: models\n"
        "summary: Model registry and selection\n"
        "nav:\n"
        "  mkdocs:\n"
        "    how-to: how-to/models\n"
        "    architecture: architecture/models\n"
        "    reference: reference/models\n"
        "---\n\n"
        "## Overview\n\nthe overview\n\n"
        "## Concepts\n\nthe concepts\n\n"
        "## Quickstart\n\nthe quickstart\n\n"
        "## Tasks\n\nthe tasks\n\n"
        "## Reference\n\nthe reference\n\n"
        "## Design & extension\n\nthe design\n",
        encoding="utf-8",
    )
    return master


def test_hub_tutorial_hero_links_tutorial_and_omits_it_from_cards(tmp_path):
    # spec-engine's master declares nav.mkdocs.tutorial → the hero links
    # the tutorial path; the tutorial is NOT repeated as a card.
    result = project_feature(FIXTURE, tmp_path, tmp_path / ".help", dry_run=True)
    hub = _hub_content(result)

    assert hub.startswith("# Spec Engine\n")
    assert "Spec-driven development with approval loops" in hub
    # Hero "Start here" admonition points at the tutorial.
    assert '!!! tip "Start here"' in hub
    assert "[Tutorial](../tutorials/spec-engine.md)" in hub
    # Card grid uses Material idioms and lists how-to/reference/architecture.
    assert '<div class="grid cards" markdown>' in hub
    assert "[Open the how-to guide](../how-to/spec-engine.md)" in hub
    assert "[Open the reference](../reference/spec-engine.md)" in hub
    assert "[Open the architecture](../architecture/spec-engine.md)" in hub
    # The tutorial is the hero, never a card.
    assert "Open the tutorial" not in hub
    assert hub.count("../tutorials/spec-engine.md") == 1


def test_hub_degraded_how_to_hero_when_no_tutorial(tmp_path):
    # No tutorial declared → hero degrades to how-to; cards are the
    # remaining present pages (reference, architecture). No tutorial card.
    master = _degraded_master(tmp_path)
    result = project_feature(master, tmp_path, tmp_path / ".help", dry_run=True)
    hub = _hub_content(result)

    assert hub.startswith("# Models\n")
    assert '!!! tip "Start here"' in hub
    # Hero is the how-to, not a tutorial.
    assert "[How-to guide](../how-to/models.md)" in hub
    assert "tutorial" not in hub.lower()
    # Remaining pages become cards; the hero how-to is not repeated.
    assert "[Open the reference](../reference/models.md)" in hub
    assert "[Open the architecture](../architecture/models.md)" in hub
    assert "Open the how-to" not in hub


def test_hub_skipped_when_no_nav_pages(tmp_path):
    # A master with no nav.mkdocs pages → hub recorded in result.skipped,
    # no hub output, no file written.
    master = tmp_path / "barebones.md"
    master.write_text(
        "---\nfeature: barebones\nsummary: x\n---\n\n## Overview\n\nprose\n",
        encoding="utf-8",
    )

    result = project_feature(master, tmp_path, tmp_path / ".help", dry_run=False)

    assert "hub (no docs pages)" in result.skipped
    assert not any(o.kind == "hub" for o in result.outputs)
    assert not (tmp_path / "docs" / "features" / "barebones.md").exists()


def test_hub_dry_run_writes_nothing_but_is_in_outputs(tmp_path):
    # dry_run=True: hub content is planned in result.outputs but no file
    # is written.
    result = project_feature(FIXTURE, tmp_path, tmp_path / ".help", dry_run=True)

    assert any(o.kind == "hub" for o in result.outputs)
    assert result.written == []
    assert not (tmp_path / "docs" / "features" / "spec-engine.md").exists()


# --- validate_master_file (warn-only) --------------------------------------


def _write_master_with_mispathed_import(tmp_path) -> Path:
    """A project_root with a source module and a master file whose
    example imports it by the wrong (basename-guessed) module path."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mymod.py").write_text(
        '"""A module."""\n\n\ndef do_thing():\n    """Do the thing."""\n    return 1\n',
        encoding="utf-8",
    )
    master = tmp_path / "feat.md"
    master.write_text(
        "---\n"
        "feature: feat\n"
        "summary: A feature\n"
        "source_globs: [pkg/*.py]\n"
        "---\n\n"
        "## Tasks\n\n"
        "```python\n"
        # Wrong module path: real module is pkg.mymod, not bare mymod.
        "from mymod import do_thing\n" "\n" "do_thing()\n" "```\n",
        encoding="utf-8",
    )
    return master


def test_validate_master_file_flags_import_repair_and_is_warn_only(tmp_path):
    master = _write_master_with_mispathed_import(tmp_path)

    findings = validate_master_file(master, tmp_path)

    # Never raises — the pilot is warn-only; it returns a plain list.
    assert isinstance(findings, list)
    # The import_repair probe surfaces a warning that the example import
    # would be rewritten to its canonical module path.
    repair = [f for f in findings if "import_repair would rewrite" in f.message]
    assert len(repair) == 1
    assert repair[0].severity == "warning"


def test_validate_master_file_clean_when_no_source_globs(tmp_path):
    # No source_globs -> import_repair probe degrades to None; a clean
    # master with no fishy refs yields no import_repair finding.
    master = tmp_path / "clean.md"
    master.write_text(
        "---\n"
        "feature: clean\n"
        "summary: Clean feature\n"
        "---\n\n"
        "## Overview\n\nJust prose, no code, no references.\n",
        encoding="utf-8",
    )

    findings = validate_master_file(master, tmp_path)

    assert isinstance(findings, list)
    assert not any("import_repair would rewrite" in f.message for f in findings)


# --- video frontmatter (help-page videos, A-track) --------------------------


def _fixture_with_video(tmp_path, video_yaml: str) -> Path:
    """Copy the spec-engine fixture with a ``video`` frontmatter block."""
    text = FIXTURE.read_text(encoding="utf-8").replace(
        "feature: spec-engine\n",
        f"feature: spec-engine\n{video_yaml}",
        1,
    )
    master = tmp_path / "spec-engine.md"
    master.write_text(text, encoding="utf-8")
    return master


def test_video_mapping_projects_to_concept_and_hub_only(tmp_path):
    master = _fixture_with_video(
        tmp_path,
        "video:\n  url: https://youtu.be/demo123\n  title: Spec engine in 4 minutes\n",
    )
    result = project_feature(master, tmp_path, tmp_path / ".help", dry_run=True)
    by_kind = {o.kind: o.content for o in result.outputs}

    expected = "**Watch:** [Spec engine in 4 minutes](https://youtu.be/demo123)"
    assert expected in by_kind["concept"]
    assert expected in by_kind["hub"]
    # The link lands after the concept H1, not inside the frontmatter.
    assert expected in _help_body(by_kind["concept"])
    # No other kind carries the link.
    for kind, content in by_kind.items():
        if kind not in ("concept", "hub"):
            assert "**Watch:**" not in content, kind


def test_video_bare_url_string_gets_default_title(tmp_path):
    master = _fixture_with_video(tmp_path, "video: https://youtu.be/demo123\n")
    result = project_feature(master, tmp_path, tmp_path / ".help", dry_run=True)
    by_kind = {o.kind: o.content for o in result.outputs}

    assert "**Watch:** [Watch the video](https://youtu.be/demo123)" in by_kind["concept"]


def test_video_mapping_without_url_projects_nothing(tmp_path):
    master = _fixture_with_video(tmp_path, "video:\n  title: Title but no url\n")
    result = project_feature(master, tmp_path, tmp_path / ".help", dry_run=True)

    assert not any("**Watch:**" in o.content for o in result.outputs)


def test_no_video_frontmatter_output_unchanged(tmp_path):
    result = project_feature(FIXTURE, tmp_path, tmp_path / ".help", dry_run=True)

    assert not any("**Watch:**" in o.content for o in result.outputs)
