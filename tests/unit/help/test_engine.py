"""Unit tests for attune.help.engine module.

Tests cover:
- TemplateContext / AudienceProfile / PopulatedTemplate dataclasses
- _find_template_file prefix routing
- _parse_template_file YAML frontmatter + section extraction
- _load_cross_links (success, missing, corrupt)
- _resolve_related cross-link expansion
- _adapt_for_audience (compact, claude-code, normal)
- populate() end-to-end (found, not found, with context)
- search_by_tag / list_tags helpers

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from pathlib import Path

import pytest

from attune.help.engine import (
    AudienceProfile,
    PopulatedTemplate,
    TemplateContext,
    _adapt_for_audience,
    _find_template_file,
    _load_cross_links,
    _parse_template_file,
    _resolve_related,
    list_tags,
    populate,
    search_by_tag,
)

# -- Fixtures --------------------------------------------------------


@pytest.fixture()
def generated_dir(tmp_path: Path) -> Path:
    """Create a minimal generated/ directory with templates."""
    gen = tmp_path / "generated"
    (gen / "errors").mkdir(parents=True)
    (gen / "warnings").mkdir(parents=True)
    (gen / "tips").mkdir(parents=True)
    (gen / "references").mkdir(parents=True)

    # Error template
    (gen / "errors" / "shadow-dirs.md").write_text(
        "---\n"
        "type: error\n"
        "subtype: import\n"
        "name: shadow-dirs\n"
        "confidence: Verified\n"
        "tags: [imports, python]\n"
        "source: CLAUDE.md\n"
        "---\n"
        "\n"
        "# Error: Shadow directories break imports\n"
        "\n"
        "## Signature\n"
        "\n"
        "ModuleNotFoundError on submodules\n"
        "\n"
        "## Root Cause\n"
        "\n"
        "A directory at repo root shadows the installed package.\n"
        "\n"
        "## Resolution\n"
        "\n"
        "Delete or rename the shadow directory.\n"
        "\n"
        "## Related Topics\n"
        "\n"
        "- See also: tip-check-for-shadow-dirs\n",
        encoding="utf-8",
    )

    # Tip template
    (gen / "tips" / "check-for-shadow-dirs.md").write_text(
        "---\n"
        "type: tip\n"
        "subtype: practice\n"
        "name: check-for-shadow-dirs\n"
        "confidence: High\n"
        "tags: [imports]\n"
        "source: Best practice\n"
        "---\n"
        "\n"
        "# Tip: Check for shadow directories\n"
        "\n"
        "## Recommendation\n"
        "\n"
        "Run ls at repo root before debugging import errors.\n"
        "\n"
        "## Why\n"
        "\n"
        "Shadow directories cause confusing failures.\n",
        encoding="utf-8",
    )

    # Warning template with string tags
    (gen / "warnings" / "stale-lock.md").write_text(
        "---\n"
        "type: warning\n"
        "name: stale-lock\n"
        "confidence: Medium\n"
        "tags: stale, lockfile\n"
        "source: Manual\n"
        "---\n"
        "\n"
        "# Warning: Stale lock file\n"
        "\n"
        "## Condition\n"
        "\n"
        "Lock file older than 30 days.\n"
        "\n"
        "## Risk\n"
        "\n"
        "Dependency drift.\n"
        "\n"
        "## Mitigation\n"
        "\n"
        "Run uv lock.\n",
        encoding="utf-8",
    )

    # Cross-links index
    cross_links = {
        "stats": {"linked_templates": 2, "total_tags": 3},
        "links": {
            "err-shadow-dirs": {
                "related_warning": [],
                "prevented_by": ["tip-check-for-shadow-dirs"],
                "references_tools": ["ref-tool-security-audit"],
            },
        },
        "tag_index": {
            "imports": ["err-shadow-dirs", "tip-check-for-shadow-dirs"],
            "python": ["err-shadow-dirs"],
            "stale": ["war-stale-lock"],
        },
    }
    (gen / "cross_links.json").write_text(
        json.dumps(cross_links),
        encoding="utf-8",
    )

    return gen


# -- TemplateContext / AudienceProfile --------------------------------


@pytest.mark.unit
class TestDataclasses:
    """Tests for helper dataclasses."""

    def test_template_context_defaults(self) -> None:
        """Test TemplateContext default values."""
        ctx = TemplateContext()
        assert ctx.file_path is None
        assert ctx.extra == {}

    def test_audience_profile_defaults(self) -> None:
        """Test AudienceProfile default values."""
        ap = AudienceProfile()
        assert ap.channel == "claude-code"
        assert ap.verbosity == "normal"

    def test_populated_template_fields(self) -> None:
        """Test PopulatedTemplate holds all fields."""
        pt = PopulatedTemplate(
            template_id="err-test",
            type="error",
            subtype="",
            name="test",
            title="Test",
            body="body",
            sections={},
            tags=[],
            related=[],
            confidence="",
            source="",
        )
        assert pt.template_id == "err-test"
        assert pt.metadata == {}


# -- _find_template_file ----------------------------------------------


@pytest.mark.unit
class TestFindTemplateFile:
    """Tests for _find_template_file prefix routing."""

    def test_finds_error_template(self, generated_dir: Path) -> None:
        """Test err- prefix routes to errors/."""
        result = _find_template_file("err-shadow-dirs", generated_dir)
        assert result is not None
        assert result.name == "shadow-dirs.md"

    def test_finds_tip_template(self, generated_dir: Path) -> None:
        """Test tip- prefix routes to tips/."""
        result = _find_template_file("tip-check-for-shadow-dirs", generated_dir)
        assert result is not None

    def test_finds_warning_template(self, generated_dir: Path) -> None:
        """Test war- prefix routes to warnings/."""
        result = _find_template_file("war-stale-lock", generated_dir)
        assert result is not None

    def test_returns_none_for_unknown_prefix(self, generated_dir: Path) -> None:
        """Test unknown prefix returns None."""
        assert _find_template_file("xyz-something", generated_dir) is None

    def test_returns_none_for_no_hyphen(self, generated_dir: Path) -> None:
        """Test ID without hyphen returns None."""
        assert _find_template_file("noseparator", generated_dir) is None

    def test_returns_none_for_missing_file(self, generated_dir: Path) -> None:
        """Test valid prefix but nonexistent file returns None."""
        assert _find_template_file("err-nonexistent", generated_dir) is None


# -- _parse_template_file ---------------------------------------------

pytest.importorskip("frontmatter")


@pytest.mark.unit
class TestParseTemplateFile:
    """Tests for _parse_template_file."""

    def test_extracts_frontmatter_fields(self, generated_dir: Path) -> None:
        """Test YAML frontmatter fields are extracted."""
        filepath = generated_dir / "errors" / "shadow-dirs.md"
        data = _parse_template_file(filepath)
        assert data["type"] == "error"
        assert data["subtype"] == "import"
        assert data["confidence"] == "Verified"
        assert data["source"] == "CLAUDE.md"

    def test_extracts_title(self, generated_dir: Path) -> None:
        """Test title is extracted from # heading."""
        filepath = generated_dir / "errors" / "shadow-dirs.md"
        data = _parse_template_file(filepath)
        assert "Shadow directories" in data["title"]

    def test_extracts_sections(self, generated_dir: Path) -> None:
        """Test ## sections are parsed into dict."""
        filepath = generated_dir / "errors" / "shadow-dirs.md"
        data = _parse_template_file(filepath)
        assert "Signature" in data["sections"]
        assert "Root Cause" in data["sections"]
        assert "Resolution" in data["sections"]

    def test_list_tags_parsed(self, generated_dir: Path) -> None:
        """Test tags as YAML list are parsed correctly."""
        filepath = generated_dir / "errors" / "shadow-dirs.md"
        data = _parse_template_file(filepath)
        assert "imports" in data["tags"]
        assert "python" in data["tags"]

    def test_string_tags_parsed(self, generated_dir: Path) -> None:
        """Test tags as comma-separated string are parsed."""
        filepath = generated_dir / "warnings" / "stale-lock.md"
        data = _parse_template_file(filepath)
        assert "stale" in data["tags"]
        assert "lockfile" in data["tags"]


