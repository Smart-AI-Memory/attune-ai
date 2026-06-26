"""Regression coverage for the confirm/review FormQuestion enum bug.

``_run_confirm_step`` / ``_run_review_step`` once built
``FormQuestion(type="single_select")`` with a plain string, but
``to_ask_user_format()`` calls ``self.type.value`` — so every confirm
and review step raised ``AttributeError`` the moment the engine tried to
render it. The existing ``test_wizard_core`` confirm/review tests mocked
the form response *above* ``to_ask_user_format()``, so the bug shipped
uncaught until a wizard was actually run end-to-end (#1091).

These tests run a wizard with confirm and review steps through the REAL
``BaseWizard.run()`` path with a plain callback (no mock above the format
seam), so a regression to a bare-string ``type=`` fails loudly here.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any

import pytest

from attune.meta_workflows.models import FormQuestion, QuestionType
from attune.prompts import PromptContext
from attune.wizards.base import BaseWizard, StepType, WizardConfig, WizardStep


def _answer(questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Resolve the question step; leave confirm/review to their defaults."""
    out: dict[str, Any] = {}
    for q in questions:
        qid = q.get("question_id") or q.get("header") or q.get("question")
        if qid == "topic":
            out[qid] = "auth"
    return out


class _ConfirmWizard(BaseWizard):
    """Minimal question -> confirm wizard — runs fully offline (no LLM)."""

    config = WizardConfig(wizard_id="confirm-test", name="Confirm", description="t")
    steps = [
        WizardStep(
            id="ask",
            name="Ask",
            description="gather",
            step_type=StepType.QUESTION,
            questions=[FormQuestion(id="topic", text="What topic?", type=QuestionType.TEXT_INPUT)],
        ),
        WizardStep(id="confirm", name="Confirm", description="ok?", step_type=StepType.CONFIRM),
    ]

    def build_prompt_context(self, step: WizardStep) -> PromptContext:  # pragma: no cover
        return PromptContext(role="r", goal="g", instructions="i")

    def process_step_result(self, step, result):  # pragma: no cover
        pass


@pytest.mark.unit
class TestConfirmReviewFormQuestionEnum:
    """The confirm/review FormQuestion must use a QuestionType enum, not a
    bare string — else ``to_ask_user_format()`` raises AttributeError."""

    async def test_confirm_step_runs_without_attribute_error(self) -> None:
        wizard = _ConfirmWizard(ask_user_callback=_answer)
        result = await wizard.run({})
        assert result.success is True
        assert "confirm" in result.steps_completed
        assert result.collected_data.get("topic") == "auth"

    def test_confirm_form_question_renders(self) -> None:
        """The exact failure mode: to_ask_user_format() on a SINGLE_SELECT."""
        q = FormQuestion(
            id="confirm",
            text="Proceed?",
            type=QuestionType.SINGLE_SELECT,
            options=["Yes, proceed", "No, cancel"],
            default="Yes, proceed",
        )
        rendered = q.to_ask_user_format()
        assert rendered["question_id"] == "confirm"
