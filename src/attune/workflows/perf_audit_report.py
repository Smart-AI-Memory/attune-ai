"""Performance Audit Report Formatting

Functions to create human-readable and Rich-renderable reports
from performance audit results.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .output import Finding, WorkflowReport


def create_perf_audit_workflow_report(result: dict, input_data: dict) -> WorkflowReport:
    """Create a WorkflowReport from performance audit results.

    Args:
        result: The optimize stage result
        input_data: Input data from previous stages

    Returns:
        WorkflowReport instance for Rich or plain text rendering
    """
    perf_score = result.get("perf_score", 0)
    perf_level = result.get("perf_level", "unknown")

    # Determine report level
    if perf_score >= 85:
        level = "success"
    elif perf_score >= 50:
        level = "warning"
    else:
        level = "error"

    # Build summary
    files_scanned = input_data.get("files_scanned", 0)
    finding_count = input_data.get("finding_count", 0)
    by_impact = input_data.get("by_impact", {})

    summary = (
        f"Scanned {files_scanned} files, found "
        f"{finding_count} issues. "
        f"High: {by_impact.get('high', 0)}, "
        f"Medium: {by_impact.get('medium', 0)}, "
        f"Low: {by_impact.get('low', 0)}"
    )

    report = WorkflowReport(
        title="Performance Audit Report",
        summary=summary,
        score=perf_score,
        level=level,
        metadata={
            "perf_level": perf_level,
            "files_scanned": files_scanned,
            "finding_count": finding_count,
        },
    )

    # Add top issues section
    top_issues = result.get("top_issues", [])
    if top_issues:
        issues_content = {
            issue.get("type", "unknown")
            .replace("_", " ")
            .title(): f"{issue.get('count', 0)} occurrences"
            for issue in top_issues
        }
        report.add_section("Top Performance Issues", issues_content)

    # Add hotspots section
    hotspot_result = input_data.get("hotspot_result", {})
    hotspots = hotspot_result.get("hotspots", [])
    if hotspots:
        hotspot_content = {
            "Critical Hotspots": hotspot_result.get("critical_count", 0),
            "Moderate Hotspots": hotspot_result.get("moderate_count", 0),
        }
        report.add_section("Hotspot Summary", hotspot_content)

    # Add findings section
    findings = input_data.get("findings", [])
    high_impact = [f for f in findings if f.get("impact") == "high"]
    if high_impact:
        finding_objs = [
            Finding(
                severity="high",
                file=f.get("file", "unknown"),
                line=f.get("line"),
                message=f.get("description", ""),
            )
            for f in high_impact[:10]
        ]
        report.add_section("High Impact Findings", finding_objs, style="error")

    # Add recommendations section
    optimization_plan = result.get("optimization_plan", "")
    if optimization_plan:
        report.add_section("Optimization Recommendations", optimization_plan)

    return report


def format_perf_audit_report(result: dict, input_data: dict) -> str:
    """Format performance audit output as a human-readable report.

    Args:
        result: The optimize stage result
        input_data: Input data from previous stages

    Returns:
        Formatted report string
    """
    lines: list[str] = []

    # Header with performance score
    perf_score = result.get("perf_score", 0)
    perf_level = result.get("perf_level", "unknown").upper()

    if perf_score >= 85:
        perf_icon = "\U0001f7e2"
        perf_text = "EXCELLENT"
    elif perf_score >= 75:
        perf_icon = "\U0001f7e1"
        perf_text = "GOOD"
    elif perf_score >= 50:
        perf_icon = "\U0001f7e0"
        perf_text = "NEEDS OPTIMIZATION"
    else:
        perf_icon = "\U0001f534"
        perf_text = "CRITICAL"

    lines.append("=" * 60)
    lines.append("PERFORMANCE AUDIT REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Performance Score: {perf_icon} " f"{perf_score}/100 ({perf_text})")
    lines.append(f"Performance Level: {perf_level}")
    lines.append("")

    # Scan summary
    files_scanned = input_data.get("files_scanned", 0)
    finding_count = input_data.get("finding_count", 0)
    by_impact = input_data.get("by_impact", {})

    lines.append("-" * 60)
    lines.append("SCAN SUMMARY")
    lines.append("-" * 60)
    lines.append(f"Files Scanned: {files_scanned}")
    lines.append(f"Issues Found: {finding_count}")
    lines.append("")
    lines.append("Issues by Impact:")
    lines.append(f"  \U0001f534 High: {by_impact.get('high', 0)}")
    lines.append(f"  \U0001f7e1 Medium: {by_impact.get('medium', 0)}")
    lines.append(f"  \U0001f7e2 Low: {by_impact.get('low', 0)}")
    lines.append("")

    # Top issues
    top_issues = result.get("top_issues", [])
    if top_issues:
        lines.append("-" * 60)
        lines.append("TOP PERFORMANCE ISSUES")
        lines.append("-" * 60)
        for issue in top_issues:
            issue_type = issue.get("type", "unknown").replace("_", " ").title()
            count = issue.get("count", 0)
            lines.append(f"  \u2022 {issue_type}: {count} occurrences")
        lines.append("")

    # Hotspots
    hotspot_result = input_data.get("hotspot_result", {})
    hotspots = hotspot_result.get("hotspots", [])
    if hotspots:
        lines.append("-" * 60)
        lines.append("PERFORMANCE HOTSPOTS")
        lines.append("-" * 60)
        lines.append("Critical Hotspots: " f"{hotspot_result.get('critical_count', 0)}")
        lines.append("Moderate Hotspots: " f"{hotspot_result.get('moderate_count', 0)}")
        lines.append("")
        for h in hotspots[:8]:
            file_path = h.get("file", "unknown")
            score = h.get("complexity_score", 0)
            concerns = h.get("concerns", [])
            if score >= 20:
                score_icon = "\U0001f534"
            elif score >= 10:
                score_icon = "\U0001f7e0"
            else:
                score_icon = "\U0001f7e1"
            lines.append(f"  {score_icon} {file_path}")
            lines.append(f"      Score: {score} | " f"Concerns: {', '.join(concerns[:3])}")
        lines.append("")

    # High impact findings
    findings = input_data.get("findings", [])
    high_impact = [f for f in findings if f.get("impact") == "high"]
    if high_impact:
        lines.append("-" * 60)
        lines.append("HIGH IMPACT FINDINGS")
        lines.append("-" * 60)
        for f in high_impact[:10]:
            file_path = f.get("file", "unknown")
            line = f.get("line", "?")
            desc = f.get("description", "Unknown issue")
            lines.append(f"  \U0001f534 {file_path}:{line}")
            lines.append(f"      {desc}")
        lines.append("")

    # Optimization recommendations
    optimization_plan = result.get("optimization_plan", "")
    if optimization_plan:
        lines.append("-" * 60)
        lines.append("OPTIMIZATION RECOMMENDATIONS")
        lines.append("-" * 60)
        lines.append(optimization_plan)
        lines.append("")

    # Footer
    lines.append("=" * 60)
    model_tier = result.get("model_tier_used", "unknown")
    rec_count = result.get("recommendation_count", 0)
    lines.append(f"Analyzed {rec_count} hotspots " f"using {model_tier} tier model")
    lines.append("=" * 60)

    return "\n".join(lines)
