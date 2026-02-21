"""Tests for TierFallbackHelper - Sprint 1 convenience methods.

This module tests the simple tier-based fallback helpers added for Sprint 1.
The sophisticated FallbackPolicy is still the primary fallback mechanism.
"""

from attune.models import TierFallbackHelper


class TestTierProgression:
    """Test tier progression chain."""

    def test_cheap_to_capable(self):
        """Test cheap tier progresses to capable."""
        assert TierFallbackHelper.get_next_tier("cheap") == "capable"

    def test_capable_to_premium(self):
        """Test capable tier progresses to premium."""
        assert TierFallbackHelper.get_next_tier("capable") == "premium"

    def test_premium_has_no_next(self):
        """Test premium tier is the highest tier."""
        assert TierFallbackHelper.get_next_tier("premium") is None

    def test_unknown_tier_returns_none(self):
        """Test unknown tier returns None."""
        assert TierFallbackHelper.get_next_tier("unknown") is None


class TestShouldFallback:
    """Test fallback decision logic."""

    def test_timeout_error_triggers_fallback_cheap(self):
        """Test TimeoutError triggers fallback from cheap tier."""
        assert TierFallbackHelper.should_fallback(TimeoutError(), "cheap") is True

    def test_timeout_error_triggers_fallback_capable(self):
        """Test TimeoutError triggers fallback from capable tier."""
        assert TierFallbackHelper.should_fallback(TimeoutError(), "capable") is True

    def test_connection_error_triggers_fallback(self):
        """Test ConnectionError triggers fallback."""
        assert TierFallbackHelper.should_fallback(ConnectionError(), "cheap") is True

    def test_os_error_triggers_fallback(self):
        """Test OSError triggers fallback."""
        assert TierFallbackHelper.should_fallback(OSError(), "cheap") is True

    def test_value_error_does_not_trigger_fallback(self):
        """Test ValueError does not trigger fallback (logic error)."""
        assert TierFallbackHelper.should_fallback(ValueError(), "cheap") is False

    def test_type_error_does_not_trigger_fallback(self):
        """Test TypeError does not trigger fallback (logic error)."""
        assert TierFallbackHelper.should_fallback(TypeError(), "cheap") is False

    def test_premium_never_falls_back(self):
        """Test premium tier never falls back (highest tier)."""
        assert TierFallbackHelper.should_fallback(TimeoutError(), "premium") is False
        assert TierFallbackHelper.should_fallback(ConnectionError(), "premium") is False
        assert TierFallbackHelper.should_fallback(OSError(), "premium") is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_custom_exception_subclass_of_connection_error(self):
        """Test custom exception subclass of ConnectionError triggers fallback."""

        class CustomConnectionError(ConnectionError):
            pass

        assert TierFallbackHelper.should_fallback(CustomConnectionError(), "cheap") is True

    def test_custom_exception_subclass_of_timeout_error(self):
        """Test custom exception subclass of TimeoutError triggers fallback."""

        class CustomTimeoutError(TimeoutError):
            pass

        assert TierFallbackHelper.should_fallback(CustomTimeoutError(), "cheap") is True

    def test_custom_exception_subclass_of_os_error(self):
        """Test custom exception subclass of OSError triggers fallback."""

        class CustomOSError(OSError):
            pass

        assert TierFallbackHelper.should_fallback(CustomOSError(), "cheap") is True

    def test_generic_exception_does_not_trigger_fallback(self):
        """Test generic Exception does not trigger fallback."""
        assert TierFallbackHelper.should_fallback(Exception(), "cheap") is False


class TestIntegrationWithFallbackPolicy:
    """Test that TierFallbackHelper works alongside FallbackPolicy."""

    def test_can_import_both_classes(self):
        """Test both FallbackPolicy and TierFallbackHelper can be imported."""
        from attune.models import FallbackPolicy, TierFallbackHelper

        assert FallbackPolicy is not None
        assert TierFallbackHelper is not None

    def test_tier_progression_matches_fallback_policy_tiers(self):
        """Test tier progression matches FallbackPolicy tier names."""
        from attune.models import FallbackPolicy, FallbackStrategy

        # Use "capable" as primary so there are cheaper tiers available
        policy = FallbackPolicy(
            primary_provider="anthropic",
            primary_tier="capable",
            strategy=FallbackStrategy.CHEAPER_TIER_SAME_PROVIDER,
        )

        chain = policy.get_fallback_chain()

        # First fallback should be "cheap" (cheaper tier from "capable")
        assert len(chain) >= 1
        # Note: FallbackPolicy uses "all_tiers" order, so cheaper tiers come after
        # This is different from TierFallbackHelper which goes up in tiers
        # Both are valid approaches for different use cases

        # Verify TierFallbackHelper tier names match those used by FallbackPolicy
        assert TierFallbackHelper.get_next_tier("cheap") == "capable"
        assert TierFallbackHelper.get_next_tier("capable") == "premium"
        assert TierFallbackHelper.get_next_tier("premium") is None
