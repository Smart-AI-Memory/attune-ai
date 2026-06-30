"""Unit tests for telemetry analytics

Tests the TelemetryAnalytics class for computing metrics and insights.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import tempfile
from datetime import datetime, timezone

import pytest

from attune.models.telemetry import (
    LLMCallRecord,
    TelemetryAnalytics,
    TelemetryStore,
    WorkflowRunRecord,
)


@pytest.mark.unit
class TestTelemetryAnalyticsInitialization:
    """Test telemetry analytics initialization."""

    def test_initialization_with_store(self):
        """Test creating analytics with telemetry store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            assert analytics.store == store

    def test_initialization_creates_store_if_none(self):
        """Test that analytics creates store if none provided."""
        analytics = TelemetryAnalytics()

        assert analytics.store is not None
        assert isinstance(analytics.store, TelemetryStore)


@pytest.mark.unit
class TestTopExpensiveWorkflows:
    """Test top expensive workflows analytics."""

    def test_top_expensive_workflows_basic(self):
        """Test getting top expensive workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add workflow runs with different costs
            store.log_workflow(
                WorkflowRunRecord(
                    run_id="run_001",
                    workflow_name="expensive-workflow",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    stages=[],
                    total_input_tokens=1000,
                    total_output_tokens=500,
                    total_cost=0.50,
                    baseline_cost=1.00,
                    savings=0.50,
                    savings_percent=50.0,
                    total_duration_ms=5000,
                    success=True,
                    providers_used=["anthropic"],
                    tiers_used=["capable"],
                ),
            )

            store.log_workflow(
                WorkflowRunRecord(
                    run_id="run_002",
                    workflow_name="cheap-workflow",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    stages=[],
                    total_input_tokens=100,
                    total_output_tokens=50,
                    total_cost=0.01,
                    baseline_cost=0.05,
                    savings=0.04,
                    savings_percent=80.0,
                    total_duration_ms=1000,
                    success=True,
                    providers_used=["anthropic"],
                    tiers_used=["cheap"],
                ),
            )

            top = analytics.top_expensive_workflows(n=10)

            assert len(top) == 2
            assert top[0]["workflow_name"] == "expensive-workflow"
            assert top[0]["total_cost"] == 0.50
            assert top[0]["run_count"] == 1
            assert top[1]["workflow_name"] == "cheap-workflow"

    def test_top_expensive_workflows_aggregates_same_workflow(self):
        """Test that same workflow runs are aggregated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add multiple runs of same workflow
            for i in range(3):
                store.log_workflow(
                    WorkflowRunRecord(
                        run_id=f"run_{i:03d}",
                        workflow_name="repeated-workflow",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        stages=[],
                        total_input_tokens=100,
                        total_output_tokens=50,
                        total_cost=0.10,
                        baseline_cost=0.20,
                        savings=0.10,
                        savings_percent=50.0,
                        total_duration_ms=1000,
                        success=True,
                        providers_used=["anthropic"],
                        tiers_used=["capable"],
                    ),
                )

            top = analytics.top_expensive_workflows(n=10)

            assert len(top) == 1
            assert top[0]["workflow_name"] == "repeated-workflow"
            assert top[0]["total_cost"] == pytest.approx(0.30)  # 3 runs * 0.10
            assert top[0]["run_count"] == 3
            assert top[0]["total_savings"] == pytest.approx(0.30)  # 3 runs * 0.10

    def test_top_expensive_workflows_limits_results(self):
        """Test that n parameter limits results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add 5 different workflows
            for i in range(5):
                store.log_workflow(
                    WorkflowRunRecord(
                        run_id=f"run_{i:03d}",
                        workflow_name=f"workflow-{i}",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        stages=[],
                        total_input_tokens=100,
                        total_output_tokens=50,
                        total_cost=0.01 * (i + 1),
                        baseline_cost=0.05,
                        savings=0.04,
                        savings_percent=80.0,
                        total_duration_ms=1000,
                        success=True,
                        providers_used=["anthropic"],
                        tiers_used=["capable"],
                    ),
                )

            top = analytics.top_expensive_workflows(n=3)

            assert len(top) == 3
            # Should be sorted by cost descending
            assert top[0]["workflow_name"] == "workflow-4"
            assert top[1]["workflow_name"] == "workflow-3"
            assert top[2]["workflow_name"] == "workflow-2"

    def test_top_expensive_workflows_empty(self):
        """Test with no workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            top = analytics.top_expensive_workflows(n=10)

            assert len(top) == 0


