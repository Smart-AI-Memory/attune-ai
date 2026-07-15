"""Document Generation Report Formatter.

Format documentation generation output as human-readable reports.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import re

_RULE = "-" * 60
_EDGE = "=" * 60

# Top-level outline entries look like "1. Section Name".
_TOP_LEVEL_PATTERN = re.compile(r"^(\d+)\.\s+([A-Za-z].*)")


def _header_lines(result: dict) -> list[str]:
    """Report banner with document type and audience."""
    doc_type = result.get("doc_type", "general").replace("_", " ").title()
    audience = result.get("audience", "developers").replace("_", " ").title()
    return [
        _EDGE,
        "DOCUMENTATION GENERATION REPORT",
        _EDGE,
        "",
        f"Document Type: {doc_type}",
        f"Target Audience: {audience}",
        "",
    ]


def _outline_lines(outline: str) -> list[str]:
    """Outline preview section — first 10 lines, "..." when truncated."""
    if not outline:
        return []
    lines = [_RULE, "DOCUMENT OUTLINE", _RULE]
    outline_lines = outline.split("\n")
    lines.extend(outline_lines[:10])
    if len(outline_lines) > 10:
        lines.append("...")
    lines.append("")
    return lines


def _document_lines(document: str) -> list[str]:
    """The generated document body section."""
    if not document:
        return []
    return [_RULE, "GENERATED DOCUMENTATION", _RULE, "", document, ""]


def _statistics_lines(
    result: dict, input_data: dict, word_count: int, section_count: int
) -> list[str]:
    """Statistics section — counts, chunking modes, cost."""
    was_chunked = input_data.get("chunked", False)
    chunk_count = input_data.get("chunk_count", 0)
    chunks_completed = input_data.get("chunks_completed", chunk_count)
    stopped_early = input_data.get("stopped_early", False)
    accumulated_cost = result.get("accumulated_cost", 0)
    polish_chunked = result.get("polish_chunked", False)

    lines = [
        _RULE,
        "STATISTICS",
        _RULE,
        f"Word Count: {word_count}",
        f"Section Count: ~{section_count}",
    ]
    if was_chunked:
        if stopped_early:
            lines.append(
                f"Generation Mode: Chunked ({chunks_completed}/{chunk_count} chunks completed)",
            )
        else:
            lines.append(f"Generation Mode: Chunked ({chunk_count} chunks)")
    if polish_chunked:
        polish_chunks = result.get("polish_chunks", 0)
        lines.append(f"Polish Mode: Chunked ({polish_chunks} sections)")
    if accumulated_cost > 0:
        lines.append(f"Estimated Cost: ${accumulated_cost:.2f}")
    lines.append("")
    return lines


def _export_lines(result: dict) -> list[str]:
    """File-export section — only when an export path exists."""
    export_path = result.get("export_path")
    if not export_path:
        return []
    lines = [_RULE, "FILE EXPORT", _RULE, f"Documentation saved to: {export_path}"]
    report_path = result.get("report_path")
    if report_path:
        lines.append(f"Report saved to: {report_path}")
    lines.extend(["", "Full documentation is available in the exported file.", ""])
    return lines


def _warning_lines(result: dict, input_data: dict) -> list[str]:
    """Warning section — cost limit, errors, early stop."""
    warning = input_data.get("warning") or result.get("warning")
    stopped_early = input_data.get("stopped_early", False)
    if not (warning or stopped_early):
        return []
    lines = [_RULE, "⚠️  WARNING", _RULE]
    if warning:
        lines.append(warning)
    if stopped_early and not warning:
        lines.append("Generation stopped early due to cost or error limits.")
    lines.append("")
    return lines


def _count_planned_sections(outline: str) -> int:
    """Count top-level numbered entries ("1. Foo") in the outline."""
    if not outline:
        return 0
    return sum(1 for line in outline.split("\n") if _TOP_LEVEL_PATTERN.match(line.strip()))


def _scope_notice_lines(document: str, outline: str, section_count: int) -> list[str]:
    """Truncation / incomplete-scope notice.

    Note (pinned by the characterization suite): the historical
    ``planned_sections > section_count + 1`` disjunct was mathematically
    implied by ``is_truncated``'s planned-sections clause, so the notice
    fires exactly when a truncation indicator hits or
    ``section_count < planned_sections - 1``.
    """
    truncation_indicators = []
    if document:  # Handle None or empty document
        truncation_indicators = [
            document.rstrip().endswith("..."),
            document.rstrip().endswith("-"),
            "```" in document and document.count("```") % 2 != 0,  # Unclosed code block
            any(
                phrase in document.lower()
                for phrase in ["continued in", "see next section", "to be continued"]
            ),
        ]

    planned_sections = _count_planned_sections(outline)
    is_truncated = any(truncation_indicators) or (
        planned_sections > 0 and section_count < planned_sections - 1
    )
    if not is_truncated:
        return []

    lines = [_RULE, "SCOPE NOTICE", _RULE, "⚠️  DOCUMENTATION MAY BE INCOMPLETE"]
    if planned_sections > 0:
        lines.append(f"   Planned sections: {planned_sections}")
        lines.append(f"   Generated sections: {section_count}")
    lines.extend(
        [
            "",
            "To generate missing sections, re-run with section_focus:",
            "   workflow = DocumentGenerationWorkflow(",
            '       section_focus=["Testing Guide", "API Reference"]',
            "   )",
            "",
        ]
    )
    return lines


def format_doc_gen_report(result: dict, input_data: dict) -> str:
    """Format document generation output as a human-readable report.

    Args:
        result: The polish stage result
        input_data: Input data from previous stages

    Returns:
        Formatted report string

    """
    outline = input_data.get("outline", "")
    document = result.get("document", "")
    word_count = len(document.split()) if document else 0
    section_count = document.count("##") if document else 0  # Count markdown headers

    lines = _header_lines(result)
    lines += _outline_lines(outline)
    lines += _document_lines(document)
    lines += _statistics_lines(result, input_data, word_count, section_count)
    lines += _export_lines(result)
    lines += _warning_lines(result, input_data)
    lines += _scope_notice_lines(document, outline, section_count)

    # Footer
    model_tier = result.get("model_tier_used", "unknown")
    lines += [_EDGE, f"Generated using {model_tier} tier model", _EDGE]

    return "\n".join(lines)
