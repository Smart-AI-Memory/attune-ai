"""Coverage-gap tests for attune.models.resilient_executor.

Targets previously-uncovered lines:
- 101-104: per-call retry/fallback policy override via context.metadata
- 122-131: circuit breaker open → append skipped attempt + continue
- 134->119: max_retries=0 → no inner loop
- 138, 140: context.provider_hint / context.tier_hint set
- 154->166: response without metadata attribute
- 162: fallback_chain populated when description != "Primary"
- 201-205: get_model_for_task delegation
- 216-220: estimate_cost delegation
- 264-272: legacy execute_with_fallback circuit breaker open
- 275->261: legacy max_retries=0 inner loop empty
- 290: legacy fallback_used set when not primary
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from attune.models.resilient_executor import (
    AllProvidersFailedError,
    ResilientExecutor,
)


def _make_executor(
    inner=None,
    primary="anthropic",
    primary_tier="cheap",
    max_retries=2,
):
    """Build a ResilientExecutor with controlled policies."""
    from attune.models.circuit_breaker import CircuitBreaker
    from attune.models.fallback_policy import FallbackPolicy, FallbackStrategy
    from attune.models.retry import RetryPolicy

    fp = FallbackPolicy(
        primary_provider=primary,
        primary_tier=primary_tier,
        strategy=FallbackStrategy.CUSTOM,
        custom_chain=[],
    )
    cb = CircuitBreaker()
    rp = RetryPolicy(max_retries=max_retries)
    return ResilientExecutor(
        executor=inner,
        fallback_policy=fp,
        circuit_breaker=cb,
        retry_policy=rp,
    )


class TestRunPolicyOverrides:
    @pytest.mark.asyncio
    async def test_context_metadata_overrides_retry_policy(self):
        """Lines 101-102: context.metadata['retry_policy'] used."""
        from attune.models.retry import RetryPolicy

        # Inner executor returns a successful response
        inner = MagicMock()
        resp = MagicMock()
        resp.metadata = {}
        inner.run = AsyncMock(return_value=resp)

        rex = _make_executor(inner=inner)
        ctx = MagicMock()
        ctx.metadata = {"retry_policy": RetryPolicy(max_retries=1)}

        # Should not raise; just exercises override path
        result = await rex.run("task", "prompt", context=ctx)
        assert result is resp

    @pytest.mark.asyncio
    async def test_context_metadata_overrides_fallback_policy(self):
        """Lines 103-104: context.metadata['fallback_policy'] used."""
        from attune.models.fallback_policy import FallbackPolicy

        inner = MagicMock()
        resp = MagicMock()
        resp.metadata = {}
        inner.run = AsyncMock(return_value=resp)

        rex = _make_executor(inner=inner)
        ctx = MagicMock()
        from attune.models.fallback_policy import FallbackStrategy

        override_fp = FallbackPolicy(
            primary_provider="anthropic",
            primary_tier="capable",
            strategy=FallbackStrategy.CUSTOM,
            custom_chain=[],
        )
        ctx.metadata = {"fallback_policy": override_fp}

        result = await rex.run("task", "prompt", context=ctx)
        assert result is resp


class TestRunCircuitBreakerOpen:
    @pytest.mark.asyncio
    async def test_circuit_breaker_open_skips_step(self):
        """Lines 122-131: circuit_breaker.is_available False → skipped attempt."""
        inner = MagicMock()
        # No successful run since all steps will be skipped
        inner.run = AsyncMock()

        rex = _make_executor(inner=inner)
        rex.circuit_breaker.is_available = MagicMock(return_value=False)

        with pytest.raises(AllProvidersFailedError) as exc_info:
            await rex.run("task", "prompt")
        # All attempts should be marked skipped with circuit_breaker_open reason
        assert all(a["skipped"] for a in exc_info.value.attempts)
        assert exc_info.value.attempts[0]["reason"] == "circuit_breaker_open"


class TestRunRetryEdge:
    @pytest.mark.asyncio
    async def test_max_retries_zero_skips_inner_loop(self):
        """Line 134->119: max_retries=0 → range is empty, skips to next step."""
        inner = MagicMock()
        inner.run = AsyncMock()

        rex = _make_executor(inner=inner, max_retries=0)
        with pytest.raises(AllProvidersFailedError):
            await rex.run("task", "prompt")
        # inner.run should never have been called
        inner.run.assert_not_called()


class TestRunContextHints:
    @pytest.mark.asyncio
    async def test_provider_and_tier_hints_set(self):
        """Lines 138, 140: context.provider_hint / tier_hint assigned."""

        class _Ctx:
            metadata: dict[str, Any] = {}
            provider_hint: str | None = None
            tier_hint: str | None = None

        ctx = _Ctx()

        inner = MagicMock()
        resp = MagicMock()
        resp.metadata = {}
        inner.run = AsyncMock(return_value=resp)

        rex = _make_executor(inner=inner, primary="openai", primary_tier="premium")
        await rex.run("task", "prompt", context=ctx)

        assert ctx.provider_hint == "openai"
        assert ctx.tier_hint == "premium"


class TestRunResponseNoMetadata:
    @pytest.mark.asyncio
    async def test_response_without_metadata_attribute(self):
        """Line 154->166: response lacking 'metadata' attr is returned as-is."""
        inner = MagicMock()
        # Response without metadata — use a plain object
        plain = object()
        inner.run = AsyncMock(return_value=plain)

        rex = _make_executor(inner=inner)
        result = await rex.run("task", "prompt")
        assert result is plain


class TestRunFallbackChainMetadata:
    @pytest.mark.asyncio
    async def test_fallback_chain_populated_when_not_primary(self):
        """Line 162: response.metadata['fallback_chain'] set when step != Primary."""
        from attune.models.fallback_policy import (
            FallbackPolicy,
            FallbackStep,
            FallbackStrategy,
        )

        fp = FallbackPolicy(
            primary_provider="anthropic",
            primary_tier="cheap",
            strategy=FallbackStrategy.CUSTOM,
            custom_chain=[
                FallbackStep(provider="anthropic", tier="capable", description="Step1"),
            ],
        )

        # Inner: first call (Primary) raises; second call (Step1) succeeds
        inner = MagicMock()
        ok_resp = MagicMock()
        ok_resp.metadata = {}
        inner.run = AsyncMock(side_effect=[RuntimeError("primary down"), ok_resp])

        from attune.models.circuit_breaker import CircuitBreaker
        from attune.models.retry import RetryPolicy

        rex = ResilientExecutor(
            executor=inner,
            fallback_policy=fp,
            circuit_breaker=CircuitBreaker(),
            retry_policy=RetryPolicy(max_retries=1),
        )

        result = await rex.run("task", "prompt")
        assert result is ok_resp
        assert result.metadata["fallback_used"] is True
        assert "fallback_chain" in result.metadata


class TestDelegationMethods:
    def test_get_model_for_task_delegates(self):
        """Lines 200-205: delegates to inner executor when present."""
        inner = MagicMock()
        inner.get_model_for_task = MagicMock(return_value="model-x")
        rex = _make_executor(inner=inner)
        assert rex.get_model_for_task("task") == "model-x"

    def test_get_model_for_task_no_inner(self):
        """Line 206: empty string when no inner executor."""
        rex = _make_executor(inner=None)
        assert rex.get_model_for_task("task") == ""

    def test_estimate_cost_delegates(self):
        """Lines 215-220: estimate_cost delegated to inner."""
        inner = MagicMock()
        inner.estimate_cost = MagicMock(return_value=1.23)
        rex = _make_executor(inner=inner)
        assert rex.estimate_cost("task", 100, 50) == 1.23

    def test_estimate_cost_no_inner(self):
        """Line 221: 0.0 when no inner executor."""
        rex = _make_executor(inner=None)
        assert rex.estimate_cost("task", 100, 50) == 0.0


class TestExecuteWithFallbackLegacy:
    """Cover lines 264-272, 275->261, 290 in legacy execute_with_fallback."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_on_legacy(self):
        """Lines 264-272: circuit breaker open → step skipped."""
        rex = _make_executor()
        rex.circuit_breaker.is_available = MagicMock(return_value=False)

        async def call_fn(*a, **kw):
            return "should not be called"

        with pytest.raises(AllProvidersFailedError):
            await rex.execute_with_fallback(call_fn)

    @pytest.mark.asyncio
    async def test_legacy_max_retries_zero(self):
        """Line 275->261: max_retries=0 → inner loop never runs."""
        rex = _make_executor(max_retries=0)
        called = []

        async def call_fn(*a, **kw):
            called.append(kw)
            return "ok"

        with pytest.raises(AllProvidersFailedError):
            await rex.execute_with_fallback(call_fn)
        assert called == []

    @pytest.mark.asyncio
    async def test_legacy_fallback_used_set_when_not_primary(self):
        """Line 290: fallback_used=True when step.description != 'Primary'."""
        from attune.models.fallback_policy import (
            FallbackPolicy,
            FallbackStep,
            FallbackStrategy,
        )

        fp = FallbackPolicy(
            primary_provider="anthropic",
            primary_tier="cheap",
            strategy=FallbackStrategy.CUSTOM,
            custom_chain=[
                FallbackStep(provider="anthropic", tier="capable", description="Step1"),
            ],
        )

        from attune.models.circuit_breaker import CircuitBreaker
        from attune.models.retry import RetryPolicy

        rex = ResilientExecutor(
            executor=None,
            fallback_policy=fp,
            circuit_breaker=CircuitBreaker(),
            retry_policy=RetryPolicy(max_retries=1),
        )

        call_count = [0]

        async def call_fn(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("primary fail")
            return "fallback-result"

        result, metadata = await rex.execute_with_fallback(call_fn)
        assert result == "fallback-result"
        assert metadata["fallback_used"] is True
