"""Success Criteria and Measurement System

Define and measure success for generated workflows.

Success criteria allow users to:
1. Define what "done" looks like for their workflow
2. Track progress toward goals
3. Measure effectiveness over time
4. Iterate and improve workflows

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Re-export models for backward compatibility
from .success_models import (
    MetricDirection,  # noqa: F401
    MetricResult,
    MetricType,  # noqa: F401
    SuccessEvaluation,
    SuccessMetric,
)

# Re-export template factories for backward compatibility
from .success_templates import (
    code_review_criteria,  # noqa: F401
    security_audit_criteria,  # noqa: F401
    test_generation_criteria,  # noqa: F401
)


@dataclass
class SuccessCriteria:
    """Complete success criteria for a workflow.

    Example:
        >>> criteria = SuccessCriteria(
        ...     id="code_review_success",
        ...     name="Code Review Success Criteria",
        ...     description="Measures effectiveness of automated code review",
        ...     metrics=[
        ...         SuccessMetric(
        ...             id="issues_found",
        ...             name="Issues Found",
        ...             metric_type=MetricType.COUNT,
        ...             is_primary=True
        ...         ),
        ...         SuccessMetric(
        ...             id="review_time",
        ...             name="Review Time",
        ...             metric_type=MetricType.DURATION,
        ...             direction=MetricDirection.LOWER_IS_BETTER,
        ...             maximum_value=60,  # seconds
        ...         ),
        ...     ],
        ...     success_threshold=0.7  # 70% overall score = success
        ... )

    """

    # Unique identifier
    id: str = ""

    # Display name
    name: str = ""

    # Description
    description: str = ""

    # List of metrics
    metrics: list[SuccessMetric] = field(default_factory=list)

    # Threshold for overall success (0-1)
    success_threshold: float = 0.7

    # Whether ALL metrics must be met (vs weighted average)
    require_all: bool = False

    # Minimum primary metrics that must pass
    min_primary_metrics: int = 1

    # Custom success evaluator
    custom_evaluator: Callable[[dict[str, MetricResult]], bool] | None = None

    def add_metric(self, metric: SuccessMetric) -> None:
        """Add a metric to the criteria."""
        self.metrics.append(metric)

    def get_primary_metrics(self) -> list[SuccessMetric]:
        """Get all primary success indicators."""
        return [m for m in self.metrics if m.is_primary]

    def evaluate(
        self,
        workflow_output: dict[str, Any],
        baselines: dict[str, float | bool] | None = None,
    ) -> SuccessEvaluation:
        """Evaluate workflow output against success criteria.

        Args:
            workflow_output: The workflow's output to evaluate
            baselines: Optional baseline values for comparison

        Returns:
            SuccessEvaluation with detailed results

        """
        baselines = baselines or {}
        results: list[MetricResult] = []
        timestamp = datetime.now().isoformat()

        # Evaluate each metric
        for metric in self.metrics:
            # Extract value from output
            value = self._extract_metric_value(metric, workflow_output)

            if value is None:
                # Metric not found in output
                results.append(
                    MetricResult(
                        metric_id=metric.id,
                        value=0,
                        met_criteria=False,
                        score=0.0,
                        explanation=f"Metric '{metric.name}' not found in output",
                        timestamp=timestamp,
                    ),
                )
                continue

            # Get baseline if available
            baseline = baselines.get(metric.id)

            # Evaluate
            met, score, explanation = metric.evaluate(value, baseline)

            results.append(
                MetricResult(
                    metric_id=metric.id,
                    value=value,
                    met_criteria=met,
                    score=score,
                    explanation=explanation,
                    baseline=baseline,
                    timestamp=timestamp,
                ),
            )

        # Calculate overall success
        return self._calculate_overall_success(results)

    def _extract_metric_value(
        self,
        metric: SuccessMetric,
        output: dict[str, Any],
    ) -> float | bool | None:
        """Extract metric value from workflow output."""
        # Use custom extractor if provided
        if metric.extractor:
            try:
                return metric.extractor(output)
            except (KeyError, TypeError, ValueError):
                return None

        # Use extraction path
        if metric.extraction_path:
            try:
                value = output
                for key in metric.extraction_path.split("."):
                    if isinstance(value, dict):
                        value = value[key]
                    elif isinstance(value, list) and key.isdigit():
                        value = value[int(key)]
                    else:
                        return None
                return value
            except (KeyError, IndexError, TypeError):
                return None

        # Try direct key match
        if metric.id in output:
            return output[metric.id]

        # Try nested in 'metrics' key
        if "metrics" in output and isinstance(output["metrics"], dict):
            if metric.id in output["metrics"]:
                return output["metrics"][metric.id]

        return None

    def _calculate_overall_success(
        self,
        results: list[MetricResult],
    ) -> SuccessEvaluation:
        """Calculate overall success from metric results."""
        if not results:
            return SuccessEvaluation(
                overall_success=False,
                overall_score=0.0,
                metric_results=results,
                summary="No metrics to evaluate",
            )

        # Check primary metrics
        primary_results = [
            r for r in results if any(m.id == r.metric_id and m.is_primary for m in self.metrics)
        ]
        primary_passed = sum(1 for r in primary_results if r.met_criteria)

        # Check if minimum primary metrics are met
        primary_check = primary_passed >= self.min_primary_metrics

        # Check if all required
        if self.require_all:
            all_met = all(r.met_criteria for r in results)
            overall_success = all_met and primary_check
            overall_score = 1.0 if overall_success else sum(r.score for r in results) / len(results)
        else:
            # Weighted average score
            total_weight = sum(
                m.weight for m in self.metrics if any(r.metric_id == m.id for r in results)
            )

            if total_weight > 0:
                weighted_score = (
                    sum(
                        r.score * next((m.weight for m in self.metrics if m.id == r.metric_id), 1.0)
                        for r in results
                    )
                    / total_weight
                )
            else:
                weighted_score = sum(r.score for r in results) / len(results)

            overall_score = weighted_score
            overall_success = overall_score >= self.success_threshold and primary_check

        # Custom evaluator override
        if self.custom_evaluator:
            results_dict = {r.metric_id: r for r in results}
            overall_success = self.custom_evaluator(results_dict)

        # Generate summary
        summary = self._generate_summary(results, overall_success, overall_score)

        return SuccessEvaluation(
            overall_success=overall_success,
            overall_score=overall_score,
            metric_results=results,
            summary=summary,
            primary_metrics_passed=primary_passed,
            total_primary_metrics=len(primary_results),
        )

    def _generate_summary(
        self,
        results: list[MetricResult],
        success: bool,
        score: float,
    ) -> str:
        """Generate human-readable summary."""
        status = "✓ SUCCESS" if success else "✗ NOT MET"
        met_count = sum(1 for r in results if r.met_criteria)

        lines = [
            f"{status} - Overall score: {score:.1%}",
            f"Metrics: {met_count}/{len(results)} met criteria",
            "",
            "Details:",
        ]

        for result in results:
            metric = next((m for m in self.metrics if m.id == result.metric_id), None)
            name = metric.name if metric else result.metric_id
            indicator = "✓" if result.met_criteria else "✗"
            lines.append(f"  {indicator} {name}: {result.explanation}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "metrics": [m.to_dict() for m in self.metrics],
            "success_threshold": self.success_threshold,
            "require_all": self.require_all,
            "min_primary_metrics": self.min_primary_metrics,
        }
