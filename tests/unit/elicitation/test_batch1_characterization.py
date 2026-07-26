"""Characterization pins for Batch 1 of the D-block triage (2026-07-14).

See ``docs/reports/d-block-triage-2026-07-14.md``. Three blocks:

- ``bridge.py::form_from_dict`` (F87)
- ``widget.py::_control_html`` (F84)
- ``bridge.py::_validate_answer`` (D22)

These pins document CURRENT behavior — including quirks — for branches
NOT already covered by the existing suite (``test_bridge.py``,
``test_rich_controls.py``, ``test_decision_construct.py``,
``test_pushback_construct.py``, ``test_progress_construct.py``,
``test_progress_report_style.py``, ``test_list_style.py``,
``test_widget.py``). No refactoring accompanies this file; a future
refactor of the three pinned blocks must keep every assertion here
green (or update it deliberately, with the branch it pins named in the
diff).

Branch-family accounting for the cut stage is in the PR description /
session report, not duplicated here.
"""

from __future__ import annotations

import pytest

from attune.elicitation import (
    FormValidationError,
    collect_form_response,
    form_from_dict,
    form_to_widget_html,
)


def _form(field: dict) -> dict:
    return {"title": "T", "fields": [field]}


def _render(field: dict) -> str:
    return form_to_widget_html(form_from_dict(_form(field)))


# ===========================================================================
# form_from_dict — unpinned definition-validation branches
# ===========================================================================


