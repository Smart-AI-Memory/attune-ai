"""Code Review Report Formatting.

Human-readable report formatter for code review results.
Extracted from code_review.py for maintainability.

Contains:
- format_code_review_report: Formats code review output as a readable report

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations


def _format_perf_section(input_data: dict) -> list[str]:
    """Format the PERFORMANCE CHECK report section."""
    lines: list[str] = []
    perf_findings = input_data.get("perf_findings", [])
    perf_count = input_data.get("perf_finding_count", 0)
    perf_by_impact = input_data.get("perf_by_impact", {})
    if perf_count > 0 or perf_findings:
        perf_icon = (
            "🔴"
            if perf_by_impact.get("high", 0) > 0
            else ("🟡" if perf_by_impact.get("medium", 0) > 0 else "🟢")
        )
        lines.append("-" * 60)
        lines.append("PERFORMANCE CHECK")
        lines.append("-" * 60)
        lines.append(
            f"Perf Issues: {perf_icon} {perf_count} "
            f"(High: {perf_by_impact.get('high', 0)}, "
            f"Medium: {perf_by_impact.get('medium', 0)}, "
            f"Low: {perf_by_impact.get('low', 0)})",
        )
        if input_data.get("perf_deep_ran"):
            lines.append("Deep Analysis: ✅ LLM-validated")
        for finding in perf_findings[:10]:
            impact = finding.get("impact", "low").upper()
            desc = finding.get("description", "")
            file_loc = finding.get("file", "?")
            line_num = finding.get("line", "?")
            impact_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(impact, "⚪")
            line = f"  {impact_icon} [{impact}] {desc} ({file_loc}:{line_num})"
            if finding.get("false_positive"):
                line += " [FALSE POSITIVE]"
            lines.append(line)
            suggestion = finding.get("suggestion")
            if suggestion:
                lines.append(f"    → {suggestion}")
        lines.append("")
    elif "perf_findings" in input_data:
        lines.append("-" * 60)
        lines.append("PERFORMANCE CHECK")
        lines.append("-" * 60)
        lines.append("Perf Issues: 🟢 0 — No performance anti-patterns detected")
        lines.append("")
    return lines


def _format_health_section(input_data: dict) -> list[str]:
    """Format the HEALTH MONITOR report section."""
    lines: list[str] = []
    health_snapshot = input_data.get("health_snapshot", {})
    if health_snapshot:
        lines.append("-" * 60)
        lines.append("HEALTH MONITOR")
        lines.append("-" * 60)

        cache_stats = health_snapshot.get("cache_stats", {})
        if cache_stats:
            lines.append("Cache Metrics:")
            for name, stats in cache_stats.items():
                if isinstance(stats, dict):
                    hit_rate = stats.get("hit_rate", 0)
                    lines.append(f"  {name}: {hit_rate:.0%} hit rate")
                else:
                    lines.append(f"  {name}: {stats}")
        else:
            lines.append("Cache Metrics: No active caches")

        cost_today = health_snapshot.get("cost_today", {})
        if cost_today:
            total = cost_today.get("total_cost", cost_today.get("total", 0))
            lines.append(
                (
                    f"Cost Today: ${total:.4f}"
                    if isinstance(total, int | float)
                    else f"Cost Today: {total}"
                ),
            )
        else:
            lines.append("Cost Today: No cost data")

        usage_stats = health_snapshot.get("usage_stats_7d", {})
        if usage_stats:
            total_calls = usage_stats.get("total_calls", usage_stats.get("count", "N/A"))
            lines.append(f"Usage (7d): {total_calls} LLM calls")
        else:
            lines.append("Usage (7d): No telemetry data")
        lines.append("")
    return lines


def _format_quality_section(input_data: dict) -> list[str]:
    """Format the QUALITY CHECK report section."""
    lines: list[str] = []
    quality_findings = input_data.get("quality_findings", [])
    quality_count = input_data.get("quality_finding_count", 0)
    quality_by_severity = input_data.get("quality_by_severity", {})
    if quality_count > 0 or quality_findings:
        quality_icon = (
            "🔴"
            if quality_by_severity.get("high", 0) > 0
            else ("🟡" if quality_by_severity.get("medium", 0) > 0 else "🟢")
        )
        lines.append("-" * 60)
        lines.append("QUALITY CHECK")
        lines.append("-" * 60)
        lines.append(
            f"Quality Issues: {quality_icon} {quality_count} "
            f"(High: {quality_by_severity.get('high', 0)}, "
            f"Medium: {quality_by_severity.get('medium', 0)}, "
            f"Low: {quality_by_severity.get('low', 0)})",
        )
        if input_data.get("quality_deep_ran"):
            lines.append("Deep Analysis: ✅ LLM-validated")
        for finding in quality_findings[:10]:
            severity = finding.get("severity", "low").upper()
            desc = finding.get("description", "")
            file_loc = finding.get("file", "?")
            line_num = finding.get("line")
            loc_str = f"{file_loc}:{line_num}" if line_num else file_loc
            sev_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")
            line = f"  {sev_icon} [{severity}] {desc} ({loc_str})"
            if finding.get("false_positive"):
                line += " [FALSE POSITIVE]"
            lines.append(line)
            suggestion = finding.get("suggestion")
            if suggestion:
                lines.append(f"    → {suggestion}")
        lines.append("")
    elif "quality_findings" in input_data:
        lines.append("-" * 60)
        lines.append("QUALITY CHECK")
        lines.append("-" * 60)
        lines.append("Quality Issues: 🟢 0 — No quality issues detected")
        lines.append("")
    return lines


def _format_security_section(input_data: dict) -> list[str]:
    """Format security analysis section."""
    lines = []
    has_critical = input_data.get("has_critical_issues", False)
    security_score = input_data.get("security_score", 100)
    security_icon = "🔴" if has_critical else ("🟡" if security_score < 90 else "🟢")

    lines.append("-" * 60)
    lines.append("SECURITY ANALYSIS")
    lines.append("-" * 60)
    lines.append(f"Security Score: {security_icon} {security_score}/100")
    lines.append(f"Critical Issues: {'Yes' if has_critical else 'No'}")
    lines.append("")

    security_findings = input_data.get("security_findings", [])
    if security_findings:
        lines.append("Security Findings:")
        for finding in security_findings[:10]:
            severity = finding.get("severity", "unknown").upper()
            title = finding.get("title", "N/A")
            sev_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(
                severity,
                "⚪",
            )
            lines.append(f"  {sev_icon} [{severity}] {title}")
        lines.append("")

    scan_results = input_data.get("scan_results", "")
    if scan_results:
        lines.append("Scan Summary:")
        summary = scan_results[:800] + ("..." if len(scan_results) > 800 else "")
        lines.append(summary)
        lines.append("")
    return lines


def _format_crew_section(crew_review: dict) -> list[str]:
    """Format crew review section."""
    lines = ["-" * 60, "CREW REVIEW ANALYSIS", "-" * 60]
    lines.append(f"Quality Score: {crew_review.get('quality_score', 'N/A')}/100")
    lines.append(f"Finding Count: {crew_review.get('finding_count', 0)}")
    agents = crew_review.get("agents_used", [])
    if agents:
        lines.append(f"Agents Used: {', '.join(agents)}")
    summary = crew_review.get("summary", "")
    if summary:
        lines.append(f"Summary: {summary[:300]}")
    lines.append("")
    return lines


def _format_no_content_message() -> list[str]:
    """Format help message when no review content was generated."""
    return [
        "-" * 60,
        "NO ISSUES FOUND",
        "-" * 60,
        "",
        "The code review workflow completed but found no issues to report.",
        "This could mean:",
        "  • No code was provided for review (check input parameters)",
        "  • The code is clean and follows best practices",
        "  • The workflow needs configuration (check .attune/workflows.yaml)",
        "",
        "Tip: Try running with a specific file or diff:",
        '  empathy workflow run code-review --input \'{"target": "path/to/file.py"}\'',
        "",
    ]


def format_code_review_report(result: dict, input_data: dict) -> str:
    """Format code review output as a human-readable report.

    Renders all workflow stage results — classification, security scan,
    performance check, health monitor, quality check, architectural review,
    and crew review — into a structured text report.

    Args:
        result: Final stage result dict (verdict, recommendations, etc.)
        input_data: Accumulated data from all prior stages

    Returns:
        Formatted report string

    """
    if input_data.get("error"):
        return "\n".join(
            [
                "=" * 60,
                "CODE REVIEW - INPUT ERROR",
                "=" * 60,
                "",
                input_data.get("error_message", "No code provided for review."),
                "",
                "=" * 60,
            ]
        )

    lines = []
    verdict = result.get("verdict", "unknown").upper().replace("_", " ")
    verdict_icon = {
        "APPROVE": "✅",
        "APPROVE WITH SUGGESTIONS": "🔶",
        "REQUEST CHANGES": "⚠️",
        "REJECT": "❌",
    }.get(verdict, "❓")

    lines.append("=" * 60)
    lines.append("CODE REVIEW REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Verdict: {verdict_icon} {verdict}")
    lines.append("")

    classification = input_data.get("classification", "")
    if classification:
        lines.extend(["-" * 60, "CLASSIFICATION", "-" * 60, classification[:500], ""])

    lines.extend(_format_security_section(input_data))
    lines.extend(_format_perf_section(input_data))
    lines.extend(_format_health_section(input_data))
    lines.extend(_format_quality_section(input_data))

    arch_review = result.get("architectural_review", "")
    if arch_review:
        lines.extend(["-" * 60, "ARCHITECTURAL REVIEW", "-" * 60, arch_review, ""])

    recommendations = result.get("recommendations", [])
    if recommendations:
        lines.extend(["-" * 60, "RECOMMENDATIONS", "-" * 60])
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    crew_review = input_data.get("crew_review", {})
    if crew_review and crew_review.get("available") and not crew_review.get("fallback"):
        lines.extend(_format_crew_section(crew_review))

    content_sections = [
        input_data.get("classification"),
        input_data.get("security_findings"),
        input_data.get("scan_results"),
        input_data.get("perf_findings"),
        input_data.get("health_snapshot"),
        input_data.get("quality_findings"),
        result.get("architectural_review"),
        result.get("recommendations"),
    ]
    if not any(content_sections) and len(lines) < 15:
        lines.extend(_format_no_content_message())

    lines.append("=" * 60)
    model_tier = result.get("model_tier_used", "unknown")
    lines.append(f"Review completed using {model_tier} tier model")
    lines.append("=" * 60)

    return "\n".join(lines)
