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

import json
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.meta_workflows.models import (
    FormQuestion,
    FormResponse,
    FormSchema,
    QuestionType,
)
from attune.telemetry.form_events import log_surface_decision

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


def _parse_field_identity(
    where: str, raw: dict[str, Any], seen_ids: set[str]
) -> tuple[Any, Any, list[str]]:
    """Parse and validate a field's ``id`` and ``text``/``label``.

    Adds ``fid`` to ``seen_ids`` in place when it is a new, valid id.
    Returns the raw (possibly invalid) ``fid``/``text`` values alongside
    any problems — the caller only builds a :class:`FormQuestion` when
    both turn out to be non-empty strings, mirroring the original
    inline check at the end of the field loop.
    """
    problems: list[str] = []

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

    return fid, text, problems


def _resolve_question_type(where: str, type_str: Any) -> tuple[QuestionType | None, list[str]]:
    """Resolve a field's ``type`` string to a :class:`QuestionType`.

    Returns ``(None, [problem])`` on an unrecognised value. The caller
    must skip the rest of that field's parsing in that case — no
    options/bounds/extras are checked for a field whose type didn't
    resolve, matching the original's ``continue``.
    """
    try:
        return QuestionType(type_str), []
    except ValueError:
        valid = ", ".join(t.value for t in QuestionType)
        return None, [f"{where} invalid type {type_str!r} (use one of: {valid})"]


#: Question types whose control needs at least one option.
_OPTIONS_REQUIRED_TYPES = (
    QuestionType.SINGLE_SELECT,
    QuestionType.MULTI_SELECT,
    QuestionType.DECISION,
    QuestionType.PUSHBACK,
)


def _parse_options(
    where: str, raw: dict[str, Any], qtype: QuestionType
) -> tuple[list[str], list[str]]:
    """Parse ``options`` and enforce non-empty for select-like types."""
    problems: list[str] = []
    options = raw.get("options", [])
    if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
        problems.append(f"{where} 'options' must be a list of strings")
        options = []
    if qtype in _OPTIONS_REQUIRED_TYPES and not options:
        problems.append(f"{where} type {qtype.value} requires non-empty 'options'")
    return options, problems


def _parse_rich_control_constraints(
    where: str, raw: dict[str, Any]
) -> tuple[Any, Any, int | None, list[str]]:
    """Parse the v2.1 rich-control constraints: NUMBER range
    (``minimum``/``maximum``) and TEXT/TEXTAREA length (``max_length``).
    """
    problems: list[str] = []

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

    return minimum, maximum, max_length, problems


def _parse_decision_extras(
    where: str, raw: dict[str, Any], options: list[str]
) -> tuple[str | None, str | None, dict[str, str] | None, list[str]]:
    """Parse the v3 DECISION extras: rationale callout + recommended
    option + per-option tradeoffs. Parsed generically; only DECISION
    renders them. ``recommended`` must be an option; ``option_notes``
    keys too.
    """
    problems: list[str] = []

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

    return rationale, recommended, option_notes, problems


def _parse_user_position(
    where: str, raw: dict[str, Any], options: list[str]
) -> tuple[str | None, list[str]]:
    """Parse the v4 PUSHBACK extra: ``user_position`` — the option that
    is the user's stated approach (tagged "your approach"). Parsed
    generically; only PUSHBACK renders it. Must be one of options when
    set.
    """
    user_position = raw.get("user_position")
    if user_position is not None and not isinstance(user_position, str):
        return None, [f"{where} 'user_position' must be a string"]
    if user_position is not None and options and user_position not in options:
        return user_position, [f"{where} 'user_position' {user_position!r} not in options"]
    return user_position, []