class TestFormFromDictTypeCoercion:
    """The ``type`` key coercion path — missing / non-string values.

    Existing test_bridge.py::test_invalid_type only exercises a bad
    STRING value ("slider"). These pin the missing-key and non-string
    shapes, which flow through the same ``QuestionType(type_str)``
    ``ValueError`` branch but produce a different ``type_str!r`` in the
    message.
    """

    def test_missing_type_key_reports_none(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(_form({"id": "a", "text": "A?"}))
        assert any("invalid type None" in p for p in exc.value.problems)

    def test_non_string_type_value_reported_verbatim(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(_form({"id": "a", "text": "A?", "type": 5}))
        assert any("invalid type 5" in p for p in exc.value.problems)

    def test_invalid_type_lists_every_valid_value(self):
        # The "use one of: ..." suffix enumerates QuestionType in
        # declaration order — pin the exact enumeration so a reordering
        # or renamed member is caught.
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(_form({"id": "a", "text": "A?", "type": "nope"}))
        (problem,) = [p for p in exc.value.problems if "invalid type" in p]
        assert problem == (
            "field[0] invalid type 'nope' (use one of: text_input, "
            "single_select, multi_select, boolean, number, date, "
            "textarea, decision, pushback, progress)"
        )


class TestFormFromDictIdAndTextTypeChecks:
    """``id``/``text`` present but of the wrong type (not just missing).

    test_bridge.py::test_missing_id_and_text only exercises the
    entirely-absent case (falsy via ``.get`` returning None). A
    present-but-non-string value takes the same ``not isinstance``
    branch, which is otherwise unpinned.
    """

    def test_non_string_id_rejected(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(_form({"id": 123, "text": "A?", "type": "text_input"}))
        assert any("'id' is required and must be a string" in p for p in exc.value.problems)

    def test_non_string_text_rejected(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(_form({"id": "a", "text": 123, "type": "text_input"}))
        assert any("'text' (or 'label') is required" in p for p in exc.value.problems)


class TestFormFromDictRationaleValidation:
    """DECISION/PUSHBACK/PROGRESS ``rationale`` type-check — untested by
    any of the three construct-specific suites (they only exercise a
    valid string rationale)."""

    def test_non_string_rationale_rejected(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(
                _form(
                    {
                        "id": "a",
                        "text": "A?",
                        "type": "decision",
                        "options": ["x"],
                        "rationale": 123,
                    }
                )
            )
        assert exc.value.problems == ["field[0] 'rationale' must be a string"]


class TestFormFromDictRequiredCoercion:
    """``required`` is coerced via bare ``bool(...)`` — Python truthiness,
    not a strict boolean parse. A quirk worth pinning: a non-empty
    string like ``"false"`` is TRUTHY and therefore becomes
    ``required=True`` (the opposite of what an author probably meant).
    """

    def test_string_false_is_truthy_and_stays_required(self):
        form = form_from_dict(
            _form({"id": "a", "text": "A?", "type": "text_input", "required": "false"})
        )
        assert form.questions[0].required is True

    def test_int_zero_is_falsy_and_becomes_optional(self):
        form = form_from_dict(_form({"id": "a", "text": "A?", "type": "text_input", "required": 0}))
        assert form.questions[0].required is False

    def test_empty_string_is_falsy_and_becomes_optional(self):
        form = form_from_dict(
            _form({"id": "a", "text": "A?", "type": "text_input", "required": ""})
        )
        assert form.questions[0].required is False


class TestFormFromDictListStyleMessages:
    """Exact reject text for ``list_style`` — test_list_style.py only
    asserts the substring ``"list_style"`` appears, not the full
    message. Pin both exact strings so a refactor can't silently
    change the wording without a red test."""

    def test_invalid_value_exact_message(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(
                _form(
                    {
                        "id": "s",
                        "text": "S",
                        "type": "single_select",
                        "options": ["x"],
                        "list_style": "fancy",
                    }
                )
            )
        assert exc.value.problems == ["field[0] 'list_style' must be 'ordered' or 'unordered'"]

    def test_wrong_question_type_exact_message(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(
                _form(
                    {
                        "id": "t",
                        "text": "T",
                        "type": "text_input",
                        "list_style": "ordered",
                    }
                )
            )
        assert exc.value.problems == [
            "field[0] 'list_style' is only valid on single_select / "
            "multi_select (got text_input)"
        ]


# ===========================================================================
# _validate_answer (via collect_form_response) — unpinned boundary/quirk
# branches
# ===========================================================================


class TestValidateAnswerNumberBoundaries:
    """``minimum``/``maximum`` use strict ``<``/``>`` — a value exactly
    AT the bound is accepted, not rejected. test_rich_controls.py only
    exercises values strictly inside/outside the range."""

    def test_value_equal_to_minimum_accepted(self):
        form = form_from_dict(
            _form({"id": "n", "text": "N", "type": "number", "minimum": 0, "maximum": 10})
        )
        assert collect_form_response(form, {"n": 0}).responses == {"n": 0}

    def test_value_equal_to_maximum_accepted(self):
        form = form_from_dict(
            _form({"id": "n", "text": "N", "type": "number", "minimum": 0, "maximum": 10})
        )
        assert collect_form_response(form, {"n": 10}).responses == {"n": 10}


class TestValidateAnswerDateQuirks:
    """``datetime.strptime(value, "%Y-%m-%d")`` is more lenient than the
    docstring's "ISO-8601 (YYYY-MM-DD)" implies: single-digit month/day
    parse fine (no zero-padding enforced), while trailing garbage is
    still rejected. Neither is exercised by test_rich_controls.py's
    DateAnswers class."""

    def _form(self):
        return form_from_dict({"title": "T", "fields": [{"id": "d", "text": "D", "type": "date"}]})

    def test_non_zero_padded_date_is_accepted(self):
        # A genuine quirk: "2026-1-5" is NOT rejected despite the
        # YYYY-MM-DD docstring contract.
        resp = collect_form_response(self._form(), {"d": "2026-1-5"})
        assert resp.responses == {"d": "2026-1-5"}

    def test_trailing_whitespace_rejected(self):
        with pytest.raises(FormValidationError, match="not a valid YYYY-MM-DD"):
            collect_form_response(self._form(), {"d": "2026-06-27 "})


class TestValidateAnswerLengthBoundary:
    """A value whose length exactly equals ``max_length`` is accepted —
    the check is strictly ``>``, not ``>=``."""

    def test_text_input_length_equal_to_max_length_accepted(self):
        form = form_from_dict(
            _form({"id": "t", "text": "T", "type": "text_input", "max_length": 3})
        )
        assert collect_form_response(form, {"t": "abc"}).responses == {"t": "abc"}

    def test_textarea_length_equal_to_max_length_accepted(self):
        form = form_from_dict(_form({"id": "t", "text": "T", "type": "textarea", "max_length": 3}))
        assert collect_form_response(form, {"t": "abc"}).responses == {"t": "abc"}


# ===========================================================================
# _control_html — unpinned default-value rendering + card-checked branches
# ===========================================================================


class TestControlHtmlDefaultRendering:
    """Every simple control mirrors ``question.default`` onto the native
    HTML attribute (or, for textarea, element content). None of these
    are exercised by test_widget.py, which only asserts default
    pre-selection for SINGLE_SELECT."""

    def test_number_default_rendered_as_value_attribute(self):
        html = _render({"id": "n", "text": "N", "type": "number", "default": 5})
        assert 'value="5"' in html

    def test_date_default_rendered_as_value_attribute(self):
        html = _render({"id": "d", "text": "D", "type": "date", "default": "2026-06-27"})
        assert 'value="2026-06-27"' in html

    def test_textarea_default_rendered_as_element_content(self):
        html = _render({"id": "t", "text": "T", "type": "textarea", "default": "hi"})
        assert ">hi</textarea>" in html

    def test_text_input_default_rendered_as_value_attribute(self):
        html = _render({"id": "t", "text": "T", "type": "text_input", "default": "hi"})
        assert 'value="hi"' in html

    def test_boolean_default_renders_selected_option(self):
        html = _render({"id": "b", "text": "B", "type": "boolean", "default": "Yes"})
        assert 'value="Yes" selected' in html


class TestControlHtmlMultiSelectDefaultQuirk:
    """``FormQuestion.default`` is a single scalar (str), never a list —
    there is no plural "defaults" field. For MULTI_SELECT, ``_checked``
    still runs per-option, so at most ONE checkbox can ever be
    pre-checked via ``default``, no matter how many options exist. This
    is a real quirk (an author reaching for "pre-check several boxes"
    cannot do it via ``default``) worth pinning explicitly."""

    def test_exactly_one_checkbox_prechecked(self):
        html = _render(
            {
                "id": "m",
                "text": "M",
                "type": "multi_select",
                "options": ["x", "y", "z"],
                "default": "y",
            }
        )
        assert 'value="x">' in html  # unchecked
        assert 'value="y" checked>' in html  # the one match
        assert 'value="z">' in html  # unchecked
        assert html.count(" checked>") == 1


class TestControlHtmlListStyleDefaultChecked:
    """``_list_html`` reuses ``_checked`` for both radios (single_select)
    and checkboxes (multi_select) — untested by test_list_style.py,
    which never sets ``default`` on a list_style field."""

    def test_single_select_list_style_default_checked(self):
        html = _render(
            {
                "id": "s",
                "text": "S",
                "type": "single_select",
                "options": ["x", "y"],
                "list_style": "ordered",
                "default": "y",
            }
        )
        assert 'value="y" checked>' in html
        assert 'value="x" checked>' not in html

    def test_multi_select_list_style_default_checked(self):
        html = _render(
            {
                "id": "m",
                "text": "M",
                "type": "multi_select",
                "options": ["x", "y"],
                "list_style": "unordered",
                "default": "x",
            }
        )
        assert 'value="x" checked>' in html
        assert 'value="y" checked>' not in html


class TestControlHtmlCardDefaultChecked:
    """DECISION / PUSHBACK / PROGRESS card renders mirror ``default`` onto
    the radio's ``checked`` attribute — none of the four construct
    suites set ``default`` (they only check ``recommended`` ordering)."""

    def test_decision_default_checked(self):
        html = _render(
            {
                "id": "a",
                "text": "A",
                "type": "decision",
                "options": ["X", "Y"],
                "default": "Y",
            }
        )
        assert 'value="Y" checked>' in html
        assert 'value="X" checked>' not in html

    def test_pushback_default_checked(self):
        html = _render(
            {
                "id": "a",
                "text": "A",
                "type": "pushback",
                "options": ["X", "Y"],
                "default": "Y",
            }
        )
        assert 'value="Y" checked>' in html
        assert 'value="X" checked>' not in html

    def test_progress_task_style_blocked_default_checked(self):
        html = _render(
            {
                "id": "e",
                "text": "E",
                "type": "progress",
                "options": ["A", "B"],
                "default": "B",
                "progress_items": [
                    {"label": "A", "status": "blocked"},
                    {"label": "B", "status": "blocked"},
                ],
            }
        )
        assert 'value="B" checked>' in html
        assert 'value="A" checked>' not in html

    def test_progress_report_style_default_checked(self):
        html = _render(
            {
                "id": "e",
                "text": "E",
                "type": "progress",
                "progress_style": "report",
                "required": False,
                "options": ["A", "B"],
                "default": "B",
                "progress_items": [
                    {"label": "A", "status": "tag"},
                    {"label": "B", "status": "tag"},
                ],
            }
        )
        assert 'value="B" checked>' in html
        assert 'value="A" checked>' not in html


class TestControlHtmlProgressNotePrecedence:
    """PROGRESS card note text prefers ``option_notes`` over the item's
    own ``detail`` when BOTH are present (``notes.get(opt) or
    detail_by_label.get(opt)``) — a real precedence quirk unexercised
    by test_progress_construct.py (which only sets one or the other,
    never both for the same option)."""

    def test_task_style_option_notes_wins_over_item_detail(self):
        html = _render(
            {
                "id": "e",
                "text": "E",
                "type": "progress",
                "options": ["A"],
                "option_notes": {"A": "NOTE WINS"},
                "progress_items": [{"label": "A", "status": "blocked", "detail": "detail loses"}],
            }
        )
        assert "NOTE WINS" in html
        assert "detail loses" not in html

    def test_report_style_option_notes_wins_over_item_detail(self):
        html = _render(
            {
                "id": "e",
                "text": "E",
                "type": "progress",
                "progress_style": "report",
                "required": False,
                "options": ["A"],
                "option_notes": {"A": "NOTE WINS"},
                "progress_items": [{"label": "A", "status": "tag", "detail": "detail loses"}],
            }
        )
        assert "NOTE WINS" in html
        assert "detail loses" not in html


class TestFieldHtmlRationaleHeaderDefault:
    """``_field_html``'s ``rationale_headers`` map only names PUSHBACK
    ("Why I'd push back") and PROGRESS ("Summary") explicitly; every
    other type (DECISION included) falls through ``.get(q.type, "Why")``
    to the literal default "Why". Unpinned by test_decision_construct.py,
    which asserts the rationale callout exists but never its header
    text."""

    def test_decision_rationale_header_is_plain_why(self):
        html = _render(
            {
                "id": "a",
                "text": "A",
                "type": "decision",
                "options": ["X", "Y"],
                "rationale": "because reasons",
            }
        )
        assert '<span class="ae-rationale-h">Why</span>' in html


class TestFormFromDictRecommendedTypeCheck:
    """DECISION/PUSHBACK/PROGRESS ``recommended`` type-check — the
    construct suites exercise a valid string and a not-in-options
    string, but never a non-string value (bridge.py's
    "'recommended' must be a string" branch)."""

    def test_non_string_recommended_rejected(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(
                _form(
                    {
                        "id": "a",
                        "text": "A?",
                        "type": "decision",
                        "options": ["x"],
                        "recommended": 123,
                    }
                )
            )
        assert exc.value.problems == ["field[0] 'recommended' must be a string"]


class TestProgressConsistencySkippedOffProgress:
    """``progress_items`` on a NON-progress field is parsed and carried
    but never consistency-checked — the item/option cross-check
    early-returns for any qtype other than PROGRESS. A quirk worth
    pinning: a decision field with stray ``progress_items`` builds
    cleanly instead of being rejected."""

    def test_decision_with_progress_items_builds_silently(self):
        form = form_from_dict(
            _form(
                {
                    "id": "a",
                    "text": "A?",
                    "type": "decision",
                    "options": ["x"],
                    "progress_items": [{"label": "L", "status": "done"}],
                }
            )
        )
        assert form.questions[0].progress_items == [{"label": "L", "status": "done"}]
