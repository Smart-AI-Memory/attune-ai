"""Resilient Executor for LLM Calls

Combines fallback policies, circuit breakers, and retry logic to
provide fault-tolerant LLM execution with automatic failover.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
from collections.abc import Callable
from typing import Any, cast

from .circuit_breaker import CircuitBreaker
from .fallback_policy import FallbackPolicy, FallbackStep
from .retry import RetryPolicy


class AllProvidersFailedError(Exception):
    """Raised when all fallback providers have failed."""

    def __init__(self, message: str, attempts: list[dict[str, Any]]):
        """Initialize with error message and attempt history.

        Args:
            message: Error description.
            attempts: List of dicts describing each failed attempt.
        """
        super().__init__(message)
        self.attempts = attempts


class ResilientExecutor:
    """Wrapper that adds resilience to LLM execution.

    Combines fallback policies, circuit breakers, and retry logic.
    Implements the LLMExecutor protocol by wrapping another executor.

    Example:
        >>> from attune.models.empathy_executor import EmpathyLLMExecutor
        >>> base_executor = EmpathyLLMExecutor(provider="anthropic")
        >>> resilient = ResilientExecutor(executor=base_executor)
        >>> response = await resilient.run("summarize", "Summarize this...")

    """

    def __init__(
        self,
        executor: Any | None = None,
        fallback_policy: FallbackPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry_policy: RetryPolicy | None = None,
    ):
        """Initialize resilient executor.

        Args:
            executor: Inner LLMExecutor to wrap
            fallback_policy: Fallback configuration
            circuit_breaker: Circuit breaker instance
            retry_policy: Retry configuration

        """
        self._executor = executor
        self.fallback_policy = fallback_policy or FallbackPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.retry_policy = retry_policy or RetryPolicy()

    async def run(
        self,
        task_type: str,
        prompt: str,
        system: str | None = None,
        context: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute LLM call with retry and fallback support.

        Implements the LLMExecutor protocol. Uses per-call policies from
        context.metadata if provided.

        Args:
            task_type: Type of task for routing
            prompt: The user prompt
            system: Optional system prompt
            context: Optional ExecutionContext (can contain retry_policy,
                fallback_policy)
            **kwargs: Additional arguments

        Returns:
            LLMResponse from the wrapped executor

        """
        if self._executor is None:
            raise RuntimeError("ResilientExecutor requires an inner executor")

        # Allow per-call policy overrides via context.metadata
        retry_policy = self.retry_policy
        fallback_policy = self.fallback_policy

        if context and hasattr(context, "metadata"):
            if "retry_policy" in context.metadata:
                retry_policy = context.metadata["retry_policy"]
            if "fallback_policy" in context.metadata:
                fallback_policy = context.metadata["fallback_policy"]

        # Build execution chain: primary + fallbacks
        chain = [
            FallbackStep(
                provider=fallback_policy.primary_provider,
                tier=fallback_policy.primary_tier,
                description="Primary",
            ),
        ] + fallback_policy.get_fallback_chain()

        attempts: list[dict[str, Any]] = []
        last_error: Exception | None = None
        total_retries = 0  # Track total retry count across all attempts

        for step in chain:
            # Check circuit breaker (per provider:tier)
            if not self.circuit_breaker.is_available(step.provider, step.tier):
                attempts.append(
                    {
                        "provider": step.provider,
                        "tier": step.tier,
                        "skipped": True,
                        "reason": "circuit_breaker_open",
                        "circuit_breaker_state": "open",
                    },
                )
                continue

            # Try with retries
            for attempt_num in range(1, retry_policy.max_retries + 1):
                try:
                    # Update context with current provider/tier hints
                    if context and hasattr(context, "provider_hint"):
                        context.provider_hint = step.provider
                    if context and hasattr(context, "tier_hint"):
                        context.tier_hint = step.tier

                    response = await self._executor.run(
                        task_type=task_type,
                        prompt=prompt,
                        system=system,
                        context=context,
                        **kwargs,
                    )

                    # Success - record and return
                    self.circuit_breaker.record_success(step.provider, step.tier)

                    # Add resilience metadata to response
                    if hasattr(response, "metadata"):
                        response.metadata["fallback_used"] = step.description != "Primary"
                        response.metadata["attempts"] = attempts
                        response.metadata["retry_count"] = total_retries
                        response.metadata["circuit_breaker_state"] = "closed"
                        response.metadata["original_provider"] = fallback_policy.primary_provider
                        response.metadata["original_tier"] = fallback_policy.primary_tier
                        if step.description != "Primary":
                            response.metadata["fallback_chain"] = [
                                f"{a['provider']}:{a['tier']}" for a in attempts
                            ]

                    return response

                except Exception as e:  # noqa: BLE001
                    last_error = e
                    error_type = self._classify_error(e)
                    total_retries += 1

                    if retry_policy.should_retry(error_type, attempt_num):
                        delay = retry_policy.get_delay_ms(attempt_num)
                        await asyncio.sleep(delay / 1000)
                        continue

                    # Record failure and move to next fallback
                    self.circuit_breaker.record_failure(step.provider, step.tier)
                    attempts.append(
                        {
                            "provider": step.provider,
                            "tier": step.tier,
                            "skipped": False,
                            "error": str(e),
                            "error_type": error_type,
                            "attempt": attempt_num,
                        },
                    )
                    break

        # All fallbacks exhausted
        raise AllProvidersFailedError(
            f"All fallback options exhausted. Last error: {last_error}",
            attempts=attempts,
        ) from last_error

    def get_model_for_task(self, task_type: str) -> str:
        """Delegate to inner executor."""
        if self._executor and hasattr(self._executor, "get_model_for_task"):
            result: str = cast(
                "str",
                self._executor.get_model_for_task(task_type),
            )
            return result
        return ""

    def estimate_cost(
        self,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Delegate to inner executor."""
        if self._executor and hasattr(self._executor, "estimate_cost"):
            result: float = cast(
                "float",
                self._executor.estimate_cost(task_type, input_tokens, output_tokens),
            )
            return result
        return 0.0

    async def execute_with_fallback(
        self,
        call_fn: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, dict[str, Any]]:
        """Execute LLM call with fallback support (legacy API).

        Args:
            call_fn: Async function to call (takes provider, model
                as kwargs)
            *args: Positional arguments for call_fn
            **kwargs: Keyword arguments for call_fn

        Returns:
            Tuple of (result, metadata) where metadata includes
            fallback info

        """
        metadata: dict[str, Any] = {
            "fallback_used": False,
            "fallback_chain": [],
            "attempts": 0,
            "original_provider": (self.fallback_policy.primary_provider),
            "original_model": None,
        }

        # Build execution chain: primary + fallbacks
        chain = [
            FallbackStep(
                provider=self.fallback_policy.primary_provider,
                tier=self.fallback_policy.primary_tier,
                description="Primary",
            ),
        ] + self.fallback_policy.get_fallback_chain()

        last_error: Exception | None = None

        for step in chain:
            # Check circuit breaker (per provider:tier)
            if not self.circuit_breaker.is_available(step.provider, step.tier):
                metadata["fallback_chain"].append(
                    {
                        "provider": step.provider,
                        "tier": step.tier,
                        "skipped": True,
                        "reason": "circuit_breaker_open",
                    },
                )
                continue

            # Try with retries
            for attempt in range(1, self.retry_policy.max_retries + 1):
                metadata["attempts"] += 1

                try:
                    result = await call_fn(
                        *args,
                        provider=step.provider,
                        model=step.model_id,
                        **kwargs,
                    )

                    # Success
                    self.circuit_breaker.record_success(step.provider, step.tier)

                    if step.description != "Primary":
                        metadata["fallback_used"] = True

                    metadata["final_provider"] = step.provider
                    metadata["final_tier"] = step.tier
                    metadata["final_model"] = step.model_id

                    return result, metadata

                except Exception as e:  # noqa: BLE001
                    last_error = e
                    error_type = self._classify_error(e)

                    if self.retry_policy.should_retry(error_type, attempt):
                        delay = self.retry_policy.get_delay_ms(attempt)
                        await asyncio.sleep(delay / 1000)
                        continue

                    # Record failure and move to next fallback
                    self.circuit_breaker.record_failure(step.provider, step.tier)
                    metadata["fallback_chain"].append(
                        {
                            "provider": step.provider,
                            "tier": step.tier,
                            "skipped": False,
                            "error": str(e),
                            "error_type": error_type,
                        },
                    )
                    break

        # All fallbacks exhausted
        raise AllProvidersFailedError(
            f"All fallback options exhausted. Last error: {last_error}",
            attempts=metadata["fallback_chain"],
        ) from last_error

    def _classify_error(self, error: Exception) -> str:
        """Classify an error for retry decisions."""
        error_str = str(error).lower()

        if "rate" in error_str or "limit" in error_str:
            return "rate_limit"
        if "timeout" in error_str:
            return "timeout"
        if "connection" in error_str:
            return "connection_error"
        if "500" in error_str or "502" in error_str or "503" in error_str:
            return "server_error"
        return "unknown"
