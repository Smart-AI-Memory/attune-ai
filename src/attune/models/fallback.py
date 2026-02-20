"""Fallback and Resilience Policies for Multi-Model Workflows

Facade module that re-exports all fallback/resilience types from
their focused sub-modules. All imports from ``attune.models.fallback``
continue to work unchanged.

Sub-modules:
- fallback_policy: FallbackStrategy, FallbackStep, FallbackPolicy
- circuit_breaker: CircuitBreaker, CircuitBreakerState
- retry: RetryPolicy
- resilient_executor: ResilientExecutor, AllProvidersFailedError
- tier_helper: TierFallbackHelper

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerState
from .fallback_policy import FallbackPolicy, FallbackStep, FallbackStrategy
from .resilient_executor import AllProvidersFailedError, ResilientExecutor
from .retry import RetryPolicy
from .tier_helper import TierFallbackHelper

# Default policies ---------------------------------------------------------

DEFAULT_FALLBACK_POLICY = FallbackPolicy(
    primary_provider="anthropic",
    primary_tier="capable",
    strategy=FallbackStrategy.SAME_TIER_DIFFERENT_PROVIDER,
    max_retries=2,
)

# Intelligent Sonnet 4.6 -> Opus 4.6 fallback policy
# Tries Sonnet 4.6 first, then upgrades to Opus 4.6 if needed
# Tracks cost savings when Sonnet succeeds (saves 80% vs always using Opus)
SONNET_TO_OPUS_FALLBACK = FallbackPolicy(
    primary_provider="anthropic",
    primary_tier="capable",  # Sonnet 4.6
    strategy=FallbackStrategy.CUSTOM,
    custom_chain=[
        FallbackStep(
            provider="anthropic",
            tier="premium",  # Opus 4.6
            description="Upgraded to Opus 4.6 for complex reasoning",
        ),
    ],
    max_retries=1,  # Only retry once before upgrading to Opus
)

DEFAULT_RETRY_POLICY = RetryPolicy(
    max_retries=3,
    initial_delay_ms=1000,
    exponential_backoff=True,
)

# Public API ---------------------------------------------------------------

__all__ = [
    "AllProvidersFailedError",
    "CircuitBreaker",
    "CircuitBreakerState",
    "DEFAULT_FALLBACK_POLICY",
    "DEFAULT_RETRY_POLICY",
    "FallbackPolicy",
    "FallbackStep",
    "FallbackStrategy",
    "ResilientExecutor",
    "RetryPolicy",
    "SONNET_TO_OPUS_FALLBACK",
    "TierFallbackHelper",
]
