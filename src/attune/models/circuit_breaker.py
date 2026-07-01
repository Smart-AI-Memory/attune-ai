"""Circuit Breaker for LLM Provider Resilience

Temporarily disables failing providers to prevent cascading failures.
Tracks state per provider:tier combination for fine-grained control
(e.g., Opus rate-limited shouldn't block Haiku).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker for a provider."""

    failure_count: int = 0
    last_failure: datetime | None = None
    is_open: bool = False
    opened_at: datetime | None = None
    half_open_calls: int = 0


class CircuitBreaker:
    """Circuit breaker to temporarily disable failing providers.

    Prevents cascading failures by stopping calls to providers that
    are experiencing issues. Tracks state per provider:tier combination
    for fine-grained control (e.g., Opus rate-limited shouldn't block Haiku).

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        >>> if breaker.is_available("anthropic", "capable"):
        ...     try:
        ...         response = call_llm(...)
        ...         breaker.record_success("anthropic", "capable")
        ...     except Exception as e:  # noqa: BLE001
        ...         breaker.record_failure("anthropic", "capable")

    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        half_open_calls: int = 1,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout_seconds: Time before trying again
            half_open_calls: Calls to allow in half-open state

        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout_seconds)
        self.half_open_calls = half_open_calls
        self._states: dict[str, CircuitBreakerState] = {}

    def _get_key(self, provider: str, tier: str | None = None) -> str:
        """Get the state key for a provider:tier combination."""
        if tier:
            return f"{provider}:{tier}"
        return provider

    def _get_state(self, provider: str, tier: str | None = None) -> CircuitBreakerState:
        """Get or create state for a provider:tier combination."""
        key = self._get_key(provider, tier)
        if key not in self._states:
            self._states[key] = CircuitBreakerState()
        return self._states[key]

    def is_available(self, provider: str, tier: str | None = None) -> bool:
        """Check if a provider:tier is available.

        Args:
            provider: Provider to check
            tier: Optional tier (if None, checks provider-level)

        Returns:
            True if provider:tier can be called

        """
        state = self._get_state(provider, tier)

        if not state.is_open:
            return True

        # Open: after the recovery timeout, enter the half-open state and
        # allow up to ``half_open_calls`` probe calls to test recovery. A
        # success closes the circuit; a failure re-opens it (see
        # record_success / record_failure). Without this cap, every call
        # after the timeout was let through — defeating the point of the
        # half-open state under load.
        if state.opened_at and (datetime.now() - state.opened_at) >= self.recovery_timeout:
            if state.half_open_calls < self.half_open_calls:
                state.half_open_calls += 1
                return True
            return False  # probe budget spent; wait for a probe result

        return False

    def record_success(self, provider: str, tier: str | None = None) -> None:
        """Record a successful call.

        Args:
            provider: Provider that succeeded
            tier: Optional tier

        """
        state = self._get_state(provider, tier)

        # Reset on success (closes the circuit).
        state.failure_count = 0
        state.is_open = False
        state.opened_at = None
        state.half_open_calls = 0

    def record_failure(self, provider: str, tier: str | None = None) -> None:
        """Record a failed call.

        Args:
            provider: Provider that failed
            tier: Optional tier

        """
        state = self._get_state(provider, tier)

        state.failure_count += 1
        state.last_failure = datetime.now()

        if state.failure_count >= self.failure_threshold:
            state.is_open = True
            state.opened_at = datetime.now()
            # Reset the probe budget so the next recovery window starts fresh
            # (a failed half-open probe re-opens the circuit).
            state.half_open_calls = 0

    def get_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all tracked providers."""
        return {
            provider: {
                "failure_count": state.failure_count,
                "is_open": state.is_open,
                "last_failure": (state.last_failure.isoformat() if state.last_failure else None),
                "opened_at": (state.opened_at.isoformat() if state.opened_at else None),
            }
            for provider, state in self._states.items()
        }

    def reset(
        self,
        provider: str | None = None,
        tier: str | None = None,
    ) -> None:
        """Reset circuit breaker state.

        Args:
            provider: Provider to reset (all if None)
            tier: Tier to reset (provider-level if None)

        """
        if provider:
            key = self._get_key(provider, tier)
            if key in self._states:
                self._states[key] = CircuitBreakerState()
        else:
            self._states.clear()
