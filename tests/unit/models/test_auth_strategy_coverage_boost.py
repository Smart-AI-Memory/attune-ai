"""Coverage boost tests for models/auth_strategy.py

Targets uncovered authentication strategy logic and edge cases to increase
coverage from current baseline to 85%+.

Missing coverage areas:
- get_recommended_mode() logic for different tiers
- estimate_tokens() and estimate_cost() calculations
- get_pros_cons() recommendation logic
- Serialization (to_dict/from_dict)
- Persistence (save/load)
- Utility functions (count_lines_of_code, get_module_size_category)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.models.auth_strategy import (
    AuthMode,
    AuthStrategy,
    SubscriptionTier,
    count_lines_of_code,
    get_auth_strategy,
    get_module_size_category,
)


@pytest.mark.unit
class TestAuthStrategyRecommendedMode:
    """Test get_recommended_mode logic for different scenarios."""

    def test_pro_tier_recommends_api(self):
        """Test that Pro tier users are recommended to use API."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.PRO,
            default_mode=AuthMode.AUTO,
        )

        # Pro users should use API regardless of module size
        assert strategy.get_recommended_mode(100) == AuthMode.API
        assert strategy.get_recommended_mode(1000) == AuthMode.API
        assert strategy.get_recommended_mode(5000) == AuthMode.API

    def test_api_only_tier_returns_api(self):
        """Test that API-only users always get API mode."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.API_ONLY,
            default_mode=AuthMode.AUTO,
        )

        assert strategy.get_recommended_mode(100) == AuthMode.API
        assert strategy.get_recommended_mode(3000) == AuthMode.API

    def test_max_tier_small_module_uses_subscription(self):
        """Test that Max tier uses subscription for small modules."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.AUTO,
            small_module_threshold=500,
        )

        # Small module (< 500 LOC)
        assert strategy.get_recommended_mode(300) == AuthMode.SUBSCRIPTION

    def test_max_tier_medium_module_uses_subscription(self):
        """Test that Max tier uses subscription for medium modules."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.AUTO,
            small_module_threshold=500,
            medium_module_threshold=2000,
        )

        # Medium module (500-2000 LOC)
        assert strategy.get_recommended_mode(1000) == AuthMode.SUBSCRIPTION

    def test_max_tier_large_module_uses_api(self):
        """Test that Max tier uses API for large modules."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.AUTO,
            medium_module_threshold=2000,
        )

        # Large module (> 2000 LOC)
        assert strategy.get_recommended_mode(3000) == AuthMode.API

    def test_enterprise_tier_follows_max_logic(self):
        """Test that Enterprise tier follows same logic as Max."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.ENTERPRISE,
            default_mode=AuthMode.AUTO,
            small_module_threshold=500,
            medium_module_threshold=2000,
        )

        assert strategy.get_recommended_mode(300) == AuthMode.SUBSCRIPTION
        assert strategy.get_recommended_mode(1000) == AuthMode.SUBSCRIPTION
        assert strategy.get_recommended_mode(3000) == AuthMode.API

    def test_free_tier_small_module_uses_subscription(self):
        """Test that Free tier uses subscription for small modules."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.FREE,
            default_mode=AuthMode.AUTO,
            small_module_threshold=500,
        )

        assert strategy.get_recommended_mode(300) == AuthMode.SUBSCRIPTION

    def test_free_tier_large_module_uses_api(self):
        """Test that Free tier uses API for large modules."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.FREE,
            default_mode=AuthMode.AUTO,
            medium_module_threshold=2000,
        )

        assert strategy.get_recommended_mode(3000) == AuthMode.API

    def test_explicit_subscription_mode_overrides_auto(self):
        """Test that explicit SUBSCRIPTION mode overrides AUTO logic."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.PRO,
            default_mode=AuthMode.SUBSCRIPTION,  # Override
        )

        # Should return SUBSCRIPTION even though Pro would normally use API
        assert strategy.get_recommended_mode(100) == AuthMode.SUBSCRIPTION
        assert strategy.get_recommended_mode(5000) == AuthMode.SUBSCRIPTION

    def test_explicit_api_mode_overrides_auto(self):
        """Test that explicit API mode overrides AUTO logic."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.API,  # Override
        )

        # Should return API even for small modules
        assert strategy.get_recommended_mode(100) == AuthMode.API
        assert strategy.get_recommended_mode(500) == AuthMode.API


@pytest.mark.unit
class TestAuthStrategyTokenEstimation:
    """Test estimate_tokens method."""

    def test_estimate_tokens_default_multiplier(self):
        """Test token estimation with default multiplier."""
        strategy = AuthStrategy(loc_to_tokens_multiplier=4.0)

        # 100 lines * 4 tokens/line = 400 tokens
        assert strategy.estimate_tokens(100) == 400

    def test_estimate_tokens_custom_multiplier(self):
        """Test token estimation with custom multiplier."""
        strategy = AuthStrategy(loc_to_tokens_multiplier=5.0)

        # 100 lines * 5 tokens/line = 500 tokens
        assert strategy.estimate_tokens(100) == 500

    def test_estimate_tokens_large_module(self):
        """Test token estimation for large modules."""
        strategy = AuthStrategy(loc_to_tokens_multiplier=4.0)

        # 5000 lines * 4 tokens/line = 20,000 tokens
        assert strategy.estimate_tokens(5000) == 20000


@pytest.mark.unit
class TestAuthStrategyCostEstimation:
    """Test estimate_cost method."""

    def test_estimate_cost_subscription_mode(self):
        """Test cost estimation for subscription mode."""
        strategy = AuthStrategy(subscription_tier=SubscriptionTier.MAX)

        result = strategy.estimate_cost(1000, AuthMode.SUBSCRIPTION)

        assert result["mode"] == "subscription"
        assert result["tokens_used"] == 4000  # 1000 lines * 4
        assert result["monetary_cost"] == 0.0  # Included in subscription
        assert "quota_cost" in result
        assert "fits_in_context" in result

    def test_estimate_cost_api_mode(self):
        """Test cost estimation for API mode."""
        strategy = AuthStrategy()

        result = strategy.estimate_cost(1000, AuthMode.API)

        assert result["mode"] == "api"
        assert result["tokens_used"] == 4000
        assert "monetary_cost" in result
        assert result["monetary_cost"] > 0

    def test_estimate_cost_auto_mode_uses_recommended(self):
        """Test that AUTO mode uses get_recommended_mode."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.PRO,
            default_mode=AuthMode.AUTO,
        )

        # Pro tier should recommend API
        result = strategy.estimate_cost(1000, AuthMode.AUTO)

        assert result["mode"] == "api"

    def test_estimate_cost_none_mode_uses_recommended(self):
        """Test that None mode defaults to recommended mode."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.AUTO,
        )

        # Small module should use subscription
        result = strategy.estimate_cost(300, None)

        assert result["mode"] == "subscription"


@pytest.mark.unit
class TestAuthStrategyCostEstimationExactness:
    """Pin the cost-estimation contract the happy-path tests leave open.

    The existing cost tests assert ``> 0`` or key-membership only, so the
    per-tier cost constants, the ``fits_in_context`` thresholds, the
    ``int()`` truncation in ``estimate_tokens``, and the default
    ``mode=None`` parameter are never pinned. These are slice-2 mutation
    survivors (QA #2): a cost constant nudged, a ``200_000`` threshold
    bumped, or a ``<`` flipped to ``<=`` all pass the existing suite.

    Documented-equivalent mutant: ``round(total_api_cost, 4)`` ->
    ``round(..., 5)`` — both render ``0.0002`` for this total, so no input
    distinguishes them without weakening production code. Not chased.
    """

    def test_estimate_tokens_truncates_to_int(self):
        """``estimate_tokens`` returns a truncated ``int``, not a float.

        Kills an ``int()``-removal mutant: ``5 * 1.5 == 7.5`` would equal
        neither ``7`` nor pass the ``isinstance`` check.
        """
        strategy = AuthStrategy(loc_to_tokens_multiplier=1.5)

        tokens = strategy.estimate_tokens(5)

        assert tokens == 7  # int(7.5)
        assert isinstance(tokens, int)

    def test_estimate_cost_api_monetary_cost_is_exact(self):
        """API ``monetary_cost`` is the exact sum of the four tier constants.

        Kills mutants on any of the outline/write/polish/api_ref cost
        constants — the happy-path test only checks ``> 0``, which any
        nudged constant still satisfies.
        """
        strategy = AuthStrategy()

        result = strategy.estimate_cost(1000, AuthMode.API)

        # (tokens-in-millions) * ($/M input), summed across the four stages:
        # 0.003*0.25 + 0.015*3.0 + 0.010*15.0 + 0.005*0.25
        # = 0.00075 + 0.045 + 0.15 + 0.00125 = 0.197
        assert result["monetary_cost"] == 0.197
        assert result["quota_cost"] is None

    def test_estimate_cost_subscription_fits_in_context_boundary(self):
        """Subscription ``fits_in_context`` flips at the 200K-token boundary.

        Kills the ``200_000`` threshold constant and the ``<`` (vs ``<=``)
        boundary: at exactly 200_000 tokens (50_000 LOC * 4) it must be
        ``False``; one line under, ``True``.
        """
        strategy = AuthStrategy(loc_to_tokens_multiplier=4.0)

        assert strategy.estimate_cost(49_999, AuthMode.SUBSCRIPTION)["fits_in_context"] is True
        assert strategy.estimate_cost(50_000, AuthMode.SUBSCRIPTION)["fits_in_context"] is False

    def test_estimate_cost_api_fits_in_context_boundary(self):
        """API ``fits_in_context`` flips at the 1M-token boundary.

        Kills the ``1_000_000`` threshold constant and the ``<`` boundary:
        at exactly 1_000_000 tokens (250_000 LOC * 4) it must be ``False``.
        """
        strategy = AuthStrategy(loc_to_tokens_multiplier=4.0)

        assert strategy.estimate_cost(249_999, AuthMode.API)["fits_in_context"] is True
        assert strategy.estimate_cost(250_000, AuthMode.API)["fits_in_context"] is False

    def test_estimate_cost_default_mode_param_resolves_to_recommended(self):
        """Omitting ``mode`` resolves via ``get_recommended_mode`` (param default None).

        Pins the ``mode: AuthMode | None = None`` default and the
        ``if mode is None`` branch — called with no mode argument at all,
        a MAX-tier small module must route to subscription.
        """
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.AUTO,
        )

        result = strategy.estimate_cost(300)

        assert result["mode"] == "subscription"


@pytest.mark.unit
class TestAuthStrategyProsCons:
    """Test get_pros_cons recommendation logic."""

    def test_pros_cons_includes_all_modes(self):
        """Test that pros/cons includes subscription, api, and auto modes."""
        strategy = AuthStrategy(small_module_threshold=500)

        result = strategy.get_pros_cons(300)

        # Should have all three mode options
        assert "subscription" in result
        assert "api" in result
        assert "auto" in result

    def test_pros_cons_subscription_structure(self):
        """Test that subscription section has correct structure."""
        strategy = AuthStrategy()

        result = strategy.get_pros_cons(1000)

        subscription = result["subscription"]
        assert "name" in subscription
        assert "cost" in subscription
        assert "pros" in subscription
        assert "cons" in subscription
        assert "estimate" in subscription
        assert isinstance(subscription["pros"], list)
        assert isinstance(subscription["cons"], list)

    def test_pros_cons_api_structure(self):
        """Test that API section has correct structure."""
        strategy = AuthStrategy()

        result = strategy.get_pros_cons(1000)

        api = result["api"]
        assert "name" in api
        assert "cost" in api
        assert "pros" in api
        assert "cons" in api
        assert "estimate" in api
        assert isinstance(api["pros"], list)
        assert isinstance(api["cons"], list)

    def test_pros_cons_auto_includes_recommendation(self):
        """Test that auto mode includes current recommendation."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.PRO,
            default_mode=AuthMode.AUTO,
        )

        result = strategy.get_pros_cons(1000)

        auto = result["auto"]
        assert "estimate" in auto
        assert "current_recommendation" in auto["estimate"]
        # Pro tier recommends API
        assert auto["estimate"]["current_recommendation"] == "api"