@pytest.mark.unit
class TestProviderUsageSummary:
    """Test provider usage summary analytics."""

    def test_provider_usage_summary_basic(self):
        """Test basic provider usage summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add calls from different providers
            store.log_call(
                LLMCallRecord(
                    call_id="call_001",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.01,
                    latency_ms=1000,
                    success=True,
                ),
            )

            store.log_call(
                LLMCallRecord(
                    call_id="call_002",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="openai",
                    model_id="gpt-4o",
                    tier="capable",
                    task_type="test",
                    input_tokens=200,
                    output_tokens=100,
                    estimated_cost=0.02,
                    latency_ms=2000,
                    success=True,
                ),
            )

            summary = analytics.provider_usage_summary()

            assert "anthropic" in summary
            assert "openai" in summary
            assert summary["anthropic"]["call_count"] == 1
            assert summary["anthropic"]["total_tokens"] == 150
            assert summary["anthropic"]["total_cost"] == 0.01
            assert summary["openai"]["call_count"] == 1
            assert summary["openai"]["total_tokens"] == 300

    def test_provider_usage_summary_error_tracking(self):
        """Test error counting in provider summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add successful call
            store.log_call(
                LLMCallRecord(
                    call_id="call_001",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.01,
                    latency_ms=1000,
                    success=True,
                ),
            )

            # Add failed call
            store.log_call(
                LLMCallRecord(
                    call_id="call_002",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=0,
                    estimated_cost=0.0,
                    latency_ms=500,
                    success=False,
                    error_type="RateLimitError",
                ),
            )

            summary = analytics.provider_usage_summary()

            assert summary["anthropic"]["call_count"] == 2
            assert summary["anthropic"]["error_count"] == 1

    def test_provider_usage_summary_tier_distribution(self):
        """Test tier distribution in provider summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add calls from different tiers
            for tier in ["cheap", "capable", "premium"]:
                store.log_call(
                    LLMCallRecord(
                        call_id=f"call_{tier}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        provider="anthropic",
                        model_id="claude-sonnet-4",
                        tier=tier,
                        task_type="test",
                        input_tokens=100,
                        output_tokens=50,
                        estimated_cost=0.01,
                        latency_ms=1000,
                        success=True,
                    ),
                )

            summary = analytics.provider_usage_summary()

            assert summary["anthropic"]["by_tier"]["cheap"] == 1
            assert summary["anthropic"]["by_tier"]["capable"] == 1
            assert summary["anthropic"]["by_tier"]["premium"] == 1

    def test_provider_usage_summary_empty(self):
        """Test with no calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            summary = analytics.provider_usage_summary()

            assert len(summary) == 0


