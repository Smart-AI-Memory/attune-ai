"""Focused coverage for MCP elicitation handlers."""

from __future__ import annotations

import re
import unittest.mock
from types import SimpleNamespace
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

import attune.mcp.server as server_module

FORM = {
    "title": "Scope the audit",
    "description": "Pick target and depth",
    "fields": [
        {
            "id": "target",
            "text": "Which area?",
            "type": "single_select",
            "options": ["src", "tests"],
        },
        {
            "id": "depth",
            "text": "How deep?",
            "type": "single_select",
            "options": ["quick", "full"],
        },
    ],
}


def _make_server(tmp_path):
    """Create a server without plugin discovery side effects."""
    with patch.object(server_module.AttuneMCPServer, "_register_plugin_tools"):
        return server_module.AttuneMCPServer(workspace_root=str(tmp_path))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("recommendation", "has_surface_note"),
    [("widget", True), (None, False)],
)
async def test_render_form_returns_batches_and_optional_surface_note(
    tmp_path,
    recommendation,
    has_surface_note,
):
    with patch("attune.elicitation.select_form_surface", return_value=recommendation):
        result = await _make_server(tmp_path)._handle_elicitation_render_form({"form": FORM})

    assert result["success"] is True
    assert result["title"] == "Scope the audit"
    assert result["description"] == "Pick target and depth"
    assert [[question["question_id"] for question in batch] for batch in result["batches"]] == [
        ["target", "depth"]
    ]
    assert ("surface_note" in result) is has_surface_note


@pytest.mark.asyncio
async def test_render_form_rejects_malformed_form(tmp_path):
    result = await _make_server(tmp_path)._handle_elicitation_render_form({"form": {"title": "x"}})

    assert result == {
        "success": False,
        "problems": ["form must have a non-empty 'fields' list"],
    }


@pytest.mark.asyncio
async def test_render_widget_returns_content_hashed_form(tmp_path):
    with patch("attune.elicitation.select_form_surface", return_value="widget"):
        result = await _make_server(tmp_path)._handle_elicitation_render_widget(
            {"form": FORM, "message": "Choose carefully"}
        )

    assert result["success"] is True
    assert result["title"] == "Scope the audit"
    assert result["field_ids"] == ["target", "depth"]
    assert '<h2 class="sr-only">' in result["html"]
    assert "Choose carefully" in result["html"]
    assert re.search(r'<form id="attune-elicit-form-[0-9a-f]{8}"', result["html"])


@pytest.mark.asyncio
async def test_render_widget_rejects_malformed_form(tmp_path):
    result = await _make_server(tmp_path)._handle_elicitation_render_widget(
        {"form": {"title": "x"}}
    )

    assert result["success"] is False
    assert result["problems"] == ["form must have a non-empty 'fields' list"]


@pytest.mark.parametrize("error", [OSError("disk"), ValueError("config"), ImportError("module")])
def test_record_surface_choice_swallows_expected_errors(error):
    with patch("attune.elicitation.keyboard_mode_enabled", side_effect=error):
        result = server_module.AttuneMCPServer._record_surface_choice(
            SimpleNamespace(),
            chosen="ask",
        )

    assert result is None


@pytest.mark.asyncio
async def test_collect_response_returns_validated_answers_and_hint(tmp_path):
    with (
        patch("attune.telemetry.form_events.log_submission") as log_submission,
        patch("attune.telemetry.form_events.maybe_keyboard_hint", return_value="Press K"),
        patch("attune.elicitation.keyboard_mode_enabled", return_value=False),
    ):
        result = await _make_server(tmp_path)._handle_elicitation_collect_response(
            {"form": FORM, "answers": {"target": "src", "depth": "quick"}}
        )

    # Called with the form's telemetry join key — an empty string on
    # attune-forms 0.7.x (no FormSchema.form_id yet), the content hash
    # on >= 0.8.0. Asserting the kwarg shape keeps this green on both.
    log_submission.assert_called_once()
    assert set(log_submission.call_args.kwargs) == {"form_id"}
    assert result["success"] is True
    assert result["responses"] == {"target": "src", "depth": "quick"}
    # forms 0.7.0 appends an 8-hex uniqueness suffix to the response id.
    assert re.fullmatch(r"resp-\d{8}-\d{6}-[0-9a-f]{8}", result["response_id"])
    assert result["hint"] == "Press K"


