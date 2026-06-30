"""Tests for the V5 progress construct (communication grammar member #4).

A PROGRESS is a status report: the agent reports a set of items by status
(``done`` / ``in_flight`` / ``blocked``) via ``progress_items`` and offers
the ``blocked`` items as a single-select picker. The answer is one selected
blocked option, validated exactly as a single-select; with no blocked items
it degrades to a pure status display. These tests cover the model extension,
definition validation (including the blocked-subset==options invariant), the
three-bucket widget render, the empty-blocked degrade, the answer round-trip,
the AskUserQuestion fallback, and the elicitation schema mapping. See
docs/specs/elicitation-form-surface/v5-requirements.md.
"""

from __future__ import annotations

import pytest

from attune.elicitation import (
    FormValidationError,
    collect_form_response,
    form_from_dict,
    form_to_widget_html,
)
from attune.elicitation.bridge import form_to_askuserquestion
from attune.elicitation.elicitation_schema import form_to_elicitation_schema
from attune.meta_workflows.models import FormQuestion, QuestionType


def _progress(**override) -> dict:
    """Build a one-field progress form dict, overriding the field."""
    field = {
        "id": "exec",
        "text": "Where execution stands",
        "type": "progress",
        "options": ["T6 consumer wiring", "T5 surfaces"],
        "recommended": "T6 consumer wiring",
        "rationale": "6/8 done, 2 deferred on gate failures.",
        "option_notes": {"T6 consumer wiring": "gate failed: score 42"},
        "progress_items": [
            {"label": "T1 model", "status": "done"},
            {"label": "T3 widget", "status": "in_flight", "detail": "rendering cards"},
            {"label": "T6 consumer wiring", "status": "blocked", "detail": "gate failed: score 42"},
            {"label": "T5 surfaces", "status": "blocked"},
        ],
    }
    field.update(override)
    return {"title": "Spec execution", "fields": [field]}


def _display_only(**override) -> dict:
    """A progress report with nothing blocked — display only, no picker."""
    field = {
        "id": "exec",
        "text": "Where execution stands",
        "type": "progress",
        "options": [],
        "required": False,
        "progress_items": [
            {"label": "T1 model", "status": "done"},
            {"label": "T2 bridge", "status": "in_flight"},
        ],
    }
    field.update(override)
    return {"title": "Spec execution", "fields": [field]}


class TestProgressModel:
    def test_questiontype_has_progress(self) -> None:
        assert QuestionType.PROGRESS.value == "progress"

    def test_formquestion_progress_items_defaults_none(self) -> None:
        q = FormQuestion(id="a", text="t", type=QuestionType.PROGRESS)
        assert q.progress_items is None
        assert q.recommended is None
        assert q.rationale is None


class TestProgressFormFromDict:
    def test_builds_progress_with_items(self) -> None:
        form = form_from_dict(_progress())
        q = form.questions[0]
        assert q.type == QuestionType.PROGRESS
        assert q.progress_items is not None and len(q.progress_items) == 4
        assert q.recommended == "T6 consumer wiring"

    def test_requires_progress_items(self) -> None:
        with pytest.raises(FormValidationError, match="requires 'progress_items'"):
            form_from_dict(_progress(progress_items=None))

    def test_progress_items_must_be_list_of_dicts(self) -> None:
        with pytest.raises(FormValidationError, match="must be a list of dicts"):
            form_from_dict(_progress(progress_items=["nope"]))

    def test_status_must_be_valid(self) -> None:
        bad = [{"label": "X", "status": "halfway"}]
        with pytest.raises(FormValidationError, match="'status' must be one of"):
            form_from_dict(_progress(options=[], required=False, progress_items=bad))

    def test_item_needs_label(self) -> None:
        bad = [{"status": "done"}]
        with pytest.raises(FormValidationError, match="needs a 'label' string"):
            form_from_dict(_progress(options=[], required=False, progress_items=bad))

    def test_blocked_subset_must_equal_options(self) -> None:
        # options names a blocker that is not in progress_items.
        with pytest.raises(FormValidationError, match="must equal options"):
            form_from_dict(_progress(options=["Ghost blocker"]))

    def test_recommended_must_be_an_option(self) -> None:
        with pytest.raises(FormValidationError, match="'recommended' 'Ghost' not in options"):
            form_from_dict(_progress(recommended="Ghost"))

    def test_display_only_is_valid(self) -> None:
        # No blocked items, empty options — a pure status display.
        form = form_from_dict(_display_only())
        q = form.questions[0]
        assert q.options == []
        assert q.progress_items is not None and len(q.progress_items) == 2


