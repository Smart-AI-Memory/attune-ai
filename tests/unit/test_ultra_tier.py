"""Unit tests for the ultra tier (Opus 4.6 with 1M context window).

Tests cover:
- ModelTier.ULTRA enum value
- MODEL_REGISTRY ultra entry with correct pricing and beta headers
- Ultra task types and routing
- TierFallbackHelper progression
- RoutingConfig ultra fields
- ModelRouter ultra integration
- Workflow routing strategy context-based escalation
"""

import pytest

from attune.config.sections.routing import RoutingConfig
from attune.models.registry import (
    MODEL_REGISTRY,
    TIER_PRICING,
    ModelInfo,
    ModelRegistry,
    ModelTier,
)
from attune.models.tasks import (
    ULTRA_TASKS,
    TaskType,
    get_all_tasks,
    get_tasks_for_tier,
    get_tier_for_task,
)
from attune.models.tier_helper import TierFallbackHelper
from attune.routing.model_router import ModelRouter


@pytest.mark.unit
class TestModelTierUltra:
    """Test ModelTier enum includes ULTRA."""

    def test_ultra_enum_exists(self):
        """Test that ModelTier.ULTRA exists with correct value."""
        assert ModelTier.ULTRA.value == "ultra"

    def test_all_tiers_present(self):
        """Test all four tiers are defined."""
        tier_values = {t.value for t in ModelTier}
        assert tier_values == {"cheap", "capable", "premium", "ultra"}


@pytest.mark.unit
class TestModelRegistryUltra:
    """Test MODEL_REGISTRY ultra entry."""

    def test_ultra_entry_exists(self):
        """Test that MODEL_REGISTRY has an ultra entry for anthropic."""
        assert "ultra" in MODEL_REGISTRY["anthropic"]

    def test_ultra_model_id(self):
        """Test ultra uses claude-opus-4-6 model ID."""
        ultra = MODEL_REGISTRY["anthropic"]["ultra"]
        assert ultra.id == "claude-opus-4-6"

    def test_ultra_pricing(self):
        """Test ultra long-context pricing is correct."""
        ultra = MODEL_REGISTRY["anthropic"]["ultra"]
        assert ultra.input_cost_per_million == 10.00
        assert ultra.output_cost_per_million == 37.50

    def test_ultra_max_tokens(self):
        """Test ultra supports 128K output tokens."""
        ultra = MODEL_REGISTRY["anthropic"]["ultra"]
        assert ultra.max_tokens == 128_000

    def test_ultra_context_window(self):
        """Test ultra has 1M context window."""
        ultra = MODEL_REGISTRY["anthropic"]["ultra"]
        assert ultra.context_window == 1_000_000

    def test_ultra_beta_headers(self):
        """Test ultra has the required beta header."""
        ultra = MODEL_REGISTRY["anthropic"]["ultra"]
        assert ultra.beta_headers is not None
        assert "anthropic-beta" in ultra.beta_headers
        assert ultra.beta_headers["anthropic-beta"] == "context-1m-2025-08-07"

    def test_premium_has_no_beta_headers(self):
        """Test premium tier does not have beta headers."""
        premium = MODEL_REGISTRY["anthropic"]["premium"]
        assert premium.beta_headers is None

    def test_premium_default_context_window(self):
        """Test premium defaults to 200K context."""
        premium = MODEL_REGISTRY["anthropic"]["premium"]
        assert premium.context_window == 200_000

    def test_ultra_supports_vision_and_tools(self):
        """Test ultra supports vision and tool use."""
        ultra = MODEL_REGISTRY["anthropic"]["ultra"]
        assert ultra.supports_vision is True
        assert ultra.supports_tools is True


@pytest.mark.unit
class TestModelRegistryClassUltra:
    """Test ModelRegistry class handles ultra tier."""

    def test_get_model_ultra(self):
        """Test get_model returns ultra entry."""
        registry = ModelRegistry()
        model = registry.get_model("anthropic", "ultra")
        assert model is not None
        assert model.tier == "ultra"
        assert model.context_window == 1_000_000

    def test_list_tiers_includes_ultra(self):
        """Test list_tiers includes ultra."""
        registry = ModelRegistry()
        tiers = registry.list_tiers()
        assert "ultra" in tiers

    def test_get_models_by_tier_ultra(self):
        """Test get_models_by_tier returns ultra models."""
        registry = ModelRegistry()
        ultra_models = registry.get_models_by_tier("ultra")
        assert len(ultra_models) == 1
        assert ultra_models[0].tier == "ultra"


