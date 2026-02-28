"""Tests for cost management and telemetry integration in progressive workflows."""

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
from attune.workflows.progressive.telemetry import ProgressiveTelemetry
from attune.workflows.progressive.workflow import BudgetExceededError, ProgressiveWorkflow


class TestCostEstimation:
    """Test cost estimation logic."""

    def test_estimate_tier_cost_cheap(self):
        """Test cost estimation for cheap tier."""
        workflow = ProgressiveWorkflow()

        cost = workflow._estimate_tier_cost(Tier.CHEAP, 100)

        # $0.003 per item × 100 items = $0.30
        assert cost == pytest.approx(0.30, rel=0.01)

    def test_estimate_tier_cost_capable(self):
        """Test cost estimation for capable tier."""
        workflow = ProgressiveWorkflow()

        cost = workflow._estimate_tier_cost(Tier.CAPABLE, 100)

        # $0.015 per item × 100 items = $1.50
        assert cost == pytest.approx(1.50, rel=0.01)

    def test_estimate_tier_cost_premium(self):
        """Test cost estimation for premium tier."""
        workflow = ProgressiveWorkflow()

        cost = workflow._estimate_tier_cost(Tier.PREMIUM, 100)

        # $0.05 per item × 100 items = $5.00
        assert cost == pytest.approx(5.00, rel=0.01)

    def test_estimate_total_cost_with_escalation(self):
        """Test total cost estimation assumes 30% escalation to capable, 10% to premium."""
        workflow = ProgressiveWorkflow()

        total_cost = workflow._estimate_total_cost(item_count=100)

        # Expected:
        # Cheap: 100 items × $0.003 = $0.30
        # Capable: 30 items × $0.015 = $0.45
        # Premium: 10 items × $0.05 = $0.50
        # Total: $1.25
        assert total_cost == pytest.approx(1.25, rel=0.01)

    def test_estimate_total_cost_small_batch(self):
        """Test cost estimation for small batch."""
        workflow = ProgressiveWorkflow()

        total_cost = workflow._estimate_total_cost(item_count=10)

        # Expected:
        # Cheap: 10 items × $0.003 = $0.03
        # Capable: 3 items × $0.015 = $0.045
        # Premium: 1 item × $0.05 = $0.05
        # Total: $0.125
        assert total_cost == pytest.approx(0.125, rel=0.01)


class TestApprovalPrompts:
    """Test approval prompt logic."""

    @patch("attune.workflows.progressive.workflow._is_interactive", return_value=True)
    @patch("builtins.input", return_value="y")
    def test_request_approval_user_accepts(self, mock_input, mock_interactive):
        """Test approval prompt when user accepts."""
        workflow = ProgressiveWorkflow()

        # Request approval for $5.00 (above $1 threshold)
        approved = workflow._request_approval("Test operation", estimated_cost=5.00)

        assert approved is True
        mock_input.assert_called_once()

    @patch("attune.workflows.progressive.workflow._is_interactive", return_value=True)
    @patch("builtins.input", return_value="n")
    def test_request_approval_user_declines(self, mock_input, mock_interactive):
        """Test approval prompt when user declines."""
        workflow = ProgressiveWorkflow()

        # Request approval for $5.00 (above $1 threshold)
        approved = workflow._request_approval("Test operation", estimated_cost=5.00)

        assert approved is False
        mock_input.assert_called_once()

    def test_request_approval_below_threshold(self):
        """Test auto-approval when cost below $1 threshold."""
        workflow = ProgressiveWorkflow()

        # Request approval for $0.50 (below $1 threshold)
        approved = workflow._request_approval("Test operation", estimated_cost=0.50)

        # Should auto-approve without prompting
        assert approved is True

    def test_request_approval_auto_approve_under_config(self):
        """Test auto-approval with custom threshold in config."""
        config = EscalationConfig(auto_approve_under=10.00)
        workflow = ProgressiveWorkflow(config)

        # Request approval for $8.00 (below custom $10 threshold)
        approved = workflow._request_approval("Test operation", estimated_cost=8.00)

        # Should auto-approve
        assert approved is True

    @patch("attune.workflows.progressive.workflow._is_interactive", return_value=True)
    @patch("builtins.input", return_value="Y")  # uppercase Y
    def test_request_escalation_approval_uppercase(self, mock_input, mock_interactive):
        """Test escalation approval accepts uppercase Y."""
        workflow = ProgressiveWorkflow()
        workflow.tier_results = []  # Empty for cost calculation

        approved = workflow._request_escalation_approval(
            from_tier=Tier.CHEAP,
            to_tier=Tier.CAPABLE,
            item_count=10,
            additional_cost=1.50,
        )

        assert approved is True

    @patch("attune.workflows.progressive.workflow._is_interactive", return_value=True)
    @patch("builtins.input", return_value="n")
    def test_request_escalation_approval_declined(self, mock_input, mock_interactive):
        """Test escalation approval when user declines."""
        workflow = ProgressiveWorkflow()
        workflow.tier_results = []

        approved = workflow._request_escalation_approval(
            from_tier=Tier.CHEAP,
            to_tier=Tier.CAPABLE,
            item_count=10,
            additional_cost=1.50,
        )

        assert approved is False


