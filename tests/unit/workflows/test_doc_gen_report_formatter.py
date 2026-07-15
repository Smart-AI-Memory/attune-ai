"""Characterization tests (behavior pins) for format_doc_gen_report.

These tests pin the CURRENT exact behavior of
``attune.workflows.document_gen.report_formatter.format_doc_gen_report``
before a complexity refactor (radon D29). Do not "fix" expected output
here without a deliberate behavior change — the refactor must be
provably behavior-preserving against these pins.

The function is pure (dict in, str out) — no fixtures or patching.
"""

from attune.workflows.document_gen.report_formatter import format_doc_gen_report

EQ = "=" * 60
DASH = "-" * 60


# ---------------------------------------------------------------------------
# Full-output pins (exact ==)
# ---------------------------------------------------------------------------

EXPECTED_MINIMAL = """\
============================================================
DOCUMENTATION GENERATION REPORT
============================================================

Document Type: General
Target Audience: Developers

------------------------------------------------------------
STATISTICS
------------------------------------------------------------
Word Count: 0
Section Count: ~0

============================================================
Generated using unknown tier model
============================================================"""


def test_minimal_inputs_full_pin() -> None:
    """Empty dicts: defaults everywhere, only header/stats/footer emitted."""
    out = format_doc_gen_report({}, {})
    assert out == EXPECTED_MINIMAL


RICH_OUTLINE = """\
1. Introduction
   - overview
2. Usage
   - basics
3. Advanced
   - tips
4. FAQ
   - common
5. Appendix
   - extras
6. Glossary
   - terms"""

RICH_DOCUMENT = """\
## Intro
Alpha beta gamma.

## Usage
Delta epsilon."""

EXPECTED_RICH = """\
============================================================
DOCUMENTATION GENERATION REPORT
============================================================

Document Type: Api Reference
Target Audience: End Users

------------------------------------------------------------
DOCUMENT OUTLINE
------------------------------------------------------------
1. Introduction
   - overview
2. Usage
   - basics
3. Advanced
   - tips
4. FAQ
   - common
5. Appendix
   - extras
...

------------------------------------------------------------
GENERATED DOCUMENTATION
------------------------------------------------------------

## Intro
Alpha beta gamma.

## Usage
Delta epsilon.

------------------------------------------------------------
STATISTICS
------------------------------------------------------------
Word Count: 9
Section Count: ~2
Generation Mode: Chunked (2/4 chunks completed)
Polish Mode: Chunked (3 sections)
Estimated Cost: $1.50

------------------------------------------------------------
FILE EXPORT
------------------------------------------------------------
Documentation saved to: /tmp/out.md
Report saved to: /tmp/report.md

Full documentation is available in the exported file.

------------------------------------------------------------
⚠️  WARNING
------------------------------------------------------------
Cost limit reached

------------------------------------------------------------
SCOPE NOTICE
------------------------------------------------------------
⚠️  DOCUMENTATION MAY BE INCOMPLETE
   Planned sections: 6
   Generated sections: 2

To generate missing sections, re-run with section_focus:
   workflow = DocumentGenerationWorkflow(
       section_focus=["Testing Guide", "API Reference"]
   )

============================================================
Generated using capable tier model
============================================================"""


def test_rich_inputs_full_pin() -> None:
    """Every optional section active at once, pinned end to end.

    Exercises: underscore->title transforms, >10-line outline
    truncation ("..."), document section, chunked+stopped_early stats,
    polish_chunked, cost line, export with report_path, input warning,
    scope notice with planned-sections sub-branch, explicit model tier.
    """
    result = {
        "doc_type": "api_reference",
        "audience": "end_users",
        "document": RICH_DOCUMENT,
        "accumulated_cost": 1.5,
        "polish_chunked": True,
        "polish_chunks": 3,
        "export_path": "/tmp/out.md",
        "report_path": "/tmp/report.md",
        "model_tier_used": "capable",
    }
    input_data = {
        "outline": RICH_OUTLINE,
        "chunked": True,
        "chunk_count": 4,
        "chunks_completed": 2,
        "stopped_early": True,
        "warning": "Cost limit reached",
    }
    out = format_doc_gen_report(result, input_data)
    assert out == EXPECTED_RICH


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


