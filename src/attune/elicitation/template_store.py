"""Form-template library (V7): sculpt a form once, cast per fork.

A recurring fork class is persisted once as a JSON template under
``templates/`` and later invocations load it with per-use slot values.
Each template file is exactly the dict shape :func:`form_from_dict`
accepts, plus a top-level ``"slots"`` list declaring the named
substitution points (``{slot_name}`` placeholders in string fields).
Validation stays in the one existing seam: a malformed template fails
through :class:`FormValidationError` exactly like a hand-built dict,
and slot problems are reported in the same every-problem-listed style.

For the comparability frame, pass the template name as ``template_id``
when collecting answers::

    form = form_from_template("session-contract", {"project": "attune-ai"})
    response = collect_form_response(form, answers, template_id="session-contract")

Responses from the same template are then joinable on
``FormResponse.template_id`` across sessions.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import re
from importlib.resources import files
from typing import Any

from attune.elicitation.bridge import FormValidationError, form_from_dict
from attune.meta_workflows.models import FormSchema

#: Package directory holding the stored templates (monkeypatched in tests).
_TEMPLATE_DIR = files("attune.elicitation") / "templates"

#: Template names are bare kebab-case words — no path separators, so a
#: name can never escape the store directory (path validation for the
#: read below).
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

#: A named substitution point inside a template string field.
_SLOT_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def list_templates() -> list[str]:
    """Return the sorted names of all stored form templates."""
    return sorted(
        entry.name[: -len(".json")]
        for entry in _TEMPLATE_DIR.iterdir()
        if entry.name.endswith(".json")
    )


def form_from_template(name: str, slots: dict[str, Any] | None = None) -> FormSchema:
    """Load a stored template, fill its slots, and validate it.

    Args:
        name: Template name — a ``templates/<name>.json`` store entry
            (see :func:`list_templates`).
        slots: A value for every slot the template declares. Missing or
            extra values are definition errors.

    Returns:
        The validated :class:`FormSchema`.

    Raises:
        FormValidationError: If the name is unknown, the slot values do
            not match the template's declaration, or the substituted
            definition fails :func:`form_from_dict` validation — every
            problem listed.
    """
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise FormValidationError([f"invalid template name {name!r}"])
    available = list_templates()
    if name not in available:
        raise FormValidationError(
            [f"unknown template {name!r} — available: {', '.join(available)}"]
        )
    raw = (_TEMPLATE_DIR / f"{name}.json").read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FormValidationError([f"template {name!r} is not valid JSON: {exc}"]) from exc
    if not isinstance(data, dict):
        raise FormValidationError([f"template {name!r} must be a JSON object"])

    declared = data.pop("slots", [])
    values = slots or {}
    problems = _slot_problems(name, declared, values, data)
    if problems:
        raise FormValidationError(problems)
    return form_from_dict(_substitute(data, values))


def _slot_problems(
    name: str, declared: Any, values: dict[str, Any], data: dict[str, Any]
) -> list[str]:
    """Validate the slot declaration, provided values, and placeholder use."""
    if not isinstance(declared, list) or not all(isinstance(s, str) for s in declared):
        return [f"template {name!r} 'slots' must be a list of strings"]

    problems: list[str] = []
    for missing in sorted(set(declared) - set(values)):
        problems.append(f"missing value for slot '{missing}'")
    for extra in sorted(set(values) - set(declared)):
        problems.append(f"unexpected slot value '{extra}' — template declares: {declared}")
    for slot, value in sorted(values.items()):
        if slot in declared and not isinstance(value, str):
            problems.append(f"slot '{slot}' value must be a string, got {type(value).__name__}")
    for placeholder in sorted(_placeholders(data) - set(declared)):
        problems.append(f"template {name!r} uses undeclared placeholder '{{{placeholder}}}'")
    return problems


def _placeholders(value: Any) -> set[str]:
    """Collect every ``{slot}`` placeholder used in string fields."""
    if isinstance(value, str):
        return set(_SLOT_RE.findall(value))
    if isinstance(value, dict):
        return set().union(set(), *(_placeholders(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(set(), *(_placeholders(v) for v in value))
    return set()


def _substitute(value: Any, slots: dict[str, Any]) -> Any:
    """Replace declared ``{slot}`` placeholders in every string field."""
    if isinstance(value, str):
        return _SLOT_RE.sub(lambda m: str(slots.get(m.group(1), m.group(0))), value)
    if isinstance(value, dict):
        return {k: _substitute(v, slots) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, slots) for v in value]
    return value
