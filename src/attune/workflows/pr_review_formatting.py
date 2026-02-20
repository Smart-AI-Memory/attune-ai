"""PR Review formatting and CLI entry point.

Human-readable report formatting for PR review results
and the command-line interface for running reviews.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio

from .pr_review_models import PRReviewResult


def format_pr_review_report(result: PRReviewResult) -> str:
    """Format PR review result as a human-readable report.

    Args:
        result: The PRReviewResult dataclass

    Returns:
        Formatted report string

    """
    lines: list[str] = []

    # Header with verdict
    verdict_emoji = {
        "approve": "✅",
        "approve_with_suggestions": "🟡",
        "request_changes": "🟠",
        "reject": "🔴",
    }
    emoji = verdict_emoji.get(result.verdict, "⚪")

    lines.append("=" * 60)
    lines.append("PR REVIEW REPORT")
    lines.append("=" * 60)
    lines.append("")

    # Verdict banner
    lines.append("-" * 60)
    lines.append(f"{emoji} VERDICT: {result.verdict.upper().replace('_', ' ')}")
    lines.append("-" * 60)
    lines.append("")

    # Scores
    lines.append("-" * 60)
    lines.append("SCORES")
    lines.append("-" * 60)

    # Code quality score with visual bar
    cq_score = result.code_quality_score
    cq_bar = "█" * int(cq_score / 10) + "░" * (10 - int(cq_score / 10))
    lines.append(f"Code Quality:    [{cq_bar}] {cq_score:.0f}/100")

    # Security risk (inverted - lower is better)
    sr_score = result.security_risk_score
    sr_bar = "█" * int(sr_score / 10) + "░" * (10 - int(sr_score / 10))
    risk_label = "LOW" if sr_score < 30 else "MEDIUM" if sr_score < 60 else "HIGH"
    lines.append(f"Security Risk:   [{sr_bar}] {sr_score:.0f}/100 ({risk_label})")

    # Combined score
    combined = result.combined_score
    combined_bar = "█" * int(combined / 10) + "░" * (10 - int(combined / 10))
    lines.append(f"Combined Score:  [{combined_bar}] {combined:.0f}/100")
    lines.append("")

    # Summary
    if result.summary:
        lines.append("-" * 60)
        lines.append("SUMMARY")
        lines.append("-" * 60)
        # Word wrap summary
        words = result.summary.split()
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= 58:
                current_line += (" " if current_line else "") + word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        lines.append("")

    # Blockers
    if result.blockers:
        lines.append("-" * 60)
        lines.append("🚫 BLOCKERS (must fix before merge)")
        lines.append("-" * 60)
        for blocker in result.blockers:
            lines.append(f"  • {blocker}")
        lines.append("")

    # Findings summary
    if result.all_findings:
        lines.append("-" * 60)
        lines.append("FINDINGS")
        lines.append("-" * 60)
        lines.append(f"Total: {len(result.all_findings)}")
        lines.append(f"  🔴 Critical: {result.critical_count}")
        lines.append(f"  🟠 High: {result.high_count}")
        lines.append(f"  Code Issues: {len(result.code_findings)}")
        lines.append(f"  Security Issues: {len(result.security_findings)}")
        lines.append("")

        # Show top critical/high findings
        critical_high = [
            f for f in result.all_findings if f.get("severity") in ("critical", "high")
        ]
        if critical_high:
            lines.append("Top Issues:")
            for i, finding in enumerate(critical_high[:5], 1):
                severity = finding.get("severity", "unknown")
                title = finding.get("title", finding.get("message", "Unknown issue"))
                finding_emoji = "🔴" if severity == "critical" else "🟠"
                if len(title) > 50:
                    title = title[:47] + "..."
                lines.append(f"  {finding_emoji} {i}. {title}")
            if len(critical_high) > 5:
                lines.append(f"  ... and {len(critical_high) - 5} more critical/high issues")
            lines.append("")

    # Warnings
    if result.warnings:
        lines.append("-" * 60)
        lines.append("⚠️  WARNINGS")
        lines.append("-" * 60)
        for warning in result.warnings:
            lines.append(f"  • {warning}")
        lines.append("")

    # Recommendations
    if result.recommendations:
        lines.append("-" * 60)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 60)
        for i, rec in enumerate(result.recommendations[:5], 1):
            if len(rec) > 55:
                rec = rec[:52] + "..."
            lines.append(f"  {i}. {rec}")
        if len(result.recommendations) > 5:
            lines.append(f"  ... and {len(result.recommendations) - 5} more")
        lines.append("")

    # Agents used
    if result.agents_used:
        lines.append("-" * 60)
        lines.append("AGENTS USED")
        lines.append("-" * 60)
        lines.append(f"  {', '.join(result.agents_used)}")
        lines.append("")

    # Footer
    lines.append("=" * 60)
    duration_ms = result.duration_seconds * 1000
    lines.append(f"Review completed in {duration_ms:.0f}ms | Cost: ${result.cost:.4f}")
    lines.append("=" * 60)

    return "\n".join(lines)


def main() -> None:
    """Run PRReviewWorkflow from command line."""
    import argparse

    # Import here to avoid circular imports
    from .pr_review import PRReviewWorkflow

    parser = argparse.ArgumentParser(description="PR Review Workflow")
    parser.add_argument("--diff", "-d", help="PR diff content")
    parser.add_argument("--target", "-t", default=".", help="Target path for security audit")
    parser.add_argument("--files", "-f", nargs="*", default=[], help="Changed files")
    parser.add_argument("--parallel/--sequential", dest="parallel", default=True)
    parser.add_argument("--code-only", action="store_true", help="Only run code review")
    parser.add_argument("--security-only", action="store_true", help="Only run security audit")

    args = parser.parse_args()

    async def run() -> None:
        if args.code_only:
            workflow = PRReviewWorkflow.for_code_quality_focused()
        elif args.security_only:
            workflow = PRReviewWorkflow.for_security_focused()
        else:
            workflow = PRReviewWorkflow(parallel=args.parallel)

        result = await workflow.execute(
            diff=args.diff or "",
            files_changed=args.files,
            target_path=args.target,
        )

        print("\n" + "=" * 60)
        print("PR REVIEW RESULTS")
        print("=" * 60)
        print(f"\nVerdict: {result.verdict.upper()}")
        print(f"\n{result.summary}")
        print(f"\nDuration: {result.duration_seconds * 1000:.0f}ms")

        if result.agents_used:
            print(f"\nAgents Used: {', '.join(result.agents_used)}")

        print(f"\nFindings: {len(result.all_findings)} total")
        print(f"  Code: {len(result.code_findings)}")
        print(f"  Security: {len(result.security_findings)}")
        print(f"  Critical: {result.critical_count}")
        print(f"  High: {result.high_count}")

        if result.blockers:
            print("\nBlockers:")
            for b in result.blockers:
                print(f"  - {b}")

        if result.warnings:
            print("\nWarnings:")
            for w in result.warnings:
                print(f"  - {w}")

        if result.recommendations[:5]:
            print("\nTop Recommendations:")
            for r in result.recommendations[:5]:
                print(f"  - {r[:80]}...")

    asyncio.run(run())
