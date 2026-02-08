"""Unit tests for adaptive model routing module.

Tests AdaptiveModelRouter class for intelligent model selection based on
historical telemetry performance data.
"""

from unittest.mock import MagicMock, patch

import pytest

from attune.models.adaptive_routing import (
    AdaptiveModelRouter,
    ModelPerformance,
)


@pytest.mark.unit
class TestModelPerformance:
    """Test ModelPerformance dataclass."""

    def test_model_performance_required_fields(self):
        """Test ModelPerformance has all required fields."""
        perf = ModelPerformance(
            model_id="claude-haiku-4-5-20251001",
            tier="CHEAP",
            success_rate=0.95,
            avg_latency_ms=250.0,
            avg_cost=0.003,
            sample_size=100,
        )
        assert perf.model_id == "claude-haiku-4-5-20251001"
        assert perf.tier == "CHEAP"
        assert perf.success_rate == 0.95
        assert perf.avg_latency_ms == 250.0
        assert perf.avg_cost == 0.003
        assert perf.sample_size == 100
        assert perf.recent_failures == 0

    def test_model_performance_recent_failures(self):
        """Test ModelPerformance with recent_failures."""
        perf = ModelPerformance(
            model_id="test-model",
            tier="CAPABLE",
            success_rate=0.8,
            avg_latency_ms=500.0,
            avg_cost=0.01,
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
            avg_latency_ms=200.0,
            avg_cost=0.001,
            sample_size=100,
        )
        # Score = (success_rate * 100) - (avg_cost * 10)
        # = (0.9 * 100) - (0.001 * 10) = 90 - 0.01 = 89.99
        expected = 90.0 - 0.01
        assert perf.quality_score == pytest.approx(expected)

    def test_quality_score_high_cost(self):
        """Test quality_score with high cost model."""
        perf = ModelPerformance(
            model_id="premium-model",
            tier="PREMIUM",
            success_rate=0.99,
            avg_latency_ms=1000.0,
            avg_cost=0.5,
            sample_size=50,
        )
        # Score = (0.99 * 100) - (0.5 * 10) = 99 - 5 = 94
        expected = 99.0 - 5.0
        assert perf.quality_score == pytest.approx(expected)


@pytest.mark.unit
class TestAdaptiveModelRouterInit:
    """Test AdaptiveModelRouter initialization."""

    def test_init_with_telemetry(self):
        """Test initialization with telemetry instance."""
        mock_telemetry = MagicMock()
        router = AdaptiveModelRouter(mock_telemetry)
        assert router.telemetry == mock_telemetry

    def test_constants(self):
        """Test class constants are set correctly."""
        assert AdaptiveModelRouter.MIN_SAMPLE_SIZE == 10
        assert AdaptiveModelRouter.FAILURE_RATE_THRESHOLD == 0.2
        assert AdaptiveModelRouter.RECENT_WINDOW_SIZE == 20


