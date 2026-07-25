"""Tests for the D21 surface router and its inputs.

Covers ``select_form_surface`` (the widget-by-default product router),
``is_trivial_form`` (the narrow mechanical exemption),
``keyboard_mode_enabled`` (the per-project opt-out), and
``form_response_summary`` (the collapse path).

The regression these guard: the default used to be "cheapest surface
that fits", so a multi-dimension all-select form routed to
``AskUserQuestion``. D21 flipped it. ``test_multi_dimension_form_*``
below fails if that flip is ever reverted.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from attune.elicitation import (
    collect_form_response,
    form_from_dict,
    form_response_summary,
    is_trivial_form,
    keyboard_mode_enabled,
    needs_widget,
    select_form_surface,
)


def _form(fields: list[dict]) -> object:
    """Build a FormSchema from field dicts."""
    return form_from_dict({"title": "T", "description": "d", "fields": fields})


def _select(**options: object) -> dict:
    """A single_select field with the given overrides."""
    base = {"id": "a", "type": "single_select", "text": "Which?", "options": ["x", "y"]}
    base.update(options)
    return base


@pytest.fixture(autouse=True)
def _isolate_telemetry_and_env(tmp_path, monkeypatch):
    """Keep routing telemetry and the opt-out out of the real home/cwd."""
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "attune-home"))
    monkeypatch.delenv("ATTUNE_KEYBOARD_MODE", raising=False)
    monkeypatch.chdir(tmp_path)


# --------------------------------------------------------------------
# select_form_surface — the flipped default
# --------------------------------------------------------------------


def test_multi_dimension_form_defaults_to_widget() -> None:
    """The D21 flip: >1 all-select field is no longer an AskUserQuestion form.

    This is the exact class the old ``needs_widget``-owned routing sent
    to buttons. If this returns ``"ask"``, the flip was reverted.
    """
    form = _form([_select(id="a"), _select(id="b")])
    assert needs_widget(form) is False  # still AskUserQuestion-expressible
    assert select_form_surface(form) == "widget"  # ...but no longer routed there


def test_single_select_over_three_options_routes_to_widget() -> None:
    form = _form([_select(options=["w", "x", "y", "z"])])
    assert select_form_surface(form) == "widget"


def test_trivial_boolean_routes_to_ask() -> None:
    form = _form([{"id": "q", "type": "boolean", "text": "Proceed?"}])
    assert select_form_surface(form) == "ask"


def test_non_widget_client_falls_back_even_for_rich_form() -> None:
    """Capability is a constraint, not a preference — it outranks everything."""
    form = _form([{"id": "n", "type": "number", "text": "How many?"}])
    assert select_form_surface(form, widget_capable=False) == "ask"


def test_keyboard_mode_falls_back_for_expressible_form() -> None:
    form = _form([_select(id="a"), _select(id="b")])
    assert select_form_surface(form, keyboard_mode=True) == "ask"


def test_no_portable_control_outranks_keyboard_mode() -> None:
    """The opt-out must never silently drop a field the surface can't render."""
    for control in ("number", "date", "textarea"):
        form = _form([{"id": "f", "type": control, "text": "?"}])
        assert select_form_surface(form, keyboard_mode=True) == "widget", control


@pytest.mark.parametrize("construct", ["decision", "pushback", "progress"])
def test_constructs_are_lossy_not_impossible(construct: str) -> None:
    """Constructs default to the widget but yield to an explicit opt-out.

    Unlike number/date/textarea they *do* have an AskUserQuestion
    fallback (recommendation-first single-select), so keyboard mode may
    take it.
    """
    field = {
        "id": "d",
        "type": construct,
        "text": "Which approach?",
        "options": ["x", "y"],
        "recommended": "x",
    }
    if construct == "progress":
        # A progress form reports items by status; the blocked subset's
        # labels must equal ``options``.
        field["progress_items"] = [
            {"label": "done thing", "status": "done"},
            {"label": "x", "status": "blocked"},
            {"label": "y", "status": "blocked"},
        ]
    form = _form([field])
    assert select_form_surface(form) == "widget"
    assert select_form_surface(form, keyboard_mode=True) == "ask"


# --------------------------------------------------------------------
# is_trivial_form — the narrow exemption
# --------------------------------------------------------------------


def test_trivial_requires_single_question() -> None:
    assert is_trivial_form(_form([_select(id="a")])) is True
    assert is_trivial_form(_form([_select(id="a"), _select(id="b")])) is False


def test_trivial_rejects_more_than_three_options() -> None:
    assert is_trivial_form(_form([_select(options=["a", "b", "c"])])) is True
    assert is_trivial_form(_form([_select(options=["a", "b", "c", "d"])])) is False


def test_long_option_label_is_not_trivial() -> None:
    """Long labels mean tradeoffs were folded into the text — that wants a card."""
    assert is_trivial_form(_form([_select(options=["ok", "x" * 121])])) is False
    assert is_trivial_form(_form([_select(options=["ok", "x" * 120])])) is True


def test_multi_select_is_not_trivial() -> None:
    field = {"id": "m", "type": "multi_select", "text": "Which?", "options": ["a"]}
    assert is_trivial_form(_form([field])) is False


# --------------------------------------------------------------------
# keyboard_mode_enabled — per-project, env override
# --------------------------------------------------------------------


