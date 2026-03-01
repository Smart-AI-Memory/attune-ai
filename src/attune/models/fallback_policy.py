"""Fallback Policy Definitions for Multi-Model Workflows

Core types for defining fallback chains and strategies:
- FallbackStrategy: Enum of fallback selection strategies
- FallbackStep: A single step in a fallback chain
- FallbackPolicy: Complete fallback configuration

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from enum import Enum

from .registry import get_model


class FallbackStrategy(Enum):
    """Strategies for selecting fallback models."""

    # Try same tier with different provider
    SAME_TIER_DIFFERENT_PROVIDER = "same_tier_different_provider"

    # Try cheaper tier with same provider
    CHEAPER_TIER_SAME_PROVIDER = "cheaper_tier_same_provider"

    # Try different provider, any tier
    DIFFERENT_PROVIDER_ANY_TIER = "different_provider_any_tier"

    # Custom fallback chain
    CUSTOM = "custom"


@dataclass
class FallbackStep:
    """A single step in a fallback chain."""

    provider: str
    tier: str
    description: str = ""

    @property
    def model_id(self) -> str:
        """Get the model ID for this step."""
        model = get_model(self.provider, self.tier)
        return model.id if model else ""


@dataclass
class FallbackPolicy:
    """Policy for handling LLM failures with fallback chains.

    Example:
        >>> policy = FallbackPolicy(
        ...     primary_provider="anthropic",
        ...     primary_tier="capable",
        ...     strategy=FallbackStrategy.SAME_TIER_DIFFERENT_PROVIDER,
        ... )
        >>> chain = policy.get_fallback_chain()
        >>> # Returns: [("anthropic", "premium")]

    """

    # Primary configuration
    primary_provider: str = "anthropic"
    primary_tier: str = "capable"

    # Fallback configuration
    strategy: FallbackStrategy = FallbackStrategy.SAME_TIER_DIFFERENT_PROVIDER
    custom_chain: list[FallbackStep] = field(default_factory=list)

    # Retry configuration
    max_retries: int = 2
    retry_delay_ms: int = 1000
    exponential_backoff: bool = True

    # Timeout configuration
    timeout_ms: int = 30000

    def get_fallback_chain(self) -> list[FallbackStep]:
        """Get the fallback chain based on strategy.

        Returns:
            List of FallbackStep in order of preference

        """
        if self.strategy == FallbackStrategy.CUSTOM:
            return self.custom_chain

        chain: list[FallbackStep] = []
        # Anthropic-only as of v5.0.0
        all_providers = ["anthropic"]
        all_tiers = ["premium", "capable", "cheap"]
        # Cache tier index for O(1) lookup
        tier_index_map = {tier: i for i, tier in enumerate(all_tiers)}
        tier_index = tier_index_map.get(self.primary_tier, 1)

        if self.strategy == FallbackStrategy.SAME_TIER_DIFFERENT_PROVIDER:
            # Try same tier with other providers
            for provider in all_providers:
                if provider != self.primary_provider:
                    chain.append(
                        FallbackStep(
                            provider=provider,
                            tier=self.primary_tier,
                            description=(f"Same tier ({self.primary_tier}) on {provider}"),
                        ),
                    )

        elif self.strategy == FallbackStrategy.CHEAPER_TIER_SAME_PROVIDER:
            # Try cheaper tiers with same provider
            for tier in all_tiers[tier_index + 1 :]:
                chain.append(
                    FallbackStep(
                        provider=self.primary_provider,
                        tier=tier,
                        description=(f"Cheaper tier ({tier}) on {self.primary_provider}"),
                    ),
                )

        elif self.strategy == FallbackStrategy.DIFFERENT_PROVIDER_ANY_TIER:
            # Try other providers, preferring same tier then cheaper
            for provider in all_providers:
                if provider != self.primary_provider:
                    # Try same tier first
                    chain.append(
                        FallbackStep(
                            provider=provider,
                            tier=self.primary_tier,
                            description=(f"{self.primary_tier} on {provider}"),
                        ),
                    )
                    # Then cheaper tiers
                    for tier in all_tiers[tier_index + 1 :]:
                        chain.append(
                            FallbackStep(
                                provider=provider,
                                tier=tier,
                                description=(f"{tier} on {provider}"),
                            ),
                        )

        return chain