@pytest.mark.unit
class TestTierPricingUltra:
    """Test TIER_PRICING includes ultra."""

    def test_ultra_pricing_entry(self):
        """Test TIER_PRICING has ultra with correct values."""
        assert "ultra" in TIER_PRICING
        assert TIER_PRICING["ultra"]["input"] == 10.00
        assert TIER_PRICING["ultra"]["output"] == 37.50


@pytest.mark.unit
class TestUltraTaskTypes:
    """Test ultra-tier task types."""

    def test_ultra_tasks_defined(self):
        """Test ULTRA_TASKS frozenset is defined with four tasks."""
        assert len(ULTRA_TASKS) == 4
        assert "whole_repo_review" in ULTRA_TASKS
        assert "cross_module_analysis" in ULTRA_TASKS
        assert "full_codebase_refactor" in ULTRA_TASKS
        assert "deep_context_reasoning" in ULTRA_TASKS

    def test_task_type_enum_values(self):
        """Test TaskType enum has ultra task entries."""
        assert TaskType.WHOLE_REPO_REVIEW.value == "whole_repo_review"
        assert TaskType.CROSS_MODULE_ANALYSIS.value == "cross_module_analysis"
        assert TaskType.FULL_CODEBASE_REFACTOR.value == "full_codebase_refactor"
        assert TaskType.DEEP_CONTEXT_REASONING.value == "deep_context_reasoning"

    def test_get_tier_for_ultra_tasks(self):
        """Test all ultra tasks route to ULTRA tier."""
        for task in ULTRA_TASKS:
            tier = get_tier_for_task(task)
            assert tier == ModelTier.ULTRA, f"Task {task} should route to ULTRA"

    def test_get_tasks_for_ultra_tier(self):
        """Test get_tasks_for_tier returns ultra tasks."""
        tasks = get_tasks_for_tier(ModelTier.ULTRA)
        assert len(tasks) == 4
        assert set(tasks) == set(ULTRA_TASKS)

    def test_get_all_tasks_includes_ultra(self):
        """Test get_all_tasks includes ultra key."""
        all_tasks = get_all_tasks()
        assert "ultra" in all_tasks
        assert len(all_tasks["ultra"]) == 4


@pytest.mark.unit
class TestTierFallbackHelperUltra:
    """Test TierFallbackHelper with ultra tier."""

    def test_premium_progresses_to_ultra(self):
        """Test premium tier progresses to ultra."""
        assert TierFallbackHelper.get_next_tier("premium") == "ultra"

    def test_ultra_has_no_next_tier(self):
        """Test ultra is the highest tier (no progression)."""
        assert TierFallbackHelper.get_next_tier("ultra") is None

    def test_ultra_falls_back_on_network_errors(self):
        """Test that ultra falls back to premium on network errors."""
        assert TierFallbackHelper.should_fallback(TimeoutError(), "ultra") is True
        assert TierFallbackHelper.should_fallback(ConnectionError(), "ultra") is True

    def test_ultra_does_not_fallback_on_logic_errors(self):
        """Test that ultra does not fall back on logic errors."""
        assert TierFallbackHelper.should_fallback(ValueError(), "ultra") is False

    def test_should_fallback_from_premium(self):
        """Test that fallback is allowed from premium (to ultra)."""
        assert TierFallbackHelper.should_fallback(TimeoutError(), "premium") is True

    def test_full_progression_chain(self):
        """Test the full tier progression: cheap -> capable -> premium -> ultra."""
        assert TierFallbackHelper.get_next_tier("cheap") == "capable"
        assert TierFallbackHelper.get_next_tier("capable") == "premium"
        assert TierFallbackHelper.get_next_tier("premium") == "ultra"
        assert TierFallbackHelper.get_next_tier("ultra") is None


