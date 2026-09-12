"""max_tokens must reach the provider — regression for the dropped-parameter bug.

Found 2026-08-18 by the fit_source budget A/B: ``_call_llm(max_tokens=...)``
built a WorkflowStepConfig carrying the value, but
``run_step_with_executor`` never forwarded it and ``EmpathyLLM.interact``
could not accept it — so EVERY workflow LLM call ran at the empathy
level's recommendation (1024-4096, typically 1536), which Claude 5's
adaptive thinking can fully consume, yielding intermittently EMPTY
outputs. These tests pin both halves of the thread-through.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.step_config import WorkflowStepConfig


class TestExecutorForwardsMaxTokens:
    """run_step_with_executor forwards step.max_tokens to executor.run."""

    @pytest.mark.asyncio
    async def test_step_max_tokens_forwarded(self):
        from attune.workflows.test_gen_parallel import ParallelTestGenerationWorkflow

        wf = ParallelTestGenerationWorkflow.__new__(ParallelTestGenerationWorkflow)
        executor = MagicMock()
        response = MagicMock(
            content="ok",
            metadata={},
            tier="capable",
            model_id="m",
            tokens_input=1,
            tokens_output=1,
            cost_estimate=0.0,
        )
        executor.run = AsyncMock(return_value=response)
        with (
            patch.object(type(wf), "_get_executor", lambda self: executor, create=True),
            patch.object(
                type(wf), "_create_execution_context", lambda self, **kw: None, create=True
            ),
            patch.object(type(wf), "_emit_call_telemetry", lambda self, **kw: None, create=True),
        ):
            step = WorkflowStepConfig(
                name="s", task_type="general", tier_hint="capable", max_tokens=7777
            )
            await wf.run_step_with_executor(step=step, prompt="p", system="sys")
        assert executor.run.call_args.kwargs["max_tokens"] == 7777

    @pytest.mark.asyncio
    async def test_absent_max_tokens_not_injected(self):
        from attune.workflows.test_gen_parallel import ParallelTestGenerationWorkflow

        wf = ParallelTestGenerationWorkflow.__new__(ParallelTestGenerationWorkflow)
        executor = MagicMock()
        response = MagicMock(
            content="ok",
            metadata={},
            tier="capable",
            model_id="m",
            tokens_input=1,
            tokens_output=1,
            cost_estimate=0.0,
        )
        executor.run = AsyncMock(return_value=response)
        with (
            patch.object(type(wf), "_get_executor", lambda self: executor, create=True),
            patch.object(
                type(wf), "_create_execution_context", lambda self, **kw: None, create=True
            ),
            patch.object(type(wf), "_emit_call_telemetry", lambda self, **kw: None, create=True),
        ):
            step = WorkflowStepConfig(name="s", task_type="general", tier_hint="capable")
            await wf.run_step_with_executor(step=step, prompt="p", system="sys")
        assert "max_tokens" not in executor.run.call_args.kwargs


class TestInteractHonorsMaxTokens:
    """interact(max_tokens=...) overrides the level recommendation."""

    def _llm_with_mock_provider(self):
        from attune.llm.core import EmpathyLLM

        llm = EmpathyLLM(provider="anthropic", api_key="fake")  # pragma: allowlist secret
        llm.provider = MagicMock()
        llm.provider.generate = AsyncMock(
            return_value=MagicMock(content="ok", tokens_used=2, model="m")
        )
        return llm

    @pytest.mark.asyncio
    async def test_override_reaches_provider_generate(self):
        llm = self._llm_with_mock_provider()
        await llm.interact("u", "hello", force_level=2, max_tokens=9999)
        assert llm.provider.generate.call_args.kwargs["max_tokens"] == 9999

    @pytest.mark.asyncio
    async def test_default_is_level_recommendation(self):
        from attune.llm.levels import EmpathyLevel

        llm = self._llm_with_mock_provider()
        await llm.interact("u", "hello", force_level=2)
        assert llm.provider.generate.call_args.kwargs[
            "max_tokens"
        ] == EmpathyLevel.get_max_tokens_recommendation(2)
