"""Refactor Plan Report Formatting and CLI

Human-readable report generation for refactor plan workflow output,
plus CLI entry point.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any

# Debt markers imported here to avoid circular dependency
# (these are defined in refactor_plan.py but needed for report formatting)
DEBT_MARKERS_SEVERITY = {
    "TODO": {"severity": "low"},
    "FIXME": {"severity": "medium"},
    "HACK": {"severity": "high"},
    "XXX": {"severity": "medium"},
    "BUG": {"severity": "high"},
    "OPTIMIZE": {"severity": "low"},
    "REFACTOR": {"severity": "medium"},
}


def format_refactor_plan_report(result: dict, input_data: dict) -> str:
    """Format refactor plan output as a human-readable report.

    Args:
        result: The plan stage result
        input_data: Input data from previous stages

    Returns:
        Formatted report string

    """
    lines: list[str] = []

    # Header with trajectory
    summary = result.get("summary", {})
    total_debt = summary.get("total_debt", 0)
    trajectory = summary.get("trajectory", "unknown")
    high_priority_count = summary.get("high_priority_count", 0)

    # Trajectory icon
    if trajectory == "increasing":
        traj_icon = "\U0001f4c8"
        traj_text = "INCREASING"
    elif trajectory == "decreasing":
        traj_icon = "\U0001f4c9"
        traj_text = "DECREASING"
    else:
        traj_icon = "\u27a1\ufe0f"
        traj_text = "STABLE"

    lines.append("=" * 60)
    lines.append("REFACTOR PLAN REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Total Tech Debt Items: {total_debt}")
    lines.append(f"Trajectory: {traj_icon} {traj_text}")
    lines.append(f"High Priority Items: {high_priority_count}")
    lines.append("")

    # Scan summary
    _format_scan_summary(lines, input_data)

    # Analysis
    analysis = input_data.get("analysis", {})
    _format_trajectory_analysis(lines, analysis)

    # Hotspots
    hotspots = analysis.get("hotspots", [])
    _format_hotspots(lines, hotspots)

    # High priority items
    high_priority = input_data.get("high_priority", [])
    _format_high_priority(lines, high_priority)

    # Refactoring plan from LLM
    _format_roadmap(lines, result)

    # Footer
    lines.append("=" * 60)
    model_tier = result.get("model_tier_used", "unknown")
    lines.append(f"Analyzed {total_debt} debt items using {model_tier} tier model")
    lines.append("=" * 60)

    return "\n".join(lines)


def _format_scan_summary(lines: list[str], input_data: dict) -> None:
    """Format the debt scan summary section."""
    by_marker: dict[str, int] = input_data.get("by_marker", {})
    files_scanned = input_data.get("files_scanned", 0)

    lines.append("-" * 60)
    lines.append("DEBT SCAN SUMMARY")
    lines.append("-" * 60)
    lines.append(f"Files Scanned: {files_scanned}")
    if by_marker:
        lines.append("By Marker Type:")
        for marker, count in sorted(by_marker.items(), key=lambda x: -x[1]):
            marker_info = DEBT_MARKERS_SEVERITY.get(marker, {"severity": "low"})
            severity = str(marker_info.get("severity", "low"))
            sev_icon = {"high": "\U0001f534", "medium": "\U0001f7e1", "low": "\U0001f7e2"}.get(
                severity,
                "\u26aa",
            )
            lines.append(f"  {sev_icon} {marker}: {count}")
    lines.append("")


def _format_trajectory_analysis(lines: list[str], analysis: dict) -> None:
    """Format the trajectory analysis section."""
    if not analysis:
        return

    lines.append("-" * 60)
    lines.append("TRAJECTORY ANALYSIS")
    lines.append("-" * 60)
    velocity = analysis.get("velocity", 0)
    snapshots = analysis.get("historical_snapshots", 0)

    lines.append(f"Historical Snapshots: {snapshots}")
    if velocity != 0:
        velocity_text = f"+{velocity}" if velocity > 0 else str(velocity)
        lines.append(f"Velocity: {velocity_text} items/snapshot")
    lines.append("")


def _format_hotspots(lines: list[str], hotspots: list[dict[str, Any]]) -> None:
    """Format the hotspot files section."""
    if not hotspots:
        return

    lines.append("-" * 60)
    lines.append("\U0001f525 HOTSPOT FILES")
    lines.append("-" * 60)
    for h in hotspots[:10]:
        file_path = h.get("file", "unknown")
        debt_count = h.get("debt_count", 0)
        lines.append(f"  \u2022 {file_path}")
        lines.append(f"      {debt_count} debt items")
    lines.append("")


def _format_high_priority(lines: list[str], high_priority: list[dict[str, Any]]) -> None:
    """Format the high priority items section."""
    if not high_priority:
        return

    lines.append("-" * 60)
    lines.append("\U0001f534 HIGH PRIORITY ITEMS")
    lines.append("-" * 60)
    for item in high_priority[:10]:
        file_path = item.get("file", "unknown")
        line = item.get("line", "?")
        marker = item.get("marker", "DEBT")
        message = item.get("message", "")[:50]
        score = item.get("priority_score", 0)
        hotspot = "\U0001f525" if item.get("is_hotspot") else ""
        lines.append(f"  [{marker}] {file_path}:{line} {hotspot}")
        lines.append(f"      {message} (score: {score})")
    if len(high_priority) > 10:
        lines.append(f"  ... and {len(high_priority) - 10} more")
    lines.append("")


def _format_roadmap(lines: list[str], result: dict) -> None:
    """Format the LLM-generated refactoring roadmap section."""
    refactoring_plan = result.get("refactoring_plan", "")
    if not refactoring_plan or refactoring_plan.startswith("[Simulated"):
        return

    lines.append("-" * 60)
    lines.append("REFACTORING ROADMAP")
    lines.append("-" * 60)
    if len(refactoring_plan) > 2000:
        lines.append(refactoring_plan[:2000] + "...")
    else:
        lines.append(refactoring_plan)
    lines.append("")


def main() -> None:
    """CLI entry point for refactor planning workflow."""
    import asyncio

    async def run() -> None:
        """Run the refactoring plan analysis stage."""
        from .refactor_plan import RefactorPlanWorkflow

        workflow = RefactorPlanWorkflow()
        result = await workflow.execute(path=".", file_types=[".py"])

        print("\nRefactor Plan Results")
        print("=" * 50)
        print(f"Provider: {result.provider}")
        print(f"Success: {result.success}")

        summary = result.final_output.get("summary", {})
        print(f"Total Debt: {summary.get('total_debt', 0)} items")
        print(f"Trajectory: {summary.get('trajectory', 'N/A')}")
        print(f"High Priority: {summary.get('high_priority_count', 0)}")

        print("\nCost Report:")
        print(f"  Total Cost: ${result.cost_report.total_cost:.4f}")
        savings = result.cost_report.savings
        pct = result.cost_report.savings_percent
        print(f"  Savings: ${savings:.4f} ({pct:.1f}%)")

    asyncio.run(run())


if __name__ == "__main__":
    main()
