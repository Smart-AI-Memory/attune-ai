"""Release Preparation Workflow - Report Formatting and CLI Entry Point

Contains the human-readable report formatter and the ``main()`` CLI
entry point for the release preparation workflow.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""


def format_release_prep_report(result: dict, input_data: dict) -> str:
    """Format release preparation output as a human-readable report.

    Args:
        result: The approve stage result
        input_data: Input data from previous stages

    Returns:
        Formatted report string

    """
    lines: list[str] = []

    # Header with approval status
    approved = result.get("approved", False)
    confidence = result.get("confidence", "unknown").upper()

    if approved:
        status_icon = "\u2705"
        status_text = "READY FOR RELEASE"
    else:
        status_icon = "\u274c"
        status_text = "NOT READY"

    lines.append("=" * 60)
    lines.append("RELEASE PREPARATION REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Status: {status_icon} {status_text}")
    lines.append(f"Confidence: {confidence}")
    lines.append(f"Recommendation: {result.get('recommendation', 'N/A')}")
    lines.append("")

    # Health checks
    health = input_data.get("health", {})
    health_score = health.get("health_score", 0)
    checks = health.get("checks", {})

    lines.append("-" * 60)
    lines.append("HEALTH CHECKS")
    lines.append("-" * 60)
    lines.append(f"Health Score: {health_score}/100")
    lines.append("")

    for check_name, check_data in checks.items():
        passed = check_data.get("passed", False)
        skipped = check_data.get("skipped", False)
        tool = check_data.get("tool", "unknown")

        if skipped:
            icon = "\u23ed\ufe0f"
            status = "SKIPPED"
        elif passed:
            icon = "\u2705"
            status = "PASSED"
        else:
            icon = "\u274c"
            status = "FAILED"

        errors = check_data.get("errors", 0)
        extra = f" ({errors} errors)" if errors else ""
        lines.append(f"  {icon} {check_name.upper()} ({tool}): {status}{extra}")
    lines.append("")

    # Security summary
    security = input_data.get("security", {})
    if security:
        lines.append("-" * 60)
        lines.append("SECURITY SCAN")
        lines.append("-" * 60)
        total_issues = security.get("total_issues", 0)
        high = security.get("high_severity", 0)
        medium = security.get("medium_severity", 0)
        passed = security.get("passed", True)

        if passed:
            lines.append("\u2705 No high severity issues found")
        else:
            lines.append(f"\u274c {high} high severity issues found")

        lines.append(f"Total Issues: {total_issues}")
        lines.append(f"  \U0001f534 High: {high}")
        lines.append(f"  \U0001f7e1 Medium: {medium}")
        lines.append("")

    # Changelog summary
    changelog = input_data.get("changelog", {})
    if changelog:
        lines.append("-" * 60)
        lines.append("CHANGELOG")
        lines.append("-" * 60)
        commit_count = changelog.get("total_commits", 0)
        by_category = changelog.get("by_category", {})
        period = changelog.get("period", "unknown")

        lines.append(f"Period: {period}")
        lines.append(f"Total Commits: {commit_count}")
        if by_category:
            lines.append("By Category:")
            for cat, count in by_category.items():
                lines.append(f"  \u2022 {cat}: {count}")
        lines.append("")

    # Blockers
    blockers = result.get("blockers", [])
    if blockers:
        lines.append("-" * 60)
        lines.append("\U0001f6ab BLOCKERS")
        lines.append("-" * 60)
        for blocker in blockers:
            lines.append(f"  \u2022 {blocker}")
        lines.append("")

    # Warnings
    warnings = result.get("warnings", [])
    if warnings:
        lines.append("-" * 60)
        lines.append("\u26a0\ufe0f  WARNINGS")
        lines.append("-" * 60)
        for warning in warnings:
            lines.append(f"  \u2022 {warning}")
        lines.append("")

    # LLM Assessment
    assessment = result.get("assessment", "")
    if assessment and not assessment.startswith("[Simulated"):
        lines.append("-" * 60)
        lines.append("DETAILED ASSESSMENT")
        lines.append("-" * 60)
        if len(assessment) > 1500:
            lines.append(assessment[:1500] + "...")
        else:
            lines.append(assessment)
        lines.append("")

    # Footer
    lines.append("=" * 60)
    model_tier = result.get("model_tier_used", "unknown")
    lines.append(f"Assessed using {model_tier} tier model")
    lines.append("=" * 60)

    return "\n".join(lines)


def main() -> None:
    """CLI entry point for release preparation workflow."""
    import asyncio

    async def run() -> None:
        from .release_prep import ReleasePreparationWorkflow

        workflow = ReleasePreparationWorkflow()
        result = await workflow.execute(path=".")

        print("\nRelease Preparation Results")
        print("=" * 50)
        print(f"Provider: {result.provider}")
        print(f"Success: {result.success}")

        output = result.final_output
        print(f"Approved: {output.get('approved', False)}")
        print(f"Confidence: {output.get('confidence', 'N/A')}")

        if output.get("blockers"):
            print("\nBlockers:")
            for b in output["blockers"]:
                print(f"  - {b}")

        if output.get("warnings"):
            print("\nWarnings:")
            for w in output["warnings"]:
                print(f"  - {w}")

        print("\nCost Report:")
        print(f"  Total Cost: ${result.cost_report.total_cost:.4f}")
        savings = result.cost_report.savings
        pct = result.cost_report.savings_percent
        print(f"  Savings: ${savings:.4f} ({pct:.1f}%)")

    asyncio.run(run())