@pytest.mark.asyncio
async def test_collect_response_omits_empty_hint(tmp_path):
    with (
        patch("attune.telemetry.form_events.log_submission"),
        patch("attune.telemetry.form_events.maybe_keyboard_hint", return_value=None),
        patch("attune.elicitation.keyboard_mode_enabled", return_value=True),
    ):
        result = await _make_server(tmp_path)._handle_elicitation_collect_response(
            {"form": FORM, "answers": {"target": "tests", "depth": "full"}}
        )

    assert result["success"] is True
    assert "hint" not in result


@pytest.mark.asyncio
async def test_collect_response_reports_exact_validation_problems(tmp_path):
    with patch("attune.telemetry.form_events.log_submission"):
        result = await _make_server(tmp_path)._handle_elicitation_collect_response(
            {"form": FORM, "answers": {"target": "nope"}}
        )

    assert result == {
        "success": False,
        "problems": [
            "'target' value 'nope' not in options",
            "'depth' is required",
        ],
    }


@pytest.mark.parametrize("failing_seam", ["log_submission", "maybe_keyboard_hint"])
@pytest.mark.parametrize("error", [OSError("disk"), ValueError("config"), ImportError("module")])
def test_keyboard_hint_swallows_expected_errors(error, failing_seam):
    seams = {"log_submission": {}, "maybe_keyboard_hint": {}}
    seams[failing_seam]["side_effect"] = error
    with (
        patch("attune.telemetry.form_events.log_submission", **seams["log_submission"]),
        patch("attune.telemetry.form_events.maybe_keyboard_hint", **seams["maybe_keyboard_hint"]),
    ):
        result = server_module.AttuneMCPServer._maybe_keyboard_hint()

    assert result is None


def test_keyboard_hint_falls_back_to_zero_arg_log_submission():
    """attune-forms < 0.8.0 has ``log_submission()`` with no params —
    the TypeError falls back to the legacy call instead of dropping the
    submission (or the hint) on the floor."""
    log_submission = unittest.mock.Mock(side_effect=[TypeError("old signature"), None])
    with (
        patch("attune.telemetry.form_events.log_submission", log_submission),
        patch("attune.telemetry.form_events.maybe_keyboard_hint", return_value="Press K"),
        patch("attune.elicitation.keyboard_mode_enabled", return_value=False),
    ):
        result = server_module.AttuneMCPServer._maybe_keyboard_hint(
            SimpleNamespace(form_id="abc123")
        )

    assert result == "Press K"
    assert log_submission.call_count == 2
    assert log_submission.call_args_list[0].kwargs == {"form_id": "abc123"}
    assert log_submission.call_args_list[1] == unittest.mock.call()


def test_keyboard_hint_passes_empty_form_id_without_form():
    """The zero-arg call path (older in-tree callers, tests) still works:
    no form object degrades to an empty join key, never an AttributeError."""
    with (
        patch("attune.telemetry.form_events.log_submission") as log_submission,
        patch("attune.telemetry.form_events.maybe_keyboard_hint", return_value=None),
        patch("attune.elicitation.keyboard_mode_enabled", return_value=False),
    ):
        result = server_module.AttuneMCPServer._maybe_keyboard_hint()

    assert result is None
    log_submission.assert_called_once_with(form_id="")


def test_elicitation_session_is_empty_outside_request():
    assert server_module.AttuneMCPServer._elicitation_session() == (None, None)


