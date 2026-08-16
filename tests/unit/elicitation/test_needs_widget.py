"""Tests for the ``needs_widget`` surface-routing predicate.

Guards three things:

1. **Correctness** — native-eligible forms route to ``AskUserQuestion``
   (False); any rich control or v3–v5 construct forces the widget (True).
2. **The routing set is pinned** — ``_WIDGET_ONLY_TYPES`` is exactly the
   documented set, so a change to it is deliberate.
3. **Every control type is classified** — the widget-only and
   native-eligible sets partition ``QuestionType`` exactly. A new control
   added without a routing decision fails ``test_types_partition``.
"""

from __future__ import annotations

import pytest

from attune.elicitation import REFERENCE_FORM, form_from_dict, needs_widget
from attune.elicitation.bridge import _WIDGET_ONLY_TYPES
from attune.meta_workflows.models import QuestionType

#: The types AskUserQuestion can express natively (the complement of
#: ``_WIDGET_ONLY_TYPES``). Kept here, not imported, so the partition
#: test cross-checks the routing rather than restating it.
_NATIVE_ELIGIBLE_TYPES = {
    QuestionType.TEXT_INPUT,
    QuestionType.SINGLE_SELECT,
    QuestionType.MULTI_SELECT,
    QuestionType.BOOLEAN,
}

#: One minimal, valid form definition per widget-only type.
_WIDGET_ONLY_FORMS: dict[str, dict] = {
    "number": {"id": "n", "type": "number", "text": "How many?", "minimum": 0},
    "date": {"id": "d", "type": "date", "text": "When?"},
    "textarea": {"id": "t", "type": "textarea", "text": "Notes?"},
    "decision": {
        "id": "dec",
        "type": "decision",
        "text": "Which?",
        "options": ["a", "b"],
        "recommended": "a",
    },
    "pushback": {
        "id": "pb",
        "type": "pushback",
        "text": "Reconsider?",
        "options": ["yours", "mine"],
        "user_position": "yours",
        "recommended": "mine",
    },
    "progress": {
        "id": "pr",
        "type": "progress",
        "text": "Which blocker?",
        "options": ["X"],
        "progress_items": [{"label": "X", "status": "blocked"}],
    },
}


def test_native_eligible_form_routes_native() -> None:
    """A form of only selects/boolean/text does not need the widget."""
    form = form_from_dict(
        {
            "title": "native",
            "fields": [
                {"id": "s", "type": "single_select", "text": "Pick", "options": ["a", "b"]},
                {"id": "m", "type": "multi_select", "text": "Pick many", "options": ["a", "b"]},
                {"id": "b", "type": "boolean", "text": "Yes?"},
                {"id": "txt", "type": "text_input", "text": "Name?"},
            ],
        }
    )
    assert needs_widget(form) is False


@pytest.mark.parametrize("type_name", sorted(_WIDGET_ONLY_FORMS))
def test_each_widget_only_type_forces_widget(type_name: str) -> None:
    """Any single widget-only field forces the widget surface."""
    form = form_from_dict({"title": type_name, "fields": [_WIDGET_ONLY_FORMS[type_name]]})
    assert needs_widget(form) is True


def test_one_widget_only_field_among_natives_forces_widget() -> None:
    """A single rich field taints an otherwise-native form."""
    form = form_from_dict(
        {
            "title": "mixed",
            "fields": [
                {"id": "s", "type": "single_select", "text": "Pick", "options": ["a", "b"]},
                {"id": "d", "type": "date", "text": "When?"},
            ],
        }
    )
    assert needs_widget(form) is True


def test_reference_form_needs_widget() -> None:
    """The all-controls reference exercises rich controls, so it routes wide."""
    assert needs_widget(form_from_dict(REFERENCE_FORM)) is True


def test_widget_only_set_is_pinned() -> None:
    """The routing set is exactly the documented eleven — a change is deliberate."""
    assert _WIDGET_ONLY_TYPES == {
        QuestionType.NUMBER,
        QuestionType.DATE,
        QuestionType.TEXTAREA,
        QuestionType.DECISION,
        QuestionType.PUSHBACK,
        QuestionType.PROGRESS,
        QuestionType.DELIBERATION,
        QuestionType.TRIAGE,
        QuestionType.CONFIRM,
        QuestionType.RANKING,
        QuestionType.ASSUMPTION_REVIEW,
    }


def test_types_partition() -> None:
    """Every QuestionType is routed exactly once (drift guard).

    A new control type must be added to one side or the other; until it
    is, this fails — no control silently defaults to a surface.
    """
    all_types = set(QuestionType)
    assert _WIDGET_ONLY_TYPES | _NATIVE_ELIGIBLE_TYPES == all_types
    assert _WIDGET_ONLY_TYPES & _NATIVE_ELIGIBLE_TYPES == set()
