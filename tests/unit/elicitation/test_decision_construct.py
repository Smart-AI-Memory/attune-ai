"""Tests for the V3 decision construct (communication grammar).

A DECISION is a presentation-enriched single-select: the agent offers a
recommended option with a rationale and per-option tradeoffs; the answer
is one selected option, validated exactly as a single-select. These tests
cover the model extension, definition validation, the widget card render,
the answer round-trip, the AskUserQuestion fallback, and the elicitation
schema mapping. See docs/specs/elicitation-form-surface/v3-requirements.md.
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


def _decision(**override) -> dict:
    """Build a one-field decision form dict, overriding the field."""
    field = {
        "id": "approach",
        "text": "Which approach?",
        "type": "decision",
        "options": ["X", "Y", "Z"],
        "recommended": "Y",
        "rationale": "Y is the safest.",
        "option_notes": {"X": "fast", "Y": "safe", "Z": "cheap"},
    }
    field.update(override)
    return {"title": "Pick one", "fields": [field]}


class TestDecisionModel:
    def test_questiontype_has_decision(self) -> None:
        assert QuestionType.DECISION.value == "decision"

    def test_formquestion_decision_fields_default_none(self) -> None:
        q = FormQuestion(id="a", text="t", type=QuestionType.DECISION)
        assert q.rationale is None
        assert q.option_notes is None
        assert q.recommended is None


class TestDecisionFormFromDict:
    def test_builds_decision_with_extras(self) -> None:
        form = form_from_dict(_decision())
        q = form.questions[0]
        assert q.type == QuestionType.DECISION
        assert q.recommended == "Y"
        assert q.rationale == "Y is the safest."
        assert q.option_notes == {"X": "fast", "Y": "safe", "Z": "cheap"}

    def test_decision_requires_options(self) -> None:
        with pytest.raises(FormValidationError, match="requires non-empty 'options'"):
            form_from_dict(_decision(options=[]))

    def test_recommended_must_be_an_option(self) -> None:
        with pytest.raises(FormValidationError, match="'recommended' 'Ghost' not in options"):
            form_from_dict(_decision(recommended="Ghost"))

    def test_option_notes_keys_must_be_options(self) -> None:
        with pytest.raises(FormValidationError, match="'option_notes' keys not in options"):
            form_from_dict(_decision(option_notes={"Nope": "x"}))

    def test_option_notes_must_be_string_map(self) -> None:
        with pytest.raises(FormValidationError, match="'option_notes' must be a map of strings"):
            form_from_dict(_decision(option_notes={"X": 5}))

    def test_recommended_and_notes_optional(self) -> None:
        # A decision with neither recommendation nor notes is valid.
        form = form_from_dict(_decision(recommended=None, option_notes=None, rationale=None))
        q = form.questions[0]
        assert q.recommended is None and q.option_notes is None


class TestDecisionAnswer:
    def test_collect_accepts_selected_option(self) -> None:
        form = form_from_dict(_decision())
        resp = collect_form_response(form, {"approach": "Y"})
        assert resp.responses == {"approach": "Y"}

    def test_collect_rejects_out_of_option(self) -> None:
        form = form_from_dict(_decision())
        with pytest.raises(FormValidationError, match="not in options"):
            collect_form_response(form, {"approach": "nope"})

    def test_fallback_maps_to_single_select_recommended_first(self) -> None:
        form = form_from_dict(_decision())
        payload = form_to_askuserquestion(form)[0][0]
        assert payload["type"] == "single_select"
        # Recommended option is ordered first.
        assert payload["options"][0] == "Y"
        assert payload["default"] == "Y"


class TestDecisionWidget:
    def test_renders_cards_badge_rationale(self) -> None:
        html = form_to_widget_html(form_from_dict(_decision()))
        assert 'class="ae-cards"' in html
        assert 'role="radiogroup"' in html
        assert "Recommended" in html
        assert 'class="ae-rationale"' in html
        assert "Y is the safest." in html
        assert "safe" in html  # an option_note

    def test_recommended_ordered_first(self) -> None:
        html = form_to_widget_html(form_from_dict(_decision()))
        assert html.index('value="Y"') < html.index('value="X"')

    def test_data_ftype_is_decision(self) -> None:
        html = form_to_widget_html(form_from_dict(_decision()))
        assert 'data-ftype="decision"' in html

    def test_submit_script_has_decision_branch(self) -> None:
        # forms 0.7.0: decision answers like a single-select, so it reads
        # through the "checked-one" mode rather than a decision-specific
        # branch (the reader dispatches on data-collect, not construct type).
        html = form_to_widget_html(form_from_dict(_decision()))
        assert 'data-collect="checked-one"' in html
        assert "mode === 'checked-one'" in html
        assert "[data-control]:checked" in html

    def test_static_fallback_guard_present(self) -> None:
        html = form_to_widget_html(form_from_dict(_decision()))
        assert "typeof sendPrompt === 'function'" in html

    def test_no_recommended_no_badge(self) -> None:
        html = form_to_widget_html(form_from_dict(_decision(recommended=None, option_notes=None)))
        assert "Recommended" not in html
        assert 'class="ae-cards"' in html

    def test_escapes_option_text(self) -> None:
        html = form_to_widget_html(
            form_from_dict(
                _decision(
                    options=["A & <b>", "Y", "Z"],
                    recommended="Y",
                    option_notes=None,
                )
            )
        )
        assert "A &amp; &lt;b&gt;" in html
        assert "<b>" not in html


class TestDecisionElicitationSchema:
    def test_decision_maps_to_string_enum(self) -> None:
        schema = form_to_elicitation_schema(form_from_dict(_decision()))
        prop = schema["properties"]["approach"]
        assert prop["type"] == "string"
        assert prop["enum"] == ["X", "Y", "Z"]