@pytest.mark.unit
class TestAuthStrategyProsConsRendering:
    """Pin the data-bearing renders in get_pros_cons; document cosmetic ones.

    ``get_pros_cons`` is mostly descriptive copy. Per the slice-3 plan,
    the f-string *content* mutants (pro/con prose, section names, the
    "LOC) -> Subscription" boilerplate) are display text with no asserted
    contract — equivalent mutants, not chased. The genuinely killable
    survivors are:

    - dict-**key** drops/renames, especially in the ``auto`` section,
      which the happy-path ``TestAuthStrategyProsCons`` checks far less
      thoroughly than ``subscription`` / ``api``;
    - the ``auto.estimate`` ``mode`` key/value and a ``.value``-removal on
      ``current_recommendation`` (the enum subclasses ``str``, so an
      ``== "api"`` assertion alone would not catch it).

    The remaining tests are regression guards on the data-bearing
    interpolations (configured tier value, the two routing thresholds, the
    estimated monetary cost) — they ensure the user-facing guidance keeps
    reflecting real config even though mutmut's literal mutations cannot
    swap an interpolated expression.
    """

    def test_auto_section_has_full_structure(self):
        """The auto section carries the same keys as subscription/api.

        Kills key-drop/rename mutants on the auto section, which the
        happy-path suite only spot-checks for ``estimate``.
        """
        auto = AuthStrategy().get_pros_cons(1000)["auto"]

        for key in ("name", "cost", "pros", "cons", "estimate"):
            assert key in auto
        assert isinstance(auto["pros"], list)
        assert isinstance(auto["cons"], list)

    def test_auto_estimate_exposes_mode_and_typed_recommendation(self):
        """auto.estimate carries mode='auto' and a raw-string recommendation.

        Kills the ``"mode"`` key/value mutants and a ``.value``-removal on
        ``current_recommendation`` (``type(...) is str`` is required — the
        enum is a ``str`` subclass, so ``== "api"`` would pass on the enum).
        """
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.PRO,
            default_mode=AuthMode.AUTO,
        )

        estimate = strategy.get_pros_cons(1000)["auto"]["estimate"]

        assert estimate["mode"] == "auto"
        assert estimate["current_recommendation"] == "api"  # PRO -> API
        assert type(estimate["current_recommendation"]) is str

    def test_subscription_pros_reflect_configured_tier(self):
        """The subscription pros echo the configured tier's on-disk value.

        Regression guard: the ``f"Uses existing {tier.value} subscription"``
        line must keep reflecting real config.
        """
        pros = AuthStrategy(subscription_tier=SubscriptionTier.MAX).get_pros_cons(1000)[
            "subscription"
        ]["pros"]

        assert any("max" in pro for pro in pros)

    def test_auto_pros_reflect_routing_thresholds(self):
        """The auto guidance embeds the actual small/medium thresholds.

        Regression guard: user-facing routing guidance must match the real
        thresholds. With distinctive values, both must appear verbatim.
        """
        strategy = AuthStrategy(
            small_module_threshold=321,
            medium_module_threshold=654,
        )

        joined = " ".join(strategy.get_pros_cons(1000)["auto"]["pros"])

        assert "321" in joined
        assert "654" in joined

    def test_api_cost_reflects_estimated_monetary_cost(self):
        """The api 'cost' line echoes the estimated monetary cost.

        Regression guard: the displayed ``~$<cost> per module`` string
        stays tied to ``estimate.monetary_cost``.
        """
        api = AuthStrategy().get_pros_cons(1000)["api"]

        assert str(api["estimate"]["monetary_cost"]) in api["cost"]

    def test_both_estimate_subdicts_are_real_cost_dicts(self):
        """The subscription AND api sections embed their real cost estimates.

        Found by the closing mutmut refresh: ``sub_estimate = None`` in
        ``get_pros_cons`` survived because the suite asserted the *api*
        estimate but never the *subscription* one. Both sub-dicts must
        carry their mode-correct cost estimate (not None).
        """
        result = AuthStrategy().get_pros_cons(1000)

        assert result["subscription"]["estimate"]["mode"] == "subscription"
        assert result["api"]["estimate"]["mode"] == "api"