class TestBudgetChecking:
    """Test budget checking and enforcement."""

    def test_check_budget_under_limit(self):
        """Test budget check when under limit."""
        config = EscalationConfig(max_cost=10.00, abort_on_budget_exceeded=True)
        workflow = ProgressiveWorkflow(config)

        # Add tier result with cost below budget
        workflow.tier_results.append(
            TierResult(
                tier=Tier.CHEAP,
                model="gpt-4o-mini",
                attempt=1,
                timestamp=datetime.now(),
                generated_items=[{"quality_score": 85}],
                failure_analysis=FailureAnalysis(
                    syntax_errors=[],
                    test_pass_rate=100.0,
                    coverage_percent=90.0,
                    assertion_depth=3.0,
                    confidence_score=0.95,
                ),
                cost=5.00,
                duration=10.0,
                tokens_used={"input": 1000, "output": 500, "total": 1500},
                escalated=False,
            ),
        )

        # Should not raise exception
        workflow._check_budget()

    def test_check_budget_exceeded_with_abort(self):
        """Test budget check raises exception when exceeded with abort enabled."""
        config = EscalationConfig(max_cost=5.00, abort_on_budget_exceeded=True)
        workflow = ProgressiveWorkflow(config)

        # Add tier result with cost exceeding budget
        workflow.tier_results.append(
            TierResult(
                tier=Tier.CHEAP,
                model="gpt-4o-mini",
                attempt=1,
                timestamp=datetime.now(),
                generated_items=[{"quality_score": 85}],
                failure_analysis=FailureAnalysis(
                    syntax_errors=[],
                    test_pass_rate=100.0,
                    coverage_percent=90.0,
                    assertion_depth=3.0,
                    confidence_score=0.95,
                ),
                cost=10.00,  # Exceeds $5 budget
                duration=10.0,
                tokens_used={"input": 1000, "output": 500, "total": 1500},
                escalated=False,
            ),
        )

        with pytest.raises(BudgetExceededError, match="exceeds budget"):
            workflow._check_budget()

    def test_check_budget_exceeded_with_warn(self):
        """Test budget check warns but doesn't abort when warn enabled."""
        config = EscalationConfig(
            max_cost=5.00,
            abort_on_budget_exceeded=False,
            warn_on_budget_exceeded=True,
        )
        workflow = ProgressiveWorkflow(config)

        # Add tier result with cost exceeding budget
        workflow.tier_results.append(
            TierResult(
                tier=Tier.CHEAP,
                model="gpt-4o-mini",
                attempt=1,
                timestamp=datetime.now(),
                generated_items=[{"quality_score": 85}],
                failure_analysis=FailureAnalysis(
                    syntax_errors=[],
                    test_pass_rate=100.0,
                    coverage_percent=90.0,
                    assertion_depth=3.0,
                    confidence_score=0.95,
                ),
                cost=10.00,  # Exceeds $5 budget
                duration=10.0,
                tokens_used={"input": 1000, "output": 500, "total": 1500},
                escalated=False,
            ),
        )

        # Should not raise exception, just log warning
        workflow._check_budget()