@pytest.mark.unit
@patch("attune.models.adaptive_routing.logger")
class TestGetBestModel:
    """Test get_best_model method."""

    def test_get_best_model_no_history(self, mock_logger):
        """Test returns default model when no history."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = []

        router = AdaptiveModelRouter(mock_telemetry)
        model = router.get_best_model(workflow="test-workflow", stage="analysis")

        assert model is not None
        assert isinstance(model, str)

    def test_get_best_model_with_history(self, mock_logger):
        """Test returns best model from history."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test-workflow",
                "stage": "analysis",
                "model": "claude-haiku-4-5-20251001",
                "tier": "CHEAP",
                "success": True,
                "cost": 0.002,
                "duration_ms": 200,
            }
            for _ in range(15)  # Above MIN_SAMPLE_SIZE
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        model = router.get_best_model(workflow="test-workflow", stage="analysis")

        assert model == "claude-haiku-4-5-20251001"

    def test_get_best_model_filters_by_min_success_rate(self, mock_logger):
        """Test filters models below min_success_rate."""
        mock_telemetry = MagicMock()
        # 5 successes + 10 failures = 33% success rate
        entries = []
        for _i in range(5):
            entries.append(
                {
                    "workflow": "test",
                    "stage": "test",
                    "model": "low-success-model",
                    "tier": "CHEAP",
                    "success": True,
                    "cost": 0.001,
                    "duration_ms": 100,
                }
            )
        for _i in range(10):
            entries.append(
                {
                    "workflow": "test",
                    "stage": "test",
                    "model": "low-success-model",
                    "tier": "CHEAP",
                    "success": False,
                    "cost": 0.001,
                    "duration_ms": 100,
                }
            )
        mock_telemetry.get_recent_entries.return_value = entries

        router = AdaptiveModelRouter(mock_telemetry)
        # With default min_success_rate=0.8, should fall back to default
        model = router.get_best_model(workflow="test", stage="test", min_success_rate=0.8)
        # Should return default model since no candidates meet threshold
        assert model is not None

    def test_get_best_model_filters_by_max_cost(self, mock_logger):
        """Test filters models above max_cost."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "stage": "test",
                "model": "expensive-model",
                "tier": "PREMIUM",
                "success": True,
                "cost": 0.5,  # Expensive
                "duration_ms": 100,
            }
            for _ in range(15)
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        model = router.get_best_model(workflow="test", stage="test", max_cost=0.01)  # Low budget
        # Should fall back to default due to cost constraint
        assert model is not None

    def test_get_best_model_filters_by_max_latency(self, mock_logger):
        """Test filters models above max_latency_ms."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "stage": "test",
                "model": "slow-model",
                "tier": "CAPABLE",
                "success": True,
                "cost": 0.01,
                "duration_ms": 5000,  # Slow
            }
            for _ in range(15)
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        model = router.get_best_model(
            workflow="test", stage="test", max_latency_ms=1000  # Fast requirement
        )
        # Should fall back to default due to latency constraint
        assert model is not None

    def test_get_best_model_insufficient_samples(self, mock_logger):
        """Test skips models with insufficient samples."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "stage": "test",
                "model": "rare-model",
                "tier": "CHEAP",
                "success": True,
                "cost": 0.001,
                "duration_ms": 100,
            }
            for _ in range(5)  # Below MIN_SAMPLE_SIZE
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        model = router.get_best_model(workflow="test", stage="test")
        # Should fall back to default due to insufficient samples
        assert model is not None


@pytest.mark.unit
class TestRecommendTierUpgrade:
    """Test recommend_tier_upgrade method."""

    def test_recommend_upgrade_insufficient_data(self):
        """Test returns False with insufficient data."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {"workflow": "test", "stage": "test", "success": True}
            for _ in range(5)  # Below MIN_SAMPLE_SIZE
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        should_upgrade, reason = router.recommend_tier_upgrade("test", "test")

        assert should_upgrade is False
        assert "Insufficient data" in reason

    def test_recommend_upgrade_high_failure_rate(self):
        """Test recommends upgrade with high failure rate."""
        mock_telemetry = MagicMock()
        # Recent entries with high failure rate (>20%)
        entries = [{"workflow": "test", "stage": "test", "success": True} for _ in range(10)]
        entries.extend([{"workflow": "test", "stage": "test", "success": False} for _ in range(10)])
        mock_telemetry.get_recent_entries.return_value = entries

        router = AdaptiveModelRouter(mock_telemetry)
        should_upgrade, reason = router.recommend_tier_upgrade("test", "test")

        assert should_upgrade is True
        assert "High failure rate" in reason

    def test_recommend_upgrade_low_failure_rate(self):
        """Test does not recommend upgrade with low failure rate."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {"workflow": "test", "stage": "test", "success": True} for _ in range(20)
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        should_upgrade, reason = router.recommend_tier_upgrade("test", "test")

        assert should_upgrade is False
        assert "Performance acceptable" in reason


@pytest.mark.unit
class TestGetRoutingStats:
    """Test get_routing_stats method."""

    def test_get_routing_stats_no_data(self):
        """Test returns empty stats with no data."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = []

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test-workflow")

        assert stats["models_used"] == []
        assert stats["total_calls"] == 0
        assert stats["avg_cost"] == 0.0
        assert stats["avg_success_rate"] == 0.0

    def test_get_routing_stats_with_data(self):
        """Test returns correct stats with data."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test-workflow",
                "stage": "analysis",
                "model": "model-a",
                "success": True,
                "cost": 0.01,
                "duration_ms": 200,
            },
            {
                "workflow": "test-workflow",
                "stage": "analysis",
                "model": "model-a",
                "success": True,
                "cost": 0.02,
                "duration_ms": 300,
            },
            {
                "workflow": "test-workflow",
                "stage": "synthesis",
                "model": "model-b",
                "success": False,
                "cost": 0.05,
                "duration_ms": 500,
            },
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test-workflow")

        assert stats["workflow"] == "test-workflow"
        assert stats["total_calls"] == 3
        assert "model-a" in stats["models_used"]
        assert "model-b" in stats["models_used"]
        assert stats["avg_cost"] == pytest.approx((0.01 + 0.02 + 0.05) / 3)
        assert stats["avg_success_rate"] == pytest.approx(2 / 3)

    def test_get_routing_stats_with_stage_filter(self):
        """Test filters by stage when specified."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "stage": "analysis",
                "model": "model-a",
                "success": True,
                "cost": 0.01,
                "duration_ms": 100,
            },
            {
                "workflow": "test",
                "stage": "synthesis",
                "model": "model-b",
                "success": True,
                "cost": 0.05,
                "duration_ms": 500,
            },
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test", stage="analysis")

        assert stats["stage"] == "analysis"
        assert stats["total_calls"] == 1
        assert stats["models_used"] == ["model-a"]

    def test_get_routing_stats_performance_by_model(self):
        """Test includes per-model performance breakdown."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {
                "workflow": "test",
                "stage": "test",
                "model": "fast-model",
                "success": True,
                "cost": 0.001,
                "duration_ms": 100,
            },
            {
                "workflow": "test",
                "stage": "test",
                "model": "fast-model",
                "success": True,
                "cost": 0.001,
                "duration_ms": 150,
            },
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        stats = router.get_routing_stats("test")

        assert "performance_by_model" in stats
        assert "fast-model" in stats["performance_by_model"]

        model_perf = stats["performance_by_model"]["fast-model"]
        assert model_perf["calls"] == 2
        assert model_perf["success_rate"] == 1.0
        assert model_perf["avg_cost"] == 0.001
        assert model_perf["avg_latency_ms"] == 125.0


@pytest.mark.unit
class TestAnalyzeModelPerformance:
    """Test _analyze_model_performance method."""

    def test_analyze_empty_entries(self):
        """Test analysis with no entries returns empty list."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = []

        router = AdaptiveModelRouter(mock_telemetry)
        performances = router._analyze_model_performance("test", "test")

        assert performances == []

    def test_analyze_multiple_models(self):
        """Test analysis with multiple models."""
        mock_telemetry = MagicMock()
        entries = [
            {
                "workflow": "test",
                "stage": "test",
                "model": "model-a",
                "tier": "CHEAP",
                "success": True,
                "cost": 0.001,
                "duration_ms": 100,
            }
            for _ in range(15)
        ]
        entries.extend(
            [
                {
                    "workflow": "test",
                    "stage": "test",
                    "model": "model-b",
                    "tier": "CAPABLE",
                    "success": True,
                    "cost": 0.01,
                    "duration_ms": 200,
                }
                for _ in range(15)
            ]
        )
        mock_telemetry.get_recent_entries.return_value = entries

        router = AdaptiveModelRouter(mock_telemetry)
        performances = router._analyze_model_performance("test", "test")

        assert len(performances) == 2
        model_ids = [p.model_id for p in performances]
        assert "model-a" in model_ids
        assert "model-b" in model_ids

    def test_analyze_calculates_metrics(self):
        """Test analysis calculates correct metrics."""
        mock_telemetry = MagicMock()
        # 8 successes, 2 failures = 80% success rate
        entries = []
        for _i in range(8):
            entries.append(
                {
                    "workflow": "test",
                    "stage": "test",
                    "model": "test-model",
                    "tier": "CHEAP",
                    "success": True,
                    "cost": 0.001,
                    "duration_ms": 100,
                }
            )
        for _i in range(2):
            entries.append(
                {
                    "workflow": "test",
                    "stage": "test",
                    "model": "test-model",
                    "tier": "CHEAP",
                    "success": False,
                    "cost": 0.001,
                    "duration_ms": 100,
                }
            )
        mock_telemetry.get_recent_entries.return_value = entries

        router = AdaptiveModelRouter(mock_telemetry)
        performances = router._analyze_model_performance("test", "test")

        assert len(performances) == 1
        perf = performances[0]
        assert perf.success_rate == 0.8
        assert perf.sample_size == 10
        assert perf.avg_cost == pytest.approx(0.001)
        assert perf.avg_latency_ms == pytest.approx(100.0)


