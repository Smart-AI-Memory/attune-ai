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

    def test_blocks_path_traversal(self, generated_dir: Path) -> None:
        """Test path traversal attempts are blocked (CWE-22)."""
        assert _find_template_file("err-../../etc/passwd", generated_dir) is None
        assert _find_template_file("err-../../../etc/shadow", generated_dir) is None


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


# -- Phase 3+4 Feature Tests -------------------------------------------


class TestProgressiveDepth:
    """Tests for populate_progressive() depth escalation."""

    def test_first_call_returns_compact(self, generated_dir: Path) -> None:
        """First call to a template returns compact verbosity."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        result = populate_progressive(
            "err-shadow-dirs",
            generated_dir=generated_dir,
        )
        assert result is not None
        assert result.metadata["depth_level"] == 0
        # Compact body should be shorter than full
        full = populate(
            "err-shadow-dirs",
            audience=AudienceProfile(verbosity="normal"),
            generated_dir=generated_dir,
        )
        assert len(result.body) <= len(full.body)

    def test_second_call_escalates(self, generated_dir: Path) -> None:
        """Second call to same template returns normal."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        populate_progressive("err-shadow-dirs", generated_dir=generated_dir)
        result = populate_progressive(
            "err-shadow-dirs",
            generated_dir=generated_dir,
        )
        assert result.metadata["depth_level"] == 1

    def test_third_call_detailed(self, generated_dir: Path) -> None:
        """Third call returns detailed (max depth)."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        populate_progressive("err-shadow-dirs", generated_dir=generated_dir)
        populate_progressive("err-shadow-dirs", generated_dir=generated_dir)
        result = populate_progressive(
            "err-shadow-dirs",
            generated_dir=generated_dir,
        )
        assert result.metadata["depth_level"] == 2

    def test_new_template_resets_depth(self, generated_dir: Path) -> None:
        """Switching template ID resets depth to 0."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        populate_progressive("err-shadow-dirs", generated_dir=generated_dir)
        populate_progressive("err-shadow-dirs", generated_dir=generated_dir)
        # Switch to tip
        result = populate_progressive(
            "tip-check-for-shadow-dirs",
            generated_dir=generated_dir,
        )
        assert result.metadata["depth_level"] == 0

    def test_caps_at_depth_2(self, generated_dir: Path) -> None:
        """Depth does not exceed 2."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        for _ in range(5):
            result = populate_progressive(
                "err-shadow-dirs",
                generated_dir=generated_dir,
            )
        assert result.metadata["depth_level"] == 2


class TestWorkflowChainPrediction:
    """Tests for get_workflow_help()."""

    def test_returns_templates_for_known_workflow(
        self,
        generated_dir: Path,
    ) -> None:
        """Known workflow returns matching templates."""
        from attune.help.engine import get_workflow_help

        # Add workflow_map to cross_links
        cross_path = generated_dir / "cross_links.json"
        data = json.loads(cross_path.read_text(encoding="utf-8"))
        data["workflow_map"] = {
            "code-review": ["tip-check-for-shadow-dirs"],
        }
        cross_path.write_text(
            json.dumps(data),
            encoding="utf-8",
        )

        results = get_workflow_help(
            "code-review",
            generated_dir=generated_dir,
        )
        assert len(results) == 1
        assert results[0].template_id == "tip-check-for-shadow-dirs"

    def test_returns_empty_for_unknown_workflow(
        self,
        generated_dir: Path,
    ) -> None:
        """Unknown workflow returns empty list."""
        from attune.help.engine import get_workflow_help

        results = get_workflow_help(
            "nonexistent",
            generated_dir=generated_dir,
        )
        assert results == []


class TestPrecursorWarnings:
    """Tests for get_precursor_warnings()."""

    def test_python_file_returns_warnings(
        self,
        generated_dir: Path,
    ) -> None:
        """Python file returns templates tagged with python/imports."""
        from attune.help.engine import get_precursor_warnings

        results = get_precursor_warnings(
            "src/module.py",
            generated_dir=generated_dir,
        )
        # Should find templates tagged 'imports' or 'python'
        assert len(results) > 0
        for r in results:
            assert r.template_id.startswith(("err-", "war-"))

    def test_unknown_extension_returns_empty(
        self,
        generated_dir: Path,
    ) -> None:
        """Unknown file extension returns empty list."""
        from attune.help.engine import get_precursor_warnings

        results = get_precursor_warnings(
            "image.png",
            generated_dir=generated_dir,
        )
        assert results == []


class TestFeedbackLoop:
    """Tests for record_template_feedback / get_template_confidence."""

    def test_record_good_feedback(self, generated_dir: Path) -> None:
        """Recording good feedback returns confidence 1.0."""
        from attune.help.engine import record_template_feedback

        score = record_template_feedback(
            "err-shadow-dirs",
            "good",
            generated_dir=generated_dir,
        )
        assert score == 1.0

    def test_record_bad_feedback(self, generated_dir: Path) -> None:
        """Recording bad feedback returns confidence 0.0."""
        from attune.help.engine import record_template_feedback

        score = record_template_feedback(
            "err-test",
            "bad",
            generated_dir=generated_dir,
        )
        assert score == 0.0

    def test_mixed_feedback_confidence(
        self,
        generated_dir: Path,
    ) -> None:
        """Mixed feedback returns ratio."""
        from attune.help.engine import record_template_feedback

        record_template_feedback(
            "err-mixed",
            "good",
            generated_dir=generated_dir,
        )
        record_template_feedback(
            "err-mixed",
            "good",
            generated_dir=generated_dir,
        )
        score = record_template_feedback(
            "err-mixed",
            "bad",
            generated_dir=generated_dir,
        )
        # 2 good + 1 bad = 2/3
        assert abs(score - 2 / 3) < 0.01

    def test_no_feedback_returns_1(self, generated_dir: Path) -> None:
        """No feedback defaults to confidence 1.0."""
        from attune.help.engine import get_template_confidence

        score = get_template_confidence(
            "err-unknown",
            generated_dir=generated_dir,
        )
        assert score == 1.0

    def test_feedback_persists_to_file(
        self,
        generated_dir: Path,
    ) -> None:
        """Feedback is saved to feedback.json."""
        from attune.help.engine import record_template_feedback

        record_template_feedback(
            "err-persist",
            "good",
            generated_dir=generated_dir,
        )
        feedback_path = generated_dir / "feedback.json"
        assert feedback_path.exists()
        data = json.loads(feedback_path.read_text(encoding="utf-8"))
        assert "err-persist" in data
        assert data["err-persist"]["good"] == 1


class TestComposition:
    """Tests for populate(compose=True)."""

    def test_compose_inlines_embedded_content(
        self,
        generated_dir: Path,
    ) -> None:
        """Compose=True appends embedded template content."""
        # Add embed rule to cross_links
        cross_path = generated_dir / "cross_links.json"
        data = json.loads(cross_path.read_text(encoding="utf-8"))
        data["links"]["err-shadow-dirs"] = {
            **data["links"].get("err-shadow-dirs", {}),
            "embeds": [
                {"id": "tip-check-for-shadow-dirs", "position": "after_resolution"},
            ],
        }
        cross_path.write_text(
            json.dumps(data),
            encoding="utf-8",
        )

        result = populate(
            "err-shadow-dirs",
            compose=True,
            generated_dir=generated_dir,
        )
        assert "composed_from" in result.metadata
        assert "tip-check-for-shadow-dirs" in result.metadata["composed_from"]
        # Body should contain embedded tip content
        assert "Check for shadow" in result.body

    def test_compose_false_no_embedding(
        self,
        generated_dir: Path,
    ) -> None:
        """Compose=False does not inline anything."""
        result = populate(
            "err-shadow-dirs",
            compose=False,
            generated_dir=generated_dir,
        )
        assert "composed_from" not in result.metadata


# -- Type-driven progression fixture -----------------------------------


@pytest.fixture()
def typed_dir(tmp_path: Path) -> Path:
    """Create a generated/ directory with concept/task/reference for one topic."""
    gen = tmp_path / "generated"
    (gen / "concepts").mkdir(parents=True)
    (gen / "tasks").mkdir(parents=True)
    (gen / "references").mkdir(parents=True)
    (gen / "errors").mkdir(parents=True)

    # Concept template for security-audit
    (gen / "concepts" / "tool-security-audit.md").write_text(
        "---\n"
        "type: concept\n"
        "name: tool-security-audit\n"
        "tags: [security, skill]\n"
        "source: test\n"
        "---\n"
        "\n"
        "# Security Audit\n"
        "\n"
        "## What\n"
        "\n"
        "Scans code for vulnerabilities.\n"
        "\n"
        "## Why\n"
        "\n"
        "Catches bugs before release.\n",
        encoding="utf-8",
    )

    # Task template for security-audit
    (gen / "tasks" / "use-security-audit.md").write_text(
        "---\n"
        "type: task\n"
        "name: use-security-audit\n"
        "tags: [security, task]\n"
        "source: test\n"
        "---\n"
        "\n"
        "# Task: Use the security-audit skill\n"
        "\n"
        "## Steps\n"
        "\n"
        "1. Define scope\n"
        "2. Run the tool\n"
        "3. Review results\n",
        encoding="utf-8",
    )

    # Reference template for security-audit
    (gen / "references" / "skill-security-audit.md").write_text(
        "---\n"
        "type: reference\n"
        "subtype: procedural\n"
        "name: skill-security-audit\n"
        "tags: [security, skill]\n"
        "source: test\n"
        "---\n"
        "\n"
        "# Reference: Skill: security-audit\n"
        "\n"
        "## Scoping\n"
        "\n"
        "Ask which path to scan.\n"
        "\n"
        "## Execution\n"
        "\n"
        "Call security_audit MCP tool.\n"
        "\n"
        "## What It Checks\n"
        "\n"
        "eval, exec, path traversal, secrets.\n",
        encoding="utf-8",
    )

    # Error template (for fallback testing)
    (gen / "errors" / "shadow-dirs.md").write_text(
        "---\n"
        "type: error\n"
        "name: shadow-dirs\n"
        "tags: [imports]\n"
        "source: test\n"
        "---\n"
        "\n"
        "# Error: Shadow directories\n"
        "\n"
        "## Signature\n"
        "\n"
        "ModuleNotFoundError\n"
        "\n"
        "## Resolution\n"
        "\n"
        "Delete the shadow directory.\n",
        encoding="utf-8",
    )

    # Empty cross_links.json
    (gen / "cross_links.json").write_text(
        json.dumps({"links": {}, "tag_index": {}}),
        encoding="utf-8",
    )

    return gen


# -- _extract_topic ----------------------------------------------------


@pytest.mark.unit
class TestExtractTopic:
    """Tests for _extract_topic prefix stripping."""

    def test_strips_ref_skill_prefix(self) -> None:
        """Test ref-skill- prefix is stripped."""
        from attune.help.engine import _extract_topic

        assert _extract_topic("ref-skill-security-audit") == "security-audit"

    def test_strips_tas_use_prefix(self) -> None:
        """Test tas-use- prefix is stripped."""
        from attune.help.engine import _extract_topic

        assert _extract_topic("tas-use-security-audit") == "security-audit"

    def test_strips_con_tool_prefix(self) -> None:
        """Test con-tool- prefix is stripped."""
        from attune.help.engine import _extract_topic

        assert _extract_topic("con-tool-security-audit") == "security-audit"

    def test_strips_ref_tool_prefix(self) -> None:
        """Test ref-tool- prefix is stripped."""
        from attune.help.engine import _extract_topic

        assert _extract_topic("ref-tool-code-review") == "code-review"

    def test_bare_topic_unchanged(self) -> None:
        """Test bare topic slug passes through."""
        from attune.help.engine import _extract_topic

        assert _extract_topic("security-audit") == "security-audit"

    def test_err_prefix(self) -> None:
        """Test err- prefix is stripped."""
        from attune.help.engine import _extract_topic

        assert _extract_topic("err-shadow-dirs") == "shadow-dirs"


# -- _resolve_topic_at_level -------------------------------------------


@pytest.mark.unit
class TestResolveTopicAtLevel:
    """Tests for _resolve_topic_at_level."""

    def test_resolves_concept(self, typed_dir: Path) -> None:
        """Level 0 resolves to concept template."""
        from attune.help.engine import _resolve_topic_at_level

        result = _resolve_topic_at_level("security-audit", 0, typed_dir)
        assert result == "con-tool-security-audit"

    def test_resolves_task(self, typed_dir: Path) -> None:
        """Level 1 resolves to task template."""
        from attune.help.engine import _resolve_topic_at_level

        result = _resolve_topic_at_level("security-audit", 1, typed_dir)
        assert result == "tas-use-security-audit"

    def test_resolves_reference(self, typed_dir: Path) -> None:
        """Level 2 resolves to reference template."""
        from attune.help.engine import _resolve_topic_at_level

        result = _resolve_topic_at_level("security-audit", 2, typed_dir)
        assert result == "ref-skill-security-audit"

    def test_returns_none_for_missing(self, typed_dir: Path) -> None:
        """Returns None when no template exists at level."""
        from attune.help.engine import _resolve_topic_at_level

        result = _resolve_topic_at_level("nonexistent-topic", 0, typed_dir)
        assert result is None


# -- Type-driven progressive depth -------------------------------------


@pytest.mark.unit
class TestTypeDrivenProgression:
    """Tests for type-driven populate_progressive()."""

    def test_first_call_returns_concept(self, typed_dir: Path) -> None:
        """First call to a topic returns concept template."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        result = populate_progressive(
            "security-audit",
            generated_dir=typed_dir,
        )
        assert result is not None
        assert result.metadata["depth_level"] == 0
        assert result.metadata["level_label"] == "concept"
        assert result.type == "concept"
        assert "Scans code" in result.body

    def test_second_call_returns_task(self, typed_dir: Path) -> None:
        """Second call returns task/procedural template."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        populate_progressive("security-audit", generated_dir=typed_dir)
        result = populate_progressive(
            "security-audit",
            generated_dir=typed_dir,
        )
        assert result is not None
        assert result.metadata["depth_level"] == 1
        assert result.metadata["level_label"] == "procedural"
        assert result.type == "task"
        assert "Steps" in result.body

    def test_third_call_returns_reference(self, typed_dir: Path) -> None:
        """Third call returns reference template."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        populate_progressive("security-audit", generated_dir=typed_dir)
        populate_progressive("security-audit", generated_dir=typed_dir)
        result = populate_progressive(
            "security-audit",
            generated_dir=typed_dir,
        )
        assert result is not None
        assert result.metadata["depth_level"] == 2
        assert result.metadata["level_label"] == "reference"
        assert result.type == "reference"
        assert "What It Checks" in result.body

    def test_full_template_id_extracts_topic(self, typed_dir: Path) -> None:
        """Full template ID like ref-skill-X extracts topic and routes."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        result = populate_progressive(
            "ref-skill-security-audit",
            generated_dir=typed_dir,
        )
        assert result is not None
        assert result.metadata["depth_level"] == 0
        assert result.metadata["topic"] == "security-audit"
        # Should get concept, not reference (topic starts at 0)
        assert result.type == "concept"

    def test_starting_level_skips_concept(self, typed_dir: Path) -> None:
        """starting_level=1 skips concept, starts at task."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        result = populate_progressive(
            "security-audit",
            generated_dir=typed_dir,
            starting_level=1,
        )
        assert result is not None
        assert result.metadata["depth_level"] == 1
        assert result.type == "task"

    def test_new_topic_resets_depth(self, typed_dir: Path) -> None:
        """Switching topics resets depth to 0."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        populate_progressive("security-audit", generated_dir=typed_dir)
        populate_progressive("security-audit", generated_dir=typed_dir)
        # Depth is now 1, switch topic
        result = populate_progressive(
            "err-shadow-dirs",
            generated_dir=typed_dir,
        )
        assert result is not None
        assert result.metadata["depth_level"] == 0

    def test_fallback_to_verbosity_based(self, typed_dir: Path) -> None:
        """Falls back to verbosity-based when no typed templates exist."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        # err-shadow-dirs has no concept/task/reference variants
        result = populate_progressive(
            "err-shadow-dirs",
            generated_dir=typed_dir,
        )
        assert result is not None
        assert result.metadata["depth_level"] == 0
        # Should get the error template itself via fallback
        assert "Shadow directories" in result.body

    def test_reset_session_returns_to_concept(self, typed_dir: Path) -> None:
        """reset_session() resets depth back to 0."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        populate_progressive("security-audit", generated_dir=typed_dir)
        populate_progressive("security-audit", generated_dir=typed_dir)
        # Now at depth 1, reset
        reset_session()
        result = populate_progressive(
            "security-audit",
            generated_dir=typed_dir,
        )
        assert result is not None
        assert result.metadata["depth_level"] == 0
        assert result.type == "concept"

    def test_caps_at_depth_2(self, typed_dir: Path) -> None:
        """Depth does not exceed 2 with type-driven routing."""
        from attune.help.engine import populate_progressive, reset_session

        reset_session()
        for _ in range(5):
            result = populate_progressive(
                "security-audit",
                generated_dir=typed_dir,
            )
        assert result.metadata["depth_level"] == 2
        assert result.type == "reference"
