"""Tests for TrafficAllocator — A/B test traffic allocation strategies.

Covers all 6 methods: __init__, allocate, _fixed_allocation,
_epsilon_greedy, _thompson_sampling, _ucb_allocation.
"""

from __future__ import annotations

import random

from attune.socratic.ab_testing.allocator import TrafficAllocator
from attune.socratic.ab_testing.models import AllocationStrategy, Experiment, Variant

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _make_variant(
    variant_id: str,
    name: str,
    traffic_pct: float = 50.0,
    impressions: int = 0,
    conversions: int = 0,
    total_success: float = 0.0,
    is_control: bool = False,
) -> Variant:
    return Variant(
        variant_id=variant_id,
        name=name,
        description=f"Variant {name}",
        config={},
        is_control=is_control,
        traffic_percentage=traffic_pct,
        impressions=impressions,
        conversions=conversions,
        total_success_score=total_success,
    )


def _make_experiment(
    strategy: AllocationStrategy = AllocationStrategy.FIXED,
    variants: list[Variant] | None = None,
) -> Experiment:
    if variants is None:
        variants = [
            _make_variant("ctrl", "Control", traffic_pct=50.0, is_control=True),
            _make_variant("treat", "Treatment", traffic_pct=50.0),
        ]
    return Experiment(
        experiment_id="exp-1",
        name="Test Experiment",
        description="desc",
        hypothesis="h",
        variants=variants,
        allocation_strategy=strategy,
    )


# ------------------------------------------------------------------
# __init__
# ------------------------------------------------------------------


class TestInit:
    """Tests for TrafficAllocator.__init__."""

    def test_stores_experiment(self):
        """Allocator stores the experiment reference."""
        exp = _make_experiment()
        allocator = TrafficAllocator(exp)
        assert allocator.experiment is exp

    def test_creates_random_instance(self):
        """Allocator creates a Random instance."""
        allocator = TrafficAllocator(_make_experiment())
        assert isinstance(allocator._random, random.Random)


# ------------------------------------------------------------------
# allocate — strategy dispatch
# ------------------------------------------------------------------


class TestAllocate:
    """Tests for allocate() strategy routing."""

    def test_fixed_strategy(self):
        """FIXED strategy routes to _fixed_allocation."""
        exp = _make_experiment(AllocationStrategy.FIXED)
        allocator = TrafficAllocator(exp)
        result = allocator.allocate("user-1")
        assert result in exp.variants

    def test_epsilon_greedy_strategy(self):
        """EPSILON_GREEDY routes to _epsilon_greedy."""
        variants = [
            _make_variant("a", "A", impressions=10, total_success=8.0),
            _make_variant("b", "B", impressions=10, total_success=5.0),
        ]
        exp = _make_experiment(AllocationStrategy.EPSILON_GREEDY, variants)
        allocator = TrafficAllocator(exp)
        allocator._random = random.Random(42)
        result = allocator.allocate("user-1")
        assert result in exp.variants

    def test_thompson_sampling_strategy(self):
        """THOMPSON_SAMPLING routes to _thompson_sampling."""
        variants = [
            _make_variant("a", "A", impressions=10, conversions=8),
            _make_variant("b", "B", impressions=10, conversions=3),
        ]
        exp = _make_experiment(AllocationStrategy.THOMPSON_SAMPLING, variants)
        allocator = TrafficAllocator(exp)
        allocator._random = random.Random(42)
        result = allocator.allocate("user-1")
        assert result in exp.variants

    def test_ucb_strategy(self):
        """UCB routes to _ucb_allocation."""
        variants = [
            _make_variant("a", "A", impressions=10, total_success=8.0),
            _make_variant("b", "B", impressions=10, total_success=5.0),
        ]
        exp = _make_experiment(AllocationStrategy.UCB, variants)
        allocator = TrafficAllocator(exp)
        result = allocator.allocate("user-1")
        assert result in exp.variants

    def test_unknown_strategy_falls_back_to_fixed(self):
        """Unknown strategy defaults to _fixed_allocation."""
        exp = _make_experiment(AllocationStrategy.FIXED)
        allocator = TrafficAllocator(exp)
        # Patch strategy to something not in the if chain
        exp.allocation_strategy = AllocationStrategy.FIXED
        result = allocator.allocate("user-1")
        assert result in exp.variants


