"""Unit tests for attune.help.transformers module.

Tests cover:
- render_claude_code for each template type (error, warning, tip, reference)
- render_marketplace YAML frontmatter output
- render_cli Rich fallback to plain text
- _render_cli_plain formatting

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.help.engine import PopulatedTemplate
from attune.help.transformers import (
    _render_cli_plain,
    render_claude_code,
    render_cli,
    render_marketplace,
)

# -- Fixtures --------------------------------------------------------


def _make_template(
    type: str = "error",
    subtype: str = "",
    title: str = "Test Title",
    body: str = "# Test Title\n\nBody text.",
    sections: dict | None = None,
    tags: list | None = None,
    related: list | None = None,
    confidence: str = "Verified",
    source: str = "test",
) -> PopulatedTemplate:
    return PopulatedTemplate(
        template_id=f"{type[:3]}-test",
        type=type,
        subtype=subtype,
        name="test",
        title=title,
        body=body,
        sections=sections or {},
        tags=tags or [],
        related=related or [],
        confidence=confidence,
        source=source,
    )


# -- render_claude_code ------------------------------------------------


@pytest.mark.unit
class TestRenderClaudeCode:
    """Tests for render_claude_code."""

    def test_error_includes_signature_and_resolution(self) -> None:
        """Test error template includes key sections."""
        t = _make_template(
            type="error",
            sections={
                "Signature": "ImportError: no module named foo",
                "Root Cause": "Missing dependency.",
                "Resolution": "Run pip install foo.",
            },
        )
        result = render_claude_code(t)
        assert "ImportError" in result
        assert "pip install foo" in result

    def test_error_truncates_long_root_cause(self) -> None:
        """Test long Root Cause is truncated to ~200 chars."""
        t = _make_template(
            type="error",
            sections={"Root Cause": "x" * 300},
        )
        result = render_claude_code(t)
        assert "..." in result
        # Should be around 200 chars max for root cause portion
        assert len(result) < 400

    def test_warning_includes_condition_and_mitigation(self) -> None:
        """Test warning template includes key sections."""
        t = _make_template(
            type="warning",
            sections={
                "Condition": "Lock file older than 30 days",
                "Risk": "Dependency drift",
                "Mitigation": "Run uv lock.",
            },
        )
        result = render_claude_code(t)
        assert "Lock file" in result
        assert "uv lock" in result

    def test_tip_includes_recommendation(self) -> None:
        """Test tip template includes Recommendation."""
        t = _make_template(
            type="tip",
            sections={
                "Recommendation": "Always check shadow dirs.",
                "Why": "Prevents confusion.",
            },
        )
        result = render_claude_code(t)
        assert "Always check" in result
        assert "Prevents confusion" in result

    def test_reference_returns_body(self) -> None:
        """Test reference template returns the body directly."""
        body = "# Reference: Security Audit\n\nAPI details here."
        t = _make_template(type="reference", body=body)
        result = render_claude_code(t)
        assert result == body

    def test_tool_reference_hint(self) -> None:
        """Test tool references add a run hint."""
        t = _make_template(
            type="error",
            related=[
                {"type": "Tool Reference", "id": "ref-tool-security-audit"},
            ],
        )
        result = render_claude_code(t)
        assert "security-audit" in result

    def test_bold_title(self) -> None:
        """Test output starts with bold title."""
        t = _make_template(title="My Title")
        result = render_claude_code(t)
        assert result.startswith("**My Title**")


# -- render_marketplace ------------------------------------------------


@pytest.mark.unit
class TestRenderMarketplace:
    """Tests for render_marketplace."""

    def test_yaml_frontmatter(self) -> None:
        """Test output includes YAML frontmatter."""
        t = _make_template(
            type="error",
            subtype="import",
            tags=["imports", "python"],
            confidence="Verified",
            source="CLAUDE.md",
        )
        result = render_marketplace(t)
        assert result.startswith("---")
        assert "type: error" in result
        assert "subtype: import" in result
        assert "tags: [imports, python]" in result
        assert "confidence: Verified" in result
        assert "source: CLAUDE.md" in result

    def test_includes_body(self) -> None:
        """Test output includes the full body."""
        body = "# Title\n\nFull content."
        t = _make_template(body=body)
        result = render_marketplace(t)
        assert body in result

    def test_see_also_section(self) -> None:
        """Test related items appear as See Also."""
        t = _make_template(
            related=[
                {"type": "Tip", "id": "tip-check-dirs"},
                {"type": "Error", "id": "err-shadow"},
            ],
        )
        result = render_marketplace(t)
        assert "## See Also" in result
        assert "tip-check-dirs" in result
        assert "err-shadow" in result


# -- render_cli / _render_cli_plain ------------------------------------


@pytest.mark.unit
class TestRenderCli:
    """Tests for render_cli and _render_cli_plain."""

    def test_plain_fallback_has_title(self) -> None:
        """Test plain text output includes title and type."""
        t = _make_template(title="Shadow Dirs", type="error")
        result = _render_cli_plain(t)
        assert "Shadow Dirs" in result
        assert "[error]" in result

    def test_plain_includes_sections(self) -> None:
        """Test plain text includes section headings."""
        t = _make_template(
            sections={"Root Cause": "Some cause", "Resolution": "A fix"},
        )
        result = _render_cli_plain(t)
        assert "Root Cause" in result
        assert "Some cause" in result

    def test_plain_includes_tags(self) -> None:
        """Test plain text includes tags."""
        t = _make_template(tags=["imports", "python"])
        result = _render_cli_plain(t)
        assert "Tags:" in result
        assert "imports" in result

    def test_plain_includes_related(self) -> None:
        """Test plain text includes related items."""
        t = _make_template(
            related=[{"type": "Tip", "id": "tip-test"}],
        )
        result = _render_cli_plain(t)
        assert "Related:" in result
        assert "tip-test" in result

    def test_plain_skips_related_topics_section(self) -> None:
        """Test plain text skips 'Related Topics' section."""
        t = _make_template(
            sections={
                "Root Cause": "Cause",
                "Related Topics": "Should be skipped",
                "Confidence": "Also skipped",
            },
        )
        result = _render_cli_plain(t)
        assert "Root Cause" in result
        assert "Should be skipped" not in result
        assert "Also skipped" not in result

    def test_render_cli_returns_string(self) -> None:
        """Test render_cli returns a non-empty string."""
        t = _make_template(
            title="Test",
            sections={"Root Cause": "Something"},
            tags=["test"],
        )
        result = render_cli(t)
        assert isinstance(result, str)
        assert len(result) > 0


# -- Branch coverage gap fillers ---------------------------------------


@pytest.mark.unit
class TestClaudeCodeMissingSections:
    """Cover missing-section branches for warning/tip/unknown types."""

    def test_warning_with_empty_sections(self) -> None:
        """Warning with no Condition/Risk/Mitigation hits all False branches (50->52, 52->54, 54->69)."""
        t = _make_template(type="warning", sections={})
        result = render_claude_code(t)
        # Bare title only — none of the warning sections present
        assert "**Test Title**" in result
        assert "When:" not in result
        assert "Risk:" not in result
        assert "Mitigation:" not in result

    def test_tip_with_empty_sections(self) -> None:
        """Tip with no Recommendation/Why hits both False branches (58->60, 60->69)."""
        t = _make_template(type="tip", sections={})
        result = render_claude_code(t)
        assert "**Test Title**" in result

    def test_unknown_type_falls_through_elif_chain(self) -> None:
        """Type that isn't error/warning/tip/reference falls through to related-handling (63->69)."""
        t = _make_template(type="info", sections={"Whatever": "ignored"})
        result = render_claude_code(t)
        # Title appears, body-section content does not — falls through to related
        assert "**Test Title**" in result

    def test_related_without_tool_reference_no_hint(self) -> None:
        """Related items present, but no 'Tool Reference' type — no run hint added (71->75)."""
        t = _make_template(
            type="error",
            sections={"Signature": "X"},
            related=[{"type": "Tip", "id": "tip-something"}],
        )
        result = render_claude_code(t)
        assert "Run `" not in result


