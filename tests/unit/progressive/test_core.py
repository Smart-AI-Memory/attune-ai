"""Unit tests for progressive escalation core data structures.

Tests cover:
- FailureAnalysis quality score calculation
- Escalation decision logic
- Tier comparison and ordering
- EscalationConfig methods
- TierResult properties
- ProgressiveWorkflowResult metrics
"""

from datetime import datetime

from attune.workflows.progressive.core import (
    EscalationConfig,
    FailureAnalysis,
    ProgressiveWorkflowResult,
    Tier,
    TierResult,
)


class TestTier:
    """Test Tier enum and comparison logic."""

    def test_tier_values(self):
        """Test tier enum values."""
        assert Tier.CHEAP.value == "cheap"
        assert Tier.CAPABLE.value == "capable"
        assert Tier.PREMIUM.value == "premium"

    def test_tier_ordering(self):
        """Test tier comparison for ordering."""
        assert Tier.CHEAP < Tier.CAPABLE
        assert Tier.CAPABLE < Tier.PREMIUM
        assert Tier.CHEAP < Tier.PREMIUM

        # Test reverse
        assert not (Tier.PREMIUM < Tier.CAPABLE)
        assert not (Tier.CAPABLE < Tier.CHEAP)

    def test_tier_equality(self):
        """Test tier equality."""
        assert Tier.CHEAP == Tier.CHEAP
        assert Tier.CAPABLE == Tier.CAPABLE
        assert Tier.PREMIUM == Tier.PREMIUM


