"""Tests for the show_widget HTML renderer (elicitation v2 / S1).

Covers the pure ``form_to_widget_html`` transform: one control per type,
HTML-escaping of form-supplied text, native bound attributes, the
sentinel postback payload, and the sendPrompt wiring.
"""

from __future__ import annotations

from attune.elicitation import (
    WIDGET_RESPONSE_MARKER,
    form_from_dict,
    form_to_widget_html,
)


def _render(fields: list[dict], **form_extra: object) -> str:
    form = form_from_dict({"title": "T", "fields": fields, **form_extra})
    return form_to_widget_html(form)


class TestStructure:
    def test_includes_title_and_form_shell(self):
        html = _render([{"id": "a", "text": "A?", "type": "text_input"}])
        assert 'id="attune-elicit-form-' in html
        assert "<h3>T</h3>" in html
        assert 'data-form-title="T"' in html
        assert 'id="ae-submit-' in html

    def test_element_ids_unique_per_render(self):
        # Two forms shown on the same page must not collide in the DOM —
        # a duplicate id would make the second submit script read the
        # first form's fields.
        fields = [{"id": "a", "text": "A?", "type": "text_input"}]
        first = _render(fields)
        second = _render(fields)

        def form_id(html: str) -> str:
            start = html.index('id="attune-elicit-form-')
            return html[start:].split('"')[1]

        assert form_id(first) != form_id(second)

    def test_fixed_instance_id_is_deterministic_and_sanitized(self):
        form = form_from_dict(
            {"title": "T", "fields": [{"id": "a", "text": "A?", "type": "text_input"}]}
        )
        html = form_to_widget_html(form, instance_id="beat-2!")
        # Non-alphanumeric chars are dropped; the suffix lands on every id
        # the submit script looks up.
        assert 'id="attune-elicit-form-beat2"' in html
        assert 'id="ae-submit-beat2"' in html
        assert 'id="ae-error-beat2"' in html
        assert "getElementById('attune-elicit-form-beat2')" in html
        assert html == form_to_widget_html(form, instance_id="beat-2!")
        # The scoped CSS must follow the suffixed id.
        assert "#attune-elicit-form-beat2 {" in html
        assert "#attune-elicit-form " not in html

    def test_message_and_description_render_when_present(self):
        form = form_from_dict(
            {
                "title": "T",
                "description": "Desc here",
                "fields": [{"id": "a", "text": "A?", "type": "text_input"}],
            }
        )
        html = form_to_widget_html(form, message="Please fill")
        assert "Please fill" in html
        assert "Desc here" in html

    def test_sr_only_summary_present(self):
        html = _render([{"id": "a", "text": "A?", "type": "text_input"}])
        assert 'class="sr-only"' in html

    def test_field_carries_id_and_type_attrs(self):
        html = _render([{"id": "goal", "text": "Goal?", "type": "text_input"}])
        assert 'data-fid="goal"' in html
        assert 'data-ftype="text_input"' in html


class TestControls:
    def test_text_input_renders_text_field(self):
        html = _render([{"id": "a", "text": "A?", "type": "text_input"}])
        assert '<input type="text"' in html

    def test_textarea_renders_textarea(self):
        html = _render([{"id": "a", "text": "A?", "type": "textarea", "max_length": 200}])
        assert "<textarea" in html
        assert 'maxlength="200"' in html

    def test_number_renders_with_bounds(self):
        html = _render(
            [
                {
                    "id": "n",
                    "text": "N?",
                    "type": "number",
                    "minimum": 1,
                    "maximum": 9,
                }
            ]
        )
        assert '<input type="number"' in html
        assert 'min="1"' in html
        assert 'max="9"' in html

    def test_date_renders_date_input(self):
        html = _render([{"id": "d", "text": "When?", "type": "date"}])
        assert '<input type="date"' in html

    def test_single_select_renders_select_with_options(self):
        html = _render(
            [
                {
                    "id": "s",
                    "text": "Pick",
                    "type": "single_select",
                    "options": ["x", "y"],
                }
            ]
        )
        assert "<select" in html
        assert "<option" in html
        assert ">x<" in html and ">y<" in html

    def test_multi_select_renders_checkboxes(self):
        html = _render(
            [
                {
                    "id": "m",
                    "text": "Pick many",
                    "type": "multi_select",
                    "options": ["x", "y"],
                }
            ]
        )
        assert html.count('type="checkbox"') == 2

    def test_boolean_renders_yes_no_select(self):
        html = _render([{"id": "b", "text": "OK?", "type": "boolean"}])
        assert ">Yes<" in html and ">No<" in html

    def test_default_preselected_for_single_select(self):
        html = _render(
            [
                {
                    "id": "s",
                    "text": "Pick",
                    "type": "single_select",
                    "options": ["x", "y"],
                    "default": "y",
                }
            ]
        )
        assert 'value="y" selected' in html

    def test_required_marker_only_when_required(self):
        html = _render(
            [
                {"id": "r", "text": "Req", "type": "text_input"},
                {
                    "id": "o",
                    "text": "Opt",
                    "type": "text_input",
                    "required": False,
                },
            ]
        )
        # one required field -> exactly one required marker
        assert html.count('class="ae-req"') == 1