class TestProgressAnswer:
    def test_collect_accepts_blocked_option(self) -> None:
        form = form_from_dict(_progress())
        resp = collect_form_response(form, {"exec": "T5 surfaces"})
        assert resp.responses == {"exec": "T5 surfaces"}

    def test_collect_rejects_non_blocked_item(self) -> None:
        # A done/in_flight item is reported but not a valid answer.
        form = form_from_dict(_progress())
        with pytest.raises(FormValidationError, match="not in options"):
            collect_form_response(form, {"exec": "T1 model"})

    def test_collect_rejects_out_of_option(self) -> None:
        form = form_from_dict(_progress())
        with pytest.raises(FormValidationError, match="not in options"):
            collect_form_response(form, {"exec": "nope"})

    def test_display_only_needs_no_answer(self) -> None:
        # required=False + empty options → no answer collected, no error.
        form = form_from_dict(_display_only())
        resp = collect_form_response(form, {})
        assert resp.responses == {}

    def test_fallback_maps_to_single_select_suggested_first(self) -> None:
        form = form_from_dict(_progress())
        payload = form_to_askuserquestion(form)[0][0]
        assert payload["type"] == "single_select"
        # Only blocked items are pickable; recommended ordered first.
        assert payload["options"] == ["T6 consumer wiring", "T5 surfaces"]
        assert payload["default"] == "T6 consumer wiring"


class TestProgressWidget:
    def test_renders_three_bucket_structure(self) -> None:
        html = form_to_widget_html(form_from_dict(_progress()))
        assert 'class="ae-progress"' in html
        assert 'class="ae-prog-rows"' in html  # static done/in_flight rows
        assert 'role="radiogroup"' in html  # blocked picker
        assert "suggested next" in html  # recommended badge
        assert "Blocked — pick one to tackle:" in html
        assert "Summary" in html  # rationale header
        assert "T1 model" in html  # a done item rendered
        assert "rendering cards" in html  # an in_flight detail rendered

    def test_blocked_items_ordered_recommended_first(self) -> None:
        html = form_to_widget_html(form_from_dict(_progress()))
        assert html.index('value="T6 consumer wiring"') < html.index('value="T5 surfaces"')

    def test_done_in_flight_not_selectable(self) -> None:
        # Only the two blocked items get radio inputs; done/in_flight don't.
        html = form_to_widget_html(form_from_dict(_progress()))
        assert html.count('type="radio"') == 2

    def test_display_only_has_no_picker(self) -> None:
        html = form_to_widget_html(form_from_dict(_display_only()))
        assert "radiogroup" not in html
        assert 'type="radio"' not in html
        assert 'class="ae-prog-rows"' in html

    def test_data_ftype_is_progress(self) -> None:
        html = form_to_widget_html(form_from_dict(_progress()))
        assert 'data-ftype="progress"' in html

    def test_submit_script_handles_progress(self) -> None:
        html = form_to_widget_html(form_from_dict(_progress()))
        assert "ftype === 'progress'" in html
        assert "[data-control]:checked" in html

    def test_static_fallback_guard_present(self) -> None:
        html = form_to_widget_html(form_from_dict(_progress()))
        assert "typeof sendPrompt === 'function'" in html

    def test_escapes_item_text(self) -> None:
        html = form_to_widget_html(
            form_from_dict(
                _progress(
                    options=["A & <b>"],
                    recommended="A & <b>",
                    option_notes=None,
                    progress_items=[
                        {"label": "T1 model", "status": "done"},
                        {"label": "A & <b>", "status": "blocked"},
                    ],
                )
            )
        )
        assert "A &amp; &lt;b&gt;" in html
        assert "<b>" not in html


class TestProgressElicitationSchema:
    def test_progress_maps_to_string_enum(self) -> None:
        schema = form_to_elicitation_schema(form_from_dict(_progress()))
        prop = schema["properties"]["exec"]
        assert prop["type"] == "string"
        assert prop["enum"] == ["T6 consumer wiring", "T5 surfaces"]
