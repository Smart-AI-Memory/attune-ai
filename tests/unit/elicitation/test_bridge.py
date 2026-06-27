"""Tests for the elicitation declarative-form bridge.

Covers:

- form_from_dict: construction, aliases, and every validation problem
- form_to_askuserquestion: ≤4 batching + per-type payload shape
- collect_form_response: valid answers, defaults, and every reject path
- FormValidationError carries the problem list
"""

from __future__ import annotations

import pytest

from attune.elicitation import (
    FormValidationError,
    collect_form_response,
    form_from_dict,
    form_to_askuserquestion,
)
from attune.meta_workflows.models import QuestionType


def _form_dict(**overrides):
    base = {
        "title": "Intake",
        "description": "test",
        "fields": [
            {"id": "outcome", "text": "Outcome?", "type": "text_input"},
            {
                "id": "approach",
                "text": "Approach?",
                "type": "single_select",
                "options": ["spec", "inline"],
            },
            {
                "id": "concerns",
                "text": "Concerns?",
                "type": "multi_select",
                "options": ["impl", "test", "docs"],
            },
            {"id": "specfirst", "text": "Spec-first?", "type": "boolean"},
        ],
    }
    base.update(overrides)
    return base


# --- form_from_dict ---------------------------------------------------


class TestFormFromDict:
    def test_builds_all_types(self):
        form = form_from_dict(_form_dict())
        assert form.title == "Intake"
        assert [q.id for q in form.questions] == [
            "outcome",
            "approach",
            "concerns",
            "specfirst",
        ]
        assert form.questions[2].type == QuestionType.MULTI_SELECT

    def test_label_and_questions_aliases(self):
        data = {
            "title": "T",
            "questions": [{"id": "a", "label": "A?", "type": "text_input"}],
        }
        form = form_from_dict(data)
        assert form.questions[0].text == "A?"

    def test_optional_attrs_passthrough(self):
        data = {
            "title": "T",
            "fields": [
                {
                    "id": "a",
                    "text": "A?",
                    "type": "text_input",
                    "default": "x",
                    "help_text": "h",
                    "required": False,
                }
            ],
        }
        q = form_from_dict(data).questions[0]
        assert q.default == "x" and q.help_text == "h" and q.required is False

    def test_not_a_mapping(self):
        with pytest.raises(FormValidationError, match="mapping"):
            form_from_dict(["nope"])  # type: ignore[arg-type]

    def test_missing_title(self):
        with pytest.raises(FormValidationError, match="title"):
            form_from_dict(_form_dict(title=""))

    def test_empty_fields(self):
        with pytest.raises(FormValidationError, match="non-empty 'fields'"):
            form_from_dict({"title": "T", "fields": []})

    def test_field_not_mapping(self):
        with pytest.raises(FormValidationError, match=r"field\[0\] must be a mapping"):
            form_from_dict({"title": "T", "fields": ["x"]})

    def test_missing_id_and_text(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict({"title": "T", "fields": [{"type": "text_input"}]})
        assert any("'id'" in p for p in exc.value.problems)
        assert any("'text'" in p for p in exc.value.problems)

    def test_duplicate_id(self):
        data = {
            "title": "T",
            "fields": [
                {"id": "a", "text": "A?", "type": "text_input"},
                {"id": "a", "text": "B?", "type": "text_input"},
            ],
        }
        with pytest.raises(FormValidationError, match="duplicate id"):
            form_from_dict(data)

    def test_invalid_type(self):
        with pytest.raises(FormValidationError, match="invalid type"):
            form_from_dict({"title": "T", "fields": [{"id": "a", "text": "A?", "type": "slider"}]})

    def test_select_requires_options(self):
        with pytest.raises(FormValidationError, match="requires non-empty 'options'"):
            form_from_dict(
                {"title": "T", "fields": [{"id": "a", "text": "A?", "type": "single_select"}]}
            )

    def test_options_must_be_list_of_strings(self):
        with pytest.raises(FormValidationError, match="list of strings"):
            form_from_dict(
                {
                    "title": "T",
                    "fields": [
                        {"id": "a", "text": "A?", "type": "single_select", "options": [1, 2]}
                    ],
                }
            )


# --- form_to_askuserquestion ------------------------------------------


class TestFormToAskUserQuestion:
    def test_batches_at_four(self):
        fields = [{"id": f"q{i}", "text": f"Q{i}?", "type": "text_input"} for i in range(9)]
        form = form_from_dict({"title": "T", "fields": fields})
        batches = form_to_askuserquestion(form)
        assert [len(b) for b in batches] == [4, 4, 1]

    def test_payload_shapes_per_type(self):
        form = form_from_dict(_form_dict())
        flat = [q for batch in form_to_askuserquestion(form) for q in batch]
        by_id = {q["question_id"]: q for q in flat}
        assert by_id["concerns"]["type"] == "multi_select"
        assert by_id["approach"]["options"] == ["spec", "inline"]
        # boolean renders as a Yes/No single-select
        assert by_id["specfirst"]["type"] == "single_select"
        assert by_id["specfirst"]["options"] == ["Yes", "No"]

    def test_custom_batch_size(self):
        form = form_from_dict(_form_dict())
        batches = form_to_askuserquestion(form, batch_size=2)
        assert [len(b) for b in batches] == [2, 2]


# --- collect_form_response --------------------------------------------


class TestCollectFormResponse:
    def test_valid_answers(self):
        form = form_from_dict(_form_dict())
        resp = collect_form_response(
            form,
            {
                "outcome": "ship it",
                "approach": "spec",
                "concerns": ["impl", "test"],
                "specfirst": "Yes",
            },
            template_id="t1",
        )
        assert resp.template_id == "t1"
        assert resp.responses["concerns"] == ["impl", "test"]
        assert resp.get("approach") == "spec"

    def test_missing_required_raises(self):
        form = form_from_dict(_form_dict())
        with pytest.raises(FormValidationError, match="'outcome' is required"):
            collect_form_response(form, {"approach": "spec", "concerns": [], "specfirst": "No"})

    def test_optional_missing_uses_default(self):
        data = {
            "title": "T",
            "fields": [
                {
                    "id": "a",
                    "text": "A?",
                    "type": "text_input",
                    "required": False,
                    "default": "fallback",
                }
            ],
        }
        form = form_from_dict(data)
        resp = collect_form_response(form, {})
        assert resp.responses["a"] == "fallback"

    def test_optional_missing_no_default_omitted(self):
        data = {
            "title": "T",
            "fields": [{"id": "a", "text": "A?", "type": "text_input", "required": False}],
        }
        resp = collect_form_response(form_from_dict(data), {})
        assert "a" not in resp.responses

    def test_multiselect_non_list_rejected(self):
        form = form_from_dict(_form_dict())
        with pytest.raises(FormValidationError, match="expects a list"):
            collect_form_response(
                form,
                {"outcome": "x", "approach": "spec", "concerns": "impl", "specfirst": "No"},
            )

    def test_multiselect_out_of_option_rejected(self):
        form = form_from_dict(_form_dict())
        with pytest.raises(FormValidationError, match="out-of-option"):
            collect_form_response(
                form,
                {"outcome": "x", "approach": "spec", "concerns": ["nope"], "specfirst": "No"},
            )

    def test_single_select_out_of_option_rejected(self):
        form = form_from_dict(_form_dict())
        with pytest.raises(FormValidationError, match="not in options"):
            collect_form_response(
                form,
                {"outcome": "x", "approach": "wat", "concerns": [], "specfirst": "No"},
            )

    def test_boolean_invalid_rejected(self):
        form = form_from_dict(_form_dict())
        with pytest.raises(FormValidationError, match="must be 'Yes' or 'No'"):
            collect_form_response(
                form,
                {"outcome": "x", "approach": "spec", "concerns": [], "specfirst": "maybe"},
            )

    def test_text_non_string_rejected(self):
        form = form_from_dict(_form_dict())
        with pytest.raises(FormValidationError, match="expects a string"):
            collect_form_response(
                form,
                {"outcome": 123, "approach": "spec", "concerns": [], "specfirst": "No"},
            )

    def test_multiple_problems_collected(self):
        form = form_from_dict(_form_dict())
        with pytest.raises(FormValidationError) as exc:
            collect_form_response(form, {})
        # outcome required + approach required + specfirst required (3 of 4;
        # concerns is multi-select, empty list → required miss too)
        assert len(exc.value.problems) >= 3


def test_validation_error_carries_problems():
    err = FormValidationError(["a", "b"])
    assert err.problems == ["a", "b"]
    assert "a" in str(err) and "b" in str(err)