@pytest.mark.unit
class TestGetWorkflowStageEntries:
    """Test _get_workflow_stage_entries method."""

    def test_filters_by_workflow(self):
        """Test filters entries by workflow."""
        mock_telemetry = MagicMock()
        mock_telemetry.get_recent_entries.return_value = [
            {"workflow": "target", "stage": "test"},
            {"workflow": "other", "stage": "test"},
            {"workflow": "target", "stage": "test"},
        ]

        router = AdaptiveModelRouter(mock_telemetry)
        entries = router._get_workflow_stage_entries("target", None, days=7)

        assert len(entries) == 2
        assert all(e["workflow"] == "target" for e in entries)

    def test_filters_by_stage(self):
        """Test filters entries by stage when specified."""
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


@pytest.mark.unit
class TestGetDefaultModel:
    """Test _get_default_model method."""

    def test_get_default_cheap(self):
        """Test default CHEAP tier model."""
        mock_telemetry = MagicMock()
        router = AdaptiveModelRouter(mock_telemetry)
        model = router._get_default_model("CHEAP")
        assert model is not None
        assert isinstance(model, str)

    def test_get_default_capable(self):
        """Test default CAPABLE tier model."""
        mock_telemetry = MagicMock()
        router = AdaptiveModelRouter(mock_telemetry)
        model = router._get_default_model("CAPABLE")
        assert model is not None

    def test_get_default_premium(self):
        """Test default PREMIUM tier model."""
        mock_telemetry = MagicMock()
        router = AdaptiveModelRouter(mock_telemetry)
        model = router._get_default_model("PREMIUM")
        assert model is not None

    def test_get_default_unknown_tier(self):
        """Test default model for unknown tier falls back to CHEAP."""
        mock_telemetry = MagicMock()
        router = AdaptiveModelRouter(mock_telemetry)
        model = router._get_default_model("UNKNOWN")
        # Should return a default model even for unknown tier
        assert model is not None


@pytest.mark.unit
class TestModuleExports:
    """Test module exports."""

    def test_all_exports(self):
        """Test __all__ exports are accessible."""
        from attune.models.adaptive_routing import __all__

        assert "AdaptiveModelRouter" in __all__
        assert "ModelPerformance" in __all__
