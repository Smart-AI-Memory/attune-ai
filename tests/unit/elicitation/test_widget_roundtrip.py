"""Standing widget round-trip check (issue #1656).

Exercises the real renderer→validator loop the manual live-widget
ritual guards: ``form_to_widget_html`` emits the DOM + submit script;
a small DOM simulator reads the emitted HTML the way the submit
script's reader does (by ``data-fid`` / ``data-collect`` /
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

#: The full ``data-collect`` vocabulary the renderer can emit — HOW the
#: submit script reads each field's answer out of the DOM (mirrors
#: ``widget._COLLECT_MODES`` plus its ``value`` default). The script
#: switches on the attribute, never on the construct type; ``value`` is
#: the switch's else-tail (read the field's one control directly), so it
#: never appears as a literal case in the script.
_COLLECT_VOCABULARY = {
    "value",
    "checked-one",
    "checked-many",
    "rulings",
    "ranked",
    "rulings-with-text",
}


class _WidgetDOM(HTMLParser):
    """Parse the emitted widget HTML into fields the way the submit
    script sees them: ``.ae-field`` wrappers carrying ``data-fid`` /
    ``data-collect``, each holding its ``[data-control]`` elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.script = ""
        self.fields: list[dict[str, Any]] = []
        self._in_script = False
        self._select: dict[str, Any] | None = None
        self._textarea: dict[str, Any] | None = None
        self._item: str | None = None
        self._in_ranked = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "form":
            self.title = a.get("data-form-title")
        elif tag == "script":
            self._in_script = True
        if "data-fid" in a:
            self.fields.append(
                {
                    "fid": a["data-fid"],
                    "ftype": a.get("data-ftype"),
                    "collect": a.get("data-collect"),
                    "required": "data-required" in a,
                    "controls": [],
                }
            )
            self._item = None
        if "data-rank-n" in a and self.fields:
            # The ranking's slot budget, which the script reads off the
            # same attribute to cap "add" clicks.
            self.fields[-1]["slots"] = int(a["data-rank-n"] or 0)
        if "ae-rank-ranked" in (a.get("class") or ""):
            # Rows rendered INSIDE the ranked <ol> (a `suggested` order
            # pre-populates it) are already the answer the script reads
            # at submit — the simulator must see them without a _fill,
            # or it claims an untouched form posts nothing when the real
            # widget posts the proposal (review finding, 2026-08-16).
            self._in_ranked = True
        elif "ae-rank-pool" in (a.get("class") or ""):
            self._in_ranked = False
        if "data-item" in a and self.fields:
            # A triage row: subsequent controls belong to this item, the
            # way the submit script scopes its per-row query. The row
            # count is what the gate's completeness check divides by
            # (`f.querySelectorAll('[data-item]').length`).
            self._item = a["data-item"]
            self.fields[-1]["rows"] = self.fields[-1].get("rows", 0) + 1
        if "data-control" in a and self.fields:
            controls = self.fields[-1]["controls"]
            if self._in_ranked and tag == "input":
                self.fields[-1].setdefault("ranked", []).append(a.get("value", "") or "")
            if tag == "input":
                controls.append(
                    {
                        "type": a.get("type", "text"),
                        "value": a.get("value", "") or "",
                        "checked": "checked" in a,
                        "item": self._item,
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
        if isinstance(value, dict):
            # Triage / assumption review: per-row radios — check the row's
            # chosen ruling; an edit ruling also types its replacement text
            # into the row's text box.
            for ctl in field["controls"]:
                ruling = value.get(ctl.get("item"))
                if ctl["type"] == "radio":
                    wanted_value = "edit" if isinstance(ruling, dict) else ruling
                    ctl["checked"] = wanted_value == ctl["value"]
                elif ctl["type"] == "text" and isinstance(ruling, dict):
                    ctl["value"] = ruling.get("edit", "")
            continue
        wanted = [str(v) for v in (value if isinstance(value, list) else [value])]
        if field["collect"] == "ranked":
            # Ranking: the user moves rows into the ranked list in the
            # answer's order — the DOM order the script reads at submit.
            # The script refuses an "add" past the slot budget, so the
            # simulator caps too rather than modelling a fill no user
            # could perform.
            picked = [v for v in wanted if v in {c["value"] for c in field["controls"]}]
            field["ranked"] = picked[: field.get("slots", len(picked))]
            continue
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
    """Build the payload the submit script posts, per its reader logic:
    a switch on each field's ``data-collect`` mode."""
    answers: dict[str, Any] = {}
    for field in dom.fields:
        fid, mode, controls = field["fid"], field["collect"], field["controls"]
        if mode == "checked-many":
            answers[fid] = [c["value"] for c in controls if c.get("checked")]
        elif mode == "checked-one":
            picked = next((c for c in controls if c.get("checked")), None)
            if picked:
                answers[fid] = picked["value"]
        elif mode == "rulings":
            rulings = {c["item"]: c["value"] for c in controls if c.get("checked")}
            if rulings:
                answers[fid] = rulings
        elif mode == "rulings-with-text":
            rulings: dict[str, Any] = {}
            texts = {c["item"]: c["value"] for c in controls if c["type"] == "text"}
            for c in controls:
                if c["type"] == "radio" and c.get("checked"):
                    item = c["item"]
                    rulings[item] = (
                        {"edit": texts.get(item, "")} if c["value"] == "edit" else c["value"]
                    )
            if rulings:
                answers[fid] = rulings
        elif mode == "ranked":
            # The ranked list's rows in DOM order; untouched posts nothing.
            if field.get("ranked"):
                answers[fid] = list(field["ranked"])
        else:
            # 'value': the field's one control, read directly; a number
            # input posts a Number (the control type, not the construct,
            # decides).
            if not controls:
                continue
            el = controls[0]
            if el["value"] != "":
                answers[fid] = float(el["value"]) if el["type"] == "number" else el["value"]
    payload = {WIDGET_RESPONSE_MARKER: True, "title": dom.title, "answers": answers}
    # The payload must survive the JSON.stringify → agent-parse hop.
    return json.loads(json.dumps(payload))


def _gate(dom: _WidgetDOM, answers: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Port of the submit script's required-field gate, rule for rule.

    Mirrors the two gate passes the script runs before posting: the
    required-field check (empty answer, incomplete rulings board, an
    unfilled ranking slot, an ``edit`` ruling with blank replacement
    text) and the all-or-nothing check for OPTIONAL partially-filled
    rankings. Returns ``(missing, partial)`` field-id lists — the
    script blocks the post when either is non-empty.
    """
    missing: list[str] = []
    for field in dom.fields:
        if not field.get("required"):
            continue
        v = answers.get(field["fid"])
        rows = field.get("rows", 0)
        slots = field.get("slots", 0)
        blank_edit = False
        if isinstance(v, dict):
            for ruling in v.values():
                if isinstance(ruling, dict) and not str(ruling.get("edit") or "").strip():
                    blank_edit = True
        empty = (
            v is None
            or v == ""
            or (isinstance(v, list) and not v)
            or (rows > 0 and (not v or len(v) < rows))
            or (slots > 0 and (not v or len(v) < slots))
            or blank_edit
        )
        if empty:
            missing.append(field["fid"])
    partial: list[str] = []
    for field in dom.fields:
        if field.get("required"):
            continue
        slots = field.get("slots", 0)
        if not slots:
            continue
        v = answers.get(field["fid"])
        if not isinstance(v, list) or len(v) == 0 or len(v) >= slots:
            continue
        partial.append(field["fid"])
    return missing, partial


def _gate_allows(dom: _WidgetDOM) -> bool:
    """True iff the gate would let the current DOM state post."""
    missing, partial = _gate(dom, _submit(dom)["answers"])
    return not missing and not partial


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

    def test_script_switch_covers_the_emitted_collect_modes(self) -> None:
        """Drift catcher: the ``data-collect`` modes the renderer emits
        and the cases the emitted reader switches on are both exactly
        the pinned vocabulary (``value`` is the switch's else-tail, so
        it never appears as a literal case). A new construct type must
        reuse a handled mode — or add its case to the script AND here."""
        _, dom = _render_reference()
        handled = set(re.findall(r"mode === '([\w-]+)'", dom.script)) | {"value"}
        emitted = {f["collect"] for f in dom.fields}
        assert emitted == _COLLECT_VOCABULARY  # reference form spans it
        assert handled == _COLLECT_VOCABULARY


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

    def test_list_style_single_select_collects_as_checked_one(self) -> None:
        """A ``list_style`` SINGLE_SELECT renders radios, not a native
        ``<select>`` — its field must emit ``data-collect="checked-one"``
        so the reader picks the checked radio (the render-time mode
        switch is what replaced the reader's old radio sniffing), and
        the answer must round-trip."""
        form = form_from_dict(
            {
                "title": "List pick",
                "fields": [
                    {
                        "id": "route",
                        "type": "single_select",
                        "text": "Which route?",
                        "options": ["a", "b"],
                        "list_style": "ordered",
                    }
                ],
            }
        )
        dom = _WidgetDOM()
        dom.feed(form_to_widget_html(form, instance_id="ls"))
        assert dom.fields[0]["collect"] == "checked-one"
        _fill(dom, {"route": "b"})
        payload = _submit(dom)
        response = collect_form_response(form, payload["answers"])
        assert response.responses["route"] == "b"

    def test_unanswered_required_fields_fail_validation_by_name(self) -> None:
        """R4 seam: an empty submit must be rejected naming the missing
        required fields — never silently accepted."""
        form, dom = _render_reference()
        payload = _submit(dom)  # nothing filled in
        with pytest.raises(FormValidationError) as excinfo:
            collect_form_response(form, payload["answers"])
        assert "feature_name" in str(excinfo.value)


class TestReviewFindings:
    """Regressions pinned from the 2026-08-16 five-lens review: the
    simulator diverged from the real submit script on rankings — it
    never read rows pre-populated in the ranked <ol> and it filled past
    the slot budget the script caps at."""

    def test_untouched_suggested_ranking_posts_the_proposal(self) -> None:
        """The reference form's ranking carries a `suggested` order, so
        its rows render INSIDE the ranked <ol> — an untouched submit
        posts the proposal (the visible badge plus the submit IS the
        confirmation, D2-c), never nothing."""
        form, dom = _render_reference()
        payload = _submit(dom)  # untouched
        assert payload["answers"]["rollout_order"] == ["staging", "canary", "eu-prod"]

    def test_fill_caps_ranking_at_the_slot_budget(self) -> None:
        """The script refuses an "add" past `data-rank-n`; the simulator
        must model the same cap rather than a fill no user could
        perform."""
        _, dom = _render_reference()
        _fill(dom, {"rollout_order": ["us-prod", "eu-prod", "canary", "staging"]})
        field = next(f for f in dom.fields if f["fid"] == "rollout_order")
        assert field["ranked"] == ["us-prod", "eu-prod", "canary"]


def _gate_form(field: dict[str, Any]) -> tuple[Any, _WidgetDOM]:
    form = form_from_dict({"title": "Gate parity", "fields": [field]})
    dom = _WidgetDOM()
    dom.feed(form_to_widget_html(form, instance_id="gate"))
    return form, dom


#: One fixture per construct type × fill state: ``(case id, field dict,
#: fill)`` — ``fill=None`` leaves the rendered DOM untouched. No case
#: hardcodes an expected verdict: the parity assertion is the property
#: itself (gate blocks ⇔ validator rejects), so a fixture whose two
#: sides disagree fails no matter which side is "right".
_TRIAGE_FIELD: dict[str, Any] = {
    "id": "board",
    "type": "triage",
    "text": "Rule each finding.",
    "triage_items": [{"id": "a", "label": "Finding A"}, {"id": "b", "label": "Finding B"}],
    "dispositions": ["fix", "dismiss"],
}
_ASSUME_FIELD: dict[str, Any] = {
    "id": "review",
    "type": "assumption_review",
    "text": "Rule each assumption.",
    "assumptions": [{"id": "a1", "label": "Py 3.10 floor"}, {"id": "a2", "label": "CI on push"}],
}
_RANK_FIELD: dict[str, Any] = {
    "id": "order",
    "type": "ranking",
    "text": "Ship order?",
    "options": ["staging", "canary", "prod"],
    "top_n": 2,
}
_GATE_CASES: list[tuple[str, dict[str, Any], Any]] = [
    ("text-empty", {"id": "f", "type": "text_input", "text": "Name?"}, None),
    ("text-filled", {"id": "f", "type": "text_input", "text": "Name?"}, "Dark mode"),
    (
        "select-empty",
        {"id": "f", "type": "single_select", "text": "?", "options": ["a", "b"]},
        None,
    ),
    (
        "select-filled",
        {"id": "f", "type": "single_select", "text": "?", "options": ["a", "b"]},
        "b",
    ),
    ("multi-empty", {"id": "f", "type": "multi_select", "text": "?", "options": ["a", "b"]}, None),
    (
        "multi-filled",
        {"id": "f", "type": "multi_select", "text": "?", "options": ["a", "b"]},
        ["a"],
    ),
    ("boolean-empty", {"id": "f", "type": "boolean", "text": "?"}, None),
    ("boolean-filled", {"id": "f", "type": "boolean", "text": "?"}, "Yes"),
    ("number-empty", {"id": "f", "type": "number", "text": "?", "minimum": 0}, None),
    ("number-zero", {"id": "f", "type": "number", "text": "?", "minimum": 0}, 0),
    ("date-empty", {"id": "f", "type": "date", "text": "?"}, None),
    ("date-filled", {"id": "f", "type": "date", "text": "?"}, "2026-08-01"),
    ("textarea-empty", {"id": "f", "type": "textarea", "text": "?"}, None),
    ("textarea-filled", {"id": "f", "type": "textarea", "text": "?"}, "notes"),
    (
        "decision-empty",
        {
            "id": "f",
            "type": "decision",
            "text": "?",
            "options": ["flag", "all at once"],
            "recommended": "flag",
            "rationale": "safer",
        },
        None,
    ),
    (
        "decision-filled",
        {
            "id": "f",
            "type": "decision",
            "text": "?",
            "options": ["flag", "all at once"],
            "recommended": "flag",
            "rationale": "safer",
        },
        "flag",
    ),
    (
        "pushback-empty",
        {
            "id": "f",
            "type": "pushback",
            "text": "?",
            "options": ["branch", "stacked PRs"],
            "user_position": "branch",
            "recommended": "stacked PRs",
            "rationale": "drift",
        },
        None,
    ),
    (
        "deliberation-filled",
        {
            "id": "f",
            "type": "deliberation",
            "text": "?",
            "options": ["lru", "redis"],
            "endorsements": {"lru": ["claude"]},
            "recommended": "lru",
            "rationale": "one consumer",
        },
        "lru",
    ),
    (
        "progress-empty",
        {
            "id": "f",
            "type": "progress",
            "text": "?",
            "options": ["Design sign-off"],
            "progress_items": [
                {"label": "Prototype", "status": "done"},
                {"label": "Design sign-off", "status": "blocked"},
            ],
        },
        None,
    ),
    (
        "progress-filled",
        {
            "id": "f",
            "type": "progress",
            "text": "?",
            "options": ["Design sign-off"],
            "progress_items": [
                {"label": "Prototype", "status": "done"},
                {"label": "Design sign-off", "status": "blocked"},
            ],
        },
        "Design sign-off",
    ),
    (
        "confirm-empty",
        {"id": "f", "type": "confirm", "text": "Flip the flag?", "consequences": [{"label": "x"}]},
        None,
    ),
    (
        "confirm-approved",
        {"id": "f", "type": "confirm", "text": "Flip the flag?", "consequences": [{"label": "x"}]},
        "Approve",
    ),
    ("triage-empty", _TRIAGE_FIELD, None),
    ("triage-partial", _TRIAGE_FIELD, {"a": "fix"}),
    ("triage-full", _TRIAGE_FIELD, {"a": "fix", "b": "dismiss"}),
    ("triage-optional-partial", {**_TRIAGE_FIELD, "required": False}, {"a": "fix"}),
    ("ranking-empty", _RANK_FIELD, None),
    ("ranking-partial", _RANK_FIELD, ["staging"]),
    ("ranking-full", _RANK_FIELD, ["staging", "prod"]),
    ("ranking-optional-empty", {**_RANK_FIELD, "required": False}, None),
    ("ranking-optional-partial", {**_RANK_FIELD, "required": False}, ["staging"]),
    ("assume-empty", _ASSUME_FIELD, None),
    ("assume-partial", _ASSUME_FIELD, {"a1": "accept"}),
    ("assume-blank-edit", _ASSUME_FIELD, {"a1": {"edit": ""}, "a2": "accept"}),
    ("assume-edit-text", _ASSUME_FIELD, {"a1": {"edit": "3.11 floor"}, "a2": "accept"}),
    ("assume-full", _ASSUME_FIELD, {"a1": "accept", "a2": "reject"}),
]


class TestGateParity:
    """The submit script's client-side gate re-implements the server
    validators' completeness rules (required boards fully ruled, ranking
    all-or-nothing, blank ``edit`` text). Nothing in production keeps the
    two in sync — this class is the sync test (architecture review
    finding F2, 2026-08-20): for every construct × fill state, the gate
    blocks the post exactly when ``collect_form_response`` would reject
    the posted payload.
    """

    @pytest.mark.parametrize(
        ("field", "fill"),
        [pytest.param(f, v, id=cid) for cid, f, v in _GATE_CASES],
    )
    def test_gate_blocks_iff_validator_rejects(self, field: dict[str, Any], fill: Any) -> None:
        form, dom = _gate_form(field)
        if fill is not None:
            _fill(dom, {field["id"]: fill})
        payload = _submit(dom)
        try:
            collect_form_response(form, payload["answers"])
            validator_clean = True
        except FormValidationError:
            validator_clean = False
        assert _gate_allows(dom) == validator_clean

    def test_untouched_reference_form_gate_matches_validator(self) -> None:
        """The all-construct form, untouched: the gate must block for
        the same reason the validator names required fields."""
        form, dom = _render_reference()
        payload = _submit(dom)
        with pytest.raises(FormValidationError):
            collect_form_response(form, payload["answers"])
        assert not _gate_allows(dom)

    def test_filled_reference_form_gate_matches_validator(self) -> None:
        """The all-construct form, fully filled: both sides pass."""
        form, dom = _render_reference()
        _fill(dom, EXAMPLE_ANSWERS)
        payload = _submit(dom)
        collect_form_response(form, payload["answers"])  # no problems
        assert _gate_allows(dom)

    def test_gate_reads_the_anchors_the_renderer_emits(self) -> None:
        """Structural drift catcher, gate edition (extends the reader's
        collect-mode pin at :meth:`TestSentinelContract`): every DOM
        anchor the gate JS queries must appear in the emitted script,
        and the ``data-required`` flags the renderer emits must match
        the form's required questions — a renamed attribute on either
        side fails here before it silently disables a gate rule."""
        form, dom = _render_reference()
        for anchor in (
            "data-required",
            "[data-item]",
            "data-rank-n",
            ".ae-rank",
            "ae-field-missing",
        ):
            assert anchor in dom.script, f"gate anchor {anchor!r} missing from script"
        required_fids = {f["fid"] for f in dom.fields if f.get("required")}
        assert required_fids == {q.id for q in form.questions if q.required}
