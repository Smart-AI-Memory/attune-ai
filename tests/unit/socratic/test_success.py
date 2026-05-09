"""Tests for the Success Criteria and Measurement System.

Tests cover:
- MetricType and MetricDirection enums
- SuccessMetric dataclass and evaluate() method
- SuccessCriteria dataclass and overall evaluation
- Predefined criteria factory functions

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.socratic.success import (
    MetricDirection,
    MetricResult,
    MetricType,
    SuccessCriteria,
    SuccessEvaluation,
    SuccessMetric,
    code_review_criteria,
    security_audit_criteria,
    test_generation_criteria,
)

# =============================================================================
# METRIC TYPE ENUM TESTS
# =============================================================================


@pytest.mark.unit
class TestMetricType:
    """Tests for MetricType enum."""

    def test_all_metric_types_exist(self):
        """Verify all expected metric types are defined."""
        expected_types = [
            "COUNT",
            "PERCENTAGE",
            "RATIO",
            "DURATION",
            "BOOLEAN",
            "IMPROVEMENT",
            "THRESHOLD",
            "SCORE",
            "RATING",
        ]
        for type_name in expected_types:
            assert hasattr(MetricType, type_name)

    @pytest.mark.parametrize(
        "metric_type,expected_value",
        [
            (MetricType.COUNT, "count"),
            (MetricType.PERCENTAGE, "percentage"),
            (MetricType.RATIO, "ratio"),
            (MetricType.DURATION, "duration"),
            (MetricType.BOOLEAN, "boolean"),
            (MetricType.IMPROVEMENT, "improvement"),
            (MetricType.THRESHOLD, "threshold"),
            (MetricType.SCORE, "score"),
            (MetricType.RATING, "rating"),
        ],
    )
    def test_metric_type_values(self, metric_type, expected_value):
        """Test that metric types have correct string values."""
        assert metric_type.value == expected_value


@pytest.mark.unit
class TestMetricDirection:
    """Tests for MetricDirection enum."""

    def test_all_directions_exist(self):
        """Verify all expected directions are defined."""
        expected_directions = [
            "HIGHER_IS_BETTER",
            "LOWER_IS_BETTER",
            "TARGET_VALUE",
            "RANGE",
        ]
        for direction_name in expected_directions:
            assert hasattr(MetricDirection, direction_name)

    @pytest.mark.parametrize(
        "direction,expected_value",
        [
            (MetricDirection.HIGHER_IS_BETTER, "higher"),
            (MetricDirection.LOWER_IS_BETTER, "lower"),
            (MetricDirection.TARGET_VALUE, "target"),
            (MetricDirection.RANGE, "range"),
        ],
    )
    def test_direction_values(self, direction, expected_value):
        """Test that directions have correct string values."""
        assert direction.value == expected_value


# =============================================================================
# SUCCESS METRIC TESTS
# =============================================================================


@pytest.mark.unit
class TestSuccessMetricCreation:
    """Tests for SuccessMetric dataclass creation."""

    def test_minimal_creation(self):
        """Test creating metric with minimal required fields."""
        metric = SuccessMetric(
            id="test_metric",
            name="Test Metric",
            description="A test metric",
            metric_type=MetricType.COUNT,
        )
        assert metric.id == "test_metric"
        assert metric.name == "Test Metric"
        assert metric.direction == MetricDirection.HIGHER_IS_BETTER  # default

    def test_full_creation(self):
        """Test creating metric with all fields."""
        metric = SuccessMetric(
            id="full_metric",
            name="Full Metric",
            description="Fully specified metric",
            metric_type=MetricType.PERCENTAGE,
            direction=MetricDirection.LOWER_IS_BETTER,
            target_value=50.0,
            minimum_value=0.0,
            maximum_value=100.0,
            unit="%",
            weight=0.8,
            is_primary=True,
            extraction_path="metrics.value",
        )
        assert metric.id == "full_metric"
        assert metric.weight == 0.8
        assert metric.is_primary is True
        assert metric.unit == "%"

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        metric = SuccessMetric(
            id="test",
            name="Test",
            description="Test description",
            metric_type=MetricType.COUNT,
            is_primary=True,
        )
        result = metric.to_dict()

        assert result["id"] == "test"
        assert result["name"] == "Test"
        assert result["metric_type"] == "count"
        assert result["direction"] == "higher"
        assert result["is_primary"] is True


@pytest.mark.unit
class TestSuccessMetricBooleanEvaluation:
    """Tests for evaluating boolean metrics."""

    @pytest.fixture
    def boolean_metric(self):
        """Create a boolean metric for testing."""
        return SuccessMetric(
            id="bool_test",
            name="Boolean Test",
            description="Tests boolean values",
            metric_type=MetricType.BOOLEAN,
        )

    def test_boolean_true_passes(self, boolean_metric):
        """Test that True value passes boolean metric."""
        met, score, explanation = boolean_metric.evaluate(True)
        assert met is True
        assert score == 1.0
        assert "met" in explanation.lower()

    def test_boolean_false_fails(self, boolean_metric):
        """Test that False value fails boolean metric."""
        met, score, explanation = boolean_metric.evaluate(False)
        assert met is False
        assert score == 0.0
        assert "not met" in explanation.lower()


@pytest.mark.unit
class TestSuccessMetricHigherIsBetter:
    """Tests for HIGHER_IS_BETTER direction."""

    @pytest.fixture
    def higher_metric(self):
        """Create a higher-is-better metric."""
        return SuccessMetric(
            id="issues_found",
            name="Issues Found",
            description="Number of issues",
            metric_type=MetricType.COUNT,
            direction=MetricDirection.HIGHER_IS_BETTER,
            minimum_value=5,
            unit="issues",
        )

    def test_value_above_minimum_passes(self, higher_metric):
        """Test that values above minimum pass."""
        met, score, _ = higher_metric.evaluate(10)
        assert met is True
        assert score == 1.0  # Capped at 1.0

    def test_value_at_minimum_passes(self, higher_metric):
        """Test that value exactly at minimum passes."""
        met, score, _ = higher_metric.evaluate(5)
        assert met is True
        assert score == 1.0

    def test_value_below_minimum_fails(self, higher_metric):
        """Test that values below minimum fail."""
        met, score, _ = higher_metric.evaluate(3)
        assert met is False
        assert score == 0.6  # 3/5 = 0.6

    def test_no_minimum_always_passes(self):
        """Test that no minimum means always passes."""
        metric = SuccessMetric(
            id="test",
            name="Test",
            description="No minimum",
            metric_type=MetricType.COUNT,
            direction=MetricDirection.HIGHER_IS_BETTER,
        )
        met, score, _ = metric.evaluate(0)
        assert met is True
        assert score == 1.0


@pytest.mark.unit
class TestSuccessMetricLowerIsBetter:
    """Tests for LOWER_IS_BETTER direction."""

    @pytest.fixture
    def lower_metric(self):
        """Create a lower-is-better metric."""
        return SuccessMetric(
            id="response_time",
            name="Response Time",
            description="Time to respond",
            metric_type=MetricType.DURATION,
            direction=MetricDirection.LOWER_IS_BETTER,
            maximum_value=100,
            unit="ms",
        )

    def test_value_below_maximum_passes(self, lower_metric):
        """Test that values below maximum pass."""
        met, score, _ = lower_metric.evaluate(50)
        assert met is True
        assert score == 0.5  # 1 - (50/100) = 0.5

    def test_value_at_maximum_passes(self, lower_metric):
        """Test that value exactly at maximum passes."""
        met, score, _ = lower_metric.evaluate(100)
        assert met is True
        assert score == 0.0  # 1 - (100/100) = 0

    def test_value_above_maximum_fails(self, lower_metric):
        """Test that values above maximum fail."""
        met, score, _ = lower_metric.evaluate(150)
        assert met is False
        assert score == 0.0  # Clamped to 0

    def test_zero_value_perfect_score(self, lower_metric):
        """Test that zero value gives perfect score."""
        met, score, _ = lower_metric.evaluate(0)
        assert met is True
        assert score == 1.0


@pytest.mark.unit
class TestSuccessMetricTargetValue:
    """Tests for TARGET_VALUE direction."""

    @pytest.fixture
    def target_metric(self):
        """Create a target value metric."""
        return SuccessMetric(
            id="coverage",
            name="Coverage",
            description="Target coverage",
            metric_type=MetricType.PERCENTAGE,
            direction=MetricDirection.TARGET_VALUE,
            target_value=80.0,
            unit="%",
        )

    def test_exact_target_passes(self, target_metric):
        """Test that exact target value passes with perfect score."""
        met, score, _ = target_metric.evaluate(80.0)
        assert met is True
        assert score == 1.0

    def test_within_tolerance_passes(self, target_metric):
        """Test that value within 10% tolerance passes."""
        # 10% of 80 = 8, so 72-88 should pass
        met, score, _ = target_metric.evaluate(85.0)
        assert met is True
        assert score > 0.0

    def test_outside_tolerance_fails(self, target_metric):
        """Test that value outside tolerance fails."""
        met, score, _ = target_metric.evaluate(60.0)
        assert met is False

    def test_no_target_always_passes(self):
        """Test that no target means always passes."""
        metric = SuccessMetric(
            id="test",
            name="Test",
            description="No target",
            metric_type=MetricType.PERCENTAGE,
            direction=MetricDirection.TARGET_VALUE,
        )
        met, score, _ = metric.evaluate(50.0)
        assert met is True
        assert score == 1.0


@pytest.mark.unit
class TestSuccessMetricRange:
    """Tests for RANGE direction."""

    @pytest.fixture
    def range_metric(self):
        """Create a range metric."""
        return SuccessMetric(
            id="score",
            name="Quality Score",
            description="Score in range",
            metric_type=MetricType.SCORE,
            direction=MetricDirection.RANGE,
            minimum_value=60.0,
            maximum_value=100.0,
        )

    def test_value_in_range_passes(self, range_metric):
        """Test that values within range pass."""
        met, score, _ = range_metric.evaluate(80.0)
        assert met is True
        assert score == 1.0  # Center of range

    def test_value_at_minimum_passes(self, range_metric):
        """Test that value at minimum passes."""
        met, score, _ = range_metric.evaluate(60.0)
        assert met is True
        assert score == 0.0  # At edge

    def test_value_at_maximum_passes(self, range_metric):
        """Test that value at maximum passes."""
        met, score, _ = range_metric.evaluate(100.0)
        assert met is True
        assert score == 0.0  # At edge

    def test_value_below_range_fails(self, range_metric):
        """Test that values below range fail."""
        met, score, _ = range_metric.evaluate(50.0)
        assert met is False
        assert score == 0.0

    def test_value_above_range_fails(self, range_metric):
        """Test that values above range fail."""
        met, score, _ = range_metric.evaluate(110.0)
        assert met is False
        assert score == 0.0


@pytest.mark.unit
class TestSuccessMetricEdgeCases:
    """Tests for edge cases in metric evaluation."""

    def test_non_numeric_value_fails(self):
        """Test that non-numeric values fail for numeric metrics."""
        metric = SuccessMetric(
            id="test",
            name="Test",
            description="Test",
            metric_type=MetricType.COUNT,
        )
        met, score, explanation = metric.evaluate("not a number")
        assert met is False
        assert score == 0.0
        assert "Expected numeric" in explanation

    def test_explanation_includes_unit(self):
        """Test that explanation includes unit when specified."""
        metric = SuccessMetric(
            id="test",
            name="Test",
            description="Test",
            metric_type=MetricType.COUNT,
            unit="items",
        )
        _, _, explanation = metric.evaluate(10)
        assert "items" in explanation

    def test_explanation_includes_baseline_comparison(self):
        """Test that explanation includes baseline when provided."""
        metric = SuccessMetric(
            id="test",
            name="Test",
            description="Test",
            metric_type=MetricType.COUNT,
        )
        _, _, explanation = metric.evaluate(10, baseline=5)
        assert "baseline" in explanation.lower()
        assert "100.0%" in explanation  # 100% increase from 5 to 10


# =============================================================================
# METRIC RESULT TESTS
# =============================================================================


@pytest.mark.unit
class TestMetricResult:
    """Tests for MetricResult dataclass."""

    def test_creation(self):
        """Test creating a MetricResult."""
        result = MetricResult(
            metric_id="test",
            value=85.0,
            met_criteria=True,
            score=0.85,
            explanation="Test passed",
        )
        assert result.metric_id == "test"
        assert result.value == 85.0
        assert result.met_criteria is True

    def test_with_baseline(self):
        """Test MetricResult with baseline."""
        result = MetricResult(
            metric_id="test",
            value=85.0,
            met_criteria=True,
            score=0.85,
            explanation="Test passed",
            baseline=70.0,
        )
        assert result.baseline == 70.0


# =============================================================================
# SUCCESS CRITERIA TESTS
# =============================================================================


@pytest.mark.unit
class TestSuccessCriteriaCreation:
    """Tests for SuccessCriteria creation."""

    def test_minimal_creation(self):
        """Test creating criteria with minimal fields."""
        criteria = SuccessCriteria()
        assert criteria.metrics == []
        assert criteria.success_threshold == 0.7

    def test_full_creation(self):
        """Test creating criteria with all fields."""
        metric = SuccessMetric(
            id="test",
            name="Test",
            description="Test",
            metric_type=MetricType.COUNT,
        )
        criteria = SuccessCriteria(
            id="full_criteria",
            name="Full Criteria",
            description="Full description",
            metrics=[metric],
            success_threshold=0.8,
            require_all=True,
            min_primary_metrics=1,
        )
        assert criteria.id == "full_criteria"
        assert len(criteria.metrics) == 1
        assert criteria.success_threshold == 0.8
        assert criteria.require_all is True

    def test_add_metric(self):
        """Test adding a metric to criteria."""
        criteria = SuccessCriteria()
        metric = SuccessMetric(
            id="test",
            name="Test",
            description="Test",
            metric_type=MetricType.COUNT,
        )
        criteria.add_metric(metric)
        assert len(criteria.metrics) == 1
        assert criteria.metrics[0].id == "test"

    def test_get_primary_metrics(self):
        """Test getting primary metrics only."""
        primary = SuccessMetric(
            id="primary",
            name="Primary",
            description="Primary",
            metric_type=MetricType.COUNT,
            is_primary=True,
        )
        secondary = SuccessMetric(
            id="secondary",
            name="Secondary",
            description="Secondary",
            metric_type=MetricType.COUNT,
            is_primary=False,
        )
        criteria = SuccessCriteria(metrics=[primary, secondary])
        primaries = criteria.get_primary_metrics()
        assert len(primaries) == 1
        assert primaries[0].id == "primary"

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        metric = SuccessMetric(
            id="test",
            name="Test",
            description="Test",
            metric_type=MetricType.COUNT,
        )
        criteria = SuccessCriteria(
            id="test_criteria",
            name="Test Criteria",
            metrics=[metric],
        )
        result = criteria.to_dict()
        assert result["id"] == "test_criteria"
        assert len(result["metrics"]) == 1


@pytest.mark.unit
class TestSuccessCriteriaEvaluation:
    """Tests for SuccessCriteria.evaluate()."""

    @pytest.fixture
    def basic_criteria(self):
        """Create basic criteria for testing."""
        return SuccessCriteria(
            id="basic",
            name="Basic Criteria",
            metrics=[
                SuccessMetric(
                    id="count",
                    name="Count",
                    description="Count metric",
                    metric_type=MetricType.COUNT,
                    minimum_value=5,
                    is_primary=True,
                ),
                SuccessMetric(
                    id="percentage",
                    name="Percentage",
                    description="Percentage metric",
                    metric_type=MetricType.PERCENTAGE,
                    minimum_value=50,
                ),
            ],
            success_threshold=0.7,
            min_primary_metrics=1,
        )

    def test_evaluate_all_pass(self, basic_criteria):
        """Test evaluation when all metrics pass."""
        output = {"count": 10, "percentage": 80}
        result = basic_criteria.evaluate(output)

        assert result.overall_success is True
        assert result.overall_score >= 0.7
        assert len(result.metric_results) == 2

    def test_evaluate_partial_pass(self, basic_criteria):
        """Test evaluation when some metrics pass."""
        output = {"count": 10, "percentage": 30}
        result = basic_criteria.evaluate(output)

        # Count passes (10 >= 5), percentage fails (30 < 50)
        count_result = next(r for r in result.metric_results if r.metric_id == "count")
        pct_result = next(r for r in result.metric_results if r.metric_id == "percentage")

        assert count_result.met_criteria is True
        assert pct_result.met_criteria is False

    def test_evaluate_with_missing_metric(self, basic_criteria):
        """Test evaluation when a metric is missing from output."""
        output = {"count": 10}  # percentage missing
        result = basic_criteria.evaluate(output)

        pct_result = next(r for r in result.metric_results if r.metric_id == "percentage")
        assert pct_result.met_criteria is False
        assert "not found" in pct_result.explanation.lower()

    def test_evaluate_with_baselines(self, basic_criteria):
        """Test evaluation with baseline values."""
        output = {"count": 10, "percentage": 80}
        baselines = {"count": 5, "percentage": 60}
        result = basic_criteria.evaluate(output, baselines)

        count_result = next(r for r in result.metric_results if r.metric_id == "count")
        assert count_result.baseline == 5

    def test_evaluate_empty_metrics(self):
        """Test evaluation with no metrics."""
        criteria = SuccessCriteria()
        result = criteria.evaluate({})

        assert result.overall_success is False
        assert result.overall_score == 0.0
        assert "No metrics" in result.summary

    def test_evaluate_require_all_true(self):
        """Test evaluation with require_all=True."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="a",
                    name="A",
                    description="A",
                    metric_type=MetricType.COUNT,
                    minimum_value=5,
                ),
                SuccessMetric(
                    id="b",
                    name="B",
                    description="B",
                    metric_type=MetricType.COUNT,
                    minimum_value=5,
                ),
            ],
            require_all=True,
        )

        # One passes, one fails
        output = {"a": 10, "b": 2}
        result = criteria.evaluate(output)

        assert result.overall_success is False  # require_all means both must pass


