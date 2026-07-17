"""Tests for the canonical all-controls reference form.

Guards two invariants:

1. **Completeness** — the reference exercises *every* ``QuestionType``.
   If a new control type is added to the grammar without a field in
   ``REFERENCE_FORM``, ``test_reference_covers_every_control_type``
   fails, so the reference cannot silently fall behind.
2. **Round-trip** — the reference plus its example answers validate
   through the real ``form_from_dict`` → ``collect_form_response`` seams
   (no mocks), and a missing required answer is rejected (R4).
"""

from __future__ import annotations

import pytest

from attune.elicitation import (
    EXAMPLE_ANSWERS,
    REFERENCE_FORM,
    FormValidationError,
    collect_form_response,
    form_from_dict,
    form_to_askuserquestion,
    form_to_elicitation_schema,
    form_to_widget_html,
)
from attune.meta_workflows.models import QuestionType


def test_reference_covers_every_control_type() -> None:
    """The reference must contain exactly one field per QuestionType."""
    field_types = {field["type"] for field in REFERENCE_FORM["fields"]}
    all_types = {qtype.value for qtype in QuestionType}
    assert field_types == all_types, (
        "REFERENCE_FORM drifted from the grammar: "
        f"missing {all_types - field_types}, extra {field_types - all_types}"
    )


def test_reference_form_definition_validates() -> None:
    """form_from_dict accepts the reference and keeps every field."""
    form = form_from_dict(REFERENCE_FORM)
    assert len(form.questions) == len(REFERENCE_FORM["fields"])


def test_example_answers_round_trip() -> None:
    """Valid answers collect into a FormResponse with a join key."""
    form = form_from_dict(REFERENCE_FORM)
    response = collect_form_response(form, EXAMPLE_ANSWERS, template_id="reference-form")

    assert response.template_id == "reference-form"
    assert response.response_id  # auto-populated, non-empty
    # Every field carrying an example answer round-trips.
    for field_id in EXAMPLE_ANSWERS:
        assert field_id in response.responses
    assert response.responses["priority"] == "high"
    assert response.responses["estimated_days"] == 3


def test_missing_required_answer_is_rejected() -> None:
    """R4: dropping a required answer names exactly that field."""
    form = form_from_dict(REFERENCE_FORM)
    answers = {k: v for k, v in EXAMPLE_ANSWERS.items() if k != "priority"}

    with pytest.raises(FormValidationError) as exc_info:
        collect_form_response(form, answers)

    assert any("priority" in problem for problem in exc_info.value.problems)


def test_optional_field_may_be_omitted() -> None:
    """The optional textarea (notes) is not required to collect."""
    form = form_from_dict(REFERENCE_FORM)
    answers = {k: v for k, v in EXAMPLE_ANSWERS.items() if k != "notes"}

    response = collect_form_response(form, answers)
    assert "notes" not in response.responses


def test_reference_casts_to_every_surface() -> None:
    """All three renderers accept the reference without raising."""
    form = form_from_dict(REFERENCE_FORM)

    html = form_to_widget_html(form)
    assert isinstance(html, str) and html

    batches = form_to_askuserquestion(form)
    assert isinstance(batches, list) and batches

    # Native elicitation schema (non-rendering on CC, but must not raise).
    form_to_elicitation_schema(form)
