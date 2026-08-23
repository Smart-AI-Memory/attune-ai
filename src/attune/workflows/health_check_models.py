"""Health Check Data Models

Dataclasses for health check reports and category scores.

Used by OrchestratedHealthCheckWorkflow and related modules.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CategoryScore:
    """Individual category health score.

    Attributes:
        name: Category name (e.g., "Security")
        score: Score 0-100 (meaningless when measured is False)
        weight: Weight in overall score (0-1)
        raw_metrics: Raw metrics from agent
        issues: Issues found
        passed: Whether category passed threshold
        measured: Whether the agent actually produced a measurement.
            Unmeasured categories are excluded from the weighted
            overall score and rendered as N/A — a metric that was
            not measured must not be a number.

    """

    name: str
    score: float
    weight: float
    raw_metrics: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    passed: bool = True
    measured: bool = True


@dataclass
class HealthCheckReport:
    """Comprehensive health check report.

    Attributes:
        overall_health_score: Overall health score 0-100
        grade: Letter grade (A/B/C/D/F)
        category_scores: Scores by category
        issues: All issues found
        recommendations: Actionable recommendations
        trend: Comparison with last check
        execution_time: Total execution time in seconds
        mode: Execution mode (daily/weekly/release)
        timestamp: Report generation time
        agents_executed: Number of agents executed
        success: Whether check completed successfully
        degraded: True when one or more categories were not measured
            (agent missing or failed) — the score covers only the
            measured categories and the report is INCOMPLETE DATA

    """

    overall_health_score: float
    grade: str
    category_scores: list[CategoryScore] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    trend: str = ""
    execution_time: float = 0.0
    mode: str = "daily"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    agents_executed: int = 0
    success: bool = True
    degraded: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization.

        Returns:
            Dictionary representation

        """
        return {
            "overall_health_score": self.overall_health_score,
            "grade": self.grade,
            "category_scores": [
                {
                    "name": cat.name,
                    "score": cat.score,
                    "weight": cat.weight,
                    "raw_metrics": cat.raw_metrics,
                    "issues": cat.issues,
                    "passed": cat.passed,
                    "measured": cat.measured,
                }
                for cat in self.category_scores
            ],
            "issues": self.issues,
            "recommendations": self.recommendations,
            "trend": self.trend,
            "execution_time": self.execution_time,
            "mode": self.mode,
            "timestamp": self.timestamp,
            "agents_executed": self.agents_executed,
            "success": self.success,
            "degraded": self.degraded,
        }

    def format_console_output(self) -> str:
        """Format report for console display.

        Returns:
            Human-readable formatted report

        """
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append("PROJECT HEALTH CHECK REPORT (Meta-Orchestrated)")
        lines.append("=" * 70)
        lines.append("")

        # Overall health
        grade_emoji = {
            "A": "🏆",
            "B": "✅",
            "C": "⚠️",
            "D": "❌",
            "F": "🚨",
        }
        emoji = grade_emoji.get(self.grade, "")

        if self.grade == "N/A":
            lines.append("Overall Health: ❓ N/A — no categories were measured")
        else:
            lines.append(
                f"Overall Health: {emoji} "
                f"{self.overall_health_score:.1f}/100 "
                f"(Grade {self.grade})",
            )
        if self.degraded:
            lines.append(
                "⚠️  DEGRADED — INCOMPLETE DATA: unmeasured categories "
                "are shown as N/A and excluded from the score",
            )
        lines.append(f"Mode: {self.mode.upper()}")
        lines.append(f"Agents Executed: {self.agents_executed}")
        lines.append(f"Generated: {self.timestamp}")
        lines.append(f"Duration: {self.execution_time:.2f}s")

        if self.trend:
            lines.append(f"Trend: {self.trend}")

        lines.append("")

        # Category scores
        lines.append("-" * 70)
        lines.append("CATEGORY BREAKDOWN")
        lines.append("-" * 70)

        for category in sorted(
            self.category_scores,
            key=lambda x: (x.measured, x.score),
            reverse=True,
        ):
            if not category.measured:
                lines.append(f"❓ {category.name:15}   N/A (not measured)")
                continue
            status = "✅" if category.passed else "❌"
            bar_length = int(category.score / 5)  # 0-20 chars
            bar = "█" * bar_length
            lines.append(
                f"{status} {category.name:15} "
                f"{category.score:5.1f}/100 "
                f"(weight: {category.weight * 100:2.0f}%) {bar}",
            )

            # Show issues for failing categories
            if category.issues and not category.passed:
                for issue in category.issues[:3]:  # Show first 3
                    lines.append(f"     • {issue}")

        lines.append("")

        # Issues summary
        if self.issues:
            lines.append("-" * 70)
            lines.append(f"🚨 ISSUES FOUND ({len(self.issues)})")
            lines.append("-" * 70)
            for issue in self.issues[:10]:  # Show first 10
                lines.append(f"  • {issue}")
            if len(self.issues) > 10:
                lines.append(f"  ... and {len(self.issues) - 10} more")
            lines.append("")

        # Recommendations
        if self.recommendations:
            lines.append("-" * 70)
            lines.append(f"💡 RECOMMENDATIONS ({len(self.recommendations)})")
            lines.append("-" * 70)
            for rec in self.recommendations:
                lines.append(f"  • {rec}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)