@pytest.mark.unit
class TestTierDistribution:
    """Test tier distribution analytics."""

    def test_tier_distribution_basic(self):
        """Test basic tier distribution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add calls from different tiers
            store.log_call(
                LLMCallRecord(
                    call_id="call_001",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-haiku-4",
                    tier="cheap",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.001,
                    latency_ms=500,
                    success=True,
                ),
            )

            store.log_call(
                LLMCallRecord(
                    call_id="call_002",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=200,
                    output_tokens=100,
                    estimated_cost=0.01,
                    latency_ms=1000,
                    success=True,
                ),
            )

            dist = analytics.tier_distribution()

            assert "cheap" in dist
            assert "capable" in dist
            assert "premium" in dist
            assert dist["cheap"]["count"] == 1
            assert dist["cheap"]["cost"] == 0.001
            assert dist["cheap"]["tokens"] == 150
            assert dist["capable"]["count"] == 1
            assert dist["capable"]["cost"] == 0.01

    def test_tier_distribution_percentages(self):
        """Test that percentages are calculated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add 2 cheap, 1 capable, 1 premium (4 total)
            for i in range(2):
                store.log_call(
                    LLMCallRecord(
                        call_id=f"call_cheap_{i}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        provider="anthropic",
                        model_id="claude-haiku-4",
                        tier="cheap",
                        task_type="test",
                        input_tokens=100,
                        output_tokens=50,
                        estimated_cost=0.001,
                        latency_ms=500,
                        success=True,
                    ),
                )

            store.log_call(
                LLMCallRecord(
                    call_id="call_capable",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.01,
                    latency_ms=1000,
                    success=True,
                ),
            )

            store.log_call(
                LLMCallRecord(
                    call_id="call_premium",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-opus-4",
                    tier="premium",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.05,
                    latency_ms=2000,
                    success=True,
                ),
            )

            dist = analytics.tier_distribution()

            assert dist["cheap"]["percent"] == 50.0  # 2/4
            assert dist["capable"]["percent"] == 25.0  # 1/4
            assert dist["premium"]["percent"] == 25.0  # 1/4

    def test_tier_distribution_empty(self):
        """Test with no calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            dist = analytics.tier_distribution()

            assert dist["cheap"]["count"] == 0
            assert dist["cheap"]["percent"] == 0.0
            assert dist["capable"]["count"] == 0
            assert dist["premium"]["count"] == 0


@pytest.mark.unit
class TestFallbackStats:
    """Test fallback statistics."""

    def test_fallback_stats_basic(self):
        """Test basic fallback statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add call without fallback
            store.log_call(
                LLMCallRecord(
                    call_id="call_001",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.01,
                    latency_ms=1000,
                    success=True,
                ),
            )

            # Add call with fallback
            store.log_call(
                LLMCallRecord(
                    call_id="call_002",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.01,
                    latency_ms=1000,
                    success=True,
                    fallback_used=True,
                    original_provider="openai",
                    original_model="gpt-4o",
                ),
            )

            stats = analytics.fallback_stats()

            assert stats["total_calls"] == 2
            assert stats["fallback_count"] == 1
            assert stats["fallback_percent"] == 50.0

    def test_fallback_stats_by_provider(self):
        """Test fallback breakdown by original provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add fallback from OpenAI
            store.log_call(
                LLMCallRecord(
                    call_id="call_001",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.01,
                    latency_ms=1000,
                    success=True,
                    fallback_used=True,
                    original_provider="openai",
                ),
            )

            # Add another fallback from OpenAI
            store.log_call(
                LLMCallRecord(
                    call_id="call_002",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.01,
                    latency_ms=1000,
                    success=True,
                    fallback_used=True,
                    original_provider="openai",
                ),
            )

            stats = analytics.fallback_stats()

            assert stats["by_original_provider"]["openai"] == 2

    def test_fallback_stats_error_rate(self):
        """Test error rate calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add successful call
            store.log_call(
                LLMCallRecord(
                    call_id="call_001",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.01,
                    latency_ms=1000,
                    success=True,
                ),
            )

            # Add failed call
            store.log_call(
                LLMCallRecord(
                    call_id="call_002",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    provider="anthropic",
                    model_id="claude-sonnet-4",
                    tier="capable",
                    task_type="test",
                    input_tokens=100,
                    output_tokens=0,
                    estimated_cost=0.0,
                    latency_ms=500,
                    success=False,
                    error_type="RateLimitError",
                ),
            )

            stats = analytics.fallback_stats()

            assert stats["total_calls"] == 2
            assert stats["error_count"] == 1
            assert stats["error_rate"] == 50.0

    def test_fallback_stats_empty(self):
        """Test with no calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            stats = analytics.fallback_stats()

            assert stats["total_calls"] == 0
            assert stats["fallback_count"] == 0
            assert stats["fallback_percent"] == 0.0


@pytest.mark.unit
class TestCostSavingsReport:
    """Test cost savings report."""

    def test_cost_savings_report_basic(self):
        """Test basic cost savings report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            store.log_workflow(
                WorkflowRunRecord(
                    run_id="run_001",
                    workflow_name="test",
                    started_at=datetime.now(timezone.utc).isoformat(),
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    stages=[],
                    total_input_tokens=100,
                    total_output_tokens=50,
                    total_cost=0.01,
                    baseline_cost=0.05,
                    savings=0.04,
                    savings_percent=80.0,
                    total_duration_ms=1000,
                    success=True,
                    providers_used=["anthropic"],
                    tiers_used=["capable"],
                ),
            )

            report = analytics.cost_savings_report()

            assert report["workflow_count"] == 1
            assert report["total_actual_cost"] == 0.01
            assert report["total_baseline_cost"] == 0.05
            assert report["total_savings"] == 0.04
            assert report["savings_percent"] == 80.0

    def test_cost_savings_report_aggregates_multiple_workflows(self):
        """Test that report aggregates multiple workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Add 3 workflows
            for i in range(3):
                store.log_workflow(
                    WorkflowRunRecord(
                        run_id=f"run_{i:03d}",
                        workflow_name=f"workflow-{i}",
                        started_at=datetime.now(timezone.utc).isoformat(),
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        stages=[],
                        total_input_tokens=100,
                        total_output_tokens=50,
                        total_cost=0.01,
                        baseline_cost=0.05,
                        savings=0.04,
                        savings_percent=80.0,
                        total_duration_ms=1000,
                        success=True,
                        providers_used=["anthropic"],
                        tiers_used=["capable"],
                    ),
                )

            report = analytics.cost_savings_report()

            assert report["workflow_count"] == 3
            assert report["total_actual_cost"] == pytest.approx(0.03)
            assert report["total_baseline_cost"] == pytest.approx(0.15)
            assert report["total_savings"] == pytest.approx(0.12)
            assert report["avg_cost_per_workflow"] == pytest.approx(0.01)

    def test_cost_savings_report_empty(self):
        """Test with no workflows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            report = analytics.cost_savings_report()

            assert report["workflow_count"] == 0
            assert report["total_actual_cost"] == 0.0
            assert report["total_baseline_cost"] == 0.0
            assert report["total_savings"] == 0.0
            assert report["avg_cost_per_workflow"] == 0.0


