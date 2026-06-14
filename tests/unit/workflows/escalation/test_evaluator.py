"""Tests for the Evaluator ABC and SemanticEvaluator.

Completes coverage of ``escalation/evaluator.py``: the base
``should_run`` default, ``SemanticEvaluator`` gating, the lazy executor
init, and the ``evaluate()`` LLM path (pass, fail, dict-response,
invalid-JSON, and executor-exception branches).

The evaluator's LLM call is the only mocked dependency; responses are
real JSON strings so the parsing logic runs for real.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.escalation.evaluator import Evaluator, SemanticEvaluator
from attune.workflows.escalation.models import FeedbackType


class _MinimalEvaluator(Evaluator):
    """Concrete Evaluator that does not override should_run()."""

    async def evaluate(self, prompt, response, context=None):
        return True, None


def _fake_executor(content):
    """Return a fake executor whose async run() yields ``content``."""
    executor = MagicMock()
    executor.run = AsyncMock(return_value=SimpleNamespace(content=content))
    return executor


@pytest.mark.unit
class TestBaseEvaluator:
    """The Evaluator ABC default behavior."""

    def test_should_run_defaults_to_true(self):
        evaluator = _MinimalEvaluator()
        assert evaluator.should_run(is_last_tier=False) is True
        assert evaluator.should_run(is_last_tier=True) is True


@pytest.mark.unit
class TestSemanticEvaluatorGating:
    """should_run() gate behavior."""

    def test_never_gate(self):
        assert SemanticEvaluator(gate="never").should_run(is_last_tier=True) is False

    def test_last_tier_gate(self):
        ev = SemanticEvaluator(gate="last_tier")
        assert ev.should_run(is_last_tier=False) is False
        assert ev.should_run(is_last_tier=True) is True

    def test_always_gate(self):
        ev = SemanticEvaluator(gate="always")
        assert ev.should_run(is_last_tier=False) is True


@pytest.mark.unit
class TestGetExecutor:
    """Lazy executor initialization."""

    def test_lazy_init_and_cache(self):
        ev = SemanticEvaluator()
        sentinel = object()
        with patch(
            "attune.models.empathy_executor.EmpathyLLMExecutor",
            return_value=sentinel,
        ) as MockExec:
            first = ev._get_executor()
            second = ev._get_executor()

        assert first is sentinel
        assert second is sentinel
        # Constructed once (cached on second call), with the anthropic provider.
        MockExec.assert_called_once_with(provider="anthropic")


@pytest.mark.unit
class TestEvaluate:
    """The async evaluate() LLM path."""

    @pytest.mark.asyncio
    async def test_passes_when_llm_says_passed(self):
        ev = SemanticEvaluator()
        ev._executor = _fake_executor('{"passed": true, "failed_criteria": [], "feedback": ""}')

        passed, feedback = await ev.evaluate("task", "a thorough answer")

        assert passed is True
        assert feedback is None

    @pytest.mark.asyncio
    async def test_fails_with_feedback(self):
        ev = SemanticEvaluator()
        ev._executor = _fake_executor('{"passed": false, "feedback": "Missing the conclusion"}')

        passed, feedback = await ev.evaluate("task", "partial answer")

        assert passed is False
        assert feedback is not None
        assert feedback.feedback_type == FeedbackType.SEMANTIC
        assert feedback.validator_name == "SemanticEvaluator"
        assert feedback.message == "Missing the conclusion"
        assert feedback.suggestion == "Missing the conclusion"

    @pytest.mark.asyncio
    async def test_fail_without_feedback_has_no_suggestion(self):
        ev = SemanticEvaluator()
        ev._executor = _fake_executor('{"passed": false}')

        passed, feedback = await ev.evaluate("task", "answer")

        assert passed is False
        assert feedback.suggestion is None
        assert feedback.message == "Semantic evaluation failed"

    @pytest.mark.asyncio
    async def test_dict_response_is_json_encoded(self):
        ev = SemanticEvaluator()
        ev._executor = _fake_executor('{"passed": true}')

        passed, _ = await ev.evaluate("task", {"key": "value"})

        assert passed is True
        # The dict was serialized into the eval prompt, not str()'d.
        sent_prompt = ev._executor.run.call_args.kwargs["prompt"]
        assert '{"key": "value"}' in sent_prompt

    @pytest.mark.asyncio
    async def test_invalid_json_does_not_block(self):
        ev = SemanticEvaluator()
        ev._executor = _fake_executor("not json at all")

        passed, feedback = await ev.evaluate("task", "answer")

        assert passed is True
        assert feedback is None

    @pytest.mark.asyncio
    async def test_executor_exception_does_not_block(self):
        ev = SemanticEvaluator()
        executor = MagicMock()
        executor.run = AsyncMock(side_effect=RuntimeError("LLM down"))
        ev._executor = executor

        passed, feedback = await ev.evaluate("task", "answer")

        assert passed is True
        assert feedback is None
