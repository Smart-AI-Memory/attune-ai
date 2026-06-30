"""Tests for the shared report/config types."""

from __future__ import annotations

from attune.authoring.fact_check.report import (
    CHECK_CLI_REFS,
    CHECK_MD_LINKS,
    CHECK_PYTHON_REFS,
    FactCheckConfig,
    FactCheckReport,
    Finding,
    format_unresolved_block,
)


def test_report_has_errors_distinguishes_severity() -> None:
    """``has_errors`` returns True only for ``error`` severity."""
    report = FactCheckReport()
    assert report.has_errors() is False

    report.extend(
        [
            Finding(
                check=CHECK_MD_LINKS,
                severity="warning",
                location="Line 1",
                message="warn",
            )
        ]
    )
    assert report.has_errors() is False

    report.extend(
        [
            Finding(
                check=CHECK_MD_LINKS,
                severity="error",
                location="Line 2",
                message="err",
            )
        ]
    )
    assert report.has_errors() is True


def test_format_unresolved_block_empty_returns_empty() -> None:
    """No findings → empty string so callers can append unconditionally."""
    assert format_unresolved_block([]) == ""


def test_format_unresolved_block_renders_table() -> None:
    """The block contains a heading, a table, and one row per finding."""
    findings = [
        Finding(
            check=CHECK_PYTHON_REFS,
            severity="error",
            location="Line 77 (code fence)",
            message="`from attune.ops._readers import …` — module not importable",
        ),
        Finding(
            check=CHECK_MD_LINKS,
            severity="warning",
            location="Line 124",
            message="`[Concept](concepts/template-patterns.md)` — target does not exist",
        ),
    ]
    block = format_unresolved_block(findings)
    assert "## Unresolved references" in block
    assert "| Location | Severity | Issue |" in block
    assert "Line 77 (code fence)" in block
    assert "Line 124" in block
    # Severity rendered.
    assert "| error |" in block
    assert "| warning |" in block


def test_format_unresolved_block_escapes_pipes() -> None:
    """Pipe characters in messages are escaped so the table doesn't break."""
    findings = [
        Finding(
            check=CHECK_CLI_REFS,
            severity="error",
            location="Line 1",
            message="oops | this would break the table",
        )
    ]
    block = format_unresolved_block(findings)
    assert "oops \\| this would break" in block


def test_config_is_check_enabled_respects_global_toggle() -> None:
    """A False global toggle disables the check regardless of skip list."""
    cfg = FactCheckConfig(check_python_refs=False)
    assert cfg.is_check_enabled(CHECK_PYTHON_REFS) is False
    assert cfg.is_check_enabled(CHECK_PYTHON_REFS, "any.md") is False


def test_config_is_check_enabled_respects_skip_list() -> None:
    """Per-file skip turns off the check only for the matching path."""
    cfg = FactCheckConfig(skip={"docs/foo.md": [CHECK_MD_LINKS]})
    assert cfg.is_check_enabled(CHECK_MD_LINKS, "docs/foo.md") is False
    assert cfg.is_check_enabled(CHECK_MD_LINKS, "docs/bar.md") is True
    assert cfg.is_check_enabled(CHECK_PYTHON_REFS, "docs/foo.md") is True