@pytest.mark.unit
class TestAuthStrategySerialization:
    """Test to_dict and from_dict methods."""

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict includes all configuration fields."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.AUTO,
            small_module_threshold=500,
            medium_module_threshold=2000,
            loc_to_tokens_multiplier=4.0,
            setup_completed=True,
            prefer_subscription=True,
            cost_optimization=True,
            metadata={"version": "1.0"},
        )

        data = strategy.to_dict()

        assert data["subscription_tier"] == "max"
        assert data["default_mode"] == "auto"
        assert data["small_module_threshold"] == 500
        assert data["medium_module_threshold"] == 2000
        assert data["loc_to_tokens_multiplier"] == 4.0
        assert data["setup_completed"] is True
        assert data["prefer_subscription"] is True
        assert data["cost_optimization"] is True
        assert data["metadata"] == {"version": "1.0"}

    def test_from_dict_restores_strategy(self):
        """Test that from_dict correctly restores AuthStrategy."""
        data = {
            "subscription_tier": "pro",
            "default_mode": "api",
            "small_module_threshold": 600,
            "medium_module_threshold": 2500,
            "loc_to_tokens_multiplier": 5.0,
            "setup_completed": True,
            "prefer_subscription": False,
            "cost_optimization": False,
            "metadata": {"test": "value"},
        }

        strategy = AuthStrategy.from_dict(data)

        assert strategy.subscription_tier == SubscriptionTier.PRO
        assert strategy.default_mode == AuthMode.API
        assert strategy.small_module_threshold == 600
        assert strategy.medium_module_threshold == 2500
        assert strategy.loc_to_tokens_multiplier == 5.0
        assert strategy.setup_completed is True
        assert strategy.prefer_subscription is False
        assert strategy.cost_optimization is False
        assert strategy.metadata == {"test": "value"}

    def test_round_trip_serialization(self):
        """Test that to_dict/from_dict round-trip works correctly."""
        original = AuthStrategy(
            subscription_tier=SubscriptionTier.ENTERPRISE,
            default_mode=AuthMode.SUBSCRIPTION,
            setup_completed=True,
            metadata={"custom_field": "custom_value"},
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = AuthStrategy.from_dict(data)

        # Should be equivalent
        assert restored.subscription_tier == original.subscription_tier
        assert restored.default_mode == original.default_mode
        assert restored.setup_completed == original.setup_completed
        assert restored.metadata == original.metadata


@pytest.mark.unit
class TestAuthStrategySerializationDefaults:
    """Pin the serialization contract that happy-path tests leave open.

    The existing serialization tests always pass explicit values, so the
    on-disk enum strings, the dataclass field defaults, and the
    ``from_dict`` ``.get()`` fallbacks are never asserted. These are the
    slice-1 mutation survivors (QA #2): an enum value flipped to ``None``,
    a ``500`` default bumped to ``501``, a ``True`` default flipped to
    ``False`` — all pass the happy-path suite. These tests close that gap.
    """

    def test_subscription_tier_enum_values_pinned(self):
        """Every SubscriptionTier on-disk string is exact (serialization key)."""
        assert SubscriptionTier.FREE.value == "free"
        assert SubscriptionTier.PRO.value == "pro"
        assert SubscriptionTier.MAX.value == "max"
        assert SubscriptionTier.ENTERPRISE.value == "enterprise"
        assert SubscriptionTier.API_ONLY.value == "api_only"

    def test_auth_mode_enum_values_pinned(self):
        """Every AuthMode on-disk string is exact (serialization key)."""
        assert AuthMode.SUBSCRIPTION.value == "subscription"
        assert AuthMode.API.value == "api"
        assert AuthMode.AUTO.value == "auto"

    def test_default_construction_pins_all_field_defaults(self):
        """A no-arg AuthStrategy uses the documented dataclass defaults.

        Kills mutants on the field defaults (e.g. ``500`` -> ``501``,
        ``True`` -> ``False``/``None``, ``4.0`` -> other), which the
        happy-path tests never exercise because they pass explicit values.
        """
        strategy = AuthStrategy()

        assert strategy.subscription_tier == SubscriptionTier.PRO
        assert strategy.default_mode == AuthMode.AUTO
        assert strategy.small_module_threshold == 500
        assert strategy.medium_module_threshold == 2000
        assert strategy.loc_to_tokens_multiplier == 4.0
        assert strategy.setup_completed is True
        assert strategy.prefer_subscription is True
        assert strategy.cost_optimization is True
        assert strategy.metadata == {}

    def test_default_metadata_is_fresh_per_instance(self):
        """``metadata`` default_factory yields an independent dict per instance."""
        first = AuthStrategy()
        second = AuthStrategy()

        first.metadata["touched"] = True

        assert second.metadata == {}

    def test_from_dict_empty_uses_documented_defaults(self):
        """``from_dict({})`` falls back to every documented ``.get()`` default.

        Kills mutants on the ``.get(key, DEFAULT)`` fallbacks in
        ``from_dict`` — these are unreachable when the input dict already
        carries every key (as the happy-path test does).
        """
        strategy = AuthStrategy.from_dict({})

        assert strategy.subscription_tier == SubscriptionTier.PRO
        assert strategy.default_mode == AuthMode.AUTO
        assert strategy.small_module_threshold == 500
        assert strategy.medium_module_threshold == 2000
        assert strategy.loc_to_tokens_multiplier == 4.0
        assert strategy.setup_completed is True
        assert strategy.prefer_subscription is True
        assert strategy.cost_optimization is True
        assert strategy.metadata == {}

    def test_to_dict_emits_json_serializable_strings_not_enums(self):
        """``to_dict`` emits raw strings (via ``.value``) that survive JSON.

        ``type(...) is str`` kills a ``.value``-removal mutant (the enum is
        a ``str`` subclass, so ``== "..."`` alone would not catch it). The
        JSON round-trip pins the API_ONLY / SUBSCRIPTION on-disk strings
        through the ``to_dict`` path specifically.
        """
        data = AuthStrategy(
            subscription_tier=SubscriptionTier.API_ONLY,
            default_mode=AuthMode.SUBSCRIPTION,
        ).to_dict()

        assert type(data["subscription_tier"]) is str
        assert type(data["default_mode"]) is str

        reloaded = json.loads(json.dumps(data))
        assert reloaded["subscription_tier"] == "api_only"
        assert reloaded["default_mode"] == "subscription"


@pytest.mark.unit
class TestAuthStrategyPersistence:
    """Test save and load methods."""

    def test_save_creates_file(self):
        """Test that save creates JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "auth_strategy.json"

            strategy = AuthStrategy(
                subscription_tier=SubscriptionTier.MAX,
                default_mode=AuthMode.AUTO,
            )

            strategy.save(filepath)

            assert filepath.exists()

    def test_save_writes_owner_only_file_in_private_dir(self):
        """Regression: config is 0600 inside a 0700 dir (no co-tenant reads)."""
        import sys

        if sys.platform == "win32":
            pytest.skip("POSIX file modes")
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "telemetry" / "auth_strategy.json"

            AuthStrategy().save(filepath)

            assert (filepath.stat().st_mode & 0o777) == 0o600
            assert (filepath.parent.stat().st_mode & 0o777) == 0o700
            # No leftover temp file from the atomic write.
            assert not list(filepath.parent.glob(".auth_strategy.*.tmp"))

    def test_save_creates_parent_directories(self):
        """Test that save creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "nested" / "dir" / "auth_strategy.json"

            strategy = AuthStrategy()
            strategy.save(filepath)

            assert filepath.exists()
            assert filepath.parent.exists()

    def test_save_writes_valid_json(self):
        """Test that save writes valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "auth_strategy.json"

            strategy = AuthStrategy(subscription_tier=SubscriptionTier.PRO)
            strategy.save(filepath)

            # Should be valid JSON
            with open(filepath) as f:
                data = json.load(f)

            assert data["subscription_tier"] == "pro"

    def test_load_reads_saved_strategy(self):
        """Test that load correctly reads saved strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "auth_strategy.json"

            # Save strategy
            original = AuthStrategy(
                subscription_tier=SubscriptionTier.MAX,
                default_mode=AuthMode.API,
                setup_completed=True,
            )
            original.save(filepath)

            # Load strategy
            loaded = AuthStrategy.load(filepath)

            assert loaded.subscription_tier == SubscriptionTier.MAX
            assert loaded.default_mode == AuthMode.API
            assert loaded.setup_completed is True

    def test_load_nonexistent_file_returns_default(self):
        """Test that loading nonexistent file returns default strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "does_not_exist.json"

            strategy = AuthStrategy.load(filepath)

            # Should return default strategy
            assert isinstance(strategy, AuthStrategy)
            assert strategy.subscription_tier == SubscriptionTier.PRO

    def test_load_invalid_json_returns_default(self):
        """Test that loading invalid JSON returns default strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "invalid.json"
            filepath.write_text("{ invalid json }")

            strategy = AuthStrategy.load(filepath)

            # Should return default strategy
            assert isinstance(strategy, AuthStrategy)


@pytest.mark.unit
class TestAuthStrategyPersistenceDefaultPath:
    """Pin load()'s default-path branch and full disk round-trip fidelity.

    The existing persistence tests cover ``save()``'s default-path branch
    and ``load()`` with EXPLICIT paths, but ``load(None)`` — the
    ``if path is None: path = AUTH_STRATEGY_FILE`` branch and its
    interaction with the ``.exists()`` guard — is never asserted against a
    known file. That is the slice-4 survivor (QA #2). Every test patches
    ``AUTH_STRATEGY_FILE`` so the real ``~/.attune/auth_strategy.json`` is
    never read or written (mechanics note: a mutant can otherwise clobber
    real user state).

    Documented-equivalent (cosmetic, not chased): the ``json.dump``
    ``indent`` value and the load-failure ``logger.warning`` message /
    ``exc_info`` flag — none carry an asserted contract.
    """

    def test_load_default_path_reads_auth_strategy_file(self, tmp_path):
        """``load()`` with no arg reads AUTH_STRATEGY_FILE, not a fresh default.

        Kills the ``path is None`` branch and the ``.exists()`` guard: with
        a populated file present, the loaded tier/mode must be the saved
        MAX/API, not the PRO/AUTO default.
        """
        target = tmp_path / "auth_strategy.json"
        AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.API,
        ).save(target)

        with patch("attune.models.auth_strategy.AUTH_STRATEGY_FILE", target):
            loaded = AuthStrategy.load()

        assert loaded.subscription_tier == SubscriptionTier.MAX
        assert loaded.default_mode == AuthMode.API

    def test_load_default_path_missing_file_returns_default(self, tmp_path):
        """``load()`` falls back to a fresh default when the file is absent."""
        missing = tmp_path / "absent.json"

        with patch("attune.models.auth_strategy.AUTH_STRATEGY_FILE", missing):
            loaded = AuthStrategy.load()

        assert loaded.subscription_tier == SubscriptionTier.PRO  # dataclass default
        assert loaded.default_mode == AuthMode.AUTO

    def test_save_default_path_writes_serialized_content(self, tmp_path):
        """``save(None)`` serializes through ``to_dict`` into AUTH_STRATEGY_FILE.

        Kills the save ``path is None`` branch and confirms the on-disk
        payload is the real serialization (not just that a file appears).
        """
        target = tmp_path / "auth_strategy.json"
        strategy = AuthStrategy(subscription_tier=SubscriptionTier.ENTERPRISE)

        with patch("attune.models.auth_strategy.AUTH_STRATEGY_FILE", target):
            strategy.save(path=None)

        assert json.loads(target.read_text())["subscription_tier"] == "enterprise"

    def test_save_load_round_trip_preserves_every_field(self, tmp_path):
        """A full save -> load disk round-trip preserves every configured field.

        The existing round-trip test only checks tier/mode/setup_completed;
        this pins the thresholds, multiplier, the three booleans, and
        metadata through the JSON persistence path.
        """
        target = tmp_path / "auth_strategy.json"
        original = AuthStrategy(
            subscription_tier=SubscriptionTier.ENTERPRISE,
            default_mode=AuthMode.SUBSCRIPTION,
            small_module_threshold=123,
            medium_module_threshold=456,
            loc_to_tokens_multiplier=7.5,
            setup_completed=False,
            prefer_subscription=False,
            cost_optimization=False,
            metadata={"k": "v"},
        )
        original.save(target)

        loaded = AuthStrategy.load(target)

        assert loaded.subscription_tier == SubscriptionTier.ENTERPRISE
        assert loaded.default_mode == AuthMode.SUBSCRIPTION
        assert loaded.small_module_threshold == 123
        assert loaded.medium_module_threshold == 456
        assert loaded.loc_to_tokens_multiplier == 7.5
        assert loaded.setup_completed is False
        assert loaded.prefer_subscription is False
        assert loaded.cost_optimization is False
        assert loaded.metadata == {"k": "v"}


