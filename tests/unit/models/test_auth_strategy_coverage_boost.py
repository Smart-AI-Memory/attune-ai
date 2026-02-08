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
            assert strategy.subscription_tier == SubscriptionTier.API_ONLY

    def test_load_invalid_json_returns_default(self):
        """Test that loading invalid JSON returns default strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "invalid.json"
            filepath.write_text("{ invalid json }")

            strategy = AuthStrategy.load(filepath)

            # Should return default strategy
            assert isinstance(strategy, AuthStrategy)


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
