"""Predefined success criteria templates.

Factory functions that create standard SuccessCriteria for
common workflow types.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .success_models import MetricDirection, MetricType, SuccessMetric

if TYPE_CHECKING:
    from .success import SuccessCriteria


def code_review_criteria() -> SuccessCriteria:
    """Create standard success criteria for code review workflows."""
    from .success import SuccessCriteria

    return SuccessCriteria(
        id="code_review_success",
        name="Code Review Success",
        description="Standard metrics for code review effectiveness",
        metrics=[
            SuccessMetric(
                id="issues_found",
                name="Issues Found",
                description="Number of issues identified",
                metric_type=MetricType.COUNT,
                direction=MetricDirection.HIGHER_IS_BETTER,
                is_primary=True,
                weight=1.0,
                extraction_path="findings_count",
            ),
            SuccessMetric(
                id="severity_coverage",
                name="Severity Coverage",
                description="Percentage of severity levels covered",
                metric_type=MetricType.PERCENTAGE,
                direction=MetricDirection.HIGHER_IS_BETTER,
                minimum_value=50,
                weight=0.8,
                extraction_path="severity_coverage",
            ),
            SuccessMetric(
                id="review_time",
                name="Review Duration",
                description="Time to complete review",
                metric_type=MetricType.DURATION,
                direction=MetricDirection.LOWER_IS_BETTER,
                maximum_value=120,  # 2 minutes
                unit="seconds",
                weight=0.6,
                extraction_path="duration_seconds",
            ),
            SuccessMetric(
                id="actionable_recommendations",
                name="Actionable Recommendations",
                description="Whether recommendations are actionable",
                metric_type=MetricType.BOOLEAN,
                is_primary=True,
                weight=1.0,
                extraction_path="has_recommendations",
            ),
        ],
        success_threshold=0.7,
        min_primary_metrics=1,
    )


def security_audit_criteria() -> SuccessCriteria:
    """Create success criteria for security audit workflows."""
    from .success import SuccessCriteria

    return SuccessCriteria(
        id="security_audit_success",
        name="Security Audit Success",
        description="Metrics for security audit effectiveness",
        metrics=[
            SuccessMetric(
                id="vulnerabilities_found",
                name="Vulnerabilities Found",
                description="Security vulnerabilities identified",
                metric_type=MetricType.COUNT,
                direction=MetricDirection.HIGHER_IS_BETTER,
                is_primary=True,
                weight=1.0,
                extraction_path="vulnerabilities.count",
            ),
            SuccessMetric(
                id="critical_issues",
                name="Critical Issues",
                description="High/critical severity issues found",
                metric_type=MetricType.COUNT,
                direction=MetricDirection.HIGHER_IS_BETTER,
                is_primary=True,
                weight=1.2,  # Extra weight for critical issues
                extraction_path="vulnerabilities.critical_count",
            ),
            SuccessMetric(
                id="owasp_coverage",
                name="OWASP Coverage",
                description="OWASP Top 10 categories checked",
                metric_type=MetricType.PERCENTAGE,
                direction=MetricDirection.HIGHER_IS_BETTER,
                minimum_value=80,
                weight=0.9,
                extraction_path="owasp_coverage_percent",
            ),
            SuccessMetric(
                id="false_positive_rate",
                name="False Positive Rate",
                description="Estimated false positive rate",
                metric_type=MetricType.PERCENTAGE,
                direction=MetricDirection.LOWER_IS_BETTER,
                maximum_value=20,
                weight=0.7,
                extraction_path="estimated_fp_rate",
            ),
        ],
        success_threshold=0.75,
        min_primary_metrics=1,
    )


def test_generation_criteria() -> SuccessCriteria:
    """Create success criteria for test generation workflows."""
    from .success import SuccessCriteria

    return SuccessCriteria(
        id="test_generation_success",
        name="Test Generation Success",
        description="Metrics for test generation effectiveness",
        metrics=[
            SuccessMetric(
                id="tests_generated",
                name="Tests Generated",
                description="Number of test cases generated",
                metric_type=MetricType.COUNT,
                direction=MetricDirection.HIGHER_IS_BETTER,
                minimum_value=1,
                is_primary=True,
                weight=1.0,
                extraction_path="tests.count",
            ),
            SuccessMetric(
                id="coverage_increase",
                name="Coverage Increase",
                description="Increase in code coverage",
                metric_type=MetricType.IMPROVEMENT,
                direction=MetricDirection.HIGHER_IS_BETTER,
                minimum_value=5,  # At least 5% increase
                unit="%",
                weight=1.0,
                extraction_path="coverage.increase_percent",
            ),
            SuccessMetric(
                id="tests_passing",
                name="Tests Passing",
                description="Percentage of generated tests that pass",
                metric_type=MetricType.PERCENTAGE,
                direction=MetricDirection.HIGHER_IS_BETTER,
                minimum_value=80,
                is_primary=True,
                weight=1.2,
                extraction_path="tests.pass_rate",
            ),
            SuccessMetric(
                id="edge_cases_covered",
                name="Edge Cases Covered",
                description="Number of edge cases with tests",
                metric_type=MetricType.COUNT,
                direction=MetricDirection.HIGHER_IS_BETTER,
                weight=0.8,
                extraction_path="edge_cases.count",
            ),
        ],
        success_threshold=0.7,
        min_primary_metrics=2,
    )