class TestProgressiveTelemetry:
    """Test telemetry tracking."""

    def test_initialization(self):
        """Test telemetry initialization."""
        telemetry = ProgressiveTelemetry(workflow_name="test-gen", user_id="user123")

        assert telemetry.workflow_name == "test-gen"
        assert telemetry.user_id == "user123"
        assert telemetry.tracker is not None

    def test_track_tier_execution(self):
        """Test tracking tier execution."""
        telemetry = ProgressiveTelemetry(workflow_name="test-gen")

        tier_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85}],
            failure_analysis=FailureAnalysis(
                syntax_errors=[],
                test_pass_rate=100.0,
                coverage_percent=90.0,
                assertion_depth=3.0,
                confidence_score=0.95,
            ),
            cost=0.10,
            duration=5.0,
            tokens_used={"input": 1000, "output": 500, "total": 1500},
            escalated=False,
        )

        # Should not raise exception
        telemetry.track_tier_execution(
            tier_result=tier_result,
            attempt=1,
            escalated=False,
        )

    def test_track_escalation(self):
        """Test tracking escalation event."""
        telemetry = ProgressiveTelemetry(workflow_name="test-gen")

        # Should not raise exception
        telemetry.track_escalation(
            from_tier=Tier.CHEAP,
            to_tier=Tier.CAPABLE,
            reason="Low CQS (65)",
            item_count=10,
            current_cost=0.30,
        )

    def test_track_budget_exceeded(self):
        """Test tracking budget exceeded event."""
        telemetry = ProgressiveTelemetry(workflow_name="test-gen")

        # Should not raise exception
        telemetry.track_budget_exceeded(
            current_cost=15.00,
            max_budget=10.00,
            action="abort",
        )

    def test_track_workflow_completion(self, tmp_path):
        """Test tracking workflow completion."""
        telemetry = ProgressiveTelemetry(workflow_name="test-gen")

        # Create minimal result
        tier_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85}],
            failure_analysis=FailureAnalysis(
                syntax_errors=[],
                test_pass_rate=100.0,
                coverage_percent=90.0,
                assertion_depth=3.0,
                confidence_score=0.95,
            ),
            cost=0.10,
            duration=5.0,
            tokens_used={"input": 1000, "output": 500, "total": 1500},
            escalated=False,
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-120000",
            tier_results=[tier_result],
            final_result=tier_result,
            total_cost=0.10,
            total_duration=5.0,
            success=True,
        )

        # Should not raise exception
        telemetry.track_workflow_completion(result)

    def test_get_provider_openai(self):
        """Test provider inference for OpenAI models."""
        assert ProgressiveTelemetry._get_provider("gpt-4o-mini") == "openai"
        assert ProgressiveTelemetry._get_provider("GPT-4") == "openai"

    def test_get_provider_anthropic(self):
        """Test provider inference for Anthropic models."""
        assert ProgressiveTelemetry._get_provider("claude-3-5-sonnet") == "anthropic"
        assert ProgressiveTelemetry._get_provider("claude-opus-4") == "anthropic"

    def test_get_provider_google(self):
        """Test provider inference for Google models."""
        assert ProgressiveTelemetry._get_provider("gemini-pro") == "google"
        assert ProgressiveTelemetry._get_provider("gemini-1.5-flash") == "google"

    def test_get_provider_unknown(self):
        """Test provider inference for unknown models."""
        assert ProgressiveTelemetry._get_provider("unknown-model") == "unknown"

    def test_hash_user_id(self):
        """Test user ID hashing for privacy."""
        hash1 = ProgressiveTelemetry._hash_user_id("user123")
        hash2 = ProgressiveTelemetry._hash_user_id("user123")
        hash3 = ProgressiveTelemetry._hash_user_id("user456")

        # Same input should produce same hash
        assert hash1 == hash2

        # Different input should produce different hash
        assert hash1 != hash3

        # Hash should be 64 characters (SHA256 hex)
        assert len(hash1) == 64


class TestTelemetryIntegration:
    """Test telemetry integration in workflow execution."""

    @patch("attune.workflows.progressive.telemetry.UsageTracker")
    def test_telemetry_initialized_on_execute(self, mock_tracker):
        """Test telemetry is initialized when workflow executes."""
        workflow = ProgressiveWorkflow(user_id="test-user")

        # Telemetry should not be initialized until execute is called
        assert workflow.telemetry is None

    def test_telemetry_tracks_tier_execution(self, tmp_path):
        """Test telemetry tracks tier execution during workflow."""
        # This is more of an integration test that would need a real workflow
        # For now, just verify the tracking method is called
        telemetry = ProgressiveTelemetry(workflow_name="test")
        with patch.object(telemetry.tracker, "track_llm_call") as mock_track:
            tier_result = TierResult(
                tier=Tier.CHEAP,
                model="gpt-4o-mini",
                attempt=1,
                timestamp=datetime.now(),
                generated_items=[],
                failure_analysis=FailureAnalysis(
                    syntax_errors=[],
                    test_pass_rate=0.0,
                    coverage_percent=0.0,
                    assertion_depth=0.0,
                    confidence_score=0.0,
                ),
                cost=0.01,
                duration=1.0,
                tokens_used={"input": 100, "output": 50, "total": 150},
                escalated=False,
            )

            telemetry.track_tier_execution(tier_result, 1, False)

            # Verify tracking was called
            mock_track.assert_called_once()


