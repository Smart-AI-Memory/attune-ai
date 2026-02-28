"""Unit tests for core progressive escalation data structures."""

from datetime import datetime

from attune.workflows.progressive.core import (
    EscalationConfig,
    FailureAnalysis,
    ProgressiveWorkflowResult,
    Tier,
    TierResult,
)


class TestTier:
    """Test Tier enum."""

    def test_tier_ordering(self):
        """Test that tiers can be compared for ordering."""
        assert Tier.CHEAP < Tier.CAPABLE
        assert Tier.CAPABLE < Tier.PREMIUM
        assert not (Tier.PREMIUM < Tier.CHEAP)

    def test_tier_values(self):
        """Test tier string values."""
        assert Tier.CHEAP.value == "cheap"
        assert Tier.CAPABLE.value == "capable"
        assert Tier.PREMIUM.value == "premium"


class TestFailureAnalysis:
    """Test FailureAnalysis class."""

    def test_calculate_quality_score_perfect(self):
        """Test CQS calculation for perfect results."""
        analysis = FailureAnalysis(
            test_pass_rate=1.0,
            coverage_percent=100.0,
            assertion_depth=10.0,
            confidence_score=1.0,
            syntax_errors=[],
        )

        cqs = analysis.calculate_quality_score()

        # Expected: 0.4*100 + 0.25*100 + 0.2*100 + 0.15*100 = 100
        assert cqs == 100.0

    def test_calculate_quality_score_typical(self):
        """Test CQS calculation for typical results."""
        analysis = FailureAnalysis(
            test_pass_rate=0.85,
            coverage_percent=78.0,
            assertion_depth=5.2,
            confidence_score=0.92,
            syntax_errors=[],
        )

        cqs = analysis.calculate_quality_score()

        # Expected: 0.4*85 + 0.25*78 + 0.2*52 + 0.15*92
        #         = 34 + 19.5 + 10.4 + 13.8 = 77.7
        assert 77 <= cqs <= 78

    def test_calculate_quality_score_with_syntax_errors(self):
        """Test that syntax errors halve the score."""
        analysis = FailureAnalysis(
            test_pass_rate=0.90,
            coverage_percent=85.0,
            assertion_depth=6.0,
            confidence_score=0.95,
            syntax_errors=[SyntaxError("test")],
        )

        cqs = analysis.calculate_quality_score()

        # Expected: (0.4*90 + 0.25*85 + 0.2*60 + 0.15*95) * 0.5
        #         = (36 + 21.25 + 12 + 14.25) * 0.5 = 83.5 * 0.5 = 41.75
        assert 41 <= cqs <= 42

    def test_should_escalate_low_cqs(self):
        """Test escalation trigger on low CQS."""
        analysis = FailureAnalysis(
            test_pass_rate=0.50,
            coverage_percent=40.0,
            assertion_depth=2.0,
            confidence_score=0.60,
        )

        assert analysis.should_escalate is True

    def test_should_escalate_high_quality(self):
        """Test no escalation on high quality."""
        analysis = FailureAnalysis(
            test_pass_rate=0.90,
            coverage_percent=85.0,
            assertion_depth=7.0,
            confidence_score=0.95,
        )

        assert analysis.should_escalate is False

    def test_should_escalate_many_syntax_errors(self):
        """Test escalation trigger on many syntax errors."""
        analysis = FailureAnalysis(
            test_pass_rate=0.80,
            coverage_percent=70.0,
            assertion_depth=5.0,
            confidence_score=0.85,
            syntax_errors=[SyntaxError(f"error {i}") for i in range(5)],
        )

        assert analysis.should_escalate is True

    def test_failure_severity_critical(self):
        """Test critical severity detection."""
        analysis = FailureAnalysis(
            test_pass_rate=0.25,
            syntax_errors=[SyntaxError(f"error {i}") for i in range(6)],
        )

        assert analysis.failure_severity == "CRITICAL"

    def test_failure_severity_high(self):
        """Test high severity detection."""
        analysis = FailureAnalysis(test_pass_rate=0.45, coverage_percent=35.0)

        assert analysis.failure_severity == "HIGH"

    def test_failure_severity_moderate(self):
        """Test moderate severity detection."""
        analysis = FailureAnalysis(
            test_pass_rate=0.75,
            coverage_percent=70.0,
            assertion_depth=5.0,
            confidence_score=0.80,
        )

        # CQS = 0.4*75 + 0.25*70 + 0.2*50 + 0.15*80
        #     = 30 + 17.5 + 10 + 12 = 69.5
        # CQS < 70 but pass_rate >= 0.5, so HIGH severity
        # Let's adjust to get MODERATE (CQS 70-80, pass_rate >= 0.7)
        analysis = FailureAnalysis(
            test_pass_rate=0.75,
            coverage_percent=75.0,
            assertion_depth=6.0,
            confidence_score=0.85,
        )

        # CQS = 0.4*75 + 0.25*75 + 0.2*60 + 0.15*85
        #     = 30 + 18.75 + 12 + 12.75 = 73.5
        # CQS 70-80 and pass_rate >= 0.7, so MODERATE

        assert analysis.failure_severity == "MODERATE"

    def test_failure_severity_low(self):
        """Test low severity (acceptable quality)."""
        analysis = FailureAnalysis(
            test_pass_rate=0.90,
            coverage_percent=85.0,
            assertion_depth=7.0,
            confidence_score=0.95,
        )

        assert analysis.failure_severity == "LOW"