def test_keyboard_mode_defaults_off(tmp_path: Path) -> None:
    assert keyboard_mode_enabled(tmp_path) is False


def test_keyboard_mode_reads_project_config(tmp_path: Path) -> None:
    (tmp_path / "attune.config.json").write_text(json.dumps({"keyboard_mode": True}))
    assert keyboard_mode_enabled(tmp_path) is True


def test_env_overrides_project_config_both_directions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "attune.config.json").write_text(json.dumps({"keyboard_mode": True}))
    monkeypatch.setenv("ATTUNE_KEYBOARD_MODE", "0")
    assert keyboard_mode_enabled(tmp_path) is False
    monkeypatch.setenv("ATTUNE_KEYBOARD_MODE", "1")
    assert keyboard_mode_enabled(tmp_path) is True


def test_malformed_project_config_is_not_an_error(tmp_path: Path) -> None:
    """Routing must never fail because a config file is bad."""
    (tmp_path / "attune.config.json").write_text("{not json")
    assert keyboard_mode_enabled(tmp_path) is False


# --------------------------------------------------------------------
# form_response_summary — the collapse path
# --------------------------------------------------------------------


def test_response_summary_renders_answers_and_omits_unanswered() -> None:
    form = _form(
        [
            _select(id="scope", text="Which path?", options=["src", "tests"]),
            {
                "id": "concerns",
                "type": "multi_select",
                "text": "Which concerns?",
                "options": ["impl", "docs"],
                "required": False,
            },
            {"id": "skipped", "type": "text_input", "text": "Notes?", "required": False},
        ]
    )
    response = collect_form_response(form, {"scope": "src", "concerns": ["impl", "docs"]})
    summary = form_response_summary(form, response)

    assert "Which path?: **src**" in summary
    assert "Which concerns?: **impl, docs**" in summary
    assert "Notes?" not in summary  # unanswered questions are omitted
    assert summary.count("\n") == 2  # title + 2 answered bullets


# --------------------------------------------------------------------
# the decay receipt
# --------------------------------------------------------------------


def test_routing_decisions_are_logged_and_readable() -> None:
    """Non-mocked round trip: route -> persist -> read back the mix."""
    from attune.telemetry.form_events import surface_mix

    rich = _form([_select(id="a"), _select(id="b")])
    trivial = _form([{"id": "q", "type": "boolean", "text": "Proceed?"}])

    select_form_surface(rich)
    select_form_surface(rich)
    select_form_surface(trivial)

    assert surface_mix() == {"widget": 2, "ask": 1}


def test_telemetry_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from attune.telemetry.form_events import surface_mix

    monkeypatch.setenv("ATTUNE_FORM_TELEMETRY", "0")
    select_form_surface(_form([_select(id="a"), _select(id="b")]))
    assert surface_mix() == {}


# --------------------------------------------------------------------
# the live call site — the MCP handlers
# --------------------------------------------------------------------
#
# Without these, the router is dead code: nothing in src/ called it, so
# the telemetry above would count zero forever. These assert the wiring,
# not just the predicate.


def _events() -> list[dict]:
    """Read raw telemetry records written during the test."""
    import json

    from attune.telemetry.form_events import _events_path

    path = _events_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _run(handler_name: str, form: dict) -> dict:
    """Invoke an elicitation MCP handler without constructing the server."""
    import asyncio

    from attune.mcp.server import EmpathyMCPServer

    server = EmpathyMCPServer.__new__(EmpathyMCPServer)
    handler = getattr(EmpathyMCPServer, handler_name)
    return asyncio.run(handler(server, {"form": form}))


_RICH = {
    "title": "T",
    "fields": [
        {"id": "a", "type": "single_select", "text": "Scope?", "options": ["src", "tests"]},
        {"id": "b", "type": "single_select", "text": "Depth?", "options": ["quick", "deep"]},
    ],
}
_TRIVIAL = {"title": "T", "fields": [{"id": "q", "type": "boolean", "text": "Proceed?"}]}


def test_render_widget_handler_records_the_decision() -> None:
    result = _run("_handle_elicitation_render_widget", _RICH)
    assert result["success"] is True

    events = _events()
    assert len(events) == 1
    assert events[0]["chosen"] == "widget"
    assert events[0]["surface"] == "widget"
    assert events[0]["agreed"] is True


def test_render_form_handler_records_disagreement_and_nudges() -> None:
    """Agent flattened a form the router wanted rich — both must be visible."""
    result = _run("_handle_elicitation_render_form", _RICH)
    assert result["success"] is True
    assert "surface_note" in result  # the nudge back toward the widget

    events = _events()
    assert len(events) == 1
    assert events[0]["chosen"] == "ask"
    assert events[0]["surface"] == "widget"
    assert events[0]["agreed"] is False


def test_render_form_handler_stays_quiet_when_ask_is_correct() -> None:
    """A trivial form on AskUserQuestion is right — no nag, agreement logged."""
    result = _run("_handle_elicitation_render_form", _TRIVIAL)
    assert "surface_note" not in result

    events = _events()
    assert events[0]["agreed"] is True
    assert events[0]["reason"] == "trivial_form"


def test_handler_survives_broken_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rendering must never fail because the receipt could not be written."""
    import attune.elicitation.bridge as bridge

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(bridge, "log_surface_decision", _boom)
    result = _run("_handle_elicitation_render_widget", _RICH)
    assert result["success"] is True
    assert "html" in result
