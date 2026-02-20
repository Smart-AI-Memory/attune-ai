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


def calculate_category_scores(
    agent_results: dict[str, dict[str, Any]],
    category_weights: dict[str, float] | None = None,
) -> list[CategoryScore]:
    """Calculate health scores for each category.

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
        )
    )

    # Coverage score (from test_coverage_analyzer)
    coverage_result = agent_results.get("test_coverage_analyzer", {}).get("output", {})
    coverage_percent = coverage_result.get("coverage_percent", 0.0)

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
        )
    )

    # Quality score (from code_reviewer)
    quality_result = agent_results.get("code_reviewer", {}).get("output", {})
    quality_score = quality_result.get("quality_score", 0.0)
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
        )
    )

    # Performance score (from performance_optimizer, if available)
    if "performance_optimizer" in agent_results:
        perf_result = agent_results.get("performance_optimizer", {}).get("output", {})
        bottleneck_count = perf_result.get("bottleneck_count", 0)

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
            )
        )

    # Documentation score (from documentation_writer, if available)
    if "documentation_writer" in agent_results:
        docs_result = agent_results.get("documentation_writer", {}).get("output", {})
        doc_coverage = docs_result.get("coverage_percent", 0.0)

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
            )
        )

    return scores


def calculate_overall_score(
    category_scores: list[CategoryScore],
) -> float:
    """Calculate weighted overall health score.

    Args:
        category_scores: Category scores

    Returns:
        Overall score 0-100
    """
    total_score = 0.0
    total_weight = 0.0

    for category in category_scores:
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

    # Sort categories by score (lowest first)
    sorted_categories = sorted(category_scores, key=lambda x: x.score)

    for category in sorted_categories:
        if not category.passed:
            if category.name == "Security":
                recommendations.append(f"🔒 Address {len(category.issues)} " f"security issue(s)")
                recommendations.append("   → Run: empathy workflow run " "security-audit --path .")
            elif category.name == "Coverage":
                recommendations.append(
                    f"🧪 Increase test coverage to 80%+ " f"(currently {category.score:.1f}%)"
                )
                recommendations.append("   → Run: pytest --cov=src " "--cov-report=term-missing")
                recommendations.append(
                    "   → Or use: empathy workflow run " "test-gen --path <file>"
                )
            elif category.name == "Quality":
                quality_score = category.raw_metrics.get("quality_score", 0.0)
                recommendations.append(
                    f"✨ Improve code quality to 7+ " f"(currently {quality_score:.1f}/10)"
                )
                recommendations.append("   → Run: empathy workflow run " "code-review --path .")
                recommendations.append("   → Or: empathy fix-all  " "(auto-fix lint/format issues)")
            elif category.name == "Performance":
                bottlenecks = category.raw_metrics.get("bottleneck_count", 0)
                recommendations.append(f"⚡ Optimize {bottlenecks} " f"performance bottleneck(s)")
                recommendations.append("   → Run: empathy workflow run " "perf-audit --path .")
            elif category.name == "Documentation":
                recommendations.append(
                    f"📚 Complete documentation " f"(currently {category.score:.1f}%)"
                )
                recommendations.append("   → Run: empathy workflow run " "doc-gen --path .")

    # Add general recommendations
    if len(recommendations) == 0:
        recommendations.append("✅ Project health looks good! " "Keep up the good work.")
        recommendations.append(
            "   → Run: empathy orchestrate health-check " "--mode weekly  (for deeper analysis)"
        )
    elif len(recommendations) >= 6:  # Multiple issues
        recommendations.append("")
        recommendations.append("💡 Tip: Focus on top priority first " "for maximum impact")
        recommendations.append(
            "   → Rerun: empathy orchestrate health-check " "--mode daily  (to track progress)"
        )

    return recommendations