# ===========================================================================
# Coverage for previously-missed branches
# ===========================================================================


from attune.models.telemetry import AgentAssignmentRecord, CoverageRecord  # noqa: E402


def _now():
    return datetime.now(timezone.utc).isoformat()


@pytest.mark.unit
class TestSonnetOpusFallbackAnalysis:
    """Cover lines 200-263 of analytics.py."""

    def test_returns_zeros_when_no_anthropic_calls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)
            # Log a non-anthropic call so the calls list isn't empty
            store.log_call(
                LLMCallRecord(
                    call_id="x",
                    timestamp=_now(),
                    provider="openai",
                    model_id="gpt-4",
                ),
            )
            result = analytics.sonnet_opus_fallback_analysis()
            assert result["total_calls"] == 0
            assert result["sonnet_attempts"] == 0
            assert result["savings"] == 0.0
            assert result["fallback_rate"] == 0.0

    def test_full_analysis_with_sonnet_and_opus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # 2 sonnet successes
            for i in range(2):
                store.log_call(
                    LLMCallRecord(
                        call_id=f"sonnet-ok-{i}",
                        timestamp=_now(),
                        provider="anthropic",
                        model_id="claude-sonnet-5",
                        input_tokens=1000,
                        output_tokens=500,
                        estimated_cost=0.005,
                        success=True,
                    ),
                )
            # 1 sonnet failure
            store.log_call(
                LLMCallRecord(
                    call_id="sonnet-fail",
                    timestamp=_now(),
                    provider="anthropic",
                    model_id="claude-sonnet-5",
                    input_tokens=1000,
                    output_tokens=500,
                    estimated_cost=0.005,
                    success=False,
                ),
            )
            # 1 opus fallback
            store.log_call(
                LLMCallRecord(
                    call_id="opus-fb",
                    timestamp=_now(),
                    provider="anthropic",
                    model_id="claude-opus-4-6",
                    input_tokens=1000,
                    output_tokens=500,
                    estimated_cost=0.05,
                    success=True,
                    fallback_used=True,
                ),
            )

            result = analytics.sonnet_opus_fallback_analysis()
            assert result["total_calls"] == 4
            assert result["sonnet_attempts"] == 3
            assert result["sonnet_successes"] == 2
            assert result["opus_fallbacks"] == 1
            assert result["success_rate_sonnet"] == pytest.approx(2 / 3 * 100)
            assert result["fallback_rate"] == 25.0
            assert result["actual_cost"] > 0
            assert result["always_opus_cost"] > result["actual_cost"]
            assert result["savings"] > 0
            assert result["savings_percent"] > 0
            assert result["avg_cost_per_call"] > 0
            assert result["avg_opus_cost_per_call"] > 0


@pytest.mark.unit
class TestCoverageProgressStableTrend:
    """Cover line 460: trend = 'stable' when |change| <= 1.0."""

    def test_two_records_small_change_is_stable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Two records with tiny change → stable
            for i, pct in enumerate([85.0, 85.5]):
                store.log_coverage(
                    CoverageRecord(
                        record_id=f"c{i}",
                        timestamp=_now(),
                        overall_percentage=pct,
                        lines_total=1000,
                        lines_covered=int(pct * 10),
                    ),
                )

            result = analytics.coverage_progress()
            assert result["trend"] == "stable"
            assert result["change"] == pytest.approx(0.5)