@pytest.mark.unit
class TestSuccessCriteriaExtraction:
    """Tests for metric value extraction from output."""

    def test_direct_key_extraction(self):
        """Test extracting value from direct key."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="count",
                    name="Count",
                    description="Count",
                    metric_type=MetricType.COUNT,
                ),
            ],
        )
        result = criteria.evaluate({"count": 42})
        assert result.metric_results[0].value == 42

    def test_extraction_path(self):
        """Test extracting value using extraction path."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="nested",
                    name="Nested",
                    description="Nested",
                    metric_type=MetricType.COUNT,
                    extraction_path="data.stats.count",
                ),
            ],
        )
        output = {"data": {"stats": {"count": 100}}}
        result = criteria.evaluate(output)
        assert result.metric_results[0].value == 100

    def test_extraction_from_metrics_key(self):
        """Test extracting from nested 'metrics' key."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="special",
                    name="Special",
                    description="Special",
                    metric_type=MetricType.COUNT,
                ),
            ],
        )
        output = {"metrics": {"special": 50}}
        result = criteria.evaluate(output)
        assert result.metric_results[0].value == 50

    def test_custom_extractor(self):
        """Test using custom extractor function."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="custom",
                    name="Custom",
                    description="Custom",
                    metric_type=MetricType.COUNT,
                    extractor=lambda output: output["a"] + output["b"],
                ),
            ],
        )
        output = {"a": 10, "b": 20}
        result = criteria.evaluate(output)
        assert result.metric_results[0].value == 30

    def test_extractor_exception_returns_none(self):
        """Custom extractor that raises returns None (lines 169-170)."""

        def bad_extractor(_output):
            raise KeyError("missing")

        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="bad",
                    name="Bad",
                    description="raises",
                    metric_type=MetricType.COUNT,
                    extractor=bad_extractor,
                ),
            ],
        )
        result = criteria.evaluate({})
        assert "not found" in result.metric_results[0].explanation.lower()

    def test_extraction_path_traverses_list_index(self):
        """extraction_path with numeric segment traverses list (lines 179-180)."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="from_list",
                    name="From List",
                    description="list",
                    metric_type=MetricType.COUNT,
                    extraction_path="items.1.score",
                ),
            ],
        )
        output = {"items": [{"score": 10}, {"score": 99}]}
        result = criteria.evaluate(output)
        assert result.metric_results[0].value == 99

    def test_extraction_path_non_dict_non_list_returns_none(self):
        """extraction_path hitting non-traversable value returns None (lines 181-182)."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="dead_end",
                    name="Dead End",
                    description="x",
                    metric_type=MetricType.COUNT,
                    extraction_path="data.value.unreachable",
                ),
            ],
        )
        # data.value is a string — can't traverse further
        output = {"data": {"value": "stop here"}}
        result = criteria.evaluate(output)
        assert "not found" in result.metric_results[0].explanation.lower()

    def test_extraction_path_key_error_returns_none(self):
        """extraction_path missing key raises KeyError → returns None (lines 184-185)."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="absent",
                    name="Absent",
                    description="x",
                    metric_type=MetricType.COUNT,
                    extraction_path="data.absent_key",
                ),
            ],
        )
        result = criteria.evaluate({"data": {"present": 1}})
        assert "not found" in result.metric_results[0].explanation.lower()

    def test_metric_evaluate_boolean_metric_with_non_bool_value_falls_through(self):
        """BOOLEAN metric with non-bool value falls through to numeric check (branch 123->130)."""
        from attune.socratic.success_models import (
            MetricDirection,
            MetricType,
            SuccessMetric,
        )

        m = SuccessMetric(
            id="b",
            name="b",
            description="d",
            metric_type=MetricType.BOOLEAN,
            direction=MetricDirection.HIGHER_IS_BETTER,
        )
        # Value is not bool — falls through; then numeric check applies
        # (1 is technically bool-castable but isinstance(1, bool) is False)
        # Use a non-bool, non-numeric value to fall through AND fail numeric check.
        met, score, explanation = m.evaluate("not-a-bool")
        assert met is False
        assert "Expected numeric" in explanation

    def test_metric_lower_is_better_no_maximum_always_met(self):
        """LOWER_IS_BETTER with no maximum_value → always met (lines 151-152)."""
        from attune.socratic.success_models import (
            MetricDirection,
            MetricType,
            SuccessMetric,
        )

        m = SuccessMetric(
            id="l",
            name="l",
            description="d",
            metric_type=MetricType.COUNT,
            direction=MetricDirection.LOWER_IS_BETTER,
            # no maximum_value set
        )
        met, score, _ = m.evaluate(9999)
        assert met is True
        assert score == 1.0

    def test_metric_range_with_infinite_size_scores_one(self):
        """RANGE with infinite range_size returns score 1.0 (line 177)."""
        from attune.socratic.success_models import (
            MetricDirection,
            MetricType,
            SuccessMetric,
        )

        m = SuccessMetric(
            id="r",
            name="r",
            description="d",
            metric_type=MetricType.COUNT,
            direction=MetricDirection.RANGE,
            # No minimum/maximum → range becomes [-inf, +inf]
        )
        met, score, _ = m.evaluate(42)
        assert met is True
        assert score == 1.0

    def test_metric_unknown_direction_defaults_to_met(self):
        """An unrecognized MetricDirection hits the else branch (lines 181-182)."""
        from attune.socratic.success_models import MetricType, SuccessMetric

        m = SuccessMetric(
            id="u",
            name="u",
            description="d",
            metric_type=MetricType.COUNT,
        )
        # Manually set direction to a value not in the enum's expected paths
        # — using a string directly to bypass the elif chain.
        m.direction = "bogus-direction"  # type: ignore[assignment]
        met, score, _ = m.evaluate(10)
        assert met is True
        assert score == 1.0

    def test_zero_weight_metrics_use_simple_average(self):
        """All-zero metric weights → fallback to simple average (line 240)."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="m1",
                    name="M1",
                    description="d",
                    metric_type=MetricType.COUNT,
                    weight=0.0,
                ),
                SuccessMetric(
                    id="m2",
                    name="M2",
                    description="d",
                    metric_type=MetricType.COUNT,
                    weight=0.0,
                ),
            ],
            require_all=False,
        )
        result = criteria.evaluate({"m1": 1, "m2": 2})
        # Score is the simple average — verify no division-by-zero crash and a numeric score
        assert isinstance(result.overall_score, float)

    def test_metrics_dict_present_but_id_absent_returns_none(self):
        """output['metrics'] present but metric.id not in it → returns None (193->196)."""
        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="ghost",
                    name="Ghost",
                    description="x",
                    metric_type=MetricType.COUNT,
                ),
            ],
        )
        # 'metrics' dict exists but doesn't contain 'ghost'
        result = criteria.evaluate({"metrics": {"other": 1}})
        assert "not found" in result.metric_results[0].explanation.lower()