class TestFailureAnalysis:
    """Test FailureAnalysis quality metrics and decisions."""

    def test_calculate_quality_score_perfect(self):
        """Test CQS calculation with perfect scores."""
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

    def test_calculate_quality_score_good(self):
        """Test CQS calculation with good scores."""
        analysis = FailureAnalysis(
            test_pass_rate=0.90,
            coverage_percent=85.0,
            assertion_depth=6.0,
            confidence_score=0.95,
        )

        cqs = analysis.calculate_quality_score()

        # Expected: 0.4*90 + 0.25*85 + 0.2*60 + 0.15*95 = 83.5
        assert 83.0 <= cqs <= 84.0

    def test_calculate_quality_score_acceptable(self):
        """Test CQS calculation with acceptable scores."""
        analysis = FailureAnalysis(
            test_pass_rate=0.85,
            coverage_percent=78.0,
            assertion_depth=5.2,
            confidence_score=0.92,
        )

        cqs = analysis.calculate_quality_score()

        # Expected: 0.4*85 + 0.25*78 + 0.2*52 + 0.15*92 = 77.7
        assert 77.0 <= cqs <= 78.0

    def test_calculate_quality_score_poor(self):
        """Test CQS calculation with poor scores."""
        analysis = FailureAnalysis(
            test_pass_rate=0.50,
            coverage_percent=45.0,
            assertion_depth=2.0,
            confidence_score=0.60,
        )

        cqs = analysis.calculate_quality_score()

        # Expected: 0.4*50 + 0.25*45 + 0.2*20 + 0.15*60 = 44.25
        assert 44.0 <= cqs <= 45.0

    def test_calculate_quality_score_with_syntax_errors(self):
        """Test that syntax errors halve the score."""
        analysis = FailureAnalysis(
            test_pass_rate=0.90,
            coverage_percent=85.0,
            assertion_depth=6.0,
            confidence_score=0.95,
            syntax_errors=[SyntaxError("test error")],
        )

        cqs = analysis.calculate_quality_score()

        # Expected: 83.5 * 0.5 = 41.75
        assert 41.0 <= cqs <= 42.0

    def test_calculate_quality_score_zero(self):
        """Test CQS calculation with zero scores."""
        analysis = FailureAnalysis(
            test_pass_rate=0.0,
            coverage_percent=0.0,
            assertion_depth=0.0,
            confidence_score=0.0,
        )

        cqs = analysis.calculate_quality_score()
        assert cqs == 0.0

    def test_assertion_depth_capped_at_100(self):
        """Test that assertion quality is capped at 100%."""
        analysis = FailureAnalysis(
            test_pass_rate=1.0,
            coverage_percent=100.0,
            assertion_depth=20.0,  # 20 assertions -> 200% uncapped
            confidence_score=1.0,
        )

        cqs = analysis.calculate_quality_score()

        # Even with 20 assertions, assertion component should be capped at 100
        # Expected: 0.4*100 + 0.25*100 + 0.2*100 + 0.15*100 = 100
        assert cqs == 100.0

    def test_should_escalate_low_cqs(self):
        """Test escalation triggered by low CQS."""
        analysis = FailureAnalysis(
            test_pass_rate=0.60,
            coverage_percent=50.0,
            assertion_depth=3.0,
            confidence_score=0.70,
        )

        cqs = analysis.calculate_quality_score()
        assert cqs < 70
        assert analysis.should_escalate is True

    def test_should_escalate_syntax_errors(self):
        """Test escalation triggered by multiple syntax errors."""
        analysis = FailureAnalysis(
            test_pass_rate=0.85,
            coverage_percent=80.0,
            assertion_depth=5.0,
            confidence_score=0.90,
            syntax_errors=[
                SyntaxError("error 1"),
                SyntaxError("error 2"),
                SyntaxError("error 3"),
                SyntaxError("error 4"),
            ],
        )

        assert len(analysis.syntax_errors) > 3
        assert analysis.should_escalate is True

    def test_should_escalate_low_pass_rate(self):
        """Test escalation triggered by low test pass rate."""
        analysis = FailureAnalysis(
            test_pass_rate=0.65,  # Below 0.7 threshold
            coverage_percent=80.0,
            assertion_depth=5.0,
            confidence_score=0.90,
        )

        assert analysis.should_escalate is True

    def test_should_escalate_low_coverage(self):
        """Test escalation triggered by low coverage."""
        analysis = FailureAnalysis(
            test_pass_rate=0.85,
            coverage_percent=55.0,  # Below 60 threshold
            assertion_depth=5.0,
            confidence_score=0.90,
        )

        assert analysis.should_escalate is True

    def test_should_not_escalate_good_quality(self):
        """Test no escalation with good quality."""
        analysis = FailureAnalysis(
            test_pass_rate=0.95,
            coverage_percent=85.0,
            assertion_depth=6.0,
            confidence_score=0.92,
        )

        cqs = analysis.calculate_quality_score()
        assert cqs >= 80
        assert analysis.should_escalate is False

    def test_failure_severity_critical(self):
        """Test CRITICAL severity classification."""
        # Severity due to many syntax errors
        analysis1 = FailureAnalysis(syntax_errors=[SyntaxError(f"error {i}") for i in range(6)])
        assert analysis1.failure_severity == "CRITICAL"

        # Severity due to very low pass rate
        analysis2 = FailureAnalysis(test_pass_rate=0.25)
        assert analysis2.failure_severity == "CRITICAL"

    def test_failure_severity_high(self):
        """Test HIGH severity classification."""
        analysis = FailureAnalysis(
            test_pass_rate=0.45,
            coverage_percent=50.0,
            assertion_depth=2.0,
            confidence_score=0.60,
        )

        assert analysis.failure_severity == "HIGH"

    def test_failure_severity_moderate(self):
        """Test MODERATE severity classification."""
        analysis = FailureAnalysis(
            test_pass_rate=0.75,
            coverage_percent=70.0,
            assertion_depth=6.0,
            confidence_score=0.80,
        )

        cqs = analysis.calculate_quality_score()
        assert 70 <= cqs < 80
        assert analysis.failure_severity == "MODERATE"

    def test_failure_severity_low(self):
        """Test LOW severity classification."""
        analysis = FailureAnalysis(
            test_pass_rate=0.95,
            coverage_percent=85.0,
            assertion_depth=6.0,
            confidence_score=0.92,
        )

        cqs = analysis.calculate_quality_score()
        assert cqs >= 80
        assert analysis.failure_severity == "LOW"


class TestTierResult:
    """Test TierResult properties and calculations."""

    def test_quality_score_property(self):
        """Test that quality_score returns CQS from failure analysis."""
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
        )

        assert 77.0 <= result.quality_score <= 78.0

    def test_success_count(self):
        """Test success_count counts items with CQS >= 80."""
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[
                {"quality_score": 95},
                {"quality_score": 85},
                {"quality_score": 75},  # Below threshold
                {"quality_score": 82},
                {"quality_score": 60},  # Below threshold
            ],
        )

        assert result.success_count == 3

    def test_success_count_empty(self):
        """Test success_count with no items."""
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[],
        )

        assert result.success_count == 0

    def test_success_rate(self):
        """Test success_rate calculation."""
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[
                {"quality_score": 95},
                {"quality_score": 85},
                {"quality_score": 75},
                {"quality_score": 82},
                {"quality_score": 60},
            ],
        )

        # 3 successful out of 5 = 0.6
        assert result.success_rate == 0.6

    def test_success_rate_empty(self):
        """Test success_rate with no items returns 0."""
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[],
        )

        assert result.success_rate == 0.0