def test_header_underscore_title_transform() -> None:
    out = format_doc_gen_report({"doc_type": "user_guide", "audience": "new_team_members"}, {})
    assert "Document Type: User Guide" in out
    assert "Target Audience: New Team Members" in out


# ---------------------------------------------------------------------------
# Outline
# ---------------------------------------------------------------------------


def test_outline_short_no_truncation_marker() -> None:
    """Outline of exactly 10 lines shows fully, no '...' line."""
    outline = "\n".join(f"line {i}" for i in range(10))
    out = format_doc_gen_report({}, {"outline": outline})
    assert "DOCUMENT OUTLINE" in out
    assert "line 9" in out
    assert "\n...\n" not in out


def test_outline_eleven_lines_truncated_with_ellipsis() -> None:
    outline = "\n".join(f"line {i}" for i in range(11))
    out = format_doc_gen_report({}, {"outline": outline})
    assert "line 9" in out
    assert "line 10" not in out
    assert "\n...\n" in out


# ---------------------------------------------------------------------------
# Statistics / chunking
# ---------------------------------------------------------------------------


def test_chunked_without_stopped_early() -> None:
    out = format_doc_gen_report({}, {"chunked": True, "chunk_count": 4})
    assert "Generation Mode: Chunked (4 chunks)" in out
    assert "chunks completed" not in out


def test_chunks_completed_defaults_to_chunk_count() -> None:
    """Without chunks_completed, stopped_early reports N/N completed."""
    out = format_doc_gen_report({}, {"chunked": True, "chunk_count": 3, "stopped_early": True})
    assert "Generation Mode: Chunked (3/3 chunks completed)" in out


def test_not_chunked_omits_generation_mode() -> None:
    out = format_doc_gen_report({}, {"chunk_count": 5})
    assert "Generation Mode" not in out


def test_polish_chunked_defaults_polish_chunks_to_zero() -> None:
    out = format_doc_gen_report({"polish_chunked": True}, {})
    assert "Polish Mode: Chunked (0 sections)" in out


def test_zero_cost_omits_cost_line() -> None:
    out = format_doc_gen_report({"accumulated_cost": 0}, {})
    assert "Estimated Cost" not in out


def test_positive_cost_formatted_two_decimals() -> None:
    out = format_doc_gen_report({"accumulated_cost": 0.005}, {})
    assert "Estimated Cost: $0.01" in out


def test_word_and_section_counts_from_document() -> None:
    """word count is whitespace-split tokens (## markers count as words);
    section count is raw '##' substring occurrences."""
    out = format_doc_gen_report({"document": "## A\none two\n## B\nthree"}, {})
    assert "Word Count: 7" in out
    assert "Section Count: ~2" in out
    assert "GENERATED DOCUMENTATION" in out


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_export_path_without_report_path() -> None:
    out = format_doc_gen_report({"export_path": "/tmp/doc.md"}, {})
    assert "FILE EXPORT" in out
    assert "Documentation saved to: /tmp/doc.md" in out
    assert "Report saved to:" not in out
    assert "Full documentation is available in the exported file." in out


def test_no_export_path_omits_export_section() -> None:
    out = format_doc_gen_report({"report_path": "/tmp/r.md"}, {})
    # report_path alone is ignored — export section keyed on export_path
    assert "FILE EXPORT" not in out
    assert "Report saved to:" not in out


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------


def test_warning_from_result() -> None:
    out = format_doc_gen_report({"warning": "result-side warning"}, {})
    assert "⚠️  WARNING" in out
    assert "result-side warning" in out


def test_input_warning_takes_precedence_over_result() -> None:
    out = format_doc_gen_report({"warning": "from result"}, {"warning": "from input"})
    assert "from input" in out
    assert "from result" not in out


def test_empty_input_warning_falls_back_to_result() -> None:
    """Falsy input warning ('' ) falls through the `or` to result's."""
    out = format_doc_gen_report({"warning": "from result"}, {"warning": ""})
    assert "from result" in out