def _parse_progress_style(
    where: str, raw: dict[str, Any], qtype: QuestionType
) -> tuple[str | None, list[str]]:
    """Parse the v5.1 render variant ``progress_style``.

    "report" renders a neutral digest (status = free-form category tag,
    options = any subset of item labels offered as a "go deeper"
    picker). Pure presentation; the answer path is unchanged.
    """
    progress_style = raw.get("progress_style")
    if progress_style is None:
        return None, []
    if progress_style != "report":
        return None, [f"{where} 'progress_style' must be 'report'"]
    if qtype is not QuestionType.PROGRESS:
        return None, [f"{where} 'progress_style' is only valid on progress (got {qtype.value})"]
    return progress_style, []


def _validate_progress_item(
    where: str, idx: int, item: dict[str, Any], progress_style: str | None
) -> tuple[str | None, str | None, list[str]]:
    """Validate one ``progress_items`` entry.

    Returns ``(label_for_all_labels, label_for_blocked_labels,
    problems)``. The two label slots use different validity rules (the
    original's independent conditions, preserved exactly): the first
    requires a non-empty string label; the second only requires
    ``status == "blocked"`` and ``isinstance(label, str)`` — an empty
    string label on a blocked item still counts as blocked.
    """
    problems: list[str] = []
    valid_status = {"done", "in_flight", "blocked"}

    label = item.get("label")
    status = item.get("status")
    valid_label = label if isinstance(label, str) and label else None
    if valid_label is None:
        problems.append(f"{where} progress_items[{idx}] needs a 'label' string")

    if progress_style == "report":
        if not isinstance(status, str) or not status:
            problems.append(
                f"{where} progress_items[{idx}] 'status' must be "
                f"a non-empty tag string in report style"
            )
    elif status not in valid_status:
        problems.append(f"{where} progress_items[{idx}] 'status' must be one of {valid_status}")

    if "detail" in item and not isinstance(item["detail"], str):
        problems.append(f"{where} progress_items[{idx}] 'detail' must be a string")

    blocked_label = label if status == "blocked" and isinstance(label, str) else None
    return valid_label, blocked_label, problems


def _check_progress_item_consistency(
    where: str,
    qtype: QuestionType,
    progress_style: str | None,
    options: list[str],
    all_labels: list[str],
    blocked_labels: list[str],
) -> list[str]:
    """PROGRESS-only cross-check between ``options`` and the parsed
    items: "report" style options must name existing item labels;
    default style options must equal exactly the blocked-item labels.
    """
    if qtype is not QuestionType.PROGRESS:
        return []
    if progress_style == "report":
        stray = [o for o in options if o not in all_labels]
        if stray:
            return [f"{where} PROGRESS report options must be item labels; not items: {stray}"]
        return []
    if set(blocked_labels) != set(options):
        return [
            f"{where} PROGRESS blocked items {sorted(set(blocked_labels))} "
            f"must equal options {sorted(set(options))}"
        ]
    return []