@pytest.mark.unit
class TestSuccessCriteriaCustomEvaluator:
    """Tests for custom evaluator function."""

    def test_custom_evaluator_overrides(self):
        """Test that custom evaluator overrides default logic."""

        def custom_eval(results):
            # Always return True if any metric passes
            return any(r.met_criteria for r in results.values())

        criteria = SuccessCriteria(
            metrics=[
                SuccessMetric(
                    id="test",
                    name="Test",
                    description="Test",
                    metric_type=MetricType.COUNT,
                    minimum_value=100,  # Will fail
                ),
            ],
            success_threshold=0.9,  # High threshold
            custom_evaluator=custom_eval,
        )

        output = {"test": 1}  # Far below minimum
        result = criteria.evaluate(output)

        # Custom evaluator says any pass = success, but none pass here
        assert result.overall_success is False


# =============================================================================
# SUCCESS EVALUATION TESTS
# =============================================================================


@pytest.mark.unit
class TestSuccessEvaluation:
    """Tests for SuccessEvaluation dataclass."""

    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        result = MetricResult(
            metric_id="test",
            value=85,
            met_criteria=True,
            score=0.85,
            explanation="Test passed",
        )
        evaluation = SuccessEvaluation(
            overall_success=True,
            overall_score=0.85,
            metric_results=[result],
            summary="Test summary",
            primary_metrics_passed=1,
            total_primary_metrics=1,
        )
        d = evaluation.to_dict()

        assert d["overall_success"] is True
        assert d["overall_score"] == 0.85
        assert len(d["metric_results"]) == 1
        assert d["primary_metrics_passed"] == 1