class TestTierResult:
    """Test TierResult class."""

    def test_quality_score_property(self):
        """Test quality_score property delegates to FailureAnalysis."""
        analysis = FailureAnalysis(
            test_pass_rate=0.85,
            coverage_percent=78.0,
            assertion_depth=5.2,
            confidence_score=0.92,
        )

        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            failure_analysis=analysis,
            cost=0.15,
            duration=12.5,
        )

        assert 77 <= result.quality_score <= 78

    def test_success_count(self):
        """Test success_count calculation."""
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[
                {"quality_score": 85},
                {"quality_score": 75},  # Below threshold
                {"quality_score": 90},
                {"quality_score": 65},  # Below threshold
            ],
        )

        assert result.success_count == 2  # Two items with score >= 80

    def test_success_rate(self):
        """Test success_rate calculation."""
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[
                {"quality_score": 85},
                {"quality_score": 75},
                {"quality_score": 90},
                {"quality_score": 65},
            ],
        )

        assert result.success_rate == 0.5  # 2/4 = 50%

    def test_success_rate_no_items(self):
        """Test success_rate with no items."""
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[],
        )

        assert result.success_rate == 0.0


class TestProgressiveWorkflowResult:
    """Test ProgressiveWorkflowResult class."""

    def test_cost_savings_calculation(self):
        """Test cost savings vs all-Premium."""
        cheap_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85} for _ in range(70)],
            cost=0.21,  # 70 * $0.003
            duration=15.0,
        )

        capable_result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85} for _ in range(30)],
            cost=0.45,  # 30 * $0.015
            duration=20.0,
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-123",
            tier_results=[cheap_result, capable_result],
            final_result=capable_result,
            total_cost=0.66,
            total_duration=35.0,
            success=True,
        )

        # Total items: 100
        # All-Premium cost: 100 * $0.05 = $5.00
        # Actual cost: $0.66
        # Savings: $5.00 - $0.66 = $4.34

        assert result.cost_savings > 4.0
        assert result.cost_savings_percent > 80


class TestEscalationConfig:
    """Test EscalationConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EscalationConfig()

        assert config.enabled is False
        assert config.tiers == [Tier.CHEAP, Tier.CAPABLE, Tier.PREMIUM]
        assert config.cheap_min_attempts == 2
        assert config.capable_max_attempts == 6
        assert config.max_cost == 5.00

    def test_get_max_attempts(self):
        """Test get_max_attempts for each tier."""
        config = EscalationConfig(
            cheap_max_attempts=3,
            capable_max_attempts=6,
            premium_max_attempts=1,
        )

        assert config.get_max_attempts(Tier.CHEAP) == 3
        assert config.get_max_attempts(Tier.CAPABLE) == 6
        assert config.get_max_attempts(Tier.PREMIUM) == 1

    def test_get_min_attempts(self):
        """Test get_min_attempts for each tier."""
        config = EscalationConfig(cheap_min_attempts=2, capable_min_attempts=2)

        assert config.get_min_attempts(Tier.CHEAP) == 2
        assert config.get_min_attempts(Tier.CAPABLE) == 2
        assert config.get_min_attempts(Tier.PREMIUM) == 1  # Premium always 1

    def test_custom_thresholds(self):
        """Test custom threshold configuration."""
        config = EscalationConfig(
            cheap_to_capable_min_cqs=75.0,
            capable_to_premium_min_cqs=85.0,
            improvement_threshold=10.0,
        )

        assert config.cheap_to_capable_min_cqs == 75.0
        assert config.capable_to_premium_min_cqs == 85.0
        assert config.improvement_threshold == 10.0