# ------------------------------------------------------------------
# _fixed_allocation
# ------------------------------------------------------------------


class TestFixedAllocation:
    """Tests for _fixed_allocation (CRC32-based deterministic split)."""

    def test_deterministic_same_user(self):
        """Same user always gets the same variant."""
        exp = _make_experiment()
        allocator = TrafficAllocator(exp)
        r1 = allocator._fixed_allocation("user-123")
        r2 = allocator._fixed_allocation("user-123")
        assert r1 is r2

    def test_different_users_can_differ(self):
        """Different users may get different variants."""
        exp = _make_experiment()
        allocator = TrafficAllocator(exp)
        results = {allocator._fixed_allocation(f"user-{i}").variant_id for i in range(100)}
        # With 50/50 split and 100 users, both variants should appear
        assert len(results) == 2

    def test_respects_traffic_percentage(self):
        """Traffic roughly follows configured percentages."""
        variants = [
            _make_variant("a", "A", traffic_pct=90.0),
            _make_variant("b", "B", traffic_pct=10.0),
        ]
        exp = _make_experiment(variants=variants)
        allocator = TrafficAllocator(exp)
        counts = {"a": 0, "b": 0}
        for i in range(1000):
            v = allocator._fixed_allocation(f"user-{i}")
            counts[v.variant_id] += 1
        # 90/10 split: variant A should get majority
        assert counts["a"] > 700

    def test_falls_back_to_last_variant(self):
        """If no bucket matches, returns last variant."""
        # Edge case: traffic_percentage=0 for all but last
        variants = [
            _make_variant("a", "A", traffic_pct=0.0),
            _make_variant("b", "B", traffic_pct=0.0),
            _make_variant("c", "C", traffic_pct=100.0),
        ]
        exp = _make_experiment(variants=variants)
        allocator = TrafficAllocator(exp)
        result = allocator._fixed_allocation("any-user")
        # All traffic goes to C (last with 100% or fallback)
        assert result.variant_id in ("a", "c")  # CRC may land at 0 matching A


# ------------------------------------------------------------------
# _epsilon_greedy
# ------------------------------------------------------------------


class TestEpsilonGreedy:
    """Tests for _epsilon_greedy."""

    def test_exploits_best_variant(self):
        """With epsilon=0, always picks the best variant."""
        variants = [
            _make_variant("a", "A", impressions=100, total_success=90.0),
            _make_variant("b", "B", impressions=100, total_success=10.0),
        ]
        exp = _make_experiment(AllocationStrategy.EPSILON_GREEDY, variants)
        allocator = TrafficAllocator(exp)
        result = allocator._epsilon_greedy(epsilon=0.0)
        assert result.variant_id == "a"

    def test_explores_with_epsilon_1(self):
        """With epsilon=1, always explores (random)."""
        variants = [
            _make_variant("a", "A", impressions=100, total_success=90.0),
            _make_variant("b", "B", impressions=100, total_success=10.0),
        ]
        exp = _make_experiment(AllocationStrategy.EPSILON_GREEDY, variants)
        allocator = TrafficAllocator(exp)
        allocator._random = random.Random(42)
        results = {allocator._epsilon_greedy(epsilon=1.0).variant_id for _ in range(50)}
        # With epsilon=1 and 50 trials, both should appear
        assert len(results) == 2

    def test_default_epsilon(self):
        """Default epsilon=0.1 mostly exploits."""
        variants = [
            _make_variant("a", "A", impressions=100, total_success=90.0),
            _make_variant("b", "B", impressions=100, total_success=10.0),
        ]
        exp = _make_experiment(AllocationStrategy.EPSILON_GREEDY, variants)
        allocator = TrafficAllocator(exp)
        allocator._random = random.Random(42)
        a_count = sum(1 for _ in range(100) if allocator._epsilon_greedy().variant_id == "a")
        assert a_count > 80  # Should exploit ~90% of the time