# -- _load_cross_links ------------------------------------------------


@pytest.mark.unit
class TestLoadCrossLinks:
    """Tests for _load_cross_links."""

    def test_loads_valid_json(self, generated_dir: Path) -> None:
        """Test loading a valid cross_links.json."""
        result = _load_cross_links(generated_dir)
        assert "links" in result
        assert "tag_index" in result

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Test returns empty dict when file doesn't exist."""
        assert _load_cross_links(tmp_path) == {}

    def test_returns_empty_for_corrupt_json(self, tmp_path: Path) -> None:
        """Test returns empty dict for malformed JSON."""
        (tmp_path / "cross_links.json").write_text("not json", encoding="utf-8")
        assert _load_cross_links(tmp_path) == {}


# -- _resolve_related --------------------------------------------------


@pytest.mark.unit
class TestResolveRelated:
    """Tests for _resolve_related."""

    def test_resolves_relationships(self, generated_dir: Path) -> None:
        """Test cross-link expansion for a known template."""
        cross_links = _load_cross_links(generated_dir)
        related = _resolve_related("err-shadow-dirs", cross_links)
        types = {r["type"] for r in related}
        assert "Tip" in types
        assert "Tool Reference" in types

    def test_empty_for_unknown_template(self, generated_dir: Path) -> None:
        """Test returns empty list for unknown template ID."""
        cross_links = _load_cross_links(generated_dir)
        assert _resolve_related("err-nonexistent", cross_links) == []