class TestPostback:
    def test_marker_embedded_as_js_key(self):
        html = _render([{"id": "a", "text": "A?", "type": "text_input"}])
        assert WIDGET_RESPONSE_MARKER in html
        # embedded as a quoted JS object key
        assert f"'{WIDGET_RESPONSE_MARKER}'" in html

    def test_sendprompt_wired(self):
        html = _render([{"id": "a", "text": "A?", "type": "text_input"}])
        assert "sendPrompt(" in html
        assert "JSON.stringify(payload)" in html

    def test_number_value_coerced_to_number(self):
        html = _render([{"id": "n", "text": "N?", "type": "number"}])
        assert "Number(el.value)" in html


class TestRequiredGate:
    """Regression guard for the 2026-08-10 live failure: a required
    multi_select with nothing checked posted ``[]``, the submit script
    disabled the button and showed "Submitted", and the server-side
    reject then landed on a dead widget — the user had to answer in
    chat. The submit script must gate on required fields BEFORE
    posting: visible error, button stays alive.
    """

    _FIELDS = [
        {
            "id": "scope",
            "text": "Scope?",
            "type": "single_select",
            "options": ["narrow", "broad"],
        },
        {
            "id": "probes",
            "text": "Probes?",
            "type": "multi_select",
            "options": ["unit", "behavioral"],
        },
        {
            "id": "notes",
            "text": "Notes?",
            "type": "text_input",
            "required": False,
        },
    ]

    def test_required_fields_carry_data_required(self):
        html = _render(self._FIELDS)
        # scope + probes are required (the default); notes is not.
        assert html.count('data-required="1"') == 2
        assert 'data-fid="notes" data-ftype="text_input">' in html

    def test_multi_select_checked_boxes_post_as_array(self):
        html = _render(self._FIELDS)
        script = html[html.index("<script>") :]
        # The multi_select branch collects every checked control into an
        # array and posts it under the field id.
        assert "ftype === 'multi_select'" in script
        assert "[data-control]:checked" in script
        assert "answers[fid] = vals" in script

    def test_missing_required_blocks_send_with_visible_error(self):
        html = _render(self._FIELDS)
        script = html[html.index("<script>") :]
        # The gate reads data-required fields, treats undefined / '' /
        # empty-array as unanswered, and shows the error in the alert div.
        assert ".ae-field[data-required]" in script
        assert "Array.isArray(v) && v.length === 0" in script
        assert "'Required: '" in script
        assert "ae-field-missing" in script
        # Ordering: the gate fires BEFORE sendPrompt, and the button is
        # only disabled after a successful send — never on a rejection.
        assert script.index("'Required: '") < script.index("sendPrompt(")
        assert script.index("sendPrompt(") < script.index("btn.disabled = true")


class TestEscaping:
    def test_malicious_label_is_escaped(self):
        html = _render([{"id": "a", "text": "<script>alert(1)</script>", "type": "text_input"}])
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_malicious_option_is_escaped(self):
        html = _render(
            [
                {
                    "id": "s",
                    "text": "Pick",
                    "type": "single_select",
                    "options": ['"><img src=x onerror=alert(1)>'],
                }
            ]
        )
        assert "onerror=alert(1)>" not in html
        assert "&lt;img" in html

    def test_quote_in_id_does_not_break_attribute(self):
        html = _render([{"id": 'a"x', "text": "A?", "type": "text_input"}])
        assert 'data-fid="a"x"' not in html
        assert "&quot;" in html