@pytest.mark.unit
class TestRoutingConfigUltra:
    """Test RoutingConfig ultra fields."""

    def test_ultra_defaults(self):
        """Test RoutingConfig has correct ultra defaults."""
        config = RoutingConfig()
        assert config.ultra_model == "claude-opus-4-6"
        assert config.max_tokens_ultra == 128_000
        assert config.ultra_enabled is False
        assert config.ultra_beta_header == "context-1m-2025-08-07"

    def test_ultra_in_to_dict(self):
        """Test ultra fields are serialized."""
        config = RoutingConfig()
        d = config.to_dict()
        assert "ultra_model" in d
        assert "max_tokens_ultra" in d
        assert "ultra_enabled" in d
        assert "ultra_beta_header" in d

    def test_ultra_from_dict(self):
        """Test ultra fields are deserialized."""
        data = {
            "ultra_model": "claude-opus-4-6",
            "max_tokens_ultra": 128_000,
            "ultra_enabled": True,
            "ultra_beta_header": "context-1m-2025-08-07",
        }
        config = RoutingConfig.from_dict(data)
        assert config.ultra_enabled is True
        assert config.max_tokens_ultra == 128_000

    def test_default_tier_accepts_ultra(self):
        """Test default_tier can be set to ultra."""
        config = RoutingConfig(default_tier="ultra")
        assert config.default_tier == "ultra"


@pytest.mark.unit
class TestModelRouterUltra:
    """Test ModelRouter with ultra tier."""

    def test_route_ultra_task(self):
        """Test routing an ultra task returns claude-opus-4-6."""
        router = ModelRouter()
        model_id = router.route("whole_repo_review")
        assert model_id == "claude-opus-4-6"

    def test_route_cross_module_analysis(self):
        """Test routing cross_module_analysis to ultra."""
        router = ModelRouter()
        model_id = router.route("cross_module_analysis")
        assert model_id == "claude-opus-4-6"

    def test_compare_costs_includes_ultra(self):
        """Test compare_costs includes ultra tier."""
        router = ModelRouter()
        costs = router.compare_costs("whole_repo_review", 500_000, 10_000)
        assert "ultra" in costs
        # Ultra cost: 500k/1M * $10 + 10k/1M * $37.50
        expected = (500_000 / 1_000_000) * 10.00 + (10_000 / 1_000_000) * 37.50
        assert abs(costs["ultra"] - expected) < 0.01

    def test_get_all_tasks_includes_ultra(self):
        """Test get_all_tasks returns ultra tasks."""
        tasks = ModelRouter.get_all_tasks()
        assert "ultra" in tasks
        assert len(tasks["ultra"]) == 4

    def test_ultra_tier_enum(self):
        """Test ModelRouter's ModelTier includes ULTRA."""
        from attune.routing.model_router import ModelTier as RouterModelTier

        assert RouterModelTier.ULTRA.value == "ultra"


