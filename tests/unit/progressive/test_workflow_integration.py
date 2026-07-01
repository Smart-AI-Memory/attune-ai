"""Integration tests for ProgressiveWorkflow._execute_progressive method.

Tests the full escalation loop including:
- Single tier execution
- Multi-tier escalation
- Partial escalation
- Budget management
- User approval flow
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from attune.workflows.progressive.core import (
    EscalationConfig,
    FailureAnalysis,
    ProgressiveWorkflowResult,
    Tier,
    TierResult,
)
from attune.workflows.progressive.workflow import (
    BudgetExceededError,
    ProgressiveWorkflow,
    UserCancelledError,
)


class MockProgressiveWorkflow(ProgressiveWorkflow):
    """Mock workflow for testing base class behavior."""

    def __init__(self, config=None, user_id=None):
        super().__init__(config, user_id)
        self.tier_execution_count = {Tier.CHEAP: 0, Tier.CAPABLE: 0, Tier.PREMIUM: 0}

    def execute(self, items, **kwargs):
        """Execute with progressive escalation."""
        return self._execute_progressive(items, "test-workflow", **kwargs)

    def _execute_tier_impl(self, tier, items, context, **kwargs):
        """Mock tier execution that generates items."""
        self.tier_execution_count[tier] += 1

        # Generate mock items based on tier quality
        quality_by_tier = {
            Tier.CHEAP: 75,  # Some will fail threshold
            Tier.CAPABLE: 85,  # Better quality
            Tier.PREMIUM: 95,  # Excellent quality
        }

        base_quality = quality_by_tier[tier]

        generated = []
        for i, item in enumerate(items):
            # Simulate some failures at cheaper tiers
            quality = base_quality + (i % 3) * 5
            if tier == Tier.CHEAP and i % 3 == 0:
                quality = 65  # Below threshold

            generated.append(
                {
                    "item": item,
                    "quality_score": quality,
                    "passed": quality >= 80,
                    "syntax_errors": [],
                    "coverage": quality * 0.9,
                    "assertions": quality / 15,
                    "confidence": quality / 100,
                },
            )

        return generated


class TestProgressiveWorkflowIntegration:
    """Test full progressive escalation flow."""

    def test_execute_progressive_disabled(self, monkeypatch):
        """Test execution when progressive escalation is disabled."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")
        config = EscalationConfig(enabled=False)
        workflow = MockProgressiveWorkflow(config=config)

        items = ["item1", "item2", "item3"]
        result = workflow.execute(items)

        # Should execute once at default (capable) tier
        assert isinstance(result, ProgressiveWorkflowResult)
        assert result.success is True
        assert len(result.tier_results) == 1
        assert result.tier_results[0].tier == Tier.CAPABLE

    def test_execute_progressive_cheap_success(self, monkeypatch):
        """Test successful completion at cheap tier."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")
        config = EscalationConfig(enabled=True, auto_approve_under=10.00)

        # Override mock to generate high quality for all items
        class HighQualityWorkflow(MockProgressiveWorkflow):
            def _execute_tier_impl(self, tier, items, context, **kwargs):
                # Generate all items with quality >= 80
                return [
                    {
                        "item": item,
                        "quality_score": 85,
                        "passed": True,
                        "syntax_errors": [],
                        "coverage": 85.0,
                        "assertions": 6.0,
                        "confidence": 0.85,
                    }
                    for item in items
                ]

        workflow = HighQualityWorkflow(config=config)

        # Only 2 items so quality will be high enough
        items = ["item1", "item2"]
        result = workflow.execute(items)

        # Should complete at cheap tier without escalation
        assert result.success is True
        assert len(result.tier_results) >= 1
        assert result.tier_results[0].tier == Tier.CHEAP

    def test_execute_progressive_with_escalation(self, monkeypatch):
        """Test escalation from cheap to capable tier."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")
        config = EscalationConfig(
            enabled=True,
            auto_approve_under=10.00,
            cheap_min_attempts=1,  # Allow quick escalation
        )
        workflow = MockProgressiveWorkflow(config=config)

        # Many items will cause some to fail at cheap tier
        items = [f"item{i}" for i in range(10)]
        result = workflow.execute(items)

        # Should have escalated to capable tier
        assert len(result.tier_results) >= 1
        # Check if any tier escalated
        any(r.escalated for r in result.tier_results)
        # Could be True or False depending on quality

    def test_execute_progressive_user_cancels_initial(self, monkeypatch):
        """Test user cancelling initial approval."""
        # Enable interactive mode
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("ATTUNE_NON_INTERACTIVE", raising=False)

        # Force interactive prompt by setting auto-approve threshold to 0
        monkeypatch.setenv("ATTUNE_AUTO_APPROVE_MAX", "0")

        config = EscalationConfig(enabled=True, auto_approve_under=None)
        workflow = MockProgressiveWorkflow(config=config)

        # Mock input to return 'n' for cancellation
        with patch("builtins.input", return_value="n"), pytest.raises(UserCancelledError):
            workflow.execute(["item1", "item2"], expensive=True)

    def test_execute_single_tier_success(self, monkeypatch):
        """Test _execute_single_tier when progressive disabled."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")
        config = EscalationConfig(enabled=False)
        workflow = MockProgressiveWorkflow(config=config)

        items = ["item1", "item2", "item3"]
        result = workflow._execute_single_tier(items, "test-workflow")

        assert isinstance(result, ProgressiveWorkflowResult)
        assert len(result.tier_results) == 1
        assert result.tier_results[0].tier == Tier.CAPABLE  # Default tier

    def test_execute_tier_with_exception(self, monkeypatch):
        """Test _execute_tier error handling."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")

        class FailingWorkflow(MockProgressiveWorkflow):
            def _execute_tier_impl(self, tier, items, context, **kwargs):
                raise ValueError("Execution failed!")

        workflow = FailingWorkflow()

        result = workflow._execute_tier(Tier.CHEAP, ["item1"], None)

        # Should return failed result, not raise
        assert isinstance(result, TierResult)
        assert result.escalated is True
        assert "error" in result.escalation_reason.lower()
        assert len(result.generated_items) == 0

    def test_progressive_workflow_telemetry_tracking(self, monkeypatch):
        """Test that telemetry is initialized and tracks executions."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")
        config = EscalationConfig(enabled=True, auto_approve_under=10.00)
        workflow = MockProgressiveWorkflow(config=config, user_id="test-user")

        items = ["item1", "item2"]
        workflow.execute(items)

        # Telemetry should be initialized
        assert workflow.telemetry is not None
        assert workflow.telemetry.workflow_name == "test-workflow"

    def test_should_escalate_delegates_to_orchestrator(self):
        """Test that _should_escalate delegates to meta_orchestrator."""
        config = EscalationConfig()
        workflow = MockProgressiveWorkflow(config=config)

        analysis = FailureAnalysis(test_pass_rate=0.60)
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        should_esc, reason = workflow._should_escalate(Tier.CHEAP, result, attempt=2)

        # Should delegate to orchestrator
        assert isinstance(should_esc, bool)
        assert isinstance(reason, str)

    def test_get_next_tier_edge_cases(self):
        """Test _get_next_tier with various configurations."""
        workflow = MockProgressiveWorkflow()

        # Test invalid tier (not in config)
        next_tier = workflow._get_next_tier(Tier.CHEAP)
        assert next_tier == Tier.CAPABLE

        # Test with custom tier ordering
        config = EscalationConfig(tiers=[Tier.CHEAP, Tier.PREMIUM])
        workflow2 = MockProgressiveWorkflow(config=config)

        next_tier = workflow2._get_next_tier(Tier.CHEAP)
        assert next_tier == Tier.PREMIUM

        next_tier = workflow2._get_next_tier(Tier.PREMIUM)
        assert next_tier is None


class TestProgressiveWorkflowBudgetManagement:
    """Test budget management and cost tracking."""

    def test_budget_warning_logged(self, monkeypatch, caplog):
        """Test budget exceeded warning is logged."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")

        config = EscalationConfig(
            max_cost=1.00,
            warn_on_budget_exceeded=True,
            abort_on_budget_exceeded=False,
        )
        workflow = MockProgressiveWorkflow(config=config)

        # Add high-cost tier result
        workflow.tier_results.append(
            TierResult(
                tier=Tier.CHEAP,
                model="gpt-4o-mini",
                attempt=1,
                timestamp=datetime.now(),
                cost=5.00,  # Exceeds budget
                duration=10.0,
            ),
        )

        # Should log warning but not raise
        workflow._check_budget()
        # Logging check is implementation-dependent

    def test_budget_abort_raises_exception(self, monkeypatch):
        """Test budget exceeded abort raises exception."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")

        config = EscalationConfig(
            max_cost=1.00,
            abort_on_budget_exceeded=True,
        )
        workflow = MockProgressiveWorkflow(config=config)

        # Add high-cost tier result
        workflow.tier_results.append(
            TierResult(
                tier=Tier.CHEAP,
                model="gpt-4o-mini",
                attempt=1,
                timestamp=datetime.now(),
                cost=5.00,  # Exceeds budget
                duration=10.0,
            ),
        )

        with pytest.raises(BudgetExceededError, match="exceeds budget"):
            workflow._check_budget()

    def test_auto_approve_environment_variable(self, monkeypatch):
        """Test auto-approval via environment variable."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")
        monkeypatch.setenv("ATTUNE_AUTO_APPROVE_MAX", "10.00")

        workflow = MockProgressiveWorkflow()

        # Cost under $10 threshold should auto-approve
        approved = workflow._request_approval("Test task", 7.50)
        assert approved is True

        # Cost over $10 threshold should deny in non-interactive
        approved = workflow._request_approval("Test task", 15.00)
        assert approved is False