class TestEscalationConfig:
    """Test EscalationConfig methods and defaults."""

    def test_default_values(self):
        """Test that defaults match plan specifications."""
        config = EscalationConfig()

        # Global settings
        assert config.enabled is False
        assert config.tiers == [Tier.CHEAP, Tier.CAPABLE, Tier.PREMIUM]

        # Retry configuration
        assert config.cheap_min_attempts == 2
        assert config.cheap_max_attempts == 3
        assert config.capable_min_attempts == 2
        assert config.capable_max_attempts == 6
        assert config.premium_max_attempts == 1

        # Thresholds
        assert config.cheap_to_capable_failure_rate == 0.30
        assert config.cheap_to_capable_min_cqs == 70.0
        assert config.cheap_to_capable_max_syntax_errors == 3

        assert config.capable_to_premium_failure_rate == 0.20
        assert config.capable_to_premium_min_cqs == 80.0
        assert config.capable_to_premium_max_syntax_errors == 1

        # Stagnation
        assert config.improvement_threshold == 5.0
        assert config.consecutive_stagnation_limit == 2

        # Cost management
        assert config.max_cost == 5.00
        assert config.auto_approve_under is None
        assert config.warn_on_budget_exceeded is True
        assert config.abort_on_budget_exceeded is False

        # Storage
        assert config.save_tier_results is True
        assert config.storage_path == ".attune/progressive_runs"

    def test_get_max_attempts_cheap(self):
        """Test get_max_attempts for cheap tier."""
        config = EscalationConfig(cheap_max_attempts=5)
        assert config.get_max_attempts(Tier.CHEAP) == 5

    def test_get_max_attempts_capable(self):
        """Test get_max_attempts for capable tier."""
        config = EscalationConfig(capable_max_attempts=8)
        assert config.get_max_attempts(Tier.CAPABLE) == 8

    def test_get_max_attempts_premium(self):
        """Test get_max_attempts for premium tier."""
        config = EscalationConfig(premium_max_attempts=2)
        assert config.get_max_attempts(Tier.PREMIUM) == 2

    def test_get_min_attempts_cheap(self):
        """Test get_min_attempts for cheap tier."""
        config = EscalationConfig(cheap_min_attempts=3)
        assert config.get_min_attempts(Tier.CHEAP) == 3

    def test_get_min_attempts_capable(self):
        """Test get_min_attempts for capable tier."""
        config = EscalationConfig(capable_min_attempts=3)
        assert config.get_min_attempts(Tier.CAPABLE) == 3

    def test_get_min_attempts_premium(self):
        """Test get_min_attempts for premium tier always returns 1."""
        config = EscalationConfig()
        assert config.get_min_attempts(Tier.PREMIUM) == 1

    def test_custom_tiers(self):
        """Test configuration with custom tier list."""
        config = EscalationConfig(tiers=[Tier.CHEAP, Tier.PREMIUM])
        assert config.tiers == [Tier.CHEAP, Tier.PREMIUM]
        assert Tier.CAPABLE not in config.tiers


class TestProgressiveWorkflowResult:
    """Test ProgressiveWorkflowResult metrics and reports."""

    def test_cost_savings_calculation(self):
        """Test cost savings calculation vs all-Premium."""
        cheap_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85} for _ in range(70)],
            cost=0.30,
            duration=15.0,
        )

        capable_result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 88} for _ in range(30)],
            cost=0.45,
            duration=22.0,
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-143022",
            tier_results=[cheap_result, capable_result],
            final_result=capable_result,
            total_cost=0.75,
            total_duration=37.0,
            success=True,
        )

        # 100 items total * $0.05 per item = $5.00 if all Premium
        # Actual cost: $0.75
        # Savings: $5.00 - $0.75 = $4.25
        assert result.cost_savings == 4.25

    def test_cost_savings_percent(self):
        """Test cost savings percentage calculation."""
        cheap_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85} for _ in range(100)],
            cost=0.30,
            duration=15.0,
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-143022",
            tier_results=[cheap_result],
            final_result=cheap_result,
            total_cost=0.30,
            total_duration=15.0,
            success=True,
        )

        # 100 items * $0.05 = $5.00 if all Premium
        # Actual cost: $0.30
        # Savings: $4.70 / $5.00 = 94%
        assert result.cost_savings_percent == 94.0

    def test_cost_savings_no_items(self):
        """Test cost savings with no items returns 0."""
        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-143022",
            tier_results=[],
            final_result=TierResult(
                tier=Tier.CHEAP,
                model="gpt-4o-mini",
                attempt=1,
                timestamp=datetime.now(),
            ),
            total_cost=0.0,
            total_duration=0.0,
            success=False,
        )

        assert result.cost_savings == 0.0
        assert result.cost_savings_percent == 0.0
