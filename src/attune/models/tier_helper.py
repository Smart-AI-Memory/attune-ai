"""Tier Fallback Helper for Simple Tier-Based Logic

Provides convenience methods for tier progression and fallback
decisions. Used for simple tier-based fallback scenarios.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""


class TierFallbackHelper:
    """Helper class for simple tier-based fallback logic.

    Provides convenience methods for Sprint 1 tests while preserving
    the sophisticated FallbackPolicy for production use.

    Example:
        >>> TierFallbackHelper.get_next_tier("cheap")
        'capable'
        >>> TierFallbackHelper.should_fallback(TimeoutError(), "cheap")
        True
        >>> TierFallbackHelper.should_fallback(ValueError(), "premium")
        False

    """

    TIER_PROGRESSION = {
        "cheap": "capable",
        "capable": "premium",
        "premium": "ultra",
        "ultra": None,
    }

    @classmethod
    def get_next_tier(cls, current_tier: str) -> str | None:
        """Get next tier in fallback chain.

        Args:
            current_tier: Current tier name (cheap, capable, premium)

        Returns:
            Next tier name, or None if at highest tier

        Example:
            >>> TierFallbackHelper.get_next_tier("cheap")
            'capable'
            >>> TierFallbackHelper.get_next_tier("premium")
            None

        """
        return cls.TIER_PROGRESSION.get(current_tier)

    @classmethod
    def should_fallback(cls, error: Exception, tier: str) -> bool:
        """Determine if fallback should be attempted.

        Args:
            error: Exception that was raised
            tier: Current tier that failed

        Returns:
            True if fallback should be attempted, False otherwise

        Logic:
            - Never fallback from ultra tier (highest tier)
            - Fallback for network/connection errors
              (TimeoutError, ConnectionError, OSError)
            - Don't fallback for logic errors
              (ValueError, TypeError, etc.)

        Example:
            >>> TierFallbackHelper.should_fallback(
            ...     TimeoutError(), "cheap"
            ... )
            True
            >>> TierFallbackHelper.should_fallback(
            ...     ValueError(), "cheap"
            ... )
            False
            >>> TierFallbackHelper.should_fallback(
            ...     TimeoutError(), "ultra"
            ... )
            False

        """
        # Never fallback from ultra tier (highest tier)
        if tier == "ultra":
            return False

        # Fallback for connection/network errors
        fallback_errors = (TimeoutError, ConnectionError, OSError)
        return isinstance(error, fallback_errors)
