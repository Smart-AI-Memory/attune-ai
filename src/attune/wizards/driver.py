"""Claude-driven driving helpers for interactive wizards.

The wizards run on an interactive engine (``BaseWizard.run()`` pauses on
``QUESTION``/``REVIEW``/``CONFIRM`` steps to collect human input). A
single-shot tool cannot drive that pause/resume, so the shipped
``wizard`` skill drives it from the model side:

1. ``describe_wizard_steps(wizard_id)`` — show the user what the wizard
   does and which questions it will ask (no engine run).
2. The model collects the ``QUESTION``-step answers via
   ``AskUserQuestion``.
3. ``run_wizard_prefilled(wizard_id, answers, initial_context)`` — run
   the wizard once with those answers supplied through the engine's
   existing ``ask_user_callback`` seam.

Questions with no pre-supplied answer (a ``REVIEW``/``CONFIRM`` step's
approval prompt) are omitted, so the engine falls back to that step's
own default (proceed / approve). Full mid-run review interactivity is a
documented follow-on; see ``docs/specs/interactive-orchestration-access``.
"""

from __future__ import annotations

from typing import Any

from attune.meta_workflows.form_engine import AskUserQuestionCallback

from .base import BaseWizard, WizardResult
from .registry import get_wizard


def prefilled_answer_callback(answers: dict[str, Any]) -> AskUserQuestionCallback:
    """Build an ``ask_user_callback`` that returns pre-collected answers.

    Args:
        answers: Mapping of ``question_id`` to the user's answer, collected
            by the model up front.

    Returns:
        A callback matching ``AskUserQuestionCallback`` that, given a batch
        of questions, returns the pre-supplied answer for each question it
        recognises and omits the rest (letting the engine apply that
        step's default).

    """

    def _callback(questions: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for q in questions:
            qid = q.get("question_id") or q.get("header") or q.get("question")
            if qid in answers:
                out[qid] = answers[qid]
        return out

    return _callback


def _resolve_wizard_class(wizard_id: str) -> type[BaseWizard]:
    """Resolve a registered wizard class by id or raise ``KeyError``."""
    cls = get_wizard(wizard_id)
    if cls is None:
        raise KeyError(f"Unknown wizard: {wizard_id!r}")
    return cls


def describe_wizard_steps(wizard_id: str) -> list[dict[str, Any]]:
    """Return the declarative step views for a registered wizard.

    Args:
        wizard_id: A registered wizard id (e.g. ``"debug"``).

    Returns:
        The list produced by ``BaseWizard.list_steps()``.

    Raises:
        KeyError: If ``wizard_id`` is not registered.

    """
    return _resolve_wizard_class(wizard_id)().list_steps()


async def run_wizard_prefilled(
    wizard_id: str,
    answers: dict[str, Any] | None = None,
    initial_context: dict[str, Any] | None = None,
) -> WizardResult:
    """Run a registered wizard with pre-collected answers (non-interactive).

    Args:
        wizard_id: A registered wizard id.
        answers: ``question_id`` -> answer collected up front by the model.
        initial_context: Optional starting context (e.g. a file path).

    Returns:
        The ``WizardResult`` from the completed run.

    Raises:
        KeyError: If ``wizard_id`` is not registered.

    """
    cls = _resolve_wizard_class(wizard_id)
    wizard = cls(ask_user_callback=prefilled_answer_callback(answers or {}))
    return await wizard.run(initial_context or {})
