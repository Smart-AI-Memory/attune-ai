"""Standing widget round-trip check (issue #1656).

Exercises the real renderer→validator loop the manual live-widget
ritual guards: ``form_to_widget_html`` emits the DOM + submit script;
a small DOM simulator reads the emitted HTML the way the submit
script's reader does (by ``data-fid`` / ``data-ftype`` /
``data-control``); the resulting payload is validated through
``collect_form_response``, asserting the ``__elicitation_response__``
sentinel contract and the field-id round trip.

This deliberately does NOT prove a browser renders the form — a real
human submit stays the gold receipt (communication-grammar step 7).
What it does catch, in CI, is the drift class where the renderer and
the validator disagree: a control whose posted shape the validator
rejects, a field id that doesn't survive the DOM, an escaping bug
that corrupts option values, or a construct type the submit script
can't read.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

import pytest

from attune.elicitation import (
    WIDGET_RESPONSE_MARKER,
    FormValidationError,
    collect_form_response,
    form_from_dict,
    form_to_widget_html,
)
from attune.elicitation.reference_form import EXAMPLE_ANSWERS, REFERENCE_FORM

#: data-ftype values the submit script special-cases (read from a
#: checked control rather than the generic first-control tail).
_CHECKED_FTYPES = {"decision", "pushback", "progress"}


class _WidgetDOM(HTMLParser):
    """Parse the emitted widget HTML into fields the way the submit
    script sees them: ``.ae-field`` wrappers carrying ``data-fid`` /
    ``data-ftype``, each holding its ``[data-control]`` elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.script = ""
        self.fields: list[dict[str, Any]] = []
        self._in_script = False
        self._select: dict[str, Any] | None = None
        self._textarea: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "form":
            self.title = a.get("data-form-title")
        elif tag == "script":
            self._in_script = True
        if "data-fid" in a:
            self.fields.append({"fid": a["data-fid"], "ftype": a.get("data-ftype"), "controls": []})
        if "data-control" in a and self.fields:
            controls = self.fields[-1]["controls"]
            if tag == "input":
                controls.append(
                    {
                        "type": a.get("type", "text"),
                        "value": a.get("value", "") or "",
                        "checked": "checked" in a,
                    }
                )
            elif tag == "select":
                self._select = {"type": "select-one", "value": "", "options": []}
                controls.append(self._select)
            elif tag == "textarea":
                self._textarea = {"type": "textarea", "value": ""}
                controls.append(self._textarea)
        elif tag == "option" and self._select is not None:
            value = a.get("value", "") or ""
            self._select["options"].append(value)
            if "selected" in a:
                self._select["value"] = value

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_script = False
        elif tag == "select":
            self._select = None
        elif tag == "textarea":
            self._textarea = None

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self.script += data
        if self._textarea is not None:
            self._textarea["value"] += data


def _fill(dom: _WidgetDOM, answers: dict[str, Any]) -> None:
    """Apply user answers to the parsed DOM (check boxes, set values)."""
    for field in dom.fields:
        if field["fid"] not in answers:
            continue
        value = answers[field["fid"]]
        wanted = [str(v) for v in (value if isinstance(value, list) else [value])]
        for ctl in field["controls"]:
            if ctl["type"] in ("checkbox", "radio"):
                # Radio semantics: picking one clears the group.
                ctl["checked"] = ctl["value"] in wanted
            elif "options" in ctl:
                if str(value) in ctl["options"]:
                    ctl["value"] = str(value)
            else:
                ctl["value"] = str(value)


def _submit(dom: _WidgetDOM) -> dict[str, Any]:
    """Build the payload the submit script posts, per its reader logic."""
    answers: dict[str, Any] = {}
    for field in dom.fields:
        fid, ftype, controls = field["fid"], field["ftype"], field["controls"]
        if ftype == "multi_select":
            answers[fid] = [c["value"] for c in controls if c.get("checked")]
        elif ftype in _CHECKED_FTYPES:
            picked = next((c for c in controls if c.get("checked")), None)
            if picked:
                answers[fid] = picked["value"]
        else:
            if not controls:
                continue
            el = controls[0]
            if el["type"] == "radio":
                picked = next((c for c in controls if c.get("checked")), None)
                if picked:
                    answers[fid] = picked["value"]
            elif el["value"] != "":
                answers[fid] = float(el["value"]) if ftype == "number" else el["value"]
    payload = {WIDGET_RESPONSE_MARKER: True, "title": dom.title, "answers": answers}
    # The payload must survive the JSON.stringify → agent-parse hop.
    return json.loads(json.dumps(payload))


