"""Cache-token telemetry plumbing.

Verifies that ``cache_creation_tokens`` and ``cache_read_tokens`` flow
from the LLM provider's ``LLMResponse.metadata`` -> ``StepResult`` ->
``_track_telemetry`` -> ``UsageTracker.track_llm_call``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from attune.workflows.executor_mixin import StepResult
from attune.workflows.telemetry_mixin import TelemetryMixin


class TestStepResult:
    def test_default_cache_fields_zero(self) -> None:
        sr = StepResult(content="x", input_tokens=1, output_tokens=2, cost=0.0)
        assert sr.cache_creation_tokens == 0
        assert sr.cache_read_tokens == 0
        assert sr.prompt_cache_hit is False

    def test_prompt_cache_hit_true_when_read_tokens(self) -> None:
        sr = StepResult(
            content="x",
            input_tokens=1,
            output_tokens=2,
            cost=0.0,
            cache_creation_tokens=0,
            cache_read_tokens=1024,
        )
        assert sr.prompt_cache_hit is True

    def test_prompt_cache_hit_false_when_only_creation(self) -> None:
        """Creation tokens alone don't count as a hit — that's a write."""
        sr = StepResult(
            content="x",
            input_tokens=1,
            output_tokens=2,
            cost=0.0,
            cache_creation_tokens=2048,
            cache_read_tokens=0,
        )
        assert sr.prompt_cache_hit is False


class TestTrackTelemetryForwardsCacheTokens:
    """``_track_telemetry`` must pass cache fields through to track_llm_call."""

    def _make_mixin(self) -> tuple[TelemetryMixin, MagicMock]:
        mixin = TelemetryMixin()
        mixin.name = "test-workflow"
        mixin._provider_str = "anthropic"
        tracker = MagicMock()
        mixin._telemetry_tracker = tracker
        return mixin, tracker

    def test_zero_cache_fields_default(self) -> None:
        """When cache fields aren't passed, tracker sees zeros + hit=False."""
        mixin, tracker = self._make_mixin()
        tier = MagicMock()
        tier.value = "capable"

        mixin._track_telemetry(
            stage="s",
            tier=tier,
            model="m",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=10,
        )

        call_kwargs = tracker.track_llm_call.call_args.kwargs
        assert call_kwargs["prompt_cache_hit"] is False
        assert call_kwargs["prompt_cache_creation_tokens"] == 0
        assert call_kwargs["prompt_cache_read_tokens"] == 0

    def test_cache_creation_only_marks_hit_false(self) -> None:
        mixin, tracker = self._make_mixin()
        tier = MagicMock()
        tier.value = "capable"

        mixin._track_telemetry(
            stage="s",
            tier=tier,
            model="m",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=10,
            prompt_cache_creation_tokens=2048,
            prompt_cache_read_tokens=0,
        )

        call_kwargs = tracker.track_llm_call.call_args.kwargs
        assert call_kwargs["prompt_cache_hit"] is False  # creation alone is a write
        assert call_kwargs["prompt_cache_creation_tokens"] == 2048
        assert call_kwargs["prompt_cache_read_tokens"] == 0

    def test_cache_read_marks_hit_true(self) -> None:
        mixin, tracker = self._make_mixin()
        tier = MagicMock()
        tier.value = "capable"

        mixin._track_telemetry(
            stage="s",
            tier=tier,
            model="m",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=10,
            prompt_cache_creation_tokens=0,
            prompt_cache_read_tokens=1024,
        )

        call_kwargs = tracker.track_llm_call.call_args.kwargs
        assert call_kwargs["prompt_cache_hit"] is True
        assert call_kwargs["prompt_cache_read_tokens"] == 1024


class TestRunStepWithExecutorPullsCacheFromMetadata:
    """``run_step_with_executor`` must read cache fields from
    ``response.metadata`` and surface them on ``StepResult``."""

    @pytest.mark.asyncio
    async def test_pulls_cache_creation_and_read_tokens(self) -> None:
        from attune.workflows.executor_mixin import ExecutorMixin

        # Build a minimal host that ExecutorMixin can run on.
        class _Host(ExecutorMixin):
            def __init__(self) -> None:
                self.name = "test"
                self._executor = MagicMock()
                self._provider_str = "anthropic"

                async def _run(**_kwargs):
                    response = MagicMock()
                    response.content = "ok"
                    response.tokens_input = 1500
                    response.tokens_output = 50
                    response.cost_estimate = 0.01
                    response.tier = "capable"
                    response.model_id = "claude-sonnet-5"
                    response.metadata = {
                        "cache_creation_tokens": 1200,
                        "cache_read_tokens": 0,
                    }
                    return response

                self._executor.run = _run

            def _create_execution_context(self, **_kwargs):
                return MagicMock()

            def _emit_call_telemetry(self, **_kwargs) -> None:  # noqa: D401
                pass

        host = _Host()
        step = MagicMock()
        step.name = "s"
        step.task_type = "general"

        result = await host.run_step_with_executor(step=step, prompt="hi")

        assert isinstance(result, StepResult)
        assert result.content == "ok"
        assert result.input_tokens == 1500
        assert result.output_tokens == 50
        assert result.cache_creation_tokens == 1200
        assert result.cache_read_tokens == 0
        assert result.prompt_cache_hit is False  # creation only

    @pytest.mark.asyncio
    async def test_zero_when_metadata_absent(self) -> None:
        """No metadata key => StepResult cache fields default to zero."""
        from attune.workflows.executor_mixin import ExecutorMixin

        class _Host(ExecutorMixin):
            def __init__(self) -> None:
                self.name = "test"
                self._executor = MagicMock()
                self._provider_str = "openai"  # no cache support

                async def _run(**_kwargs):
                    response = MagicMock()
                    response.content = "ok"
                    response.tokens_input = 100
                    response.tokens_output = 20
                    response.cost_estimate = 0.001
                    response.tier = "cheap"
                    response.model_id = "gpt-x"
                    response.metadata = {}  # no cache fields
                    return response

                self._executor.run = _run

            def _create_execution_context(self, **_kwargs):
                return MagicMock()

            def _emit_call_telemetry(self, **_kwargs) -> None:
                pass

        host = _Host()
        step = MagicMock()
        step.name = "s"
        step.task_type = "general"

        result = await host.run_step_with_executor(step=step, prompt="hi")
        assert result.cache_creation_tokens == 0
        assert result.cache_read_tokens == 0