def _parse_progress_items(
    where: str,
    raw: dict[str, Any],
    qtype: QuestionType,
    progress_style: str | None,
    options: list[str],
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    """Parse the v5 PROGRESS extra ``progress_items``: the reported
    items keyed by status. Parsed generically; only PROGRESS renders
    them. Each item is {label, status, detail?}. Default (task) style:
    status in {done, in_flight, blocked}; the blocked subset's labels
    must equal options (the picker offers exactly the actionable
    items). "report" style: status is any non-empty category tag;
    options may be any subset of item labels. Both allow empty options
    (a pure status display).
    """
    progress_items = raw.get("progress_items")
    if progress_items is None:
        if qtype is QuestionType.PROGRESS:
            return None, [f"{where} type progress requires 'progress_items'"]
        return None, []

    if not isinstance(progress_items, list) or not all(
        isinstance(it, dict) for it in progress_items
    ):
        return None, [f"{where} 'progress_items' must be a list of dicts"]

    problems: list[str] = []
    all_labels: list[str] = []
    blocked_labels: list[str] = []
    for idx, item in enumerate(progress_items):
        valid_label, blocked_label, item_problems = _validate_progress_item(
            where, idx, item, progress_style
        )
        problems.extend(item_problems)
        if valid_label is not None:
            all_labels.append(valid_label)
        if blocked_label is not None:
            blocked_labels.append(blocked_label)

    problems.extend(
        _check_progress_item_consistency(
            where, qtype, progress_style, options, all_labels, blocked_labels
        )
    )
    return progress_items, problems


def _parse_progress_extras(
    where: str, raw: dict[str, Any], qtype: QuestionType, options: list[str]
) -> tuple[str | None, list[dict[str, Any]] | None, list[str]]:
    """Parse the v5.1 ``progress_style`` render variant and the v5
    PROGRESS ``progress_items`` payload. ``progress_style`` is resolved
    first so the item validation can branch on it, matching the
    original single-pass order.
    """
    progress_style, style_problems = _parse_progress_style(where, raw, qtype)
    progress_items, item_problems = _parse_progress_items(
        where, raw, qtype, progress_style, options
    )
    return progress_style, progress_items, [*style_problems, *item_problems]


def _parse_list_style(
    where: str, raw: dict[str, Any], qtype: QuestionType
) -> tuple[str | None, list[str]]:
    """Parse the render variant ``list_style``: render select options as
    an ordered/unordered selectable list. Only valid on the select
    types; pure presentation, the answer and its validation are
    unchanged.
    """
    list_style = raw.get("list_style")
    if list_style is None:
        return None, []
    if list_style not in ("ordered", "unordered"):
        return None, [f"{where} 'list_style' must be 'ordered' or 'unordered'"]
    if qtype not in (QuestionType.SINGLE_SELECT, QuestionType.MULTI_SELECT):
        return None, [
            f"{where} 'list_style' is only valid on single_select / "
            f"multi_select (got {qtype.value})"
        ]
    return list_style, []


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

        fid, text, id_problems = _parse_field_identity(where, raw, seen_ids)
        problems.extend(id_problems)

        qtype, type_problems = _resolve_question_type(where, raw.get("type"))
        problems.extend(type_problems)
        if qtype is None:
            continue

        options, options_problems = _parse_options(where, raw, qtype)
        problems.extend(options_problems)

        minimum, maximum, max_length, constraint_problems = _parse_rich_control_constraints(
            where, raw
        )
        problems.extend(constraint_problems)

        rationale, recommended, option_notes, decision_problems = _parse_decision_extras(
            where, raw, options
        )
        problems.extend(decision_problems)

        user_position, position_problems = _parse_user_position(where, raw, options)
        problems.extend(position_problems)

        progress_style, progress_items, progress_problems = _parse_progress_extras(
            where, raw, qtype, options
        )
        problems.extend(progress_problems)

        list_style, list_style_problems = _parse_list_style(where, raw, qtype)
        problems.extend(list_style_problems)

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
                    progress_style=progress_style,
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


#: Question types that lose fidelity on ``AskUserQuestion`` — either
#: because the surface has no control for them at all
#: (:data:`_NO_PORTABLE_CONTROL`) or because the construct's card layout
#: flattens into prose (``decision`` / ``pushback`` / ``progress``).
#: See :func:`needs_widget`.
_WIDGET_ONLY_TYPES = frozenset(
    {
        QuestionType.NUMBER,
        QuestionType.DATE,
        QuestionType.TEXTAREA,
        QuestionType.DECISION,
        QuestionType.PUSHBACK,
        QuestionType.PROGRESS,
    }
)

#: The strict subset with NO portable ``AskUserQuestion`` control at
#: all. A form using any of these cannot be asked on ``AskUserQuestion``
#: in any form — unlike the v3–v5 constructs, which are expressible but
#: lossy (they degrade to a recommendation-first single-select). D21
#: splits these two cases: "impossible" is a hard routing constraint,
#: "lossy" is a fidelity preference the user may override.
_NO_PORTABLE_CONTROL = frozenset(
    {
        QuestionType.NUMBER,
        QuestionType.DATE,
        QuestionType.TEXTAREA,
    }
)

#: An option label longer than this is evidence the author folded
#: tradeoffs into the label text — the thing a card renders properly.
#: Used by :func:`is_trivial_form` as a mechanical "this wanted to be a
#: card" detector (D21, Claude seat).
_TRIVIAL_OPTION_LABEL_MAX = 120

#: Max options a form may carry and still count as trivial. Comparison
#: strain starts around here, and it is also ``AskUserQuestion``'s own
#: practical ceiling for a scannable button row.
_TRIVIAL_MAX_OPTIONS = 3


def needs_widget(form: FormSchema) -> bool:
    """Return True iff ``form`` loses fidelity on ``AskUserQuestion``.

    True when any field is a rich control (``number`` / ``date`` /
    ``textarea``) or a v3–v5 construct (``decision`` / ``pushback`` /
    ``progress``) — the controls that either have no portable
    ``AskUserQuestion`` equivalent or flatten into prose on it.

    .. note::
       This predicate no longer owns the surface decision (D21). It is
       the low-level *controls* check; :func:`select_form_surface` is
       the product-level router and calls this as one input among
       several. Prefer the selector at call sites.

    Args:
        form: The form to inspect.

    Returns:
        True if rendering on ``AskUserQuestion`` would lose fidelity.
    """
    return any(question.type in _WIDGET_ONLY_TYPES for question in form.questions)


def is_trivial_form(form: FormSchema) -> bool:
    """Return True iff ``form`` is small enough that buttons lose nothing.

    Mechanical and deliberately narrow (D21): a form is trivial only
    when it is a single low-ceremony choice with nothing to compare.
    Every clause must hold — one question, a plain select/boolean,
    at most :data:`_TRIVIAL_MAX_OPTIONS` options, and no option label
    long enough to suggest a tradeoff was folded into it.

    The length clause is the load-bearing one: when an author smuggles
    tradeoffs into option text, the strings get long, and that is
    exactly the form that wanted a card.

    Args:
        form: The form to inspect.

    Returns:
        True if the form can go to ``AskUserQuestion`` with no loss.
    """
    if len(form.questions) != 1:
        return False
    question = form.questions[0]
    if question.type not in (QuestionType.SINGLE_SELECT, QuestionType.BOOLEAN):
        return False
    options = question.options or []
    if len(options) > _TRIVIAL_MAX_OPTIONS:
        return False
    return all(len(str(option)) <= _TRIVIAL_OPTION_LABEL_MAX for option in options)


def select_form_surface(
    form: FormSchema,
    *,
    widget_capable: bool = True,
    keyboard_mode: bool = False,
) -> str:
    """Choose the surface to render ``form`` on. Returns ``"widget"`` or ``"ask"``.

    The product-level router (D21). The rich widget is the **default**;
    ``AskUserQuestion`` is the explicit fallback. Latency is not an
    input — the axis is how much of the option space the user can see
    at once, not how many tool calls it costs.

    Precedence, highest first:

    1. **Capability floor** — a client that cannot render widgets gets
       ``"ask"`` regardless of fidelity loss. A constraint, not a
       preference.
    2. **No portable control** — ``number`` / ``date`` / ``textarea``
       have no ``AskUserQuestion`` equivalent, so the widget is forced.
       This outranks ``keyboard_mode`` so the opt-out can never
       silently drop a field.
    3. **Keyboard mode** — the user's opt-out (D17). Applies only to
       forms ``AskUserQuestion`` can actually express, which by this
       point is all that remain.
    4. **Triviality** — see :func:`is_trivial_form`.
    5. Otherwise the widget, which is the default.

    Args:
        form: The form to route.
        widget_capable: Whether the client can render inline HTML.
        keyboard_mode: Whether the user opted into terse/keyboard mode.

    Returns:
        ``"widget"`` or ``"ask"``.
    """
    surface, reason = _route(form, widget_capable=widget_capable, keyboard_mode=keyboard_mode)
    log_surface_decision(surface, reason=reason, question_count=len(form.questions))
    return surface


def _route(
    form: FormSchema,
    *,
    widget_capable: bool,
    keyboard_mode: bool,
) -> tuple[str, str]:
    """Pure routing decision + the reason, for :func:`select_form_surface`.

    Split out so the reason is available to telemetry without the
    caller-facing signature carrying it.
    """
    if not widget_capable:
        return "ask", "client_not_widget_capable"
    if any(question.type in _NO_PORTABLE_CONTROL for question in form.questions):
        return "widget", "no_portable_control"
    if keyboard_mode:
        return "ask", "keyboard_mode"
    if is_trivial_form(form):
        return "ask", "trivial_form"
    return "widget", "default"


#: Values read as "on" / "off" for :func:`keyboard_mode_enabled`.
_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALSEY = frozenset({"0", "false", "no", "off"})

#: Project-local config file the preference persists in. This is the
#: established project-scope convention (``config/loader.py``); we read
#: the one key directly rather than pulling the full unified-config
#: loader into the routing path.
_PROJECT_CONFIG = "attune.config.json"

#: The key holding the preference inside :data:`_PROJECT_CONFIG`.
_KEYBOARD_MODE_KEY = "keyboard_mode"


def _project_keyboard_mode(project_root: Path | None = None) -> bool:
    """Read the persisted per-project preference. False on any problem.

    Best-effort: a missing file, unreadable file, malformed JSON, or
    absent key all mean "not opted in" rather than an error. Surface
    routing must never fail because a config file is bad.
    """
    base = Path(project_root) if project_root is not None else Path.cwd()
    try:
        raw = (base / _PROJECT_CONFIG).read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    value = data.get(_KEYBOARD_MODE_KEY)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUTHY


def keyboard_mode_enabled(project_root: Path | None = None) -> bool:
    """True when the user opted into terse/keyboard mode.

    D17 ratified keyboard mode as an on-demand opt-in available from day
    one — no tenure timer, no per-user tenure state. The chair ruled
    (2026-07-25) that the preference persists **per project**, so it
    lives under ``keyboard_mode`` in the project-local
    ``attune.config.json``.

    ``ATTUNE_KEYBOARD_MODE`` remains a session-scoped override in both
    directions: set it truthy to force terse mode for one shell, or
    falsey to force rich forms even where the project opted out. Unset
    (or unrecognised) defers to the project file.

    Args:
        project_root: Directory holding ``attune.config.json``. Defaults
            to the current working directory.

    Returns:
        True if terse/keyboard mode is on.
    """
    env = os.environ.get("ATTUNE_KEYBOARD_MODE", "").strip().lower()
    if env in _TRUTHY:
        return True
    if env in _FALSEY:
        return False
    return _project_keyboard_mode(project_root)


def form_response_summary(form: FormSchema, response: FormResponse) -> str:
    """Render an answered form as a compact markdown summary.

    The collapse path (chair-ruled 2026-07-25, from the Antigravity
    seat's context-bloat objection): once a form is submitted, the
    multi-kB rendered HTML has done its job and only the question/answer
    pairs still carry meaning. Callers substitute this summary for the
    rendered form so a long session accumulates a few lines per ask
    instead of a screenful of markup.

    Unanswered questions are omitted — the summary reports what was
    decided, not what was displayed. List answers (multi-select) join
    with commas; booleans render Yes/No.

    Args:
        form: The form that was asked.
        response: The validated response to it.

    Returns:
        A markdown summary. Title line plus one bullet per answer.
    """
    lines = [f"**{form.title}** — answered ({response.response_id})"]
    for question in form.questions:
        if question.id not in response.responses:
            continue
        value = response.responses[question.id]
        if isinstance(value, bool):
            rendered = "Yes" if value else "No"
        elif isinstance(value, list):
            rendered = ", ".join(str(item) for item in value) or "(none)"
        else:
            rendered = str(value)
        lines.append(f"- {question.text}: **{rendered}**")
    return "\n".join(lines)


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


def _validate_multi_select(question: FormQuestion, value: Any) -> str | None:
    """MULTI_SELECT: value must be a list whose entries are all options."""
    if not isinstance(value, list):
        return f"{question.id!r} expects a list (multi-select)"
    bad = [v for v in value if v not in question.options]
    if bad:
        return f"{question.id!r} has out-of-option value(s): {bad}"
    return None


def _validate_membership(question: FormQuestion, value: Any) -> str | None:
    """SINGLE_SELECT / DECISION / PUSHBACK / PROGRESS: value in options.

    PROGRESS: a provided answer is one selected blocked item, validated
    by membership. When nothing is blocked the form is built display-
    only (required=False, empty options) and no answer is collected.
    """
    if value not in question.options:
        return f"{question.id!r} value {value!r} not in options"
    return None


def _validate_boolean(question: FormQuestion, value: Any) -> str | None:
    """BOOLEAN: value must be exactly one of ``_BOOLEAN_OPTIONS``."""
    if value not in _BOOLEAN_OPTIONS:
        return f"{question.id!r} boolean value {value!r} must be 'Yes' or 'No'"
    return None


def _validate_number(question: FormQuestion, value: Any) -> str | None:
    """NUMBER: value must be numeric and within [minimum, maximum]."""
    if not _is_number(value):
        return f"{question.id!r} expects a number"
    if question.minimum is not None and value < question.minimum:
        return f"{question.id!r} {value} is below minimum {question.minimum}"
    if question.maximum is not None and value > question.maximum:
        return f"{question.id!r} {value} is above maximum {question.maximum}"
    return None


def _validate_date(question: FormQuestion, value: Any) -> str | None:
    """DATE: value must parse as ``_DATE_FORMAT`` (YYYY-MM-DD)."""
    if not isinstance(value, str):
        return f"{question.id!r} expects an ISO date string (YYYY-MM-DD)"
    try:
        datetime.strptime(value, _DATE_FORMAT)
    except ValueError:
        return f"{question.id!r} {value!r} is not a valid YYYY-MM-DD date"
    return None


def _validate_text(question: FormQuestion, value: Any) -> str | None:
    """TEXT_INPUT / TEXTAREA (and the fallback for any other type): a
    string, optionally bounded by ``max_length``.
    """
    if not isinstance(value, str):
        return f"{question.id!r} expects a string"
    if question.max_length is not None and len(value) > question.max_length:
        return f"{question.id!r} exceeds max_length {question.max_length}"
    return None


#: Per-type answer validators; a type not present here (TEXT_INPUT,
#: TEXTAREA) falls back to ``_validate_text``, matching the original's
#: unconditional string-check tail.
_ANSWER_VALIDATORS: dict[QuestionType, Callable[[FormQuestion, Any], str | None]] = {
    QuestionType.MULTI_SELECT: _validate_multi_select,
    QuestionType.SINGLE_SELECT: _validate_membership,
    QuestionType.DECISION: _validate_membership,
    QuestionType.PUSHBACK: _validate_membership,
    QuestionType.PROGRESS: _validate_membership,
    QuestionType.BOOLEAN: _validate_boolean,
    QuestionType.NUMBER: _validate_number,
    QuestionType.DATE: _validate_date,
}


def _validate_answer(question: FormQuestion, value: Any) -> str | None:
    """Return a problem string for one answer, or None if it is valid."""
    handler = _ANSWER_VALIDATORS.get(question.type, _validate_text)
    return handler(question, value)


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