# =============================================================================
# PREDEFINED CRITERIA FACTORY TESTS
# =============================================================================


@pytest.mark.unit
class TestCodeReviewCriteria:
    """Tests for code_review_criteria() factory."""

    def test_factory_returns_valid_criteria(self):
        """Test that factory returns valid SuccessCriteria."""
        criteria = code_review_criteria()

        assert isinstance(criteria, SuccessCriteria)
        assert criteria.id == "code_review_success"
        assert len(criteria.metrics) == 4

    def test_has_primary_metrics(self):
        """Test that criteria has primary metrics."""
        criteria = code_review_criteria()
        primaries = criteria.get_primary_metrics()

        assert len(primaries) >= 1

    def test_metrics_have_extraction_paths(self):
        """Test that metrics have extraction paths."""
        criteria = code_review_criteria()

        for metric in criteria.metrics:
            assert metric.extraction_path != ""

    def test_evaluate_with_sample_output(self):
        """Test evaluating with realistic output."""
        criteria = code_review_criteria()
        output = {
            "findings_count": 5,
            "severity_coverage": 75,
            "duration_seconds": 60,
            "has_recommendations": True,
        }
        result = criteria.evaluate(output)

        assert result.overall_success is True
        assert result.overall_score > 0


@pytest.mark.unit
class TestSecurityAuditCriteria:
    """Tests for security_audit_criteria() factory."""

    def test_factory_returns_valid_criteria(self):
        """Test that factory returns valid SuccessCriteria."""
        criteria = security_audit_criteria()

        assert isinstance(criteria, SuccessCriteria)
        assert criteria.id == "security_audit_success"
        assert len(criteria.metrics) == 4

    def test_has_critical_issues_metric(self):
        """Test that criteria has critical issues metric with higher weight."""
        criteria = security_audit_criteria()
        critical = next((m for m in criteria.metrics if m.id == "critical_issues"), None)

        assert critical is not None
        assert critical.weight > 1.0  # Extra weight


@pytest.mark.unit
class TestTestGenerationCriteria:
    """Tests for test_generation_criteria() factory."""

    def test_factory_returns_valid_criteria(self):
        """Test that factory returns valid SuccessCriteria."""
        criteria = test_generation_criteria()

        assert isinstance(criteria, SuccessCriteria)
        assert criteria.id == "test_generation_success"
        assert len(criteria.metrics) == 4

    def test_requires_multiple_primary_metrics(self):
        """Test that criteria requires multiple primary metrics."""
        criteria = test_generation_criteria()

        assert criteria.min_primary_metrics == 2

    def test_evaluate_with_sample_output(self):
        """Test evaluating with realistic output."""
        criteria = test_generation_criteria()
        output = {
            "tests": {
                "count": 10,
                "pass_rate": 90,
            },
            "coverage": {
                "increase_percent": 15,
            },
            "edge_cases": {
                "count": 5,
            },
        }
        result = criteria.evaluate(output)

        assert len(result.metric_results) == 4
