"""Unit tests for adaptive model routing module.

This test suite provides comprehensive coverage for the adaptive routing system
that learns from telemetry to optimize model selection based on performance,
cost, and success rates.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from unittest.mock import MagicMock, patch

import pytest

from attune.models.adaptive_routing import (
    AdaptiveModelRouter,
    ModelPerformance,
)


@pytest.mark.unit
class TestModelPerformance:
    """Test suite for ModelPerformance dataclass."""

    def test_create_model_performance_with_required_fields(self):
        """Test creating ModelPerformance with required fields."""
        perf = ModelPerformance(
            model_id="claude-haiku-4-5-20251001",
            tier="CHEAP",
            success_rate=0.95,
            avg_latency_ms=850.5,
            avg_cost=0.0025,
            sample_size=100,
        )

        assert perf.model_id == "claude-haiku-4-5-20251001"
        assert perf.tier == "CHEAP"
        assert perf.success_rate == 0.95
        assert perf.avg_latency_ms == 850.5
        assert perf.avg_cost == 0.0025
        assert perf.sample_size == 100
        assert perf.recent_failures == 0

    def test_create_model_performance_with_recent_failures(self):
        """Test creating ModelPerformance with recent failures."""
        perf = ModelPerformance(
            model_id="test-model",
            tier="CAPABLE",
            success_rate=0.8,
            avg_latency_ms=1200,
            avg_cost=0.005,
            sample_size=50,
            recent_failures=5,
        )

        assert perf.recent_failures == 5

    def test_quality_score_calculation(self):
        """Test quality_score property calculation."""
        perf = ModelPerformance(
            model_id="test-model",
            tier="CHEAP",
            success_rate=0.9,
            avg_latency_ms=1000,
            avg_cost=0.002,
            sample_size=100,
        )

        # Formula: (success_rate * 100) - (avg_cost * 10)
        # = (0.9 * 100) - (0.002 * 10)
        # = 90 - 0.02 = 89.98
        expected_score = (0.9 * 100) - (0.002 * 10)
        assert perf.quality_score == expected_score

    def test_quality_score_prioritizes_success_rate(self):
        """Test that quality score is dominated by success rate."""
        high_success = ModelPerformance(
            model_id="model1",
            tier="CHEAP",
            success_rate=0.95,
            avg_latency_ms=1000,
            avg_cost=0.005,
            sample_size=100,
        )

        low_success = ModelPerformance(
            model_id="model2",
            tier="CHEAP",
            success_rate=0.5,
            avg_latency_ms=1000,
            avg_cost=0.001,  # Cheaper but worse success rate
            sample_size=100,
        )

        # High success rate should have better quality score despite higher cost
        assert high_success.quality_score > low_success.quality_score

    def test_quality_score_favors_lower_cost(self):
        """Test that quality score favors lower cost when success rates equal."""
        cheap_model = ModelPerformance(
            model_id="model1",
            tier="CHEAP",
            success_rate=0.9,
            avg_latency_ms=1000,
            avg_cost=0.001,
            sample_size=100,
        )

        expensive_model = ModelPerformance(
            model_id="model2",
            tier="PREMIUM",
            success_rate=0.9,
            avg_latency_ms=1000,
            avg_cost=0.01,
            sample_size=100,
        )

        # Same success rate, but cheaper model should score higher
        assert cheap_model.quality_score > expensive_model.quality_score


@pytest.mark.unit
class TestAdaptiveModelRouterInit:
    """Test suite for AdaptiveModelRouter initialization."""

    def test_router_initializes_with_telemetry(self):
        """Test that router initializes with telemetry instance."""
        mock_telemetry = MagicMock()
        router = AdaptiveModelRouter(mock_telemetry)

        assert router.telemetry == mock_telemetry

    def test_router_has_class_constants(self):
        """Test that router has expected class constants."""
        assert AdaptiveModelRouter.MIN_SAMPLE_SIZE == 10
        assert AdaptiveModelRouter.FAILURE_RATE_THRESHOLD == 0.2
        assert AdaptiveModelRouter.RECENT_WINDOW_SIZE == 20


@pytest.mark.unit
class TestGetBestModel:
    """Test suite for get_best_model method."""

    def test_get_best_model_returns_default_when_no_history(self):
        """Test that get_best_model returns default model when no telemetry."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = []

        router = AdaptiveModelRouter(mock_telemetry)

        with patch.object(router, "_get_default_model", return_value="default-model"):
            model = router.get_best_model(workflow="test", stage="analysis")

        assert model == "default-model"

    def test_get_best_model_selects_highest_quality_score(self):
        """Test that get_best_model selects model with highest quality score."""
        mock_telemetry = MagicMock()

        # Mock telemetry entries for two models
        mock_telemetry.get_recent_entries.return_value = [
            # Model 1: 12 successful calls
            *[
                {
                    "workflow": "test",
                    "stage": "analysis",
                    "model": "model1",
                    "success": True,
                    "cost": 0.002,
                    "duration_ms": 800,
                    "tier": "CHEAP",
                }
                for _ in range(12)
            ],
            # Model 2: 15 successful calls, lower cost
            *[
                {
                    "workflow": "test",
                    "stage": "analysis",
                    "model": "model2",
                    "success": True,
                    "cost": 0.001,
                    "duration_ms": 900,
                    "tier": "CHEAP",
                }
                for _ in range(15)
            ],
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        model = router.get_best_model(workflow="test", stage="analysis", min_success_rate=0.8)

        # model2 should win (same success rate, lower cost)
        assert model == "model2"

    def test_get_best_model_respects_max_cost_constraint(self):
        """Test that get_best_model filters by max_cost."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            # Expensive model (avg cost: 0.01)
            *[
                {
                    "workflow": "test",
                    "stage": "analysis",
                    "model": "expensive",
                    "success": True,
                    "cost": 0.01,
                    "duration_ms": 500,
                    "tier": "PREMIUM",
                }
                for _ in range(15)
            ],
            # Cheap model (avg cost: 0.002)
            *[
                {
                    "workflow": "test",
                    "stage": "analysis",
                    "model": "cheap",
                    "success": True,
                    "cost": 0.002,
                    "duration_ms": 800,
                    "tier": "CHEAP",
                }
                for _ in range(15)
            ],
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        model = router.get_best_model(
            workflow="test", stage="analysis", max_cost=0.005, min_success_rate=0.8
        )

        # Should select cheap model (expensive exceeds max_cost)
        assert model == "cheap"

    def test_get_best_model_respects_max_latency_constraint(self):
        """Test that get_best_model filters by max_latency_ms."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            # Fast model (avg latency: 500ms)
            *[
                {
                    "workflow": "test",
                    "stage": "analysis",
                    "model": "fast",
                    "success": True,
                    "cost": 0.003,
                    "duration_ms": 500,
                    "tier": "CHEAP",
                }
                for _ in range(15)
            ],
            # Slow model (avg latency: 2000ms)
            *[
                {
                    "workflow": "test",
                    "stage": "analysis",
                    "model": "slow",
                    "success": True,
                    "cost": 0.001,
                    "duration_ms": 2000,
                    "tier": "CHEAP",
                }
                for _ in range(15)
            ],
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        model = router.get_best_model(
            workflow="test",
            stage="analysis",
            max_latency_ms=1000,
            min_success_rate=0.8,
        )

        # Should select fast model (slow exceeds max_latency)
        assert model == "fast"

    def test_get_best_model_respects_min_success_rate(self):
        """Test that get_best_model filters by min_success_rate."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            # Reliable model (100% success)
            *[
                {
                    "workflow": "test",
                    "stage": "analysis",
                    "model": "reliable",
                    "success": True,
                    "cost": 0.003,
                    "duration_ms": 800,
                    "tier": "CAPABLE",
                }
                for _ in range(15)
            ],
            # Unreliable model (70% success)
            *[
                {
                    "workflow": "test",
                    "stage": "analysis",
                    "model": "unreliable",
                    "success": i < 10,  # 10 successes, 5 failures
                    "cost": 0.001,
                    "duration_ms": 500,
                    "tier": "CHEAP",
                }
                for i in range(15)
            ],
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        model = router.get_best_model(workflow="test", stage="analysis", min_success_rate=0.9)

        # Should select reliable model (unreliable fails min_success_rate)
        assert model == "reliable"


@pytest.mark.unit
class TestRecommendTierUpgrade:
    """Test suite for recommend_tier_upgrade method."""

    def test_recommend_tier_upgrade_when_high_failure_rate(self):
        """Test that upgrade is recommended when failure rate exceeds threshold."""
        mock_telemetry = MagicMock()

        # 25 calls with 6 failures in last 20 (30% failure rate)
        entries = [{"workflow": "test", "stage": "analysis", "success": i < 19} for i in range(25)]
        mock_telemetry.get_recent_entries.return_value = entries

        router = AdaptiveModelRouter(mock_telemetry)
        should_upgrade, reason = router.recommend_tier_upgrade("test", "analysis")

        assert should_upgrade is True
        assert "High failure rate" in reason
        assert "30.0%" in reason

    def test_recommend_tier_upgrade_when_acceptable_performance(self):
        """Test that no upgrade when failure rate is acceptable."""
        mock_telemetry = MagicMock()

        # 25 calls with only 2 failures in last 20 (10% failure rate)
        entries = [{"workflow": "test", "stage": "analysis", "success": i < 23} for i in range(25)]
        mock_telemetry.get_recent_entries.return_value = entries

        router = AdaptiveModelRouter(mock_telemetry)
        should_upgrade, reason = router.recommend_tier_upgrade("test", "analysis")

        assert should_upgrade is False
        assert "Performance acceptable" in reason
        assert "10.0%" in reason

    def test_recommend_tier_upgrade_insufficient_data(self):
        """Test that no upgrade recommended when insufficient data."""
        mock_telemetry = MagicMock()

        # Only 5 calls (less than MIN_SAMPLE_SIZE of 10)
        mock_telemetry.get_recent_entries.return_value = [
            {"workflow": "test", "stage": "analysis", "success": False} for _ in range(5)
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        should_upgrade, reason = router.recommend_tier_upgrade("test", "analysis")

        assert should_upgrade is False
        assert "Insufficient data" in reason

    def test_recommend_tier_upgrade_at_exact_threshold(self):
        """Test behavior at exact failure rate threshold (20%)."""
        mock_telemetry = MagicMock()

        # Exactly 4 failures in 20 calls = 20% (at threshold)
        entries = [{"workflow": "test", "stage": "analysis", "success": i < 16} for i in range(20)]
        mock_telemetry.get_recent_entries.return_value = entries

        router = AdaptiveModelRouter(mock_telemetry)
        should_upgrade, reason = router.recommend_tier_upgrade("test", "analysis")

        # At threshold, should not upgrade (uses > not >=)
        assert should_upgrade is False


@pytest.mark.unit
class TestGetRoutingStats:
    """Test suite for get_routing_stats method."""

    def test_get_routing_stats_returns_empty_for_no_data(self):
        """Test that get_routing_stats returns empty stats when no data."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = []

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test", days=7)

        assert stats["models_used"] == []
        assert stats["performance_by_model"] == {}
        assert stats["total_calls"] == 0
        assert stats["avg_cost"] == 0.0
        assert stats["avg_success_rate"] == 0.0

    def test_get_routing_stats_calculates_totals(self):
        """Test that get_routing_stats calculates total metrics."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "model": "model1",
                "success": True,
                "cost": 0.002,
                "duration_ms": 800,
            },
            {
                "workflow": "test",
                "model": "model2",
                "success": False,
                "cost": 0.003,
                "duration_ms": 900,
            },
            {
                "workflow": "test",
                "model": "model1",
                "success": True,
                "cost": 0.002,
                "duration_ms": 850,
            },
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test", days=7)

        assert stats["total_calls"] == 3
        assert stats["avg_cost"] == (0.002 + 0.003 + 0.002) / 3
        assert stats["avg_success_rate"] == 2 / 3  # 2 successes out of 3

    def test_get_routing_stats_groups_by_model(self):
        """Test that get_routing_stats groups performance by model."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "model": "model1",
                "success": True,
                "cost": 0.002,
                "duration_ms": 800,
            },
            {
                "workflow": "test",
                "model": "model1",
                "success": True,
                "cost": 0.002,
                "duration_ms": 850,
            },
            {
                "workflow": "test",
                "model": "model2",
                "success": False,
                "cost": 0.005,
                "duration_ms": 1200,
            },
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test", days=7)

        assert set(stats["models_used"]) == {"model1", "model2"}

        # model1 performance
        assert stats["performance_by_model"]["model1"]["calls"] == 2
        assert stats["performance_by_model"]["model1"]["success_rate"] == 1.0
        assert stats["performance_by_model"]["model1"]["avg_cost"] == 0.002

        # model2 performance
        assert stats["performance_by_model"]["model2"]["calls"] == 1
        assert stats["performance_by_model"]["model2"]["success_rate"] == 0.0
        assert stats["performance_by_model"]["model2"]["avg_cost"] == 0.005

    def test_get_routing_stats_filters_by_workflow(self):
        """Test that get_routing_stats filters to specified workflow."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {"workflow": "test", "model": "m1", "success": True, "cost": 0.001},
            {"workflow": "other", "model": "m1", "success": True, "cost": 0.001},
            {"workflow": "test", "model": "m1", "success": True, "cost": 0.001},
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test", days=7)

        # Should only count entries for "test" workflow
        assert stats["total_calls"] == 2

    def test_get_routing_stats_filters_by_stage_when_specified(self):
        """Test that get_routing_stats filters by stage when provided."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "m1",
                "success": True,
                "cost": 0.001,
            },
            {
                "workflow": "test",
                "stage": "synthesis",
                "model": "m1",
                "success": True,
                "cost": 0.001,
            },
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "m1",
                "success": True,
                "cost": 0.001,
            },
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test", stage="analysis", days=7)

        # Should only count entries for "analysis" stage
        assert stats["total_calls"] == 2
        assert stats["stage"] == "analysis"

    def test_get_routing_stats_includes_all_stages_when_none_specified(self):
        """Test that get_routing_stats includes all stages when stage=None."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "m1",
                "success": True,
                "cost": 0.001,
            },
            {
                "workflow": "test",
                "stage": "synthesis",
                "model": "m1",
                "success": True,
                "cost": 0.001,
            },
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test", stage=None, days=7)

        # Should count all stages
        assert stats["total_calls"] == 2
        assert stats["stage"] == "all"


@pytest.mark.unit
class TestAnalyzeModelPerformance:
    """Test suite for _analyze_model_performance method."""

    def test_analyze_model_performance_returns_empty_for_no_data(self):
        """Test that _analyze_model_performance returns empty list when no data."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = []

        router = AdaptiveModelRouter(mock_telemetry)
        performances = router._analyze_model_performance("test", "analysis")

        assert performances == []

    def test_analyze_model_performance_calculates_metrics(self):
        """Test that _analyze_model_performance calculates correct metrics."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "model1",
                "tier": "CHEAP",
                "success": True,
                "cost": 0.002,
                "duration_ms": 800,
            },
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "model1",
                "tier": "CHEAP",
                "success": False,
                "cost": 0.002,
                "duration_ms": 850,
            },
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "model1",
                "tier": "CHEAP",
                "success": True,
                "cost": 0.002,
                "duration_ms": 900,
            },
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        performances = router._analyze_model_performance("test", "analysis")

        assert len(performances) == 1
        perf = performances[0]

        assert perf.model_id == "model1"
        assert perf.tier == "CHEAP"
        assert perf.success_rate == 2 / 3  # 2 successes out of 3
        assert perf.avg_cost == 0.002
        assert perf.avg_latency_ms == (800 + 850 + 900) / 3
        assert perf.sample_size == 3

    def test_analyze_model_performance_groups_by_model(self):
        """Test that _analyze_model_performance groups entries by model."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "model1",
                "tier": "CHEAP",
                "success": True,
                "cost": 0.001,
                "duration_ms": 500,
            },
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "model2",
                "tier": "CAPABLE",
                "success": True,
                "cost": 0.003,
                "duration_ms": 600,
            },
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        performances = router._analyze_model_performance("test", "analysis")

        assert len(performances) == 2
        model_ids = {p.model_id for p in performances}
        assert model_ids == {"model1", "model2"}

    def test_analyze_model_performance_counts_recent_failures(self):
        """Test that _analyze_model_performance counts recent failures."""
        mock_telemetry = MagicMock()

        # 30 calls with 5 failures in last 20
        entries = [
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "model1",
                "tier": "CHEAP",
                "success": i < 25,  # Last 5 are failures
                "cost": 0.001,
                "duration_ms": 500,
            }
            for i in range(30)
        ]
        mock_telemetry.get_recent_entries.return_value = entries

        router = AdaptiveModelRouter(mock_telemetry)
        performances = router._analyze_model_performance("test", "analysis")

        assert len(performances) == 1
        # Should count 5 recent failures in last 20 calls
        assert performances[0].recent_failures == 5


