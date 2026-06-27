"""Declarative-form ↔ AskUserQuestion transforms.

See :mod:`attune.elicitation` for the package overview. This module
holds the three pure functions that build, render, and collect a
declarative form, reusing the surface-agnostic model in
:mod:`attune.meta_workflows.models` (decision D6 — reuse, don't
duplicate).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

from attune.meta_workflows.models import (
    FormQuestion,
    FormResponse,
    FormSchema,
    QuestionType,
)

#: The answer values accepted for a BOOLEAN question (its
#: ``to_ask_user_format`` renders as a Yes/No single-select).
_BOOLEAN_OPTIONS = ("Yes", "No")


class FormValidationError(ValueError):
    """Raised when a form definition or a set of answers is invalid.

    Carries a list of human-readable problems so a caller (or the agent)
    can re-ask exactly the offending fields rather than guess.
    """

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


def form_from_dict(data: dict[str, Any]) -> FormSchema:
    """Build a :class:`FormSchema` from plain serializable data (D3).

    The declarative artifact a skill / future designer / data source
    produces. Validates the form *definition* (not answers) and raises
    :class:`FormValidationError` listing every problem.

    Args:
        data: ``{"title": str, "description"?: str, "fields": [ ... ]}``.
            Each field: ``{"id": str, "text": str, "type": str,
            "options"?: list[str], "default"?: str, "help_text"?: str,
            "required"?: bool}``. ``"label"`` is accepted as an alias for
            ``"text"``; ``"questions"`` as an alias for ``"fields"``.

    Returns:
        A validated :class:`FormSchema`.

    Raises:
        FormValidationError: If the definition is malformed.
    """
    problems: list[str] = []

    if not isinstance(data, dict):
        raise FormValidationError(["form must be a mapping"])

    title = data.get("title")
    if not title or not isinstance(title, str):
        problems.append("form 'title' is required and must be a string")

    raw_fields = data.get("fields", data.get("questions"))
    if not isinstance(raw_fields, list) or not raw_fields:
        problems.append("form must have a non-empty 'fields' list")
        raw_fields = []

    seen_ids: set[str] = set()
    questions: list[FormQuestion] = []
    for idx, raw in enumerate(raw_fields):
        where = f"field[{idx}]"
        if not isinstance(raw, dict):
            problems.append(f"{where} must be a mapping")
            continue

        fid = raw.get("id")
        if not fid or not isinstance(fid, str):
            problems.append(f"{where} 'id' is required and must be a string")
        elif fid in seen_ids:
            problems.append(f"{where} duplicate id {fid!r}")
        else:
            seen_ids.add(fid)

        text = raw.get("text", raw.get("label"))
        if not text or not isinstance(text, str):
            problems.append(f"{where} 'text' (or 'label') is required")

        type_str = raw.get("type")
        try:
            qtype = QuestionType(type_str)
        except ValueError:
            valid = ", ".join(t.value for t in QuestionType)
            problems.append(f"{where} invalid type {type_str!r} (use one of: {valid})")
            continue

        options = raw.get("options", [])
        if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
            problems.append(f"{where} 'options' must be a list of strings")
            options = []
        if qtype in (QuestionType.SINGLE_SELECT, QuestionType.MULTI_SELECT) and not options:
            problems.append(f"{where} type {qtype.value} requires non-empty 'options'")

        if fid and text and isinstance(fid, str) and isinstance(text, str):
            questions.append(
                FormQuestion(
                    id=fid,
                    text=text,
                    type=qtype,
                    options=options,
                    default=raw.get("default"),
                    help_text=raw.get("help_text"),
                    required=bool(raw.get("required", True)),
                )
            )

    if problems:
        raise FormValidationError(problems)

    return FormSchema(
        title=title,
        description=data.get("description", "") or "",
        questions=questions,
    )


def form_to_askuserquestion(form: FormSchema, batch_size: int = 4) -> list[list[dict[str, Any]]]:
    """Render a form to batched ``AskUserQuestion`` payloads.

    Thin reuse of the model's own batching + per-question conversion.
    Each inner list is one ``AskUserQuestion`` call (≤ ``batch_size``
    questions, the tool's limit).

    Args:
        form: The form to render.
        batch_size: Max questions per call (the tool caps at 4).

    Returns:
        A list of batches; each batch a list of question payload dicts.
    """
    return [
        [question.to_ask_user_format() for question in batch]
        for batch in form.get_question_batches(batch_size)
    ]


def _validate_answer(question: FormQuestion, value: Any) -> str | None:
    """Return a problem string for one answer, or None if it is valid."""
    if question.type == QuestionType.MULTI_SELECT:
        if not isinstance(value, list):
            return f"{question.id!r} expects a list (multi-select)"
        bad = [v for v in value if v not in question.options]
        if bad:
            return f"{question.id!r} has out-of-option value(s): {bad}"
        return None

    if question.type == QuestionType.SINGLE_SELECT:
        if value not in question.options:
            return f"{question.id!r} value {value!r} not in options"
        return None

    if question.type == QuestionType.BOOLEAN:
        if value not in _BOOLEAN_OPTIONS:
            return f"{question.id!r} boolean value {value!r} must be 'Yes' or 'No'"
        return None

    # TEXT_INPUT
    if not isinstance(value, str):
        return f"{question.id!r} expects a string"
    return None


def collect_form_response(
    form: FormSchema,
    raw_answers: dict[str, Any],
    template_id: str = "",
) -> FormResponse:
    """Validate raw answers and map them into a :class:`FormResponse`.

    Implements R4 — no silent acceptance of malformed input. A missing
    required field with no default, or a value outside a select's
    options, raises :class:`FormValidationError` naming every problem so
    the caller can re-ask just those fields. Missing optional fields fall
    back to the question's ``default`` (omitted if none).

    Args:
        form: The form the answers are for.
        raw_answers: ``{question_id: value}`` as returned by the agent.
        template_id: Identifier stored on the response.

    Returns:
        A validated :class:`FormResponse`.

    Raises:
        FormValidationError: If any answer is missing-required or invalid.
    """
    problems: list[str] = []
    responses: dict[str, Any] = {}

    for question in form.questions:
        provided = question.id in raw_answers
        value = raw_answers.get(question.id)

        if not provided or value is None or value == "" or value == []:
            if question.required and question.default is None:
                problems.append(f"{question.id!r} is required")
            elif question.default is not None:
                responses[question.id] = question.default
            continue

        problem = _validate_answer(question, value)
        if problem:
            problems.append(problem)
        else:
            responses[question.id] = value

    if problems:
        raise FormValidationError(problems)

    return FormResponse(template_id=template_id, responses=responses)
