"""Tests for the V4 pushback construct (communication grammar member #3).

A PUSHBACK is a DECISION framed as dissent: the agent disagrees with the
user's stated approach (``user_position``) and offers a concrete
alternative (``recommended``) with a disagreement ``rationale``. The
answer is one selected option, validated exactly as a single-select.
These tests cover the model extension, definition validation, the dissent
widget render, the answer round-trip, the AskUserQuestion fallback, and
the elicitation schema mapping. See
docs/specs/elicitation-form-surface/v4-requirements.md.
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


def _pushback(**override) -> dict:
    """Build a one-field pushback form dict, overriding the field."""
    field = {
        "id": "retries",
        "text": "How should we handle transient failures?",
        "type": "pushback",
        "options": ["Fixed 3x retry", "Exponential backoff + jitter"],
        "user_position": "Fixed 3x retry",
        "recommended": "Exponential backoff + jitter",
        "rationale": "Fixed retries hammer a struggling service.",
        "option_notes": {"Exponential backoff + jitter": "Industry default"},
    }
    field.update(override)
    return {"title": "Retry strategy", "fields": [field]}


class TestPushbackModel:
    def test_questiontype_has_pushback(self) -> None:
        assert QuestionType.PUSHBACK.value == "pushback"

    def test_formquestion_user_position_defaults_none(self) -> None:
        q = FormQuestion(id="a", text="t", type=QuestionType.PUSHBACK)
        assert q.user_position is None
        assert q.recommended is None
        assert q.rationale is None


class TestPushbackFormFromDict:
    def test_builds_pushback_with_extras(self) -> None:
        form = form_from_dict(_pushback())
        q = form.questions[0]
        assert q.type == QuestionType.PUSHBACK
        assert q.user_position == "Fixed 3x retry"
        assert q.recommended == "Exponential backoff + jitter"
        assert q.rationale == "Fixed retries hammer a struggling service."

    def test_pushback_requires_options(self) -> None:
        with pytest.raises(FormValidationError, match="requires non-empty 'options'"):
            form_from_dict(_pushback(options=[]))

    def test_user_position_must_be_an_option(self) -> None:
        with pytest.raises(FormValidationError, match="'user_position' 'Ghost' not in options"):
            form_from_dict(_pushback(user_position="Ghost"))

    def test_user_position_must_be_a_string(self) -> None:
        with pytest.raises(FormValidationError, match="'user_position' must be a string"):
            form_from_dict(_pushback(user_position=5))

    def test_recommended_must_be_an_option(self) -> None:
        with pytest.raises(FormValidationError, match="'recommended' 'Ghost' not in options"):
            form_from_dict(_pushback(recommended="Ghost"))

    def test_user_position_optional(self) -> None:
        # A pushback with no explicit user_position is still valid.
        form = form_from_dict(_pushback(user_position=None))
        assert form.questions[0].user_position is None


class TestPushbackAnswer:
    def test_collect_accepts_selected_option(self) -> None:
        form = form_from_dict(_pushback())
        resp = collect_form_response(form, {"retries": "Exponential backoff + jitter"})
        assert resp.responses == {"retries": "Exponential backoff + jitter"}

    def test_collect_accepts_overrule(self) -> None:
        # Picking the user's own position (overrule) is a valid answer.
        form = form_from_dict(_pushback())
        resp = collect_form_response(form, {"retries": "Fixed 3x retry"})
        assert resp.responses == {"retries": "Fixed 3x retry"}

    def test_collect_rejects_out_of_option(self) -> None:
        form = form_from_dict(_pushback())
        with pytest.raises(FormValidationError, match="not in options"):
            collect_form_response(form, {"retries": "nope"})

    def test_fallback_maps_to_single_select_alternative_first(self) -> None:
        form = form_from_dict(_pushback())
        payload = form_to_askuserquestion(form)[0][0]
        assert payload["type"] == "single_select"
        # The agent's alternative (recommended) is ordered first.
        assert payload["options"][0] == "Exponential backoff + jitter"
        assert payload["default"] == "Exponential backoff + jitter"


class TestPushbackWidget:
    def test_renders_dissent_framing(self) -> None:
        html = form_to_widget_html(form_from_dict(_pushback()))
        assert 'class="ae-cards"' in html
        assert 'role="radiogroup"' in html
        assert "I&#x27;d suggest instead" in html  # alternative badge
        assert "your approach" in html  # user_position tag
        assert "Why I&#x27;d push back" in html  # rationale header
        assert "Fixed retries hammer a struggling service." in html

    def test_alternative_ordered_first(self) -> None:
        html = form_to_widget_html(form_from_dict(_pushback()))
        assert html.index('value="Exponential backoff + jitter"') < html.index(
            'value="Fixed 3x retry"'
        )

    def test_data_ftype_is_pushback(self) -> None:
        html = form_to_widget_html(form_from_dict(_pushback()))
        assert 'data-ftype="pushback"' in html

    def test_submit_script_handles_pushback(self) -> None:
        html = form_to_widget_html(form_from_dict(_pushback()))
        assert "ftype === 'pushback'" in html
        assert "[data-control]:checked" in html

    def test_static_fallback_guard_present(self) -> None:
        html = form_to_widget_html(form_from_dict(_pushback()))
        assert "typeof sendPrompt === 'function'" in html

    def test_not_decision_recommended_badge(self) -> None:
        # A pushback must NOT use the neutral "Recommended" badge — that is
        # the decision construct's framing; pushback is dissent.
        html = form_to_widget_html(form_from_dict(_pushback()))
        assert ">Recommended<" not in html

    def test_escapes_option_text(self) -> None:
        html = form_to_widget_html(
            form_from_dict(
                _pushback(
                    options=["A & <b>", "Exponential backoff + jitter"],
                    user_position="A & <b>",
                    option_notes=None,
                )
            )
        )
        assert "A &amp; &lt;b&gt;" in html
        assert "<b>" not in html


class TestPushbackElicitationSchema:
    def test_pushback_maps_to_string_enum(self) -> None:
        schema = form_to_elicitation_schema(form_from_dict(_pushback()))
        prop = schema["properties"]["retries"]
        assert prop["type"] == "string"
        assert prop["enum"] == ["Fixed 3x retry", "Exponential backoff + jitter"]