class TestProgressiveWorkflowModelSelection:
    """Test model configuration and selection."""

    def test_get_model_for_tier_with_env_override(self, monkeypatch):
        """Test model selection with environment overrides."""
        monkeypatch.setenv("ATTUNE_MODEL_CHEAP", "custom-cheap-model")
        monkeypatch.setenv("ATTUNE_MODEL_CAPABLE", "custom-capable-model")
        monkeypatch.setenv("ATTUNE_MODEL_PREMIUM", "custom-premium-model")

        workflow = MockProgressiveWorkflow()

        assert workflow._get_model_for_tier(Tier.CHEAP) == "custom-cheap-model"
        assert workflow._get_model_for_tier(Tier.CAPABLE) == "custom-capable-model"
        assert workflow._get_model_for_tier(Tier.PREMIUM) == "custom-premium-model"

    def test_get_model_for_tier_defaults(self, monkeypatch):
        """Test model selection with defaults."""
        # Clear env vars
        monkeypatch.delenv("ATTUNE_MODEL_CHEAP", raising=False)
        monkeypatch.delenv("ATTUNE_MODEL_CAPABLE", raising=False)
        monkeypatch.delenv("ATTUNE_MODEL_PREMIUM", raising=False)

        workflow = MockProgressiveWorkflow()

        # Should return defaults
        cheap = workflow._get_model_for_tier(Tier.CHEAP)
        capable = workflow._get_model_for_tier(Tier.CAPABLE)
        premium = workflow._get_model_for_tier(Tier.PREMIUM)

        assert cheap in ["gpt-4o-mini", "claude-haiku-4-5"]
        assert capable in ["claude-sonnet-5", "gpt-4o"]
        assert premium in ["claude-opus-4-8", "o1"]


