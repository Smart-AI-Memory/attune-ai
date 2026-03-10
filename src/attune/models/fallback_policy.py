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

    # Try cheaper tier with same provider
    CHEAPER_TIER_SAME_PROVIDER = "cheaper_tier_same_provider"

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
        ...     strategy=FallbackStrategy.CHEAPER_TIER_SAME_PROVIDER,
        ... )
        >>> chain = policy.get_fallback_chain()

    """

    # Primary configuration
    primary_provider: str = "anthropic"
    primary_tier: str = "capable"

    # Fallback configuration
    strategy: FallbackStrategy = FallbackStrategy.CHEAPER_TIER_SAME_PROVIDER
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

        # CHEAPER_TIER_SAME_PROVIDER: try cheaper tiers
        all_tiers = ["premium", "capable", "cheap"]
        tier_index_map = {tier: i for i, tier in enumerate(all_tiers)}
        tier_index = tier_index_map.get(self.primary_tier, 1)

        return [
            FallbackStep(
                provider=self.primary_provider,
                tier=tier,
                description=f"Cheaper tier ({tier}) on {self.primary_provider}",
            )
            for tier in all_tiers[tier_index + 1 :]
        ]