@pytest.mark.unit
class TestMarketplaceMissingFields:
    """Cover branches where optional marketplace fields are absent."""

    def test_marketplace_no_confidence_omits_line(self) -> None:
        """Empty confidence → frontmatter omits confidence line (101->103)."""
        t = _make_template(confidence="")
        result = render_marketplace(t)
        assert "confidence:" not in result


@pytest.mark.unit
class TestRenderCliRichBranches:
    """Cover the rich-render branches: empty body, skipped sections, related table, no tags."""

    def test_rich_skips_related_topics_and_confidence_sections(self) -> None:
        """Rich render skips 'Related Topics' and 'Confidence' section headings (line 177)."""
        t = _make_template(
            sections={
                "Root Cause": "Real content",
                "Related Topics": "Should be skipped",
                "Confidence": "Also skipped",
            },
        )
        result = render_cli(t)
        assert "Real content" in result
        assert "Should be skipped" not in result
        # "Confidence" as a section heading shouldn't appear (note: type/source could,
        # but the section text "Also skipped" is the marker).
        assert "Also skipped" not in result

    def test_rich_skips_empty_body_sections(self) -> None:
        """Rich render skips sections with whitespace-only body (line 179)."""
        t = _make_template(
            sections={
                "Root Cause": "Real content",
                "Empty Section": "   ",
            },
        )
        result = render_cli(t)
        assert "Real content" in result
        # The empty section's heading should not appear in output
        assert "Empty Section" not in result

    def test_rich_no_tags_skips_tag_line(self) -> None:
        """Rich render with no tags skips the tag block (184->189)."""
        t = _make_template(
            tags=[],
            sections={"Root Cause": "Body"},
        )
        result = render_cli(t)
        # No tag markers appear
        assert "#" not in result.replace("# ", "")  # ignore markdown-ish # if any

    def test_rich_renders_related_table(self) -> None:
        """Rich render with related items renders a 'Related' table (lines 190-196)."""
        t = _make_template(
            sections={"Root Cause": "Body"},
            related=[
                {"type": "Tip", "id": "tip-1"},
                {"type": "Error", "id": "err-1"},
            ],
        )
        result = render_cli(t)
        assert "Related" in result
        assert "tip-1" in result
        assert "err-1" in result


@pytest.mark.unit
class TestRenderCliPlainFallback:
    """Cover the ImportError fallback path and plain-render empty-body branch."""

    def test_render_cli_falls_back_to_plain_when_rich_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When rich import raises ImportError, render_cli falls back to plain (lines 136-137)."""
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("rich"):
                raise ImportError(f"simulated missing {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        t = _make_template(title="Plain Fallback", sections={"Root Cause": "Cause"})
        result = render_cli(t)
        # The plain renderer uses '=' separators — distinct from rich's panel output
        assert "Plain Fallback" in result
        assert "=" * 10 in result

    def test_plain_skips_empty_body_sections(self) -> None:
        """_render_cli_plain skips sections whose body is whitespace-only (line 220)."""
        t = _make_template(
            sections={
                "Root Cause": "Real content",
                "Empty Section": "   ",
            },
        )
        result = _render_cli_plain(t)
        assert "Real content" in result
        assert "Empty Section" not in result