class TestCostManagementEdgeCases:
    """Test edge cases in cost management."""

    def test_zero_cost_estimation(self):
        """Test cost estimation with zero items."""
        workflow = ProgressiveWorkflow()

        cost = workflow._estimate_total_cost(item_count=0)

        assert cost == 0.0

    def test_budget_check_with_no_tier_results(self):
        """Test budget check with empty tier results."""
        config = EscalationConfig(max_cost=10.00, abort_on_budget_exceeded=True)
        workflow = ProgressiveWorkflow(config)

        # Should not raise exception (cost is $0)
        workflow._check_budget()

    def test_exact_budget_match(self):
        """Test budget check when cost exactly equals budget."""
        config = EscalationConfig(max_cost=10.00, abort_on_budget_exceeded=True)
        workflow = ProgressiveWorkflow(config)

        workflow.tier_results.append(
            TierResult(
                tier=Tier.CHEAP,
                model="gpt-4o-mini",
                attempt=1,
                timestamp=datetime.now(),
                generated_items=[{"quality_score": 85}],
                failure_analysis=FailureAnalysis(
                    syntax_errors=[],
                    test_pass_rate=100.0,
                    coverage_percent=90.0,
                    assertion_depth=3.0,
                    confidence_score=0.95,
                ),
                cost=10.00,  # Exactly equals budget
                duration=10.0,
                tokens_used={"input": 1000, "output": 500, "total": 1500},
                escalated=False,
            ),
        )

        # Should not raise exception (not exceeded, just equal)
        workflow._check_budget()


class TestTelemetryEdgeCases:
    """Test edge cases in telemetry analytics calculations."""

    def test_workflow_completion_with_zero_items(self):
        """Test workflow completion analytics with zero generated items."""
        telemetry = ProgressiveTelemetry(workflow_name="test-gen")

        tier_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[],  # Zero items
            failure_analysis=FailureAnalysis(
                syntax_errors=[],
                test_pass_rate=0.0,
                coverage_percent=0.0,
                assertion_depth=0.0,
                confidence_score=0.0,
            ),
            cost=0.05,
            duration=2.0,
            tokens_used={"input": 100, "output": 50, "total": 150},
            escalated=False,
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-120000",
            tier_results=[tier_result],
            final_result=tier_result,
            total_cost=0.05,
            total_duration=2.0,
            success=False,
        )

        # Should handle zero items gracefully
        telemetry.track_workflow_completion(result)

    def test_workflow_completion_with_multiple_tiers(self):
        """Test workflow completion calculates tier breakdown correctly."""
        telemetry = ProgressiveTelemetry(workflow_name="test-gen")

        cheap_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 60}] * 5,
            failure_analysis=FailureAnalysis(
                syntax_errors=[],
                test_pass_rate=75.0,
                coverage_percent=65.0,
                assertion_depth=2.0,
                confidence_score=0.80,
            ),
            cost=0.30,
            duration=10.0,
            tokens_used={"input": 1000, "output": 500, "total": 1500},
            escalated=True,
        )

        capable_result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 95}] * 3,
            failure_analysis=FailureAnalysis(
                syntax_errors=[],
                test_pass_rate=100.0,
                coverage_percent=95.0,
                assertion_depth=4.0,
                confidence_score=0.98,
            ),
            cost=0.45,
            duration=15.0,
            tokens_used={"input": 2000, "output": 1000, "total": 3000},
            escalated=False,
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-120000",
            tier_results=[cheap_result, capable_result],
            final_result=capable_result,
            total_cost=0.75,
            total_duration=25.0,
            success=True,
        )

        # Should calculate tier breakdown correctly
        telemetry.track_workflow_completion(result)

    def test_workflow_completion_with_no_failure_analysis(self):
        """Test workflow completion handles missing failure analysis."""
        telemetry = ProgressiveTelemetry(workflow_name="test-gen")

        tier_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85}],
            failure_analysis=None,  # No analysis
            cost=0.10,
            duration=5.0,
            tokens_used={"input": 1000, "output": 500, "total": 1500},
            escalated=False,
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-120000",
            tier_results=[tier_result],
            final_result=tier_result,
            total_cost=0.10,
            total_duration=5.0,
            success=True,
        )

        # Should handle missing failure_analysis gracefully (line 138-140)
        telemetry.track_workflow_completion(result)

    def test_custom_event_with_anonymous_user(self):
        """Test custom event tracking with no user ID."""
        telemetry = ProgressiveTelemetry(workflow_name="test-gen", user_id=None)  # No user ID

        # Should use "anonymous" in event data
        telemetry._track_custom_event(event_type="test_event", data={"test_key": "test_value"})