# -- _adapt_for_audience -----------------------------------------------


@pytest.mark.unit
class TestAdaptForAudience:
    """Tests for _adapt_for_audience."""

    def test_compact_returns_title_and_fix(self) -> None:
        """Test compact verbosity returns abbreviated output."""
        body = "# Title\n\nSome text\n\n## Resolution\n\nDo the fix."
        sections = {"Resolution": "Do the fix."}
        result = _adapt_for_audience(
            body,
            sections,
            AudienceProfile(verbosity="compact"),
        )
        assert "# Title" in result
        assert "Do the fix" in result

    def test_claude_code_strips_related_topics(self) -> None:
        """Test claude-code channel strips Related Topics section."""
        body = (
            "# Title\n\n"
            "## Root Cause\n\nSome cause.\n\n"
            "## Related Topics\n\n- link1\n- link2\n\n"
            "## Next Section\n\nMore text."
        )
        result = _adapt_for_audience(
            body,
            {},
            AudienceProfile(channel="claude-code"),
        )
        assert "Related Topics" not in result
        assert "Root Cause" in result
        assert "Next Section" in result

    def test_normal_returns_full_body(self) -> None:
        """Test normal/other verbosity returns body unchanged."""
        body = "# Title\n\nFull content here."
        result = _adapt_for_audience(
            body,
            {},
            AudienceProfile(channel="marketplace", verbosity="normal"),
        )
        assert result == body


# -- populate() --------------------------------------------------------


@pytest.mark.unit
class TestPopulate:
    """Tests for populate() end-to-end."""

    def test_returns_populated_template(self, generated_dir: Path) -> None:
        """Test successful population returns PopulatedTemplate."""
        result = populate("err-shadow-dirs", generated_dir=generated_dir)
        assert result is not None
        assert result.template_id == "err-shadow-dirs"
        assert result.type == "error"
        assert "Shadow directories" in result.title

    def test_returns_none_for_missing(self, generated_dir: Path) -> None:
        """Test returns None when template not found."""
        result = populate("err-nonexistent", generated_dir=generated_dir)
        assert result is None

    def test_context_populates_metadata(self, generated_dir: Path) -> None:
        """Test context fields appear in metadata."""
        ctx = TemplateContext(
            file_path="src/foo.py",
            error_message="import error",
            extra={"custom": "value"},
        )
        result = populate(
            "err-shadow-dirs",
            context=ctx,
            generated_dir=generated_dir,
        )
        assert result is not None
        assert result.metadata["file_path"] == "src/foo.py"
        assert result.metadata["custom"] == "value"

    def test_audience_adaptation(self, generated_dir: Path) -> None:
        """Test audience profile affects output."""
        compact = populate(
            "err-shadow-dirs",
            audience=AudienceProfile(verbosity="compact"),
            generated_dir=generated_dir,
        )
        normal = populate(
            "err-shadow-dirs",
            audience=AudienceProfile(verbosity="normal"),
            generated_dir=generated_dir,
        )
        assert compact is not None
        assert normal is not None
        # Compact body should be shorter
        assert len(compact.body) < len(normal.body)

    def test_cross_links_resolved(self, generated_dir: Path) -> None:
        """Test related items are populated from cross-links."""
        result = populate("err-shadow-dirs", generated_dir=generated_dir)
        assert result is not None
        assert len(result.related) > 0


# -- search_by_tag / list_tags -----------------------------------------


@pytest.mark.unit
class TestTagHelpers:
    """Tests for search_by_tag and list_tags."""

    def test_search_by_tag_returns_matches(self, generated_dir: Path) -> None:
        """Test searching by tag returns matching IDs."""
        results = search_by_tag("imports", generated_dir=generated_dir)
        assert "err-shadow-dirs" in results
        assert "tip-check-for-shadow-dirs" in results

    def test_search_by_tag_no_matches(self, generated_dir: Path) -> None:
        """Test searching by nonexistent tag returns empty."""
        assert search_by_tag("nonexistent", generated_dir=generated_dir) == []

    def test_list_tags_returns_counts(self, generated_dir: Path) -> None:
        """Test list_tags returns tag -> count mapping."""
        tags = list_tags(generated_dir=generated_dir)
        assert "imports" in tags
        assert tags["imports"] == 2

    def test_list_tags_sorted_by_count(self, generated_dir: Path) -> None:
        """Test list_tags is sorted descending by count."""
        tags = list_tags(generated_dir=generated_dir)
        counts = list(tags.values())
        assert counts == sorted(counts, reverse=True)
