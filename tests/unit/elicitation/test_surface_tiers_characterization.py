"""Characterize the current standalone-form surface tiers.

This suite deliberately pins the existing seams rather than introducing a
form-level renderer registry: rich uses the widget DOM postback, portable uses
the Markdown reply parser, and headless uses the native MCP elicitation
handler. All three answer mappings converge through ``collect_form_response``.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from attune_forms import (
    WIDGET_RESPONSE_MARKER,
    collect_form_response,
    form_from_dict,
    form_to_markdown,
    form_to_widget_html,
    markdown_to_answers,
    needs_widget,
    select_form_surface,
)

from attune.mcp.server import AttuneMCPServer
from scripts.render_demo_forms import AUDIT
from tests.unit.elicitation.test_widget_roundtrip import _fill, _submit, _WidgetDOM

_EXPECTED: dict[str, Any] = {
    "depth": "Changed files only",
    "focus": ["Injection / eval-exec", "Path traversal"],
    "tier": "Premium (Fable 5)",
    "max_findings": 12.5,
    "path": "src/attune",
}
_PORTABLE_ANSWERS = """\
depth: Changed files only
focus: Injection / eval-exec, Path traversal
tier: Premium (Fable 5)
max_findings: 12.5
path: src/attune
"""


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@pytest.mark.asyncio
async def test_demo_form_has_identical_validated_output_on_all_three_tiers() -> None:
    form = form_from_dict(AUDIT)

    assert select_form_surface(form) == "widget"
    assert needs_widget(form) is True

    rich_html = form_to_widget_html(form, instance_id="surface-parity")
    rich_dom = _WidgetDOM()
    rich_dom.feed(rich_html)
    assert {field["fid"] for field in rich_dom.fields} == set(_EXPECTED)
    _fill(rich_dom, _EXPECTED)
    rich_payload = _submit(rich_dom)
    assert rich_payload[WIDGET_RESPONSE_MARKER] is True
    rich = collect_form_response(form, rich_payload["answers"]).responses

    portable_markdown = form_to_markdown(form)
    portable_reply = f"{portable_markdown}\n{_PORTABLE_ANSWERS}"
    portable_answers, problems = markdown_to_answers(form, portable_reply)
    assert problems == []
    portable = collect_form_response(form, portable_answers).responses

    session = SimpleNamespace(
        elicit_form=AsyncMock(
            return_value=SimpleNamespace(
                action="accept",
                content=json.loads(json.dumps(_EXPECTED)),
            )
        )
    )
    server = object.__new__(AttuneMCPServer)
    server._elicitation_session = lambda: (session, "surface-parity-request")
    headless_result = await server._handle_elicitation_ask(
        {"form": AUDIT, "message": "Complete the audit form."}
    )

    session.elicit_form.assert_awaited_once()
    message, headless_schema, request_id = session.elicit_form.await_args.args
    assert message == "Complete the audit form."
    assert request_id == "surface-parity-request"
    assert headless_schema["type"] == "object"
    assert set(headless_schema["properties"]) == set(_EXPECTED)
    assert headless_schema["required"] == ["depth", "focus", "tier", "max_findings"]
    assert headless_result["success"] is True
    assert headless_result["action"] == "accept"
    headless = headless_result["responses"]

    assert _canonical(rich) == _canonical(portable) == _canonical(headless)
    assert _canonical(headless) == _canonical(_EXPECTED)