@pytest.mark.unit
class TestGetWorkflowStageEntries:
    """Test suite for _get_workflow_stage_entries method."""

    def test_get_workflow_stage_entries_filters_by_workflow(self):
        """Test that entries are filtered to specified workflow."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {"workflow": "test1", "stage": "analysis"},
            {"workflow": "test2", "stage": "analysis"},
            {"workflow": "test1", "stage": "synthesis"},
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        entries = router._get_workflow_stage_entries("test1", None, days=7)

        assert len(entries) == 2
        assert all(e["workflow"] == "test1" for e in entries)

    def test_get_workflow_stage_entries_filters_by_stage_when_specified(self):
        """Test that entries are filtered by stage when provided."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {"workflow": "test", "stage": "analysis"},
            {"workflow": "test", "stage": "synthesis"},
            {"workflow": "test", "stage": "analysis"},
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        entries = router._get_workflow_stage_entries("test", "analysis", days=7)

        assert len(entries) == 2
        assert all(e["stage"] == "analysis" for e in entries)

    def test_get_workflow_stage_entries_includes_all_stages_when_none(self):
        """Test that all stages included when stage=None."""
        mock_telemetry = MagicMock()

        mock_telemetry.get_recent_entries.return_value = [
            {"workflow": "test", "stage": "analysis"},
            {"workflow": "test", "stage": "synthesis"},
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        entries = router._get_workflow_stage_entries("test", None, days=7)

        assert len(entries) == 2


@pytest.mark.unit
class TestGetDefaultModel:
    """Test suite for _get_default_model method."""

    @patch("attune.models.adaptive_routing._get_registry")
    def test_get_default_model_returns_from_registry(self, mock_get_registry):
        """Test that _get_default_model returns model from registry."""
        # Mock registry structure
        mock_registry = {
            "anthropic": {
                "cheap": MagicMock(id="claude-haiku-4-5-20251001"),
                "capable": MagicMock(id="claude-sonnet-4-5-20250929"),
            }
        }
        mock_get_registry.return_value = mock_registry

        mock_telemetry = MagicMock()
        router = AdaptiveModelRouter(mock_telemetry)

        model = router._get_default_model("CHEAP")
        assert model == "claude-haiku-4-5-20251001"

    @patch("attune.models.adaptive_routing._get_registry")
    def test_get_default_model_falls_back_when_registry_missing(self, mock_get_registry):
        """Test fallback when tier not in registry."""
        mock_get_registry.return_value = {"anthropic": {}}

        mock_telemetry = MagicMock()
        router = AdaptiveModelRouter(mock_telemetry)

        model = router._get_default_model("CHEAP")
        # Should fall back to hardcoded default
        assert model == "claude-haiku-4-5-20251001"

    @patch("attune.models.adaptive_routing._get_registry")
    def test_get_default_model_handles_case_insensitive_tier(self, mock_get_registry):
        """Test that tier name is case-insensitive."""
        mock_registry = {
            "anthropic": {
                "cheap": MagicMock(id="test-model"),
            }
        }
        mock_get_registry.return_value = mock_registry

        mock_telemetry = MagicMock()
        router = AdaptiveModelRouter(mock_telemetry)

        # Should work with uppercase tier name
        model = router._get_default_model("CHEAP")
        assert model == "test-model"