@pytest.mark.unit
class TestGetAuthStrategy:
    """Test get_auth_strategy function."""

    @patch("attune.models.auth_strategy.configure_auth_interactive")
    def test_get_auth_strategy_loads_from_home(self, mock_interactive):
        """Test that get_auth_strategy loads from home directory."""
        # Prevent interactive prompt in CI (no stdin available)
        mock_interactive.return_value = AuthStrategy()
        strategy = get_auth_strategy()

        assert isinstance(strategy, AuthStrategy)

    @patch("attune.models.auth_strategy.configure_auth_interactive")
    def test_get_auth_strategy_returns_default_if_not_configured(self, mock_interactive):
        """Test that get_auth_strategy returns default if not configured."""
        # Prevent interactive prompt in CI (no stdin available)
        mock_interactive.return_value = AuthStrategy()
        strategy = get_auth_strategy()

        assert isinstance(strategy, AuthStrategy)
        assert hasattr(strategy, "subscription_tier")
        assert hasattr(strategy, "default_mode")


@pytest.mark.unit
class TestCountLinesOfCode:
    """Test count_lines_of_code utility function."""

    def test_count_lines_empty_file(self):
        """Test counting lines in empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            filepath = f.name

        try:
            count = count_lines_of_code(filepath)
            assert count == 0
        finally:
            Path(filepath).unlink()

    def test_count_lines_simple_file(self):
        """Test counting lines in simple file (excludes comments and blank lines)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# Comment\n")  # EXCLUDED (comment)
            f.write("print('hello')\n")  # COUNTED
            f.write("\n")  # EXCLUDED (blank)
            f.write("def foo():\n")  # COUNTED
            f.write("    pass\n")  # COUNTED
            filepath = f.name

        try:
            count = count_lines_of_code(filepath)
            # Only 3 lines counted (excludes comment and blank line)
            assert count == 3
        finally:
            Path(filepath).unlink()

    def test_count_lines_accepts_path_object(self):
        """Test that count_lines_of_code accepts Path objects."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("line 1\n")
            f.write("line 2\n")
            filepath = Path(f.name)

        try:
            count = count_lines_of_code(filepath)
            assert count == 2
        finally:
            filepath.unlink()

    def test_count_lines_nonexistent_file_returns_zero(self):
        """Test that nonexistent file returns 0."""
        count = count_lines_of_code("/nonexistent/file.py")
        assert count == 0


@pytest.mark.unit
class TestGetModuleSizeCategory:
    """Test get_module_size_category utility function."""

    def test_categorize_small_module(self):
        """Test categorizing small modules."""
        # Default: < 500 = small
        assert get_module_size_category(100) == "small"
        assert get_module_size_category(499) == "small"

    def test_categorize_medium_module(self):
        """Test categorizing medium modules."""
        # Default: 500-1999 = medium (2000+ is large)
        assert get_module_size_category(500) == "medium"
        assert get_module_size_category(1000) == "medium"
        assert get_module_size_category(1999) == "medium"

    def test_categorize_large_module(self):
        """Test categorizing large modules."""
        # Default: > 2000 = large
        assert get_module_size_category(2001) == "large"
        assert get_module_size_category(5000) == "large"

    def test_categorize_boundary_at_2000(self):
        """Test that exactly 2000 lines is categorized as large."""
        # Default thresholds: < 500 = small, 500-1999 = medium, >= 2000 = large
        assert get_module_size_category(1999) == "medium"
        assert get_module_size_category(2000) == "large"  # Boundary case
        assert get_module_size_category(2001) == "large"


@pytest.mark.unit
class TestAuthStrategyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_strategy_with_zero_lines(self):
        """Test strategy behavior with zero lines."""
        strategy = AuthStrategy()

        # Should still return a valid mode
        mode = strategy.get_recommended_mode(0)
        assert mode in [AuthMode.API, AuthMode.SUBSCRIPTION]

    def test_strategy_at_exact_threshold_boundaries(self):
        """Test behavior at exact threshold boundaries."""
        strategy = AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.AUTO,
            small_module_threshold=500,
            medium_module_threshold=2000,
        )

        # At boundaries (>= medium_module_threshold goes to API)
        assert strategy.get_recommended_mode(500) == AuthMode.SUBSCRIPTION
        assert strategy.get_recommended_mode(1999) == AuthMode.SUBSCRIPTION
        assert strategy.get_recommended_mode(2000) == AuthMode.API  # Exactly at threshold
        assert strategy.get_recommended_mode(2001) == AuthMode.API

    def test_metadata_field_is_mutable(self):
        """Test that metadata field can be modified."""
        strategy = AuthStrategy()

        strategy.metadata["custom_key"] = "custom_value"

        assert strategy.metadata["custom_key"] == "custom_value"


# =============================================================================
# Branch-coverage additions — targets previously-uncovered lines
# =============================================================================


class TestAuthStrategySaveBranch:
    """AuthStrategy.save() default path (line 274)."""

    def test_save_uses_default_path_when_none(self, tmp_path):
        from attune.models.auth_strategy import AuthStrategy

        strategy = AuthStrategy()
        custom = tmp_path / "auth_strategy.json"
        with patch("attune.models.auth_strategy.AUTH_STRATEGY_FILE", custom):
            strategy.save(path=None)
        assert custom.exists()


class TestConfigureAuthInteractive:
    """configure_auth_interactive — all print/input paths (lines 317-394)."""

    def _run_with_inputs(self, inputs, module_lines=100):
        from attune.models.auth_strategy import configure_auth_interactive

        with (
            patch("builtins.input", side_effect=inputs),
            patch("attune.models.auth_strategy.AuthStrategy.save"),
        ):
            return configure_auth_interactive(module_lines=module_lines)

    def test_subscription_mode_chosen(self):
        strategy = self._run_with_inputs(["2", "1"])  # Pro tier, Subscription mode
        from attune.models.auth_strategy import AuthMode, SubscriptionTier

        assert strategy.default_mode == AuthMode.SUBSCRIPTION
        assert strategy.subscription_tier == SubscriptionTier.PRO

    def test_api_mode_chosen(self):
        strategy = self._run_with_inputs(["5", "2"])  # API_ONLY tier, API mode
        from attune.models.auth_strategy import AuthMode

        assert strategy.default_mode == AuthMode.API

    def test_auto_mode_chosen(self):
        strategy = self._run_with_inputs(["3", "3"])  # Max tier, Auto mode
        from attune.models.auth_strategy import AuthMode

        assert strategy.default_mode == AuthMode.AUTO

    def test_invalid_tier_defaults_to_api_only(self):
        strategy = self._run_with_inputs(["99", "3"])  # Bad tier, Auto mode
        from attune.models.auth_strategy import SubscriptionTier

        assert strategy.subscription_tier == SubscriptionTier.API_ONLY

    def test_invalid_mode_defaults_to_auto(self):
        strategy = self._run_with_inputs(["1", "99"])  # Free tier, bad mode
        from attune.models.auth_strategy import AuthMode

        assert strategy.default_mode == AuthMode.AUTO

    def test_enterprise_tier(self):
        strategy = self._run_with_inputs(["4", "3"])
        from attune.models.auth_strategy import SubscriptionTier

        assert strategy.subscription_tier == SubscriptionTier.ENTERPRISE

    def test_free_tier(self):
        strategy = self._run_with_inputs(["1", "3"])
        from attune.models.auth_strategy import SubscriptionTier

        assert strategy.subscription_tier == SubscriptionTier.FREE


@pytest.mark.unit
class TestConfigureAuthInteractiveContract:
    """Pin the non-print behavioral outputs of configure_auth_interactive.

    The existing ``TestConfigureAuthInteractive`` covers ``tier_map`` /
    ``mode_map`` routing thoroughly (including the invalid-choice
    defaults). The slice-5 survivors it leaves open are the parts that are
    NOT display copy: the returned strategy is marked
    ``setup_completed=True``, the raw ``input()`` is ``.strip()``-ed before
    lookup (so stray whitespace still routes), and the chosen
    configuration is persisted via ``save()``.

    Documented-equivalent (cosmetic, not chased): the banner / pros-cons /
    recommendation ``print`` statements, the ``default_mode == AUTO``
    threshold-print branch, and the ``module_lines=1000`` display default —
    all output text with no asserted contract.
    """

    def _run(self, inputs, module_lines=100):
        from attune.models.auth_strategy import configure_auth_interactive

        with (
            patch("builtins.input", side_effect=inputs),
            patch("attune.models.auth_strategy.AuthStrategy.save") as mock_save,
        ):
            strategy = configure_auth_interactive(module_lines=module_lines)
        return strategy, mock_save

    def test_setup_is_marked_completed(self):
        """Interactive setup returns a strategy with setup_completed=True.

        Kills a ``setup_completed=True`` -> ``False`` mutant in the final
        construction — the whole point of setup is to mark it done.
        """
        strategy, _ = self._run(["3", "3"])

        assert strategy.setup_completed is True

    def test_input_is_stripped_before_lookup(self):
        """Whitespace-padded choices still route (raw input is .strip()-ed).

        Kills a ``.strip()``-removal mutant: ``" 3 "`` would miss the
        tier_map and fall back to API_ONLY instead of mapping to MAX.
        """
        strategy, _ = self._run([" 3 ", " 1 "])  # Max tier, Subscription mode

        assert strategy.subscription_tier == SubscriptionTier.MAX
        assert strategy.default_mode == AuthMode.SUBSCRIPTION

    def test_configuration_is_persisted(self):
        """Setup persists the chosen strategy via save().

        Regression guard: interactive setup must write the choice to disk,
        not just return it in memory.
        """
        _, mock_save = self._run(["2", "3"])

        mock_save.assert_called_once()


class TestCountNonBlankLines:
    """count_lines_of_code exception paths (lines 436-442)."""

    def test_counts_non_blank_lines(self, tmp_path):
        from attune.models.auth_strategy import count_lines_of_code

        f = tmp_path / "mod.py"
        f.write_text("line1\n\n# comment\nline2\n")
        result = count_lines_of_code(f)
        assert result == 2

    def test_fallback_on_first_read_error(self, tmp_path):
        from attune.models.auth_strategy import count_lines_of_code

        f = tmp_path / "mod.py"
        f.write_text("a\nb\nc\n")
        call_count = [0]
        original_open = open

        def selective_open(path, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("disk error")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=selective_open):
            result = count_lines_of_code(f)
        assert result == 3

    def test_returns_zero_when_both_reads_fail(self, tmp_path):
        from attune.models.auth_strategy import count_lines_of_code

        f = tmp_path / "mod.py"
        f.write_text("data")
        with patch("builtins.open", side_effect=OSError("no access")):
            result = count_lines_of_code(f)
        assert result == 0


@pytest.mark.unit
class TestAuthStrategyPreferSubscriptionRouting:
    """prefer_subscription routing — the spend-routing dimension the existing
    suite never exercised (every prior test left prefer_subscription at its
    True default).

    With prefer_subscription=False the small branch (SUBSCRIPTION) and the
    medium branch (API) diverge, which is what makes the
    small_module_threshold boundary observable: a value exactly at the
    threshold pins the comparison as strict ``<`` rather than ``<=``. Without
    these tests, ``module_lines < self.small_module_threshold`` could be
    weakened to ``<=`` undetected (mutmut survivor on auth_strategy.py:108).
    """

    @staticmethod
    def _max_auto(*, prefer: bool) -> AuthStrategy:
        return AuthStrategy(
            subscription_tier=SubscriptionTier.MAX,
            default_mode=AuthMode.AUTO,
            small_module_threshold=500,
            medium_module_threshold=2000,
            prefer_subscription=prefer,
        )

    def test_small_threshold_boundary_is_strict_less_than(self):
        """module_lines == small_threshold must fall through to the medium
        branch, not the small branch.

        499 takes the small branch (always SUBSCRIPTION); 500 is NOT < 500 and
        falls to the medium branch, which routes to API when
        prefer_subscription is False. If ``<`` were ``<=``, 500 would route to
        SUBSCRIPTION instead.
        """
        strategy = self._max_auto(prefer=False)
        assert strategy.get_recommended_mode(499) == AuthMode.SUBSCRIPTION
        assert strategy.get_recommended_mode(500) == AuthMode.API

    def test_medium_range_routes_to_api_when_prefer_subscription_false(self):
        """Medium modules route to API when the user does not prefer
        subscription (exercises the previously-dead ``else AuthMode.API``
        branch on line 114)."""
        strategy = self._max_auto(prefer=False)
        assert strategy.get_recommended_mode(1000) == AuthMode.API
        assert strategy.get_recommended_mode(1999) == AuthMode.API

    def test_medium_range_routes_to_subscription_when_prefer_subscription_true(self):
        """Medium modules route to SUBSCRIPTION when prefer_subscription is
        True (the True arm of the same ternary)."""
        strategy = self._max_auto(prefer=True)
        assert strategy.get_recommended_mode(1000) == AuthMode.SUBSCRIPTION
        assert strategy.get_recommended_mode(1999) == AuthMode.SUBSCRIPTION

    def test_prefer_subscription_only_gates_the_medium_range(self):
        """prefer_subscription must not change small (always SUBSCRIPTION) or
        large (always API) routing — only the medium range."""
        strategy = self._max_auto(prefer=False)
        assert strategy.get_recommended_mode(100) == AuthMode.SUBSCRIPTION
        assert strategy.get_recommended_mode(3000) == AuthMode.API
