"""Tests for the elicitation_render_widget MCP handler (S1 surface).

Thin wiring of ``form_to_widget_html``: a valid form returns the HTML +
metadata; a malformed form returns problems instead of raising.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from attune.mcp.server import AttuneMCPServer

_FORM = {
    "title": "Scope",
    "fields": [
        {"id": "goal", "text": "Goal?", "type": "single_select", "options": ["a", "b"]},
        {"id": "note", "text": "Note", "type": "textarea", "required": False},
        {"id": "n", "text": "How many?", "type": "number", "minimum": 1, "maximum": 9},
        {"id": "when", "text": "When?", "type": "date", "required": False},
    ],
}


def _make_server() -> AttuneMCPServer:
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch("attune.mcp.version_check.check_for_updates", return_value=None):
            return AttuneMCPServer()


class TestRenderWidgetHandler:
    @pytest.mark.asyncio
    async def test_valid_form_returns_html_and_metadata(self):
        server = _make_server()
        out = await server._handle_elicitation_render_widget({"form": _FORM, "message": "fill it"})
        assert out["success"] is True
        assert out["title"] == "Scope"
        assert out["field_ids"] == ["goal", "note", "n", "when"]
        assert 'id="attune-elicit-form-' in out["html"]
        assert "fill it" in out["html"]
        # the v2.1 rich controls render (D10 enum-honesty fix)
        assert '<input type="number"' in out["html"]
        assert '<input type="date"' in out["html"]

    @pytest.mark.asyncio
    async def test_registered_in_dispatch_table(self):
        server = _make_server()
        assert "elicitation_render_widget" in server._build_dispatch_table()

    @pytest.mark.asyncio
    async def test_malformed_form_returns_problems(self):
        server = _make_server()
        out = await server._handle_elicitation_render_widget({"form": {"title": ""}})
        assert out["success"] is False
        assert out["problems"]


class TestFusedTemplatePath:
    """R5.2: ``template`` + ``slots`` is loaded, cast, validated and rendered
    server-side in ONE call — the form dict never transits the agent."""

    _ARGS = {"template": "session-contract", "slots": {"project": "attune-ai"}}

    @pytest.mark.asyncio
    async def test_template_casts_and_renders(self):
        out = await _make_server()._handle_elicitation_render_widget(self._ARGS)
        assert out["success"] is True
        assert out["title"] == "Session contract — attune-ai"
        assert out["field_ids"] == ["mode", "outcome", "done_when", "effort_cap"]
        assert "Session contract — attune-ai" in out["html"]
        assert "{project}" not in out["html"]

    @pytest.mark.asyncio
    async def test_slot_problems_are_listed_not_raised(self):
        out = await _make_server()._handle_elicitation_render_widget(
            {"template": "session-contract", "slots": {}}
        )
        assert out["success"] is False
        assert out["problems"] == ["missing value for slot 'project'"]

    @pytest.mark.asyncio
    async def test_unknown_template_lists_the_available_ones(self):
        out = await _make_server()._handle_elicitation_render_widget(
            {"template": "no-such-template", "slots": {}}
        )
        assert out["success"] is False
        assert any("session-contract" in p for p in out["problems"])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "args",
        [
            {},
            {"message": "only a message"},
            {"form": _FORM, "template": "session-contract"},
        ],
    )
    async def test_exactly_one_of_form_or_template(self, args):
        out = await _make_server()._handle_elicitation_render_widget(args)
        assert out["success"] is False
        assert out["problems"] == [
            "pass exactly one of 'form' (a declarative form dict) or "
            "'template' (a stored template name, with 'slots')"
        ]

    @pytest.mark.asyncio
    async def test_slots_without_template_is_a_problem(self):
        out = await _make_server()._handle_elicitation_render_widget(
            {"form": _FORM, "slots": {"project": "x"}}
        )
        assert out == {"success": False, "problems": ["'slots' requires 'template'"]}

    @pytest.mark.asyncio
    async def test_every_form_tool_shares_the_seam(self):
        # Same problem envelope from every form-taking handler: one seam,
        # so the fused path cannot drift per tool.
        server = _make_server()
        both = {"form": _FORM, "template": "session-contract", "answers": {}}
        outs = [
            await server._handle_elicitation_render_form(both),
            await server._handle_elicitation_render_widget(both),
            await server._handle_elicitation_collect_response(both),
            await server._handle_elicitation_ask(both),
        ]
        assert len({o["problems"][0] for o in outs}) == 1
        assert all(o["success"] is False for o in outs)

    @pytest.mark.asyncio
    async def test_collect_from_template_carries_template_id(self):
        from attune.elicitation import collect_form_response as real_collect

        answers = {
            "mode": "Executing a planned spec",
            "outcome": "R5.2 shipped",
            "done_when": "both PRs green",
        }
        with patch("attune.elicitation.collect_form_response", wraps=real_collect) as spy:
            out = await _make_server()._handle_elicitation_collect_response(
                {**self._ARGS, "answers": answers}
            )
        assert out["success"] is True
        assert out["responses"]["mode"] == "Executing a planned spec"
        assert spy.call_args.kwargs["template_id"] == "session-contract"

    @pytest.mark.asyncio
    async def test_render_form_batches_a_cast_template(self):
        out = await _make_server()._handle_elicitation_render_form(self._ARGS)
        assert out["success"] is True
        assert out["title"] == "Session contract — attune-ai"
        assert out["batches"]

    @pytest.mark.asyncio
    async def test_collect_from_template_echoes_template_id(self):
        answers = {"mode": "Executing a planned spec", "outcome": "x", "done_when": "y"}
        out = await _make_server()._handle_elicitation_collect_response(
            {**self._ARGS, "answers": answers}
        )
        assert out["template_id"] == "session-contract"
        # the form path is unchanged: no template_id key at all
        plain = await _make_server()._handle_elicitation_collect_response(
            {"form": _FORM, "answers": {"goal": "a", "n": 3}}
        )
        assert plain["success"] is True and "template_id" not in plain

    @pytest.mark.asyncio
    async def test_ask_from_template_carries_template_id(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock

        from attune.elicitation import collect_form_response as real_collect

        answers = {"mode": "Executing a planned spec", "outcome": "x", "done_when": "y"}
        session = SimpleNamespace(
            elicit_form=AsyncMock(return_value=SimpleNamespace(action="accept", content=answers))
        )
        server = _make_server()
        with (
            patch.object(server, "_elicitation_session", return_value=(session, "rid")),
            patch("attune.elicitation.collect_form_response", wraps=real_collect) as spy,
        ):
            out = await server._handle_elicitation_ask(self._ARGS)
        assert out["success"] is True and out["action"] == "accept"
        assert out["template_id"] == "session-contract"
        assert spy.call_args.kwargs["template_id"] == "session-contract"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "args",
        [
            {"form": "x"},
            {"form": []},
            {"form": 5},
            {"form": {"title": None, "fields": "x"}},
            {"form": {"title": "t", "fields": [5]}},
            {"template": 5},
            {"template": ["a"]},
            {"template": ""},
            {"template": "session-contract", "slots": []},
            {"template": "session-contract", "slots": {"project": None}},
        ],
    )
    async def test_malformed_inputs_are_problems_never_raises(self, args):
        # The seam's never-raises contract across the legal-but-wrong input
        # domain (lane finding, 2026-09-05 — probed, held; pinned here).
        out = await _make_server()._handle_elicitation_render_widget(args)
        assert out["success"] is False
        assert out["problems"] and all(isinstance(p, str) for p in out["problems"])