def test_stopped_early_without_warning_default_message() -> None:
    out = format_doc_gen_report({}, {"stopped_early": True})
    assert "⚠️  WARNING" in out
    assert "Generation stopped early due to cost or error limits." in out


def test_stopped_early_with_warning_no_default_message() -> None:
    out = format_doc_gen_report({}, {"stopped_early": True, "warning": "budget hit"})
    assert "budget hit" in out
    assert "Generation stopped early due to cost or error limits." not in out


def test_no_warning_no_warning_section() -> None:
    out = format_doc_gen_report({}, {})
    assert "WARNING" not in out


# ---------------------------------------------------------------------------
# Truncation indicators -> SCOPE NOTICE
# ---------------------------------------------------------------------------


def test_truncation_trailing_ellipsis() -> None:
    out = format_doc_gen_report({"document": "Some words trailing off..."}, {})
    assert "SCOPE NOTICE" in out
    assert "⚠️  DOCUMENTATION MAY BE INCOMPLETE" in out
    # no outline -> planned_sections == 0 -> counts sub-branch skipped
    assert "Planned sections:" not in out
    assert "Generated sections:" not in out
    assert 'section_focus=["Testing Guide", "API Reference"]' in out


def test_truncation_trailing_dash() -> None:
    out = format_doc_gen_report({"document": "A sentence cut mid -"}, {})
    assert "SCOPE NOTICE" in out


def test_truncation_unclosed_code_fence() -> None:
    out = format_doc_gen_report({"document": "Intro text\n```python\nx = 1\nstill open"}, {})
    assert "SCOPE NOTICE" in out


def test_even_code_fences_not_truncated() -> None:
    out = format_doc_gen_report({"document": "Intro\n```py\nx = 1\n```\nAll closed here"}, {})
    assert "SCOPE NOTICE" not in out


def test_truncation_continuation_phrase_case_insensitive() -> None:
    out = format_doc_gen_report({"document": "Chapter one. To Be Continued in the sequel"}, {})
    assert "SCOPE NOTICE" in out


def test_clean_document_no_scope_notice() -> None:
    out = format_doc_gen_report({"document": "## Alpha\nAll good here"}, {})
    assert "SCOPE NOTICE" not in out


# ---------------------------------------------------------------------------
# Planned-sections regex + scope-notice threshold
# ---------------------------------------------------------------------------


def test_planned_sections_regex_counting() -> None:
    """Only stripped lines matching r'^(\\d+)\\.\\s+([A-Za-z].*)' count.

    '2) Skip' (paren), 'A. Skip' (letter), '3. 42skip' (digit after
    number) are NOT counted; indented and multi-digit numbered lines ARE.
    """
    outline = "\n".join(
        [
            "1. Introduction",
            "2) Skip paren style",
            "A. Skip letter style",
            "3. 42skip digit-first title",
            "  4. Indented counted",
            "10. Ten counted",
        ]
    )
    # No document -> section_count 0 < planned - 1 -> scope notice fires
    out = format_doc_gen_report({}, {"outline": outline})
    assert "SCOPE NOTICE" in out
    assert "   Planned sections: 3" in out
    assert "   Generated sections: 0" in out


def test_no_scope_notice_when_sections_meet_plan() -> None:
    """section_count == planned - 1 is tolerated (strict < in the check).

    Note: the second disjunct `planned_sections > section_count + 1` is
    mathematically equivalent to the planned-sections half of
    is_truncated, so it never fires independently — pinned as-is.
    """
    outline = "1. Alpha\n2. Beta"
    out = format_doc_gen_report({"document": "## Alpha\nwords only here"}, {"outline": outline})
    # planned=2, section_count=1: 1 < 1 is False and 2 > 2 is False
    assert "SCOPE NOTICE" not in out


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------


def test_footer_model_tier_default_unknown() -> None:
    out = format_doc_gen_report({}, {})
    assert out.endswith(f"Generated using unknown tier model\n{EQ}")


def test_footer_model_tier_explicit() -> None:
    out = format_doc_gen_report({"model_tier_used": "premium"}, {})
    assert "Generated using premium tier model" in out