def _render_reference() -> tuple[Any, _WidgetDOM]:
    form = form_from_dict(REFERENCE_FORM)
    dom = _WidgetDOM()
    dom.feed(form_to_widget_html(form, instance_id="roundtrip"))
    return form, dom


class TestSentinelContract:
    def test_submit_script_posts_the_sentinel_key(self) -> None:
        _, dom = _render_reference()
        assert WIDGET_RESPONSE_MARKER == "__elicitation_response__"
        assert f"'{WIDGET_RESPONSE_MARKER}'" in dom.script
        assert "sendPrompt" in dom.script

    def test_payload_carries_sentinel_and_form_title(self) -> None:
        form, dom = _render_reference()
        payload = _submit(dom)
        assert payload[WIDGET_RESPONSE_MARKER] is True
        assert payload["title"] == form.title

    def test_script_special_cases_cover_the_construct_types(self) -> None:
        """Drift catcher: every ftype the script must read from a checked
        control is actually special-cased in the emitted reader."""
        _, dom = _render_reference()
        handled = set(re.findall(r"ftype === '(\w+)'", dom.script))
        assert _CHECKED_FTYPES | {"multi_select"} <= handled


class TestFieldIdRoundTrip:
    def test_every_question_renders_a_readable_field(self) -> None:
        form, dom = _render_reference()
        rendered = {f["fid"]: f for f in dom.fields}
        assert set(rendered) == {q.id for q in form.questions}
        for q in form.questions:
            field = rendered[q.id]
            assert field["ftype"] == q.type.value
            assert field["controls"], f"{q.id} has no data-control element"

    def test_reference_form_round_trips_through_validator(self) -> None:
        """The standing check: render → fill → submit → validate. Every
        control type in the grammar round-trips (the reference form is
        drift-guarded to stay complete)."""
        form, dom = _render_reference()
        _fill(dom, EXAMPLE_ANSWERS)
        payload = _submit(dom)
        response = collect_form_response(form, payload["answers"])
        assert set(response.responses) == set(EXAMPLE_ANSWERS)
        for fid, expected in EXAMPLE_ANSWERS.items():
            got = response.responses[fid]
            if isinstance(expected, int | float) and not isinstance(expected, bool):
                # The script posts Number(el.value); 3 -> 3.0 is the same
                # answer.
                assert got == pytest.approx(expected)
            else:
                assert got == expected

    def test_html_special_characters_survive_the_dom_hop(self) -> None:
        """Escaping drift catcher: an option containing markup-significant
        characters must come back byte-identical through render → parse →
        validate (a corrupted value would fail membership validation)."""
        spicy = 'R&D "fast" <path> option'
        form = form_from_dict(
            {
                "title": "Escaping check",
                "fields": [
                    {
                        "id": "route",
                        "type": "single_select",
                        "text": "Which route?",
                        "options": [spicy, "plain"],
                    }
                ],
            }
        )
        dom = _WidgetDOM()
        dom.feed(form_to_widget_html(form, instance_id="esc"))
        _fill(dom, {"route": spicy})
        payload = _submit(dom)
        assert payload["answers"]["route"] == spicy
        response = collect_form_response(form, payload["answers"])
        assert response.responses["route"] == spicy

    def test_unanswered_required_fields_fail_validation_by_name(self) -> None:
        """R4 seam: an empty submit must be rejected naming the missing
        required fields — never silently accepted."""
        form, dom = _render_reference()
        payload = _submit(dom)  # nothing filled in
        with pytest.raises(FormValidationError) as excinfo:
            collect_form_response(form, payload["answers"])
        assert "feature_name" in str(excinfo.value)