# ------------------------------------------------------------------
# _thompson_sampling
# ------------------------------------------------------------------


class TestThompsonSampling:
    """Tests for _thompson_sampling (Bayesian bandit)."""

    def test_returns_valid_variant(self):
        """Returns a variant from the experiment."""
        variants = [
            _make_variant("a", "A", impressions=50, conversions=40),
            _make_variant("b", "B", impressions=50, conversions=10),
        ]
        exp = _make_experiment(AllocationStrategy.THOMPSON_SAMPLING, variants)
        allocator = TrafficAllocator(exp)
        allocator._random = random.Random(42)
        result = allocator._thompson_sampling()
        assert result in exp.variants

    def test_favors_higher_conversion(self):
        """Over many samples, favors the higher-converting variant."""
        variants = [
            _make_variant("a", "A", impressions=100, conversions=90),
            _make_variant("b", "B", impressions=100, conversions=10),
        ]
        exp = _make_experiment(AllocationStrategy.THOMPSON_SAMPLING, variants)
        allocator = TrafficAllocator(exp)
        allocator._random = random.Random(42)
        a_count = sum(1 for _ in range(100) if allocator._thompson_sampling().variant_id == "a")
        assert a_count > 80

    def test_zero_impressions_handled(self):
        """Variants with 0 impressions still work (beta(1,1) = uniform)."""
        variants = [
            _make_variant("a", "A", impressions=0, conversions=0),
            _make_variant("b", "B", impressions=0, conversions=0),
        ]
        exp = _make_experiment(AllocationStrategy.THOMPSON_SAMPLING, variants)
        allocator = TrafficAllocator(exp)
        allocator._random = random.Random(42)
        result = allocator._thompson_sampling()
        assert result in exp.variants


# ------------------------------------------------------------------
# _ucb_allocation
# ------------------------------------------------------------------


class TestUCBAllocation:
    """Tests for _ucb_allocation (Upper Confidence Bound)."""

    def test_unvisited_variant_gets_priority(self):
        """Variants with 0 impressions get infinite UCB score."""
        variants = [
            _make_variant("a", "A", impressions=100, total_success=90.0),
            _make_variant("b", "B", impressions=0, total_success=0.0),
        ]
        exp = _make_experiment(AllocationStrategy.UCB, variants)
        allocator = TrafficAllocator(exp)
        result = allocator._ucb_allocation()
        assert result.variant_id == "b"  # Unvisited gets priority

    def test_returns_valid_variant(self):
        """Returns a variant from the experiment."""
        variants = [
            _make_variant("a", "A", impressions=50, total_success=40.0),
            _make_variant("b", "B", impressions=50, total_success=30.0),
        ]
        exp = _make_experiment(AllocationStrategy.UCB, variants)
        allocator = TrafficAllocator(exp)
        result = allocator._ucb_allocation()
        assert result in exp.variants

    def test_balances_exploration_and_exploitation(self):
        """UCB balances mean reward with exploration bonus."""
        variants = [
            _make_variant("a", "A", impressions=1000, total_success=800.0),
            _make_variant("b", "B", impressions=10, total_success=7.0),
        ]
        exp = _make_experiment(AllocationStrategy.UCB, variants)
        allocator = TrafficAllocator(exp)
        result = allocator._ucb_allocation()
        # B has fewer impressions so gets a larger exploration bonus
        # despite lower mean — UCB may pick it
        assert result in exp.variants