def test_elicitation_session_returns_live_request_context():
    session = object()
    context = SimpleNamespace(session=session, request_id="request-1")
    with patch.object(
        type(server_module._mcp_server),
        "request_context",
        new_callable=PropertyMock,
        return_value=context,
    ):
        result = server_module.AttuneMCPServer._elicitation_session()

    assert result == (session, "request-1")


@pytest.mark.asyncio
async def test_ask_rejects_malformed_form_before_session_lookup(tmp_path):
    result = await _make_server(tmp_path)._handle_elicitation_ask({"form": {"title": "x"}})

    assert result == {
        "success": False,
        "problems": ["form must have a non-empty 'fields' list"],
    }


@pytest.mark.asyncio
async def test_ask_without_request_context_is_unsupported(tmp_path):
    result = await _make_server(tmp_path)._handle_elicitation_ask({"form": FORM})

    assert result == {
        "success": False,
        "action": "unsupported",
        "error": "No MCP elicitation session available (client cannot elicit).",
    }


@pytest.mark.asyncio
async def test_ask_converts_session_exception_to_error_envelope(tmp_path):
    session = SimpleNamespace(elicit_form=AsyncMock(side_effect=RuntimeError("closed")))
    with patch.object(
        server_module.AttuneMCPServer,
        "_elicitation_session",
        return_value=(session, "request-1"),
    ):
        result = await _make_server(tmp_path)._handle_elicitation_ask({"form": FORM})

    assert result == {
        "success": False,
        "action": "error",
        "error": "Elicitation failed: RuntimeError",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "expected_action"),
    [("decline", "decline"), ("cancel", "cancel"), (None, "cancel")],
)
async def test_ask_returns_non_accept_action(tmp_path, action, expected_action):
    session = SimpleNamespace(
        elicit_form=AsyncMock(return_value=SimpleNamespace(action=action, content=None))
    )
    with patch.object(
        server_module.AttuneMCPServer,
        "_elicitation_session",
        return_value=(session, "request-1"),
    ):
        result = await _make_server(tmp_path)._handle_elicitation_ask({"form": FORM})

    assert result == {"success": False, "action": expected_action, "responses": {}}


@pytest.mark.asyncio
async def test_ask_accept_reports_content_validation_problems(tmp_path):
    session = SimpleNamespace(
        elicit_form=AsyncMock(
            return_value=SimpleNamespace(action="accept", content={"target": "nope"})
        )
    )
    with patch.object(
        server_module.AttuneMCPServer,
        "_elicitation_session",
        return_value=(session, "request-1"),
    ):
        result = await _make_server(tmp_path)._handle_elicitation_ask({"form": FORM})

    assert result == {
        "success": False,
        "action": "accept",
        "problems": [
            "'target' value 'nope' not in options",
            "'depth' is required",
        ],
    }


@pytest.mark.asyncio
async def test_ask_accept_returns_validated_response(tmp_path):
    session = SimpleNamespace(
        elicit_form=AsyncMock(
            return_value=SimpleNamespace(
                action="accept",
                content={"target": "src", "depth": "quick"},
            )
        )
    )
    with patch.object(
        server_module.AttuneMCPServer,
        "_elicitation_session",
        return_value=(session, "request-1"),
    ):
        result = await _make_server(tmp_path)._handle_elicitation_ask(
            {"form": FORM, "message": "Pick scope"}
        )

    session.elicit_form.assert_awaited_once()
    call = session.elicit_form.await_args
    sent = call.args + tuple(call.kwargs.values())
    assert sent[0] == "Pick scope"
    assert sent[-1] == "request-1"
    assert result["success"] is True
    assert result["action"] == "accept"
    assert result["responses"] == {"target": "src", "depth": "quick"}
    # forms 0.7.0 appends an 8-hex uniqueness suffix to the response id.
    assert re.fullmatch(r"resp-\d{8}-\d{6}-[0-9a-f]{8}", result["response_id"])
