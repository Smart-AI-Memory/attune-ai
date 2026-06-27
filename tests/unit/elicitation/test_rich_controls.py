"""Tests for v2.1 rich controls on the elicitation artifact.

Covers the new QuestionType values (number, date, textarea) and their
constraints (minimum/maximum/max_length) on both sides:

- form_from_dict: definition parsing + every new definition-reject path
- collect_form_response: valid answers + every new answer-reject path

The lead surface for these controls is MCP elicitation (D8); this layer
is model + validation only (no renderer — that is V2.2).
"""

from __future__ import annotations

import pytest

from attune.elicitation import (
    FormValidationError,
    collect_form_response,
    form_from_dict,
)
from attune.meta_workflows.models import QuestionType


def _form(field: dict) -> dict:
    return {"title": "T", "fields": [field]}


# ---------------------------------------------------------------------------
# Definition parsing (form_from_dict)
# ---------------------------------------------------------------------------


class TestRichDefinitions:
    def test_number_with_bounds_parses(self):
        form = form_from_dict(
            _form({"id": "age", "text": "Age", "type": "number", "minimum": 0, "maximum": 120})
        )
        q = form.questions[0]
        assert q.type == QuestionType.NUMBER
        assert q.minimum == 0
        assert q.maximum == 120

    def test_number_without_bounds_parses(self):
        form = form_from_dict(_form({"id": "n", "text": "N", "type": "number"}))
        q = form.questions[0]
        assert q.minimum is None and q.maximum is None

    def test_date_needs_no_options(self):
        form = form_from_dict(_form({"id": "d", "text": "When", "type": "date"}))
        assert form.questions[0].type == QuestionType.DATE

    def test_textarea_with_max_length_parses(self):
        form = form_from_dict(
            _form({"id": "bio", "text": "Bio", "type": "textarea", "max_length": 280})
        )
        assert form.questions[0].max_length == 280

    def test_float_bounds_allowed(self):
        form = form_from_dict(
            _form({"id": "p", "text": "Price", "type": "number", "minimum": 0.5, "maximum": 9.5})
        )
        assert form.questions[0].minimum == 0.5

    def test_minimum_exceeds_maximum_rejected(self):
        with pytest.raises(FormValidationError, match="exceeds 'maximum'"):
            form_from_dict(
                _form({"id": "n", "text": "N", "type": "number", "minimum": 5, "maximum": 1})
            )

    def test_non_numeric_minimum_rejected(self):
        with pytest.raises(FormValidationError, match="'minimum' must be a number"):
            form_from_dict(_form({"id": "n", "text": "N", "type": "number", "minimum": "lo"}))

    def test_non_numeric_maximum_rejected(self):
        with pytest.raises(FormValidationError, match="'maximum' must be a number"):
            form_from_dict(_form({"id": "n", "text": "N", "type": "number", "maximum": []}))

    def test_bool_bound_rejected(self):
        # bool is an int subclass but must not pass as a number.
        with pytest.raises(FormValidationError, match="'minimum' must be a number"):
            form_from_dict(_form({"id": "n", "text": "N", "type": "number", "minimum": True}))

    @pytest.mark.parametrize("bad", [-3, 0, 2.5, True])
    def test_bad_max_length_rejected(self, bad):
        with pytest.raises(FormValidationError, match="'max_length' must be a positive integer"):
            form_from_dict(_form({"id": "t", "text": "T", "type": "textarea", "max_length": bad}))


# ---------------------------------------------------------------------------
# Answer validation (collect_form_response)
# ---------------------------------------------------------------------------


class TestNumberAnswers:
    def _form(self, **extra):
        return form_from_dict(_form({"id": "age", "text": "Age", "type": "number", **extra}))

    def test_valid_in_range(self):
        form = self._form(minimum=0, maximum=120)
        assert collect_form_response(form, {"age": 42}).responses == {"age": 42}

    def test_zero_is_not_treated_as_empty(self):
        form = self._form(minimum=0, maximum=10)
        assert collect_form_response(form, {"age": 0}).responses == {"age": 0}

    def test_float_accepted(self):
        form = self._form()
        assert collect_form_response(form, {"age": 3.14}).responses == {"age": 3.14}

    def test_below_minimum_rejected(self):
        form = self._form(minimum=18)
        with pytest.raises(FormValidationError, match="below minimum 18"):
            collect_form_response(form, {"age": 5})

    def test_above_maximum_rejected(self):
        form = self._form(maximum=120)
        with pytest.raises(FormValidationError, match="above maximum 120"):
            collect_form_response(form, {"age": 200})

    def test_non_number_rejected(self):
        form = self._form()
        with pytest.raises(FormValidationError, match="expects a number"):
            collect_form_response(form, {"age": "old"})

    def test_bool_rejected(self):
        form = self._form()
        with pytest.raises(FormValidationError, match="expects a number"):
            collect_form_response(form, {"age": True})

    def test_unbounded_accepts_any_number(self):
        form = self._form()
        assert collect_form_response(form, {"age": -9999}).responses == {"age": -9999}

    def test_required_missing(self):
        form = self._form(minimum=0)
        with pytest.raises(FormValidationError, match="'age' is required"):
            collect_form_response(form, {})


class TestDateAnswers:
    def _form(self):
        return form_from_dict(_form({"id": "d", "text": "When", "type": "date"}))

    def test_valid_iso_date(self):
        assert collect_form_response(self._form(), {"d": "2026-06-27"}).responses == {
            "d": "2026-06-27"
        }

    def test_non_string_rejected(self):
        with pytest.raises(FormValidationError, match="expects an ISO date"):
            collect_form_response(self._form(), {"d": 20260627})

    def test_bad_format_rejected(self):
        with pytest.raises(FormValidationError, match="not a valid YYYY-MM-DD"):
            collect_form_response(self._form(), {"d": "06/27/2026"})

    def test_impossible_date_rejected(self):
        with pytest.raises(FormValidationError, match="not a valid YYYY-MM-DD"):
            collect_form_response(self._form(), {"d": "2026-13-40"})


class TestTextLengthAnswers:
    def test_textarea_within_limit(self):
        form = form_from_dict(
            _form({"id": "bio", "text": "Bio", "type": "textarea", "max_length": 5})
        )
        assert collect_form_response(form, {"bio": "hi"}).responses == {"bio": "hi"}

    def test_textarea_over_limit_rejected(self):
        form = form_from_dict(
            _form({"id": "bio", "text": "Bio", "type": "textarea", "max_length": 5})
        )
        with pytest.raises(FormValidationError, match="exceeds max_length 5"):
            collect_form_response(form, {"bio": "way too long"})

    def test_textarea_non_string_rejected(self):
        form = form_from_dict(_form({"id": "bio", "text": "Bio", "type": "textarea"}))
        with pytest.raises(FormValidationError, match="expects a string"):
            collect_form_response(form, {"bio": 42})

    def test_text_input_respects_max_length(self):
        form = form_from_dict(
            _form({"id": "name", "text": "Name", "type": "text_input", "max_length": 3})
        )
        with pytest.raises(FormValidationError, match="exceeds max_length 3"):
            collect_form_response(form, {"name": "Patrick"})

    def test_textarea_unbounded_accepts_any_length(self):
        form = form_from_dict(_form({"id": "bio", "text": "Bio", "type": "textarea"}))
        big = "x" * 10_000
        assert collect_form_response(form, {"bio": big}).responses == {"bio": big}