@pytest.mark.unit
class TestWorkflowRoutingUltra:
    """Test workflow routing strategies escalate to ultra for large context."""

    def test_cost_optimized_escalates_to_ultra(self):
        """Test CostOptimizedRouting routes to ULTRA for >200K when enabled."""
        from attune.workflows.routing import CostOptimizedRouting, RoutingContext

        strategy = CostOptimizedRouting()
        context = RoutingContext(
            task_type="review",
            input_size=250_000,
            complexity="complex",
            budget_remaining=100.0,
            latency_sensitivity="low",
            ultra_enabled=True,
        )
        tier = strategy.route(context)
        assert tier.value == "ultra"

    def test_cost_optimized_falls_back_to_premium_without_ultra(self):
        """Test CostOptimizedRouting falls back to PREMIUM when ultra disabled."""
        from attune.workflows.routing import CostOptimizedRouting, RoutingContext

        strategy = CostOptimizedRouting()
        context = RoutingContext(
            task_type="review",
            input_size=250_000,
            complexity="complex",
            budget_remaining=100.0,
            latency_sensitivity="low",
            ultra_enabled=False,
        )
        tier = strategy.route(context)
        assert tier.value == "premium"

    def test_cost_optimized_stays_premium_under_200k(self):
        """Test CostOptimizedRouting stays at PREMIUM under 200K."""
        from attune.workflows.routing import CostOptimizedRouting, RoutingContext

        strategy = CostOptimizedRouting()
        context = RoutingContext(
            task_type="review",
            input_size=150_000,
            complexity="complex",
            budget_remaining=100.0,
            latency_sensitivity="low",
        )
        tier = strategy.route(context)
        assert tier.value == "premium"

    def test_performance_optimized_escalates_to_ultra(self):
        """Test PerformanceOptimizedRouting routes to ULTRA for >200K when enabled."""
        from attune.workflows.routing import (
            PerformanceOptimizedRouting,
            RoutingContext,
        )

        strategy = PerformanceOptimizedRouting()
        context = RoutingContext(
            task_type="review",
            input_size=300_000,
            complexity="moderate",
            budget_remaining=100.0,
            latency_sensitivity="high",
            ultra_enabled=True,
        )
        tier = strategy.route(context)
        assert tier.value == "ultra"

    def test_performance_optimized_falls_back_to_premium_without_ultra(self):
        """Test PerformanceOptimizedRouting falls back to PREMIUM when ultra disabled."""
        from attune.workflows.routing import (
            PerformanceOptimizedRouting,
            RoutingContext,
        )

        strategy = PerformanceOptimizedRouting()
        context = RoutingContext(
            task_type="review",
            input_size=300_000,
            complexity="moderate",
            budget_remaining=100.0,
            latency_sensitivity="high",
            ultra_enabled=False,
        )
        tier = strategy.route(context)
        assert tier.value == "premium"

    def test_balanced_escalates_to_ultra(self):
        """Test BalancedRouting routes to ULTRA for >200K when enabled."""
        from attune.workflows.routing import BalancedRouting, RoutingContext

        strategy = BalancedRouting(total_budget=100.0)
        context = RoutingContext(
            task_type="review",
            input_size=500_000,
            complexity="complex",
            budget_remaining=80.0,
            latency_sensitivity="low",
            ultra_enabled=True,
        )
        tier = strategy.route(context)
        assert tier.value == "ultra"

    def test_balanced_falls_back_to_premium_without_ultra(self):
        """Test BalancedRouting falls back to PREMIUM when ultra disabled."""
        from attune.workflows.routing import BalancedRouting, RoutingContext

        strategy = BalancedRouting(total_budget=100.0)
        context = RoutingContext(
            task_type="review",
            input_size=500_000,
            complexity="complex",
            budget_remaining=80.0,
            latency_sensitivity="low",
            ultra_enabled=False,
        )
        tier = strategy.route(context)
        assert tier.value == "premium"

    def test_ultra_enabled_defaults_to_false(self):
        """Test RoutingContext defaults ultra_enabled to False (safe default)."""
        from attune.workflows.routing import CostOptimizedRouting, RoutingContext

        strategy = CostOptimizedRouting()
        context = RoutingContext(
            task_type="review",
            input_size=250_000,
            complexity="complex",
            budget_remaining=100.0,
            latency_sensitivity="low",
        )
        # Default ultra_enabled=False should route to premium, not ultra
        tier = strategy.route(context)
        assert tier.value == "premium"


@pytest.mark.unit
class TestModelInfoBetaHeaders:
    """Test ModelInfo beta_headers field."""

    def test_default_beta_headers_is_none(self):
        """Test ModelInfo defaults to no beta headers."""
        info = ModelInfo(
            id="test-model",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=5.0,
        )
        assert info.beta_headers is None

    def test_default_context_window(self):
        """Test ModelInfo defaults to 200K context window."""
        info = ModelInfo(
            id="test-model",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=5.0,
        )
        assert info.context_window == 200_000

    def test_custom_beta_headers(self):
        """Test ModelInfo with custom beta headers."""
        info = ModelInfo(
            id="test-model",
            provider="anthropic",
            tier="ultra",
            input_cost_per_million=10.0,
            output_cost_per_million=37.5,
            context_window=1_000_000,
            beta_headers={"anthropic-beta": "test-feature"},
        )
        assert info.beta_headers == {"anthropic-beta": "test-feature"}
        assert info.context_window == 1_000_000
