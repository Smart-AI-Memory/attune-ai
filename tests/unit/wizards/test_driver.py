"""Tests for the Claude-driven wizard driver (Phase 1).

Covers ``BaseWizard.list_steps()`` and
``attune.wizards.driver`` (``prefilled_answer_callback``,
``describe_wizard_steps``, ``run_wizard_prefilled``) — the
interactive-orchestration-access bridge.

All wizard *runs* here use offline fakes (question + confirm steps only,
no ``llm_call``), so the suite never makes a real API call.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext
from attune.wizards import (
    WizardConfig,
    describe_wizard_steps,
    list_wizards,
    prefilled_answer_callback,
    run_wizard_prefilled,
)
from attune.wizards.base import BaseWizard, StepType, WizardStep


class _FakeWizard(BaseWizard):
    """Minimal question -> confirm wizard — runs fully offline (no LLM)."""

    config = WizardConfig(wizard_id="fake-test", name="Fake", description="t")
    steps = [
        WizardStep(
            id="ask",
            name="Ask",
            description="gather",
            step_type=StepType.QUESTION,
            questions=[FormQuestion(id="topic", text="What topic?", type=QuestionType.TEXT_INPUT)],
        ),
        WizardStep(
            id="confirm",
            name="Confirm",
            description="ok?",
            step_type=StepType.CONFIRM,
        ),
    ]

    def build_prompt_context(self, step: WizardStep) -> PromptContext:  # pragma: no cover
        return PromptContext(role="r", goal="g", instructions="i")

    def process_step_result(self, step, result):  # pragma: no cover
        pass


@pytest.fixture
def registered_fake():
    """Register ``_FakeWizard`` for the duration of a test, then remove it."""
    from attune.wizards import register_wizard
    from attune.wizards.registry import _WIZARD_REGISTRY

    register_wizard("fake-test", _FakeWizard)
    yield "fake-test"
    _WIZARD_REGISTRY.pop("fake-test", None)


@pytest.mark.unit
class TestListSteps:
    def test_list_steps_shape(self) -> None:
        views = _FakeWizard().list_steps()
        assert [v["id"] for v in views] == ["ask", "confirm"]
        assert views[0]["type"] == "question"
        assert views[1]["type"] == "confirm"

    def test_question_step_carries_questions(self) -> None:
        views = _FakeWizard().list_steps()
        assert "questions" in views[0]
        assert views[0]["questions"][0]["question_id"] == "topic"

    def test_non_question_step_has_no_questions(self) -> None:
        views = _FakeWizard().list_steps()
        assert "questions" not in views[1]


@pytest.mark.unit
class TestPrefilledAnswerCallback:
    def test_returns_known_answers(self) -> None:
        cb = prefilled_answer_callback({"topic": "auth", "scope": "src"})
        out = cb([{"question_id": "topic"}, {"question_id": "scope"}])
        assert out == {"topic": "auth", "scope": "src"}

    def test_omits_unknown_questions(self) -> None:
        """A review/confirm approval with no pre-supplied answer is omitted
        so the engine falls back to that step's default."""
        cb = prefilled_answer_callback({"topic": "auth"})
        out = cb([{"question_id": "topic"}, {"question_id": "review_approval"}])
        assert out == {"topic": "auth"}
        assert "review_approval" not in out

    def test_falls_back_to_header_or_question_key(self) -> None:
        cb = prefilled_answer_callback({"H": "v"})
        assert cb([{"header": "H"}]) == {"H": "v"}


@pytest.mark.unit
class TestDescribe:
    def test_describe_wizard_steps_for_real_wizard(self) -> None:
        """Introspection only — no run, so no API calls."""
        steps = describe_wizard_steps("debug")
        assert len(steps) >= 1
        assert all("id" in s and "type" in s for s in steps)

    def test_describe_unknown_wizard_raises(self) -> None:
        with pytest.raises(KeyError):
            describe_wizard_steps("does-not-exist")


@pytest.mark.unit
class TestRunPrefilled:
    async def test_run_unknown_wizard_raises(self) -> None:
        with pytest.raises(KeyError):
            await run_wizard_prefilled("does-not-exist")

    async def test_run_offline_fake_via_registry(self, registered_fake: str) -> None:
        """Drive a registered offline wizard end-to-end with prefilled
        answers; question resolves from the callback, confirm auto-proceeds."""
        result = await run_wizard_prefilled(
            registered_fake,
            answers={"topic": "auth"},
            initial_context={},
        )
        assert result.wizard_id == registered_fake
        assert result.success is True
        assert "ask" in result.steps_completed
        assert result.collected_data.get("topic") == "auth"

    async def test_run_direct_instantiation_offline(self) -> None:
        """Same path without the registry — prefilled callback + run()."""
        wizard = _FakeWizard(ask_user_callback=prefilled_answer_callback({"topic": "x"}))
        result = await wizard.run({})
        assert result.success is True
        assert result.collected_data.get("topic") == "x"

    def test_at_least_one_real_wizard_is_registered(self) -> None:
        assert len(list_wizards()) >= 1
