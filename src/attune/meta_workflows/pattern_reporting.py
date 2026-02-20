"""Analytics reporting for pattern learner.

Provides formatted output of analytics reports.

Created: 2026-01-17
"""

from typing import Any


def print_analytics_report(report: dict[str, Any]) -> None:
    """Print analytics report in human-readable format.

    Args:
        report: Analytics report dictionary
    """
    print("\n" + "=" * 70)
    print("META-WORKFLOW ANALYTICS REPORT")
    print("=" * 70)

    # Summary
    summary = report["summary"]
    print("\n## Summary")
    print(f"\n  Total Runs: {summary['total_runs']}")
    print(f"  Successful: {summary['successful_runs']} ({summary['success_rate']:.0%})")
    print(f"  Total Cost: ${summary['total_cost']:.2f}")
    print(f"  Avg Cost/Run: ${summary['avg_cost_per_run']:.2f}")
    print(f"  Total Agents: {summary['total_agents_created']}")
    print(f"  Avg Agents/Run: {summary['avg_agents_per_run']:.1f}")

    # Recommendations
    if report.get("recommendations"):
        print("\n## Recommendations")
        print()
        for rec in report["recommendations"]:
            print(f"  {rec}")

    # Insights by type
    insights = report.get("insights", {})

    if insights.get("tier_performance"):
        print("\n## Tier Performance")
        print()
        for insight in insights["tier_performance"]:
            print(f"  - {insight['description']}")
            print(f"    Confidence: {insight['confidence']:.0%} (n={insight['sample_size']})")

    if insights.get("cost_analysis"):
        print("\n## Cost Analysis")
        print()
        for insight in insights["cost_analysis"]:
            print(f"  - {insight['description']}")

    if insights.get("failure_analysis"):
        print("\n## Failure Analysis")
        print()
        for insight in insights["failure_analysis"]:
            print(f"  - {insight['description']}")

    print("\n" + "=" * 70 + "\n")
