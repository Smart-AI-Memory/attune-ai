"""Success criteria data models and metric evaluation.

Provides enums, dataclasses, and evaluation logic for
measuring workflow success.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MetricType(Enum):
    """Types of success metrics."""

    # Numeric metrics
    COUNT = "count"  # Integer count (e.g., issues found)
    PERCENTAGE = "percentage"  # 0-100 percentage
    RATIO = "ratio"  # 0-1 ratio
    DURATION = "duration"  # Time in seconds

    # Boolean metrics
    BOOLEAN = "boolean"  # True/False

    # Comparison metrics
    IMPROVEMENT = "improvement"  # Before/after comparison
    THRESHOLD = "threshold"  # Above/below threshold

    # Quality metrics
    SCORE = "score"  # 0-10 quality score
    RATING = "rating"  # Categorical (good, moderate, poor)


class MetricDirection(Enum):
    """Which direction indicates success."""

    HIGHER_IS_BETTER = "higher"  # More issues found = better
    LOWER_IS_BETTER = "lower"  # Less time = better
    TARGET_VALUE = "target"  # Specific value is best
    RANGE = "range"  # Within a range is success


@dataclass
class SuccessMetric:
    """A single success metric definition.

    Example:
        >>> metric = SuccessMetric(
        ...     id="security_issues_found",
        ...     name="Security Issues Detected",
        ...     description="Number of security vulnerabilities identified",
        ...     metric_type=MetricType.COUNT,
        ...     direction=MetricDirection.HIGHER_IS_BETTER,
        ...     target_value=None,  # No specific target
        ...     minimum_value=0,
        ...     unit="issues"
        ... )
    """

    # Unique metric identifier
    id: str

    # Display name
    name: str

    # Description of what this measures
    description: str

    # Type of metric
    metric_type: MetricType

    # Which direction indicates success
    direction: MetricDirection = MetricDirection.HIGHER_IS_BETTER

    # Target value (for TARGET_VALUE direction)
    target_value: float | None = None

    # Minimum acceptable value
    minimum_value: float | None = None

    # Maximum acceptable value
    maximum_value: float | None = None

    # Unit of measurement
    unit: str = ""

    # Weight for composite scoring (0-1)
    weight: float = 1.0

    # Whether this is a primary success indicator
    is_primary: bool = False

    # How to extract this metric from workflow output
    extraction_path: str = ""  # JSONPath-like expression

    # Custom extraction function
    extractor: Callable[[dict], float | bool] | None = None

    def evaluate(
        self,
        value: float | bool,
        baseline: float | bool | None = None,
    ) -> tuple[bool, float, str]:
        """Evaluate if a value meets this metric's success criteria.

        Args:
            value: The measured value
            baseline: Optional baseline for comparison

        Returns:
            Tuple of (met_criteria, score 0-1, explanation)
        """
        # Boolean metrics
        if self.metric_type == MetricType.BOOLEAN:
            if isinstance(value, bool):
                met = value
                score = 1.0 if value else 0.0
                explanation = "Criteria met" if met else "Criteria not met"
                return met, score, explanation

        # Ensure numeric value for other types
        if not isinstance(value, int | float):
            return False, 0.0, f"Expected numeric value, got {type(value)}"

        # Calculate score based on direction
        if self.direction == MetricDirection.HIGHER_IS_BETTER:
            if self.minimum_value is not None:
                met = value >= self.minimum_value
                # Score is ratio of value to minimum (capped at 1.0)
                score = min(value / self.minimum_value, 1.0) if self.minimum_value > 0 else 1.0
            else:
                met = True  # No minimum, always met
                score = 1.0

        elif self.direction == MetricDirection.LOWER_IS_BETTER:
            if self.maximum_value is not None:
                met = value <= self.maximum_value
                # Score is inverse ratio (lower is better)
                score = (
                    max(1.0 - (value / self.maximum_value), 0.0) if self.maximum_value > 0 else 1.0
                )
            else:
                met = True
                score = 1.0

        elif self.direction == MetricDirection.TARGET_VALUE:
            if self.target_value is not None:
                deviation = abs(value - self.target_value)
                # Allow 10% tolerance by default
                tolerance = self.target_value * 0.1 if self.target_value > 0 else 1.0
                met = deviation <= tolerance
                score = max(1.0 - (deviation / max(tolerance, 0.001)), 0.0)
            else:
                met = True
                score = 1.0

        elif self.direction == MetricDirection.RANGE:
            min_val = self.minimum_value or float("-inf")
            max_val = self.maximum_value or float("inf")
            met = min_val <= value <= max_val
            if met:
                # Score based on position in range (center = best)
                range_size = max_val - min_val
                if range_size > 0 and range_size != float("inf"):
                    center = (min_val + max_val) / 2
                    distance_from_center = abs(value - center)
                    score = 1.0 - (distance_from_center / (range_size / 2))
                else:
                    score = 1.0
            else:
                score = 0.0
        else:
            met = True
            score = 1.0

        # Generate explanation
        explanation = self._generate_explanation(value, met, score, baseline)

        return met, score, explanation

    def _generate_explanation(
        self,
        value: float | bool,
        met: bool,
        score: float,
        baseline: float | bool | None,
    ) -> str:
        """Generate human-readable explanation of the evaluation."""
        parts = []

        # Value statement
        if self.unit:
            parts.append(f"Measured: {value} {self.unit}")
        else:
            parts.append(f"Measured: {value}")

        # Comparison to baseline
        if (
            baseline is not None
            and isinstance(value, int | float)
            and isinstance(baseline, int | float)
        ):
            diff = value - baseline
            pct_change = (diff / baseline * 100) if baseline != 0 else 0
            direction = "↑" if diff > 0 else "↓" if diff < 0 else "→"
            parts.append(f"vs baseline: {direction} {abs(pct_change):.1f}%")

        # Target comparison
        if self.direction == MetricDirection.TARGET_VALUE and self.target_value is not None:
            parts.append(f"Target: {self.target_value} {self.unit}".strip())

        # Result
        result = "✓ Met" if met else "✗ Not met"
        parts.append(f"{result} (score: {score:.1%})")

        return " | ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "metric_type": self.metric_type.value,
            "direction": self.direction.value,
            "target_value": self.target_value,
            "minimum_value": self.minimum_value,
            "maximum_value": self.maximum_value,
            "unit": self.unit,
            "weight": self.weight,
            "is_primary": self.is_primary,
            "extraction_path": self.extraction_path,
        }


@dataclass
class MetricResult:
    """Result of evaluating a single metric."""

    metric_id: str
    value: float | bool
    met_criteria: bool
    score: float
    explanation: str
    baseline: float | bool | None = None
    timestamp: str = ""


@dataclass
class SuccessEvaluation:
    """Result of evaluating success criteria."""

    # Whether overall success criteria were met
    overall_success: bool

    # Overall score (0-1)
    overall_score: float

    # Individual metric results
    metric_results: list[MetricResult]

    # Human-readable summary
    summary: str

    # Primary metrics that passed
    primary_metrics_passed: int = 0

    # Total primary metrics
    total_primary_metrics: int = 0

    # Timestamp of evaluation
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "overall_success": self.overall_success,
            "overall_score": self.overall_score,
            "metric_results": [
                {
                    "metric_id": r.metric_id,
                    "value": r.value,
                    "met_criteria": r.met_criteria,
                    "score": r.score,
                    "explanation": r.explanation,
                    "baseline": r.baseline,
                }
                for r in self.metric_results
            ],
            "summary": self.summary,
            "primary_metrics_passed": self.primary_metrics_passed,
            "total_primary_metrics": self.total_primary_metrics,
            "evaluated_at": self.evaluated_at,
        }
