"""Report formatting for the ManageDocumentation crew workflow.

Contains the report generation logic extracted from
manage_documentation.py for maintainability.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .doc_crew_models import ManageDocumentationCrewResult


def format_manage_docs_report(result: ManageDocumentationCrewResult, path: str) -> str:
    """Format documentation management output as a human-readable report.

    Args:
        result: The ManageDocumentationCrewResult
        path: The path that was analyzed

    Returns:
        Formatted report string
    """
    lines: list[str] = []

    # Header with confidence
    confidence = result.confidence
    if confidence >= 0.8:
        confidence_icon = "\U0001f7e2"
        confidence_text = "HIGH CONFIDENCE"
    elif confidence >= 0.5:
        confidence_icon = "\U0001f7e1"
        confidence_text = "MODERATE CONFIDENCE"
    else:
        confidence_icon = "\U0001f534"
        confidence_text = "LOW CONFIDENCE (Mock Mode)"

    lines.append("=" * 60)
    lines.append("DOCUMENTATION SYNC REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Path Analyzed: {path}")
    lines.append(f"Confidence: {confidence_icon} {confidence_text} " f"({confidence:.0%})")
    lines.append("")

    # Summary
    lines.append("-" * 60)
    lines.append("SUMMARY")
    lines.append("-" * 60)
    lines.append(f"Files Analyzed: {result.files_analyzed}")
    lines.append(f"Docs Needing Update: {result.docs_needing_update}")
    lines.append(f"New Docs Needed: {result.new_docs_needed}")
    lines.append(f"Duration: {result.duration_ms}ms " f"({result.duration_ms / 1000:.1f}s)")
    lines.append(f"Cost: ${result.cost:.4f}")
    lines.append("")

    # Agent Findings
    if result.findings:
        lines.append("-" * 60)
        lines.append("AGENT FINDINGS")
        lines.append("-" * 60)
        for i, finding in enumerate(result.findings, 1):
            agent = finding.get("agent", f"Agent {i}")
            response = finding.get("response", "")
            thinking = finding.get("thinking", "")
            answer = finding.get("answer", "")
            has_xml = finding.get("has_xml_structure", False)
            cost = finding.get("cost", 0.0)

            xml_label = " \U0001f52c XML-Structured" if has_xml else ""
            lines.append(f"\n{i}. {agent} (Cost: ${cost:.4f}){xml_label}")
            lines.append("   " + "-" * 54)

            # Show thinking and answer separately if available
            if has_xml and thinking:
                lines.append("   \U0001f4ad Thinking:")
                if len(thinking) > 300:
                    lines.append(f"   {thinking[:300]}...")
                else:
                    lines.append(f"   {thinking}")
                lines.append("")
                lines.append("   \u2705 Answer:")
                if len(answer) > 300:
                    lines.append(f"   {answer[:300]}...")
                else:
                    lines.append(f"   {answer}")
            else:
                # Fallback to original response
                if len(response) > 500:
                    lines.append(f"   {response[:500]}...")
                    lines.append(f"   [Truncated - {len(response)} chars total]")
                else:
                    lines.append(f"   {response}")
            lines.append("")

    # Recommendations
    if result.recommendations:
        lines.append("-" * 60)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 60)
        for i, rec in enumerate(result.recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    # Next Steps
    lines.append("-" * 60)
    lines.append("NEXT STEPS")
    lines.append("-" * 60)
    lines.append("1. Review agent findings above for specific files")
    lines.append("2. Prioritize documentation updates based on impact")
    lines.append("3. Use 'Generate Docs' workflow for auto-generation")
    lines.append("4. Run this workflow periodically to keep docs in sync")
    lines.append("")

    # Footer
    lines.append("=" * 60)
    if result.success:
        lines.append("\u2705 Documentation sync analysis complete")
    else:
        lines.append("\u274c Documentation sync analysis failed")
    lines.append("=" * 60)

    return "\n".join(lines)
