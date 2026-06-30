"""Tests for the ``list_style`` render variant (D19).

A presentation-only option on ``single_select`` / ``multi_select`` that
renders the options as an ordered (numbered) or unordered (bulleted)
selectable list instead of the default dropdown/checkboxes. The answer
shape and its validation are unchanged — these tests assert both the new
render branch and that the existing answer path still validates a pick.
"""

from __future__ import annotations

import pytest

from attune.elicitation import (
    FormValidationError,
    collect_form_response,
    form_from_dict,
    form_to_widget_html,
)


def _render(field: dict) -> str:
    form = form_from_dict({"title": "T", "fields": [field]})
    return form_to_widget_html(form)


class TestRender:
    def test_single_select_ordered_renders_ol_with_radios(self):
        html = _render(
            {
                "id": "s",
                "text": "Pick",
                "type": "single_select",
                "options": ["x", "y"],
                "list_style": "ordered",
            }
        )
        assert '<ol class="ae-list"' in html
        assert html.count('type="radio"') == 2
        # not the default dropdown
        assert "<select" not in html

    def test_single_select_unordered_renders_ul(self):
        html = _render(
            {
                "id": "s",
                "text": "Pick",
                "type": "single_select",
                "options": ["x", "y"],
                "list_style": "unordered",
            }
        )
        assert '<ul class="ae-list"' in html
        assert html.count('type="radio"') == 2

    def test_multi_select_ordered_renders_ol_with_checkboxes(self):
        html = _render(
            {
                "id": "m",
                "text": "Pick many",
                "type": "multi_select",
                "options": ["x", "y", "z"],
                "list_style": "ordered",
            }
        )
        assert '<ol class="ae-list"' in html
        assert html.count('type="checkbox"') == 3
        assert '<div class="ae-checks"' not in html

    def test_radios_share_name_for_single_select(self):
        html = _render(
            {
                "id": "pick",
                "text": "Pick",
                "type": "single_select",
                "options": ["x", "y"],
                "list_style": "ordered",
            }
        )
        # one radio group: both radios carry the field id as name
        assert html.count('name="pick"') == 2

    def test_default_render_unaffected_when_absent(self):
        html = _render(
            {
                "id": "s",
                "text": "Pick",
                "type": "single_select",
                "options": ["x", "y"],
            }
        )
        assert "<select" in html
        assert '<ol class="ae-list"' not in html
        assert '<ul class="ae-list"' not in html

    def test_option_label_is_escaped_in_list(self):
        html = _render(
            {
                "id": "s",
                "text": "Pick",
                "type": "single_select",
                "options": ['<img src=x onerror="alert(1)">'],
                "list_style": "unordered",
            }
        )
        assert "<img" not in html
        assert "&lt;img" in html


class TestRoundTrip:
    def test_list_style_preserved_on_question(self):
        form = form_from_dict(
            {
                "title": "T",
                "fields": [
                    {
                        "id": "s",
                        "text": "Pick",
                        "type": "single_select",
                        "options": ["x", "y"],
                        "list_style": "ordered",
                    }
                ],
            }
        )
        assert form.questions[0].list_style == "ordered"

    def test_answer_path_unchanged_validates_pick(self):
        # list_style is presentation-only — a normal single-select answer
        # still validates by option membership.
        form = form_from_dict(
            {
                "title": "T",
                "fields": [
                    {
                        "id": "s",
                        "text": "Pick",
                        "type": "single_select",
                        "options": ["x", "y"],
                        "list_style": "ordered",
                    }
                ],
            }
        )
        resp = collect_form_response(form, {"s": "y"})
        assert resp.responses["s"] == "y"

    def test_answer_path_still_rejects_out_of_option(self):
        form = form_from_dict(
            {
                "title": "T",
                "fields": [
                    {
                        "id": "s",
                        "text": "Pick",
                        "type": "single_select",
                        "options": ["x", "y"],
                        "list_style": "unordered",
                    }
                ],
            }
        )
        with pytest.raises(FormValidationError):
            collect_form_response(form, {"s": "z"})


class TestDefinitionValidation:
    def test_rejects_list_style_on_non_select_type(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(
                {
                    "title": "T",
                    "fields": [
                        {
                            "id": "t",
                            "text": "Say",
                            "type": "text_input",
                            "list_style": "ordered",
                        }
                    ],
                }
            )
        assert "list_style" in str(exc.value)

    def test_rejects_invalid_list_style_value(self):
        with pytest.raises(FormValidationError) as exc:
            form_from_dict(
                {
                    "title": "T",
                    "fields": [
                        {
                            "id": "s",
                            "text": "Pick",
                            "type": "single_select",
                            "options": ["x"],
                            "list_style": "fancy",
                        }
                    ],
                }
            )
        assert "list_style" in str(exc.value)
