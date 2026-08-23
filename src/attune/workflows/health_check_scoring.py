"""Health Check Scoring Logic

Category score calculation, overall scoring, grade assignment,
and recommendation generation for health check workflows.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from typing import Any

from .health_check_models import CategoryScore

logger = logging.getLogger(__name__)


# Category weights for overall score
CATEGORY_WEIGHTS: dict[str, float] = {
    "Security": 0.30,
    "Coverage": 0.25,
    "Quality": 0.20,
    "Performance": 0.15,
    "Documentation": 0.10,
}

# Grade thresholds
GRADE_THRESHOLDS: dict[str, float] = {
    "A": 90.0,
    "B": 80.0,
    "C": 70.0,
    "D": 60.0,
}


def _unmeasured_category(name: str, weight: float, agent_id: str) -> CategoryScore:
    """Build the explicit N/A score for a category whose agent produced no data.

    A metric that was not measured must not be a number: the category is
    marked measured=False, carries an issue naming the missing agent, and
    is excluded from the weighted overall score.
    """
    return CategoryScore(
        name=name,
        score=0.0,
        weight=weight,
        raw_metrics={},
        issues=[f"{name} not measured — {agent_id} produced no measurement"],
        passed=False,
        measured=False,
    )


def calculate_category_scores(
    agent_results: dict[str, dict[str, Any]],
    category_weights: dict[str, float] | None = None,
) -> list[CategoryScore]:
    """Calculate health scores for each category.

    A category is only scored when its agent actually produced the
    metric it is scored on; a missing or failed agent yields an
    unmeasured (N/A) category, never a defaulted number.

    Args:
        agent_results: Results from all agents
        category_weights: Optional custom weights (defaults
            to CATEGORY_WEIGHTS)

    Returns:
        List of CategoryScore objects

    """
    weights = category_weights or CATEGORY_WEIGHTS
    scores: list[CategoryScore] = []

    # Security score (from security_auditor)
    security_result = agent_results.get("security_auditor", {}).get("output", {})
    if "critical_issues" not in security_result:
        scores.append(_unmeasured_category("Security", weights["Security"], "security_auditor"))
    else:
        critical_issues = security_result.get("critical_issues", 0)
        high_issues = security_result.get("high_issues", 0)
        medium_issues = security_result.get("medium_issues", 0)

        security_score = 100.0
        security_issues: list[str] = []

        if critical_issues > 0:
            security_score -= critical_issues * 20  # -20 per critical
            security_issues.append(f"{critical_issues} critical security issue(s)")
        if high_issues > 0:
            security_score -= high_issues * 10  # -10 per high
            security_issues.append(f"{high_issues} high severity issue(s)")
        if medium_issues > 0:
            security_score -= medium_issues * 5  # -5 per medium
            security_issues.append(f"{medium_issues} medium severity issue(s)")

        security_score = max(0.0, security_score)

        scores.append(
            CategoryScore(
                name="Security",
                score=security_score,
                weight=weights["Security"],
                raw_metrics={
                    "critical": critical_issues,
                    "high": high_issues,
                    "medium": medium_issues,
                },
                issues=security_issues,
                passed=critical_issues == 0 and high_issues == 0,
            ),
        )

    # Coverage score (from test_coverage_analyzer)
    coverage_result = agent_results.get("test_coverage_analyzer", {}).get("output", {})
    if "coverage_percent" not in coverage_result:
        scores.append(
            _unmeasured_category("Coverage", weights["Coverage"], "test_coverage_analyzer")
        )
    else:
        coverage_percent = coverage_result["coverage_percent"]

        coverage_issues: list[str] = []
        if coverage_percent < 80.0:
            coverage_issues.append(f"Coverage below 80% ({coverage_percent:.1f}%)")

        scores.append(
            CategoryScore(
                name="Coverage",
                score=coverage_percent,
                weight=weights["Coverage"],
                raw_metrics={"coverage_percent": coverage_percent},
                issues=coverage_issues,
                passed=coverage_percent >= 80.0,
            ),
        )

    # Quality score (from code_reviewer)
    quality_result = agent_results.get("code_reviewer", {}).get("output", {})
    if "quality_score" not in quality_result:
        scores.append(_unmeasured_category("Quality", weights["Quality"], "code_reviewer"))
    else:
        quality_score = quality_result["quality_score"]
        # Convert 0-10 scale to 0-100
        quality_score_100 = quality_score * 10

        quality_issues: list[str] = []
        if quality_score < 7.0:
            quality_issues.append(f"Quality score below 7 ({quality_score:.1f}/10)")

        scores.append(
            CategoryScore(
                name="Quality",
                score=quality_score_100,
                weight=weights["Quality"],
                raw_metrics={"quality_score": quality_score},
                issues=quality_issues,
                passed=quality_score >= 7.0,
            ),
        )

    # Performance score (from performance_optimizer, if available)
    if "performance_optimizer" in agent_results:
        perf_result = agent_results.get("performance_optimizer", {}).get("output", {})
        if "bottleneck_count" not in perf_result:
            scores.append(
                _unmeasured_category("Performance", weights["Performance"], "performance_optimizer")
            )
        else:
            bottleneck_count = perf_result["bottleneck_count"]

            perf_score = 100.0 - (bottleneck_count * 10)
            perf_score = max(0.0, perf_score)

            perf_issues: list[str] = []
            if bottleneck_count > 0:
                perf_issues.append(f"{bottleneck_count} performance bottleneck(s)")

            scores.append(
                CategoryScore(
                    name="Performance",
                    score=perf_score,
                    weight=weights["Performance"],
                    raw_metrics={"bottleneck_count": bottleneck_count},
                    issues=perf_issues,
                    passed=bottleneck_count <= 2,
                ),
            )

    # Documentation score (from documentation_writer, if available)
    if "documentation_writer" in agent_results:
        docs_result = agent_results.get("documentation_writer", {}).get("output", {})
        if "coverage_percent" not in docs_result:
            scores.append(
                _unmeasured_category(
                    "Documentation", weights["Documentation"], "documentation_writer"
                )
            )
        else:
            doc_coverage = docs_result["coverage_percent"]

            doc_issues: list[str] = []
            if doc_coverage < 100.0:
                doc_issues.append(f"Documentation incomplete ({doc_coverage:.1f}%)")

            scores.append(
                CategoryScore(
                    name="Documentation",
                    score=doc_coverage,
                    weight=weights["Documentation"],
                    raw_metrics={"coverage_percent": doc_coverage},
                    issues=doc_issues,
                    passed=doc_coverage >= 90.0,
                ),
            )

    return scores


def calculate_overall_score(
    category_scores: list[CategoryScore],
) -> float:
    """Calculate weighted overall health score.

    Unmeasured categories (measured=False) are excluded entirely —
    their weight does not dilute the score and their placeholder 0.0
    is never averaged in.

    Args:
        category_scores: Category scores

    Returns:
        Overall score 0-100 (0.0 when no category was measured)

    """
    total_score = 0.0
    total_weight = 0.0

    for category in category_scores:
        if not category.measured:
            continue
        total_score += category.score * category.weight
        total_weight += category.weight

    if total_weight == 0:
        return 0.0

    return total_score / total_weight


def assign_grade(
    score: float,
    thresholds: dict[str, float] | None = None,
) -> str:
    """Assign letter grade based on score.

    Args:
        score: Overall health score 0-100
        thresholds: Optional custom thresholds (defaults
            to GRADE_THRESHOLDS)

    Returns:
        Letter grade (A/B/C/D/F)

    """
    grade_thresholds = thresholds or GRADE_THRESHOLDS
    for grade, threshold in grade_thresholds.items():
        if score >= threshold:
            return grade
    return "F"


_CATEGORY_RECOMMENDATIONS: dict[str, tuple[str, list[str]]] = {
    "Security": (
        "🔒 Address {issue_count} security issue(s)",
        ["   → Run: attune workflow run security-audit --path ."],
    ),
    "Coverage": (
        "🧪 Increase test coverage to 80%+ (currently {score:.1f}%)",
        [
            "   → Run: pytest --cov=src --cov-report=term-missing",
            "   → Or use: attune workflow run test-gen --path <file>",
        ],
    ),
    "Quality": (
        "✨ Improve code quality to 7+ (currently {quality_score:.1f}/10)",
        [
            "   → Run: attune workflow run code-review --path .",
            "   → Or: ruff check --fix . && ruff format .  (auto-fix lint/format issues)",
        ],
    ),
    "Performance": (
        "⚡ Optimize {bottleneck_count} performance bottleneck(s)",
        ["   → Run: attune workflow run perf-audit --path ."],
    ),
    "Documentation": (
        "📚 Complete documentation (currently {score:.1f}%)",
        ["   → Run: attune workflow run doc-gen --path ."],
    ),
}


def generate_recommendations(
    category_scores: list[CategoryScore],
) -> list[str]:
    """Generate actionable recommendations with specific commands.

    Args:
        category_scores: Category scores

    Returns:
        List of recommendations with commands to run

    """
    recommendations: list[str] = []

    sorted_categories = sorted(category_scores, key=lambda x: x.score)
    unmeasured = [c.name for c in category_scores if not c.measured]

    for category in sorted_categories:
        # Unmeasured categories have no numbers to recommend against —
        # they are reported as missing data below, not as failures.
        if not category.measured or category.passed:
            continue
        template = _CATEGORY_RECOMMENDATIONS.get(category.name)
        if not template:
            continue
        heading_fmt, commands = template
        fmt_vars = {
            "score": category.score,
            "issue_count": len(category.issues),
            "quality_score": category.raw_metrics.get("quality_score", 0.0),
            "bottleneck_count": category.raw_metrics.get("bottleneck_count", 0),
        }
        recommendations.append(heading_fmt.format(**fmt_vars))
        recommendations.extend(commands)

    if unmeasured:
        recommendations.append(
            "⚠️ Not measured: "
            + ", ".join(unmeasured)
            + " — no data produced; excluded from the score",
        )

    # Add general recommendations
    if len(recommendations) == 0:
        recommendations.append("✅ Project health looks good! Keep up the good work.")
        recommendations.append(
            "   → Run: attune workflow run health-check --mode weekly  (for deeper analysis)",
        )
    elif len(recommendations) >= 6:  # Multiple issues
        recommendations.append("")
        recommendations.append("💡 Tip: Focus on top priority first for maximum impact")
        recommendations.append(
            "   → Rerun: attune workflow run health-check --mode daily  (to track progress)",
        )

    return recommendations
