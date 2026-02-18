"""Unit tests for src/attune/workflows/routing.py

Tests cover:
- RoutingContext dataclass (construction, field types, equality)
- TierRoutingStrategy ABC (cannot instantiate directly, requires route + can_fallback)
- CostOptimizedRouting (complexity -> CHEAP/CAPABLE/PREMIUM, can_fallback)
- PerformanceOptimizedRouting (latency_sensitivity -> PREMIUM/CAPABLE, never fallback)
- BalancedRouting (budget ratio logic, requires total_budget constructor arg)
- Strategy pluggability and interchangeability

NOTE: complexity is a string ("simple" | "moderate" | "complex").
      latency_sensitivity is a string ("low" | "medium" | "high").
      ModelTier values are CHEAP, CAPABLE, PREMIUM (not SMALL/MEDIUM/LARGE).
"""

from __future__ import annotations

from abc import ABC
from dataclasses import fields

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.routing import (
    BalancedRouting,
    CostOptimizedRouting,
    PerformanceOptimizedRouting,
    RoutingContext,
    TierRoutingStrategy,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_context(**overrides) -> RoutingContext:
    """Return a RoutingContext with sensible defaults, overridable per-test."""
    defaults = {
        "task_type": "summarization",
        "input_size": 512,
        "complexity": "moderate",
        "budget_remaining": 10.0,
        "latency_sensitivity": "medium",
    }
    defaults.update(overrides)
    return RoutingContext(**defaults)


@pytest.fixture
def default_ctx():
    return make_context()


@pytest.fixture
def simple_ctx():
    return make_context(complexity="simple")


@pytest.fixture
def complex_ctx():
    return make_context(complexity="complex")


@pytest.fixture
def high_latency_ctx():
    return make_context(latency_sensitivity="high")


@pytest.fixture
def low_latency_ctx():
    return make_context(latency_sensitivity="low")


# ---------------------------------------------------------------------------
# ModelTier sanity checks
# ---------------------------------------------------------------------------


class TestModelTier:
    """Verify the ModelTier enum values used in routing."""

    def test_cheap_tier_exists(self):
        assert hasattr(ModelTier, "CHEAP")

    def test_capable_tier_exists(self):
        assert hasattr(ModelTier, "CAPABLE")

    def test_premium_tier_exists(self):
        assert hasattr(ModelTier, "PREMIUM")

    def test_tiers_are_distinct(self):
        assert ModelTier.CHEAP != ModelTier.CAPABLE
        assert ModelTier.CAPABLE != ModelTier.PREMIUM
        assert ModelTier.CHEAP != ModelTier.PREMIUM


# ---------------------------------------------------------------------------
# RoutingContext – dataclass contract
# ---------------------------------------------------------------------------


class TestRoutingContextConstruction:
    def test_basic_construction(self, default_ctx):
        assert default_ctx.task_type == "summarization"
        assert default_ctx.input_size == 512
        assert default_ctx.complexity == "moderate"
        assert default_ctx.budget_remaining == 10.0
        assert default_ctx.latency_sensitivity == "medium"

    def test_all_five_fields_present(self):
        field_names = {f.name for f in fields(RoutingContext)}
        expected = {
            "task_type",
            "input_size",
            "complexity",
            "budget_remaining",
            "latency_sensitivity",
        }
        assert expected == field_names

    def test_complexity_is_string(self, default_ctx):
        assert isinstance(default_ctx.complexity, str)

    def test_latency_sensitivity_is_string(self, default_ctx):
        assert isinstance(default_ctx.latency_sensitivity, str)

    def test_simple_complexity_accepted(self):
        ctx = make_context(complexity="simple")
        assert ctx.complexity == "simple"

    def test_moderate_complexity_accepted(self):
        ctx = make_context(complexity="moderate")
        assert ctx.complexity == "moderate"

    def test_complex_complexity_accepted(self):
        ctx = make_context(complexity="complex")
        assert ctx.complexity == "complex"

    def test_low_latency_accepted(self):
        assert make_context(latency_sensitivity="low").latency_sensitivity == "low"

    def test_medium_latency_accepted(self):
        assert make_context(latency_sensitivity="medium").latency_sensitivity == "medium"

    def test_high_latency_accepted(self):
        assert make_context(latency_sensitivity="high").latency_sensitivity == "high"

    def test_zero_budget_accepted(self):
        ctx = make_context(budget_remaining=0.0)
        assert ctx.budget_remaining == 0.0

    def test_large_input_size(self):
        ctx = make_context(input_size=1_000_000)
        assert ctx.input_size == 1_000_000

    def test_equality(self):
        a = make_context()
        b = make_context()
        assert a == b

    def test_inequality_on_single_field(self):
        a = make_context(complexity="simple")
        b = make_context(complexity="complex")
        assert a != b

    def test_repr_contains_field_names(self, default_ctx):
        r = repr(default_ctx)
        for name in (
            "task_type",
            "input_size",
            "complexity",
            "budget_remaining",
            "latency_sensitivity",
        ):
            assert name in r


# ---------------------------------------------------------------------------
# TierRoutingStrategy – ABC contract
# ---------------------------------------------------------------------------


class TestTierRoutingStrategyABC:
    def test_is_abstract_base_class(self):
        assert issubclass(TierRoutingStrategy, ABC)

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            TierRoutingStrategy()  # type: ignore[abstract]

    def test_route_is_abstract(self):
        abstract_methods = getattr(TierRoutingStrategy, "__abstractmethods__", set())
        assert "route" in abstract_methods

    def test_can_fallback_is_abstract(self):
        abstract_methods = getattr(TierRoutingStrategy, "__abstractmethods__", set())
        assert "can_fallback" in abstract_methods

    def test_concrete_subclass_must_implement_both_methods(self):
        class Incomplete(TierRoutingStrategy):
            def route(self, context: RoutingContext):
                return ModelTier.CAPABLE

            # missing can_fallback

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_subclass_with_both_methods_is_instantiable(self):
        class Complete(TierRoutingStrategy):
            def route(self, context: RoutingContext):
                return ModelTier.CAPABLE

            def can_fallback(self, tier: ModelTier) -> bool:
                return True

        strategy = Complete()
        assert strategy is not None


# ---------------------------------------------------------------------------
# CostOptimizedRouting
# ---------------------------------------------------------------------------


class TestCostOptimizedRouting:
    @pytest.fixture
    def strategy(self):
        return CostOptimizedRouting()

    def test_is_tier_routing_strategy(self, strategy):
        assert isinstance(strategy, TierRoutingStrategy)

    def test_simple_complexity_routes_to_cheap(self, strategy, simple_ctx):
        assert strategy.route(simple_ctx) == ModelTier.CHEAP

    def test_complex_complexity_routes_to_premium(self, strategy, complex_ctx):
        assert strategy.route(complex_ctx) == ModelTier.PREMIUM

    def test_moderate_complexity_routes_to_capable(self, strategy, default_ctx):
        assert strategy.route(default_ctx) == ModelTier.CAPABLE

    def test_route_returns_model_tier(self, strategy, default_ctx):
        result = strategy.route(default_ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_can_fallback_true_for_capable(self, strategy):
        assert strategy.can_fallback(ModelTier.CAPABLE) is True

    def test_can_fallback_true_for_premium(self, strategy):
        assert strategy.can_fallback(ModelTier.PREMIUM) is True

    def test_can_fallback_false_for_cheap(self, strategy):
        assert strategy.can_fallback(ModelTier.CHEAP) is False

    def test_deterministic_for_same_context(self, strategy, default_ctx):
        results = {strategy.route(default_ctx) for _ in range(10)}
        assert len(results) == 1


# ---------------------------------------------------------------------------
# PerformanceOptimizedRouting
# ---------------------------------------------------------------------------


class TestPerformanceOptimizedRouting:
    @pytest.fixture
    def strategy(self):
        return PerformanceOptimizedRouting()

    def test_is_tier_routing_strategy(self, strategy):
        assert isinstance(strategy, TierRoutingStrategy)

    def test_high_latency_routes_to_premium(self, strategy, high_latency_ctx):
        assert strategy.route(high_latency_ctx) == ModelTier.PREMIUM

    def test_medium_latency_routes_to_capable(self, strategy, default_ctx):
        assert strategy.route(default_ctx) == ModelTier.CAPABLE

    def test_low_latency_routes_to_capable(self, strategy, low_latency_ctx):
        assert strategy.route(low_latency_ctx) == ModelTier.CAPABLE

    def test_route_returns_model_tier(self, strategy, default_ctx):
        result = strategy.route(default_ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_can_fallback_always_false(self, strategy):
        """PerformanceOptimizedRouting never allows fallback."""
        for tier in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM):
            assert strategy.can_fallback(tier) is False

    def test_deterministic(self, strategy, default_ctx):
        assert strategy.route(default_ctx) == strategy.route(default_ctx)


# ---------------------------------------------------------------------------
# BalancedRouting
# ---------------------------------------------------------------------------


class TestBalancedRouting:
    @pytest.fixture
    def strategy(self):
        return BalancedRouting(total_budget=50.0)

    def test_is_tier_routing_strategy(self, strategy):
        assert isinstance(strategy, TierRoutingStrategy)

    def test_requires_total_budget_argument(self):
        with pytest.raises(TypeError):
            BalancedRouting()  # type: ignore[call-arg]

    def test_total_budget_must_be_positive(self):
        with pytest.raises(ValueError):
            BalancedRouting(total_budget=0)
        with pytest.raises(ValueError):
            BalancedRouting(total_budget=-5.0)

    def test_low_budget_ratio_routes_cheap(self):
        """budget_remaining / total_budget < 0.2 → CHEAP."""
        strategy = BalancedRouting(total_budget=100.0)
        ctx = make_context(budget_remaining=10.0, complexity="complex")  # ratio=0.1
        assert strategy.route(ctx) == ModelTier.CHEAP

    def test_high_budget_complex_task_routes_premium(self):
        """budget_ratio > 0.7 and complexity == 'complex' → PREMIUM."""
        strategy = BalancedRouting(total_budget=100.0)
        ctx = make_context(budget_remaining=80.0, complexity="complex")  # ratio=0.8
        assert strategy.route(ctx) == ModelTier.PREMIUM

    def test_high_budget_simple_task_routes_capable(self):
        """High budget with non-complex task → CAPABLE (not PREMIUM)."""
        strategy = BalancedRouting(total_budget=100.0)
        ctx = make_context(budget_remaining=80.0, complexity="simple")
        assert strategy.route(ctx) == ModelTier.CAPABLE

    def test_mid_budget_routes_capable(self):
        """Mid-range budget → CAPABLE (neither cheap nor premium boundary)."""
        strategy = BalancedRouting(total_budget=100.0)
        ctx = make_context(budget_remaining=50.0, complexity="moderate")  # ratio=0.5
        assert strategy.route(ctx) == ModelTier.CAPABLE

    def test_route_returns_model_tier(self, strategy, default_ctx):
        result = strategy.route(default_ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_can_fallback_always_true(self, strategy):
        """BalancedRouting always allows fallback."""
        for tier in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM):
            assert strategy.can_fallback(tier) is True

    def test_total_budget_stored(self):
        strategy = BalancedRouting(total_budget=42.0)
        assert strategy.total_budget == 42.0

    def test_deterministic(self, strategy, default_ctx):
        assert strategy.route(default_ctx) == strategy.route(default_ctx)


# ---------------------------------------------------------------------------
# Strategy pluggability / interchangeability
# ---------------------------------------------------------------------------


class TestStrategyPluggability:
    """All strategies must satisfy the same interface contract."""

    @pytest.fixture(
        params=[
            pytest.param(CostOptimizedRouting(), id="cost"),
            pytest.param(PerformanceOptimizedRouting(), id="performance"),
            pytest.param(BalancedRouting(total_budget=50.0), id="balanced"),
        ]
    )
    def any_strategy(self, request):
        return request.param

    def test_all_strategies_are_tier_routing_strategies(self, any_strategy):
        assert isinstance(any_strategy, TierRoutingStrategy)

    def test_all_strategies_have_route_method(self, any_strategy):
        assert callable(getattr(any_strategy, "route", None))

    def test_all_strategies_have_can_fallback_method(self, any_strategy):
        assert callable(getattr(any_strategy, "can_fallback", None))

    def test_all_strategies_return_valid_tier(self, any_strategy, default_ctx):
        result = any_strategy.route(default_ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_all_strategies_handle_simple_complexity(self, any_strategy):
        ctx = make_context(complexity="simple", budget_remaining=50.0)
        result = any_strategy.route(ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_all_strategies_handle_complex_complexity(self, any_strategy):
        ctx = make_context(complexity="complex", budget_remaining=50.0)
        result = any_strategy.route(ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_strategy_swap_in_router(self, any_strategy):
        """Strategies are interchangeable in a router-like container."""

        class Router:
            def __init__(self, strategy: TierRoutingStrategy):
                self.strategy = strategy

            def decide(self, ctx: RoutingContext) -> ModelTier:
                return self.strategy.route(ctx)

        router = Router(strategy=any_strategy)
        result = router.decide(make_context())
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_task_type_does_not_raise(self):
        strategy = CostOptimizedRouting()
        ctx = make_context(task_type="")
        result = strategy.route(ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_very_long_task_type_does_not_raise(self):
        strategy = CostOptimizedRouting()
        ctx = make_context(task_type="x" * 10_000)
        result = strategy.route(ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_zero_input_size_does_not_raise(self):
        strategy = CostOptimizedRouting()
        ctx = make_context(input_size=0)
        result = strategy.route(ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_very_large_budget_does_not_raise(self):
        strategy = BalancedRouting(total_budget=1_000_000.0)
        ctx = make_context(budget_remaining=999_999.0, complexity="complex")
        result = strategy.route(ctx)
        assert result in (ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM)

    def test_cost_optimized_simple_vs_complex(self):
        strategy = CostOptimizedRouting()
        simple = strategy.route(make_context(complexity="simple"))
        complex_ = strategy.route(make_context(complexity="complex"))
        tier_rank = {ModelTier.CHEAP: 0, ModelTier.CAPABLE: 1, ModelTier.PREMIUM: 2}
        assert tier_rank[simple] < tier_rank[complex_]