@pytest.mark.unit
class TestAgentPerformanceBranches:
    """Cover assignment-loop branches: 532->538, 541->543, 544, 550->554."""

    def test_non_completed_with_no_review_and_no_automation(self):
        """Status != 'completed' AND not automated_eligible AND not human_review."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Single in-progress assignment, no automation flags, no human review
            store.log_agent_assignment(
                AgentAssignmentRecord(
                    assignment_id="a1",
                    timestamp=_now(),
                    task_id="t1",
                    task_title="Task 1",
                    task_description="desc",
                    assigned_agent="agent-a",
                    status="in_progress",
                    success=False,
                    automated_eligible=False,
                    human_review_required=False,
                ),
            )

            result = analytics.agent_performance()
            assert result["total_assignments"] == 1
            assert result["automation_rate"] == 0.0
            assert result["human_review_rate"] == 0.0
            stats = result["by_agent"]["agent-a"]
            # No completed assignments → avg_duration_hours stays default 0.0
            assert stats["avg_duration_hours"] == 0.0
            # Helper fields removed
            assert "total_duration" not in stats
            assert "quality_scores" not in stats
            assert "successful" not in stats

    def test_human_review_required_branch(self):
        """Cover line 544: human_review_required True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            store.log_agent_assignment(
                AgentAssignmentRecord(
                    assignment_id="a1",
                    timestamp=_now(),
                    task_id="t1",
                    task_title="Task",
                    task_description="d",
                    assigned_agent="agent-h",
                    status="completed",
                    actual_duration_hours=2.5,
                    success=True,
                    automated_eligible=True,
                    human_review_required=True,
                ),
            )

            result = analytics.agent_performance()
            assert result["automation_rate"] == 1.0
            assert result["human_review_rate"] == 1.0
            stats = result["by_agent"]["agent-h"]
            assert stats["completed"] == 1
            assert stats["avg_duration_hours"] == pytest.approx(2.5)


@pytest.mark.unit
class TestProviderAndTierBranches:
    """Cover branches in provider_usage_summary and tier_distribution."""

    def test_provider_summary_unknown_tier_not_counted(self):
        """Line 105->88: call.tier not in by_tier → skip increment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            store.log_call(
                LLMCallRecord(
                    call_id="c1",
                    timestamp=_now(),
                    provider="anthropic",
                    tier="unknown_tier",  # not in by_tier dict
                    input_tokens=100,
                    output_tokens=50,
                    estimated_cost=0.01,
                    success=True,
                ),
            )
            summary = analytics.provider_usage_summary()
            stats = summary["anthropic"]
            assert stats["call_count"] == 1
            # Unknown tier shouldn't appear or increment any tier counter
            assert sum(stats["by_tier"].values()) == 0

    def test_tier_distribution_unknown_tier_skipped(self):
        """Line 137->136: call.tier not in dist → skip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)

            # Mix: one valid tier and one unknown
            store.log_call(
                LLMCallRecord(
                    call_id="c1",
                    timestamp=_now(),
                    provider="anthropic",
                    tier="cheap",
                    estimated_cost=0.001,
                    input_tokens=10,
                    output_tokens=5,
                ),
            )
            store.log_call(
                LLMCallRecord(
                    call_id="c2",
                    timestamp=_now(),
                    provider="anthropic",
                    tier="bogus_tier",
                    estimated_cost=0.5,
                    input_tokens=10,
                    output_tokens=5,
                ),
            )
            dist = analytics.tier_distribution()
            assert dist["cheap"]["count"] == 1
            # Unknown tier not added
            assert "bogus_tier" not in dist


@pytest.mark.unit
class TestTopExpensiveZeroRunCount:
    """Cover line 66->65: skip avg_cost calc when run_count == 0.

    This branch is unreachable in normal flow (run_count is incremented for
    every workflow), but exercising the loop with no workflows still touches
    the for-loop to exit normally — so we just ensure the fallback path is
    valid (empty result set bypasses the for-body).
    """

    def test_no_workflows_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TelemetryStore(tmpdir)
            analytics = TelemetryAnalytics(store)
            assert analytics.top_expensive_workflows() == []
