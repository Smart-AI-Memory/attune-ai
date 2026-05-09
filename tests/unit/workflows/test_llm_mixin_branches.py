"""Branch coverage for attune.workflows.llm_mixin.

Targets previously-uncovered lines:
- _call_llm: cache hit path (93-123)
- _call_llm: ValueError/TypeError/KeyError exception (172-175)
- _call_llm: TimeoutError/RuntimeError/ConnectionError exception (176-179)
- _call_llm: OSError/PermissionError exception (180-183)
- _call_llm: generic Exception (184-187)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.llm_mixin import LLMMixin

# ---------------------------------------------------------------------------
# Minimal LLMMixin host
# ---------------------------------------------------------------------------


def _make_host():
    """Create a minimal LLMMixin instance with required attributes mocked."""
    host = LLMMixin()
    host.name = "test-workflow"
    host.stages = ["analyze"]
    host.provider = MagicMock()
    host.provider.value = "anthropic"
    host._provider_str = "anthropic"
    host._config = None

    # Mixin dependencies
    cheap = MagicMock()
    cheap.value = "cheap"
    host._try_cache_lookup = MagicMock(return_value=None)  # cache miss by default
    host._store_in_cache = MagicMock()
    host._get_cache_type = MagicMock(return_value="hash")
    host._calculate_cost = MagicMock(return_value=0.001)
    host._track_telemetry = MagicMock()
    host.cost_tracker = MagicMock()

    return host


def _make_tier(value="cheap"):
    tier = MagicMock()
    tier.value = value
    return tier


def _make_step_result(content="output", in_tokens=100, out_tokens=50, cost=0.001):
    r = MagicMock()
    r.content = content
    r.input_tokens = in_tokens
    r.output_tokens = out_tokens
    r.cost = cost
    r.cache_creation_tokens = 0
    r.cache_read_tokens = 0
    return r


# ---------------------------------------------------------------------------
# _call_llm — cache hit path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCallLLMCacheHit:
    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_content(self):
        host = _make_host()
        tier = _make_tier()

        cached = MagicMock()
        cached.content = "cached result"
        cached.input_tokens = 80
        cached.output_tokens = 40
        host._try_cache_lookup = MagicMock(return_value=cached)

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            result = await host._call_llm(tier, "sys", "prompt")

        assert result[0] == "cached result"
        assert result[1] == 80
        assert result[2] == 40
        # Telemetry recorded for cache hit
        host._track_telemetry.assert_called_once()
        call_kwargs = host._track_telemetry.call_args[1]
        assert call_kwargs["cache_hit"] is True

    @pytest.mark.asyncio
    async def test_cache_hit_does_not_call_run_step(self):
        host = _make_host()
        tier = _make_tier()

        cached = MagicMock()
        cached.content = "from cache"
        cached.input_tokens = 10
        cached.output_tokens = 5
        host._try_cache_lookup = MagicMock(return_value=cached)
        host.run_step_with_executor = AsyncMock()

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            await host._call_llm(tier, "sys", "user")

        host.run_step_with_executor.assert_not_called()


# ---------------------------------------------------------------------------
# _call_llm — successful execution path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCallLLMSuccess:
    @pytest.mark.asyncio
    async def test_successful_call_returns_content(self):
        host = _make_host()
        tier = _make_tier()
        result = _make_step_result("analysis done", 100, 50)
        host.run_step_with_executor = AsyncMock(return_value=result)

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            content, in_tok, out_tok = await host._call_llm(tier, "sys", "user")

        assert content == "analysis done"
        assert in_tok == 100
        assert out_tok == 50

    @pytest.mark.asyncio
    async def test_successful_call_stores_in_cache(self):
        host = _make_host()
        tier = _make_tier()
        result = _make_step_result("done")
        host.run_step_with_executor = AsyncMock(return_value=result)

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            await host._call_llm(tier, "sys", "user")

        host._store_in_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_call_tracks_telemetry(self):
        host = _make_host()
        tier = _make_tier()
        result = _make_step_result()
        host.run_step_with_executor = AsyncMock(return_value=result)

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            await host._call_llm(tier, "sys", "user")

        host._track_telemetry.assert_called_once()
        call_kwargs = host._track_telemetry.call_args[1]
        assert call_kwargs["cache_hit"] is False


# ---------------------------------------------------------------------------
# _call_llm — exception branches
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCallLLMExceptions:
    @pytest.mark.asyncio
    async def test_value_error_returns_error_string(self):
        host = _make_host()
        tier = _make_tier()
        host.run_step_with_executor = AsyncMock(side_effect=ValueError("bad input"))

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            content, in_tok, out_tok = await host._call_llm(tier, "sys", "user")

        assert "invalid input" in content
        assert in_tok == 0
        assert out_tok == 0

    @pytest.mark.asyncio
    async def test_runtime_error_returns_error_string(self):
        host = _make_host()
        tier = _make_tier()
        host.run_step_with_executor = AsyncMock(side_effect=RuntimeError("API down"))

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            content, in_tok, out_tok = await host._call_llm(tier, "sys", "user")

        assert "timeout/API" in content
        assert in_tok == 0

    @pytest.mark.asyncio
    async def test_connection_error_returns_error_string(self):
        host = _make_host()
        tier = _make_tier()
        host.run_step_with_executor = AsyncMock(side_effect=ConnectionError("network down"))

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            content, in_tok, out_tok = await host._call_llm(tier, "sys", "user")

        assert "timeout/API" in content

    @pytest.mark.asyncio
    async def test_oserror_returns_error_string(self):
        host = _make_host()
        tier = _make_tier()
        host.run_step_with_executor = AsyncMock(side_effect=OSError("disk full"))

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            content, in_tok, out_tok = await host._call_llm(tier, "sys", "user")

        assert "file system" in content
        assert in_tok == 0

    @pytest.mark.asyncio
    async def test_permission_error_returns_error_string(self):
        host = _make_host()
        tier = _make_tier()
        host.run_step_with_executor = AsyncMock(side_effect=PermissionError("access denied"))

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            content, in_tok, out_tok = await host._call_llm(tier, "sys", "user")

        assert "file system" in content

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error_string(self):
        host = _make_host()
        tier = _make_tier()

        class _WeirdError(Exception):
            pass

        host.run_step_with_executor = AsyncMock(side_effect=_WeirdError("very weird"))

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            content, in_tok, out_tok = await host._call_llm(tier, "sys", "user")

        assert "_WeirdError" in content
        assert in_tok == 0

    @pytest.mark.asyncio
    async def test_key_error_returns_error_string(self):
        host = _make_host()
        tier = _make_tier()
        host.run_step_with_executor = AsyncMock(side_effect=KeyError("missing_key"))

        with patch("attune.workflows.llm_mixin.LLMMixin.get_model_for_tier", return_value="m"):
            content, in_tok, out_tok = await host._call_llm(tier, "sys", "user")

        assert "invalid input" in content
