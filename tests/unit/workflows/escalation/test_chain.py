"""Tests for EscalationChain and related components.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.escalation.chain import EscalationChain
from attune.workflows.escalation.convenience import escalate
from attune.workflows.escalation.evaluator import Evaluator, SemanticEvaluator
from attune.workflows.escalation.models import (
    AttemptResult,
    EscalationResult,
    FeedbackType,
    ValidationFeedback,
)
from attune.workflows.escalation.validators import ConfidenceValidator, StructureValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(content: dict | str, tokens_in: int = 10, tokens_out: int = 20) -> MagicMock:
    """Build a mock LLMResponse."""
    r = MagicMock()
    r.content = json.dumps(content) if isinstance(content, dict) else content
    r.tokens_input = tokens_in
    r.tokens_output = tokens_out
    return r


def _make_executor(*responses) -> MagicMock:
    """Build a mock executor that returns responses in sequence."""
    executor = MagicMock()
    executor.run = AsyncMock(side_effect=list(responses))
    return executor


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestEscalationResult:
    def test_summary_success_no_extras(self):
        result = EscalationResult(
            success=True,
            response={"answer": "42"},
            final_model="claude-haiku-4-5",
        )
        assert result.summary() == "✓ claude-haiku-4-5"

    def test_summary_success_with_retries_and_escalations(self):
        result = EscalationResult(
            success=True,
            response={},
            final_model="claude-sonnet-4-5",
            total_retries=2,
            total_escalations=1,
        )
        assert "2 retry(ies)" in result.summary()
        assert "1 escalation(s)" in result.summary()

    def test_summary_failure(self):
        result = EscalationResult(
            success=False,
            response=None,
            final_model="claude-fable-5",
            attempts=[MagicMock(), MagicMock()],
        )
        assert result.summary().startswith("✗")
        assert "2" in result.summary()


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


class TestStructureValidator:
    def test_passes_with_all_fields(self):
        v = StructureValidator(["answer", "confidence"])
        passed, msg = v.validate({"answer": "42", "confidence": 0.9})
        assert passed is True
        assert msg is None

    def test_fails_missing_field(self):
        v = StructureValidator(["answer", "confidence"])
        passed, msg = v.validate({"answer": "42"})
        assert passed is False
        assert "confidence" in msg

    def test_fails_non_dict(self):
        v = StructureValidator(["answer"])
        passed, msg = v.validate("not a dict")
        assert passed is False
        assert "dict" in msg


class TestConfidenceValidator:
    def test_passes_above_threshold(self):
        v = ConfidenceValidator(min_confidence=0.7)
        passed, msg = v.validate({"confidence": 0.85})
        assert passed is True

    def test_fails_below_threshold(self):
        v = ConfidenceValidator(min_confidence=0.7)
        passed, msg = v.validate({"confidence": 0.5})
        assert passed is False
        assert "0.50" in msg

    def test_fails_missing_confidence(self):
        v = ConfidenceValidator()
        passed, msg = v.validate({"answer": "42"})
        assert passed is False
        assert "missing" in msg.lower()

    def test_fails_non_dict(self):
        v = ConfidenceValidator()
        passed, msg = v.validate("string")
        assert passed is False


# ---------------------------------------------------------------------------
# SemanticEvaluator gate
# ---------------------------------------------------------------------------


class TestSemanticEvaluatorGate:
    def test_gate_always_runs_on_any_tier(self):
        ev = SemanticEvaluator(gate="always")
        assert ev.should_run(is_last_tier=False) is True
        assert ev.should_run(is_last_tier=True) is True

    def test_gate_last_tier_only_runs_on_last(self):
        ev = SemanticEvaluator(gate="last_tier")
        assert ev.should_run(is_last_tier=False) is False
        assert ev.should_run(is_last_tier=True) is True

    def test_gate_never_never_runs(self):
        ev = SemanticEvaluator(gate="never")
        assert ev.should_run(is_last_tier=False) is False
        assert ev.should_run(is_last_tier=True) is False


# ---------------------------------------------------------------------------
# EscalationChain — happy path
# ---------------------------------------------------------------------------


class TestEscalationChainSuccess:
    @pytest.mark.asyncio
    async def test_succeeds_first_attempt(self):
        executor = _make_executor(_mock_response({"answer": "42"}))
        chain = EscalationChain(
            models=["claude-haiku-4-5"],
            validators=[StructureValidator(["answer"])],
            retries_per_model=0,
            executor=executor,
        )
        result = await chain.run("What is 2+2?")
        assert result.success is True
        assert result.response == {"answer": "42"}
        assert result.final_model == "claude-haiku-4-5"
        assert result.total_retries == 0
        assert result.total_escalations == 0

    @pytest.mark.asyncio
    async def test_succeeds_no_validators(self):
        executor = _make_executor(_mock_response({"x": 1}))
        chain = EscalationChain(
            models=["claude-haiku-4-5"],
            retries_per_model=0,
            executor=executor,
        )
        result = await chain.run("Hello")
        assert result.success is True


# ---------------------------------------------------------------------------
# EscalationChain — retries
# ---------------------------------------------------------------------------


class TestEscalationChainRetries:
    @pytest.mark.asyncio
    async def test_retries_on_structural_failure_then_succeeds(self):
        # First response missing field, second has it
        executor = _make_executor(
            _mock_response({"wrong": "field"}),
            _mock_response({"answer": "42"}),
        )
        chain = EscalationChain(
            models=["claude-haiku-4-5"],
            validators=[StructureValidator(["answer"])],
            retries_per_model=1,
            executor=executor,
        )
        result = await chain.run("What is 2+2?")
        assert result.success is True
        assert result.total_retries == 1
        assert executor.run.call_count == 2

    @pytest.mark.asyncio
    async def test_feedback_injected_into_retry_prompt(self):
        executor = _make_executor(
            _mock_response({"wrong": "field"}),
            _mock_response({"answer": "42"}),
        )
        chain = EscalationChain(
            models=["claude-haiku-4-5"],
            validators=[StructureValidator(["answer"])],
            retries_per_model=1,
            executor=executor,
        )
        await chain.run("What is 2+2?")
        # Second call prompt should contain feedback block
        second_call_prompt = executor.run.call_args_list[1][1]["prompt"]
        assert "previous_attempt_feedback" in second_call_prompt
        assert "answer" in second_call_prompt


# ---------------------------------------------------------------------------
# EscalationChain — escalation
# ---------------------------------------------------------------------------


class TestEscalationChainEscalation:
    @pytest.mark.asyncio
    async def test_escalates_after_retries_exhausted(self):
        executor = _make_executor(
            _mock_response({"wrong": "x"}),  # haiku attempt 1
            _mock_response({"wrong": "x"}),  # haiku retry 1
            _mock_response({"answer": "42"}),  # sonnet attempt 1
        )
        chain = EscalationChain(
            models=["claude-haiku-4-5", "claude-sonnet-4-5"],
            validators=[StructureValidator(["answer"])],
            retries_per_model=1,
            executor=executor,
        )
        result = await chain.run("What is 2+2?")
        assert result.success is True
        assert result.final_model == "claude-sonnet-4-5"
        assert result.total_escalations == 1
        assert result.total_retries == 1

    @pytest.mark.asyncio
    async def test_prior_tier_feedback_injected_on_escalation(self):
        executor = _make_executor(
            _mock_response({"wrong": "x"}),  # haiku fails
            _mock_response({"answer": "42"}),  # sonnet succeeds
        )
        chain = EscalationChain(
            models=["claude-haiku-4-5", "claude-sonnet-4-5"],
            validators=[StructureValidator(["answer"])],
            retries_per_model=0,
            executor=executor,
        )
        await chain.run("prompt")
        sonnet_prompt = executor.run.call_args_list[1][1]["prompt"]
        assert "previous_attempt_feedback" in sonnet_prompt

    @pytest.mark.asyncio
    async def test_all_tiers_fail_returns_best_attempt(self):
        executor = _make_executor(
            _mock_response({"partial": "a"}),  # haiku — parsed but fails validator
            _mock_response({"partial": "b"}),  # sonnet — parsed but fails validator
        )
        chain = EscalationChain(
            models=["claude-haiku-4-5", "claude-sonnet-4-5"],
            validators=[StructureValidator(["answer"])],
            retries_per_model=0,
            executor=executor,
        )
        result = await chain.run("prompt")
        assert result.success is False
        assert result.response is not None  # best parsed attempt returned
        assert len(result.attempts) == 2


# ---------------------------------------------------------------------------
# EscalationChain — exception and parse failure handling
# ---------------------------------------------------------------------------


class TestEscalationChainErrors:
    @pytest.mark.asyncio
    async def test_parse_failure_recorded_as_feedback(self):
        bad_response = MagicMock()
        bad_response.content = "not valid json {"
        bad_response.tokens_input = 5
        bad_response.tokens_output = 5

        executor = _make_executor(bad_response, _mock_response({"answer": "ok"}))
        chain = EscalationChain(
            models=["claude-haiku-4-5"],
            validators=[StructureValidator(["answer"])],
            retries_per_model=1,
            executor=executor,
        )
        result = await chain.run("prompt")
        first_attempt = result.attempts[0]
        assert any(fb.feedback_type == FeedbackType.PARSE_FAILURE for fb in first_attempt.feedback)

    @pytest.mark.asyncio
    async def test_api_exception_recorded_and_escalates(self):
        executor = MagicMock()
        executor.run = AsyncMock(
            side_effect=[RuntimeError("connection error"), _mock_response({"answer": "ok"})],
        )
        chain = EscalationChain(
            models=["claude-haiku-4-5", "claude-sonnet-4-5"],
            validators=[StructureValidator(["answer"])],
            retries_per_model=0,
            executor=executor,
        )
        result = await chain.run("prompt")
        assert result.success is True
        first_attempt = result.attempts[0]
        assert any(fb.feedback_type == FeedbackType.EXCEPTION for fb in first_attempt.feedback)


# ---------------------------------------------------------------------------
# EscalationChain — evaluator
# ---------------------------------------------------------------------------


class TestEscalationChainEvaluator:
    @pytest.mark.asyncio
    async def test_evaluator_fires_when_gate_always(self):
        executor = _make_executor(_mock_response({"answer": "42"}))
        mock_evaluator = MagicMock(spec=Evaluator)
        mock_evaluator.should_run.return_value = True
        mock_evaluator.evaluate = AsyncMock(return_value=(True, None))
        mock_evaluator.evaluator_model = "claude-haiku-4-5"

        chain = EscalationChain(
            models=["claude-haiku-4-5"],
            validators=[StructureValidator(["answer"])],
            evaluator=mock_evaluator,
            retries_per_model=0,
            executor=executor,
        )
        result = await chain.run("prompt")
        assert result.success is True
        mock_evaluator.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluator_skipped_when_gate_last_tier_not_last(self):
        executor = _make_executor(
            _mock_response({"answer": "42"}),  # haiku succeeds structurally
            _mock_response({"answer": "42"}),  # sonnet (not needed)
        )
        mock_evaluator = MagicMock(spec=Evaluator)
        mock_evaluator.should_run.side_effect = lambda is_last: is_last
        mock_evaluator.evaluate = AsyncMock(return_value=(True, None))
        mock_evaluator.evaluator_model = "claude-haiku-4-5"

        chain = EscalationChain(
            models=["claude-haiku-4-5", "claude-sonnet-4-5"],
            validators=[StructureValidator(["answer"])],
            evaluator=mock_evaluator,
            retries_per_model=0,
            executor=executor,
        )
        result = await chain.run("prompt")
        # Haiku is not last tier, so evaluator should not have fired
        mock_evaluator.evaluate.assert_not_called()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_evaluator_failure_triggers_retry(self):
        executor = _make_executor(
            _mock_response({"answer": "42"}),
            _mock_response({"answer": "42"}),
        )
        mock_evaluator = MagicMock(spec=Evaluator)
        mock_evaluator.should_run.return_value = True
        mock_evaluator.evaluate = AsyncMock(
            side_effect=[
                (
                    False,
                    ValidationFeedback(
                        feedback_type=FeedbackType.SEMANTIC,
                        validator_name="MockEval",
                        message="Too vague",
                        suggestion="Be more specific.",
                    ),
                ),
                (True, None),
            ],
        )
        mock_evaluator.evaluator_model = "claude-haiku-4-5"

        chain = EscalationChain(
            models=["claude-haiku-4-5"],
            validators=[StructureValidator(["answer"])],
            evaluator=mock_evaluator,
            retries_per_model=1,
            executor=executor,
        )
        result = await chain.run("prompt")
        assert result.success is True
        assert result.total_retries == 1


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------


class TestCostTracking:
    def test_total_cost_sums_attempts(self):
        chain = EscalationChain(models=["claude-haiku-4-5"])
        attempts = [
            AttemptResult(
                model="claude-haiku-4-5",
                attempt_number=1,
                raw_response="{}",
                parsed_response={},
                success=False,
                input_tokens=1000,
                output_tokens=500,
            ),
            AttemptResult(
                model="claude-haiku-4-5",
                attempt_number=2,
                raw_response="{}",
                parsed_response={},
                success=True,
                input_tokens=1000,
                output_tokens=500,
            ),
        ]
        with patch("attune.models.registry.get_model") as mock_get:
            mock_info = MagicMock()
            mock_info.input_cost_per_million = 0.25
            mock_info.output_cost_per_million = 1.25
            mock_get.return_value = mock_info
            cost = chain._total_cost(attempts)
        # 2 attempts × (1000/1M×0.25 + 500/1M×1.25)
        expected = 2 * (1000 / 1_000_000 * 0.25 + 500 / 1_000_000 * 1.25)
        assert abs(cost - expected) < 1e-10


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------


class TestEscalateConvenience:
    @pytest.mark.asyncio
    async def test_retries_defaults_to_zero(self):
        """escalate() with default retries=0 makes exactly one attempt."""
        with patch("attune.workflows.escalation.convenience.EscalationChain") as MockChain:
            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(
                return_value=EscalationResult(success=True, response={}, final_model="haiku"),
            )
            MockChain.return_value = mock_instance
            await escalate("prompt", required_fields=["answer"])
            _, kwargs = MockChain.call_args
            assert kwargs["retries_per_model"] == 0

    @pytest.mark.asyncio
    async def test_structure_validator_added_when_fields_provided(self):
        with patch("attune.workflows.escalation.convenience.EscalationChain") as MockChain:
            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(
                return_value=EscalationResult(success=True, response={}, final_model="haiku"),
            )
            MockChain.return_value = mock_instance
            await escalate("prompt", required_fields=["answer"])
            _, kwargs = MockChain.call_args
            assert any(isinstance(v, StructureValidator) for v in kwargs["validators"])

    @pytest.mark.asyncio
    async def test_evaluator_none_when_use_evaluator_false(self):
        with patch("attune.workflows.escalation.convenience.EscalationChain") as MockChain:
            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(
                return_value=EscalationResult(success=True, response={}, final_model="haiku"),
            )
            MockChain.return_value = mock_instance
            await escalate("prompt")
            _, kwargs = MockChain.call_args
            assert kwargs["evaluator"] is None

    @pytest.mark.asyncio
    async def test_confidence_validator_added_when_min_confidence_provided(self):
        """min_confidence triggers a ConfidenceValidator (covers line 68)."""
        with patch("attune.workflows.escalation.convenience.EscalationChain") as MockChain:
            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(
                return_value=EscalationResult(success=True, response={}, final_model="haiku"),
            )
            MockChain.return_value = mock_instance
            await escalate("prompt", min_confidence=0.8)
            _, kwargs = MockChain.call_args
            assert any(isinstance(v, ConfidenceValidator) for v in kwargs["validators"])