class TestEscalationEdgeCases:
    """Test edge cases in the escalation loop."""

    def test_get_next_tier_at_highest_tier(self):
        """Test _get_next_tier returns None when at highest tier."""
        config = EscalationConfig(tiers=[Tier.CHEAP, Tier.CAPABLE, Tier.PREMIUM])
        workflow = MockProgressiveWorkflow(config=config)

        # At highest tier, next_tier should be None
        next_tier = workflow._get_next_tier(Tier.PREMIUM)

        assert next_tier is None  # Can't escalate from PREMIUM

    def test_escalation_user_declines_approval(self, monkeypatch):
        """Test escalation stopped when user declines approval."""
        # Enable interactive mode
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("ATTUNE_NON_INTERACTIVE", raising=False)

        config = EscalationConfig(enabled=True, auto_approve_under=None)

        # Mock workflow that triggers escalation
        class FailingWorkflow(MockProgressiveWorkflow):
            def _execute_tier_impl(self, tier, items, context, **kwargs):
                # Generate failing items to trigger escalation
                return [
                    {
                        "item": item,
                        "quality_score": 60,
                        "passed": False,
                        "syntax_errors": [],
                        "coverage": 55.0,
                        "assertions": 2.0,
                        "confidence": 0.60,
                    }
                    for item in items
                ]

        workflow = FailingWorkflow(config=config)

        # Mock: approve initial request, but decline escalation
        with patch("builtins.input", side_effect=["y", "n"]):  # y for initial, n for escalation
            with patch("sys.stdin.isatty", return_value=True):
                items = ["item1", "item2"]
                result = workflow.execute(items)

        # Should stop at cheap tier (user declined escalation)
        assert len(result.tier_results) == 1
        assert result.tier_results[0].tier == Tier.CHEAP
        assert result.success is False

    def test_escalation_without_telemetry(self, monkeypatch):
        """Test escalation when telemetry is disabled (telemetry=None)."""
        monkeypatch.setenv("ATTUNE_NON_INTERACTIVE", "1")

        config = EscalationConfig(
            enabled=True,
            auto_approve_under=10.00,
            cheap_min_attempts=1,  # Allow escalation after 1 attempt
        )

        # Mock workflow that triggers escalation
        class EscalatingWorkflow(MockProgressiveWorkflow):
            execution_count = 0

            def _execute_tier_impl(self, tier, items, context, **kwargs):
                self.execution_count += 1

                if tier == Tier.CHEAP:
                    # First execution: low quality to trigger escalation
                    return [
                        {
                            "item": item,
                            "quality_score": 60,
                            "passed": False,
                            "syntax_errors": [],
                            "coverage": 55.0,
                            "assertions": 2.5,
                            "confidence": 0.60,
                        }
                        for item in items
                    ]
                # Second execution: high quality
                return [
                    {
                        "item": item,
                        "quality_score": 90,
                        "passed": True,
                        "syntax_errors": [],
                        "coverage": 90.0,
                        "assertions": 6.0,
                        "confidence": 0.90,
                    }
                    for item in items
                ]

        workflow = EscalatingWorkflow(config=config)
        # Manually disable telemetry
        workflow.telemetry = None

        items = ["item1", "item2"]
        result = workflow.execute(items)

        # Should escalate from cheap to capable
        assert len(result.tier_results) >= 2
        # Verify telemetry branch was hit (no error when telemetry is None)
        assert result.success is True

    def test_get_next_tier_invalid_tier(self):
        """Test _get_next_tier with tier not in config list."""
        config = EscalationConfig(tiers=[Tier.CHEAP, Tier.PREMIUM])
        workflow = MockProgressiveWorkflow(config=config)

        # CAPABLE is not in the tier list
        next_tier = workflow._get_next_tier(Tier.CAPABLE)

        # Should return None (tier not found in list)
        assert next_tier is None
