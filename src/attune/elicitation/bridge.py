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

from datetime import datetime
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

#: ISO-8601 calendar-date format used by DATE questions.
_DATE_FORMAT = "%Y-%m-%d"


def _is_number(value: Any) -> bool:
    """True if ``value`` is a real number (int or float, but not bool)."""
    return isinstance(value, int | float) and not isinstance(value, bool)


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
        if (
            qtype
            in (
                QuestionType.SINGLE_SELECT,
                QuestionType.MULTI_SELECT,
                QuestionType.DECISION,
                QuestionType.PUSHBACK,
            )
            and not options
        ):
            problems.append(f"{where} type {qtype.value} requires non-empty 'options'")

        # v2.1 rich-control constraints (number range, text length).
        minimum = raw.get("minimum")
        if minimum is not None and not _is_number(minimum):
            problems.append(f"{where} 'minimum' must be a number")
            minimum = None
        maximum = raw.get("maximum")
        if maximum is not None and not _is_number(maximum):
            problems.append(f"{where} 'maximum' must be a number")
            maximum = None
        if _is_number(minimum) and _is_number(maximum) and minimum > maximum:
            problems.append(f"{where} 'minimum' {minimum} exceeds 'maximum' {maximum}")
        max_length = raw.get("max_length")
        if max_length is not None and (
            not isinstance(max_length, int) or isinstance(max_length, bool) or max_length <= 0
        ):
            problems.append(f"{where} 'max_length' must be a positive integer")
            max_length = None

        # v3 DECISION extras: rationale callout + recommended option +
        # per-option tradeoffs. Parsed generically; only DECISION renders
        # them. recommended must be an option; option_notes keys too.
        rationale = raw.get("rationale")
        if rationale is not None and not isinstance(rationale, str):
            problems.append(f"{where} 'rationale' must be a string")
            rationale = None
        recommended = raw.get("recommended")
        if recommended is not None and not isinstance(recommended, str):
            problems.append(f"{where} 'recommended' must be a string")
            recommended = None
        elif recommended is not None and options and recommended not in options:
            problems.append(f"{where} 'recommended' {recommended!r} not in options")
        option_notes = raw.get("option_notes")
        if option_notes is not None and (
            not isinstance(option_notes, dict)
            or not all(isinstance(k, str) and isinstance(v, str) for k, v in option_notes.items())
        ):
            problems.append(f"{where} 'option_notes' must be a map of strings")
            option_notes = None
        elif isinstance(option_notes, dict) and options:
            stray = [k for k in option_notes if k not in options]
            if stray:
                problems.append(f"{where} 'option_notes' keys not in options: {stray}")

        # v4 PUSHBACK extra: user_position — the option that is the user's
        # stated approach (tagged "your approach"). Parsed generically; only
        # PUSHBACK renders it. Must be one of options when set.
        user_position = raw.get("user_position")
        if user_position is not None and not isinstance(user_position, str):
            problems.append(f"{where} 'user_position' must be a string")
            user_position = None
        elif user_position is not None and options and user_position not in options:
            problems.append(f"{where} 'user_position' {user_position!r} not in options")

        # v5 PROGRESS extra: progress_items — the reported items keyed by
        # status. Parsed generically; only PROGRESS renders them. Each item
        # is {label, status, detail?}; status ∈ {done, in_flight, blocked};
        # the blocked subset's labels must equal options (the picker offers
        # exactly the actionable items). PROGRESS allows empty options (when
        # nothing is blocked it degrades to a pure status display).
        progress_items = raw.get("progress_items")
        if progress_items is not None:
            if not isinstance(progress_items, list) or not all(
                isinstance(it, dict) for it in progress_items
            ):
                problems.append(f"{where} 'progress_items' must be a list of dicts")
                progress_items = None
            else:
                valid_status = {"done", "in_flight", "blocked"}
                blocked_labels = []
                for progress_idx, item in enumerate(progress_items):
                    label = item.get("label")
                    status = item.get("status")
                    if not isinstance(label, str) or not label:
                        problems.append(
                            f"{where} progress_items[{progress_idx}] needs a 'label' string"
                        )
                    if status not in valid_status:
                        problems.append(
                            f"{where} progress_items[{progress_idx}] 'status' must be one of {valid_status}"
                        )
                    if "detail" in item and not isinstance(item["detail"], str):
                        problems.append(
                            f"{where} progress_items[{progress_idx}] 'detail' must be a string"
                        )
                    if status == "blocked" and isinstance(label, str):
                        blocked_labels.append(label)
                if qtype is QuestionType.PROGRESS and set(blocked_labels) != set(options):
                    problems.append(
                        f"{where} PROGRESS blocked items {sorted(set(blocked_labels))} "
                        f"must equal options {sorted(set(options))}"
                    )
        elif qtype is QuestionType.PROGRESS:
            problems.append(f"{where} type progress requires 'progress_items'")

        # Render variant: list_style — render select options as an
        # ordered/unordered selectable list. Only valid on the select types;
        # pure presentation, the answer and its validation are unchanged.
        list_style = raw.get("list_style")
        if list_style is not None:
            if list_style not in ("ordered", "unordered"):
                problems.append(f"{where} 'list_style' must be 'ordered' or 'unordered'")
                list_style = None
            elif qtype not in (QuestionType.SINGLE_SELECT, QuestionType.MULTI_SELECT):
                problems.append(
                    f"{where} 'list_style' is only valid on single_select / "
                    f"multi_select (got {qtype.value})"
                )
                list_style = None

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
                    minimum=minimum,
                    maximum=maximum,
                    max_length=max_length,
                    rationale=rationale,
                    option_notes=option_notes,
                    recommended=recommended,
                    user_position=user_position,
                    progress_items=progress_items,
                    list_style=list_style,
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

    if question.type in (
        QuestionType.SINGLE_SELECT,
        QuestionType.DECISION,
        QuestionType.PUSHBACK,
        # PROGRESS: a provided answer is one selected blocked item, validated
        # by membership. When nothing is blocked the form is built display-
        # only (required=False, empty options) and no answer is collected.
        QuestionType.PROGRESS,
    ):
        if value not in question.options:
            return f"{question.id!r} value {value!r} not in options"
        return None

    if question.type == QuestionType.BOOLEAN:
        if value not in _BOOLEAN_OPTIONS:
            return f"{question.id!r} boolean value {value!r} must be 'Yes' or 'No'"
        return None

    if question.type == QuestionType.NUMBER:
        if not _is_number(value):
            return f"{question.id!r} expects a number"
        if question.minimum is not None and value < question.minimum:
            return f"{question.id!r} {value} is below minimum {question.minimum}"
        if question.maximum is not None and value > question.maximum:
            return f"{question.id!r} {value} is above maximum {question.maximum}"
        return None

    if question.type == QuestionType.DATE:
        if not isinstance(value, str):
            return f"{question.id!r} expects an ISO date string (YYYY-MM-DD)"
        try:
            datetime.strptime(value, _DATE_FORMAT)
        except ValueError:
            return f"{question.id!r} {value!r} is not a valid YYYY-MM-DD date"
        return None

    # TEXT_INPUT / TEXTAREA — a string, optionally length-bounded.
    if not isinstance(value, str):
        return f"{question.id!r} expects a string"
    if question.max_length is not None and len(value) > question.max_length:
        return f"{question.id!r} exceeds max_length {question.max_length}"
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
