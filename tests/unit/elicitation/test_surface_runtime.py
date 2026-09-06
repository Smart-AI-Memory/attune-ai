"""Native runtime behavior; fixture transports are not Codex paint evidence."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from attune.elicitation import form_from_dict
from attune.elicitation.surface_policy import SurfaceContextStore
from attune.elicitation.surface_registry import (
    InventoryReport,
    canonical_digest,
    required_obligations,
)
from attune.elicitation.surface_runtime import NATIVE_ROUTE, SurfaceFormRuntime


@pytest.fixture
def runtime():
    targets = [{"id": s.lower(), "surface": s} for s in ("RICH", "PORTABLE", "HEADLESS")]
    registry = {
        "host_profiles": [],
        "renderers": [{"id": "forms", "targets": targets}],
        "subjects": [
            {
                "id": "form",
                "subject_kind": "interactive_form",
                "targets": targets,
                "cold_routes": [NATIVE_ROUTE, "PORTABLE", "HEADLESS"],
                "warm_routes": ["RICH", NATIVE_ROUTE, "PORTABLE", "HEADLESS"],
                "route_transport_refs": {
                    r: {"kind": "subject", "id": "transport"}
                    for r in ("RICH", NATIVE_ROUTE, "PORTABLE", "HEADLESS")
                },
            },
            {
                "id": "transport",
                "subject_kind": "interaction_transport",
                "transport_id": NATIVE_ROUTE.removeprefix("mcp-native:"),
                "form_subject_ids": ["form"],
            },
        ],
    }
    keys = frozenset(required_obligations(registry))
    # Synthetic report for runtime behavior, never a production activation receipt.
    report = InventoryReport(keys, keys, frozenset(), frozenset(), canonical_digest(registry))
    return SurfaceFormRuntime(SurfaceContextStore(b"x" * 32), registry, report, subject_id="form")


@pytest.fixture
def form():
    return form_from_dict(
        {
            "title": "Plan this task",
            "fields": [
                {
                    "id": "decision",
                    "text": "Choose scope",
                    "type": "single_select",
                    "options": ["Focused", "Broad"],
                },
                {
                    "id": "minutes",
                    "text": "Time budget",
                    "type": "number",
                    "minimum": 1,
                    "maximum": 120,
                },
                {
                    "id": "outcome",
                    "text": "Desired outcome",
                    "type": "text_input",
                    "required": True,
                },
            ],
        }
    )


def session(*results):
    return SimpleNamespace(
        client_params=SimpleNamespace(
            capabilities=SimpleNamespace(elicitation=SimpleNamespace(form=object()))
        ),
        elicit_form=AsyncMock(side_effect=results),
    )


def accepted():
    return SimpleNamespace(
        action="accept", content={"decision": "Focused", "minutes": 30, "outcome": "Working form"}
    )


async def test_native_form_reject_reject_accept_renders_once(runtime, form, monkeypatch):
    import attune.elicitation.surface_runtime as module

    original = module.form_to_elicitation_schema
    calls = []

    def projection(value):
        calls.append(value)
        return original(value)

    monkeypatch.setattr(module, "form_to_elicitation_schema", projection)
    transport = session(
        SimpleNamespace(action="accept", content={}),
        SimpleNamespace(action="accept", content={}),
        accepted(),
    )
    result = await runtime.route_form(form, transport, "request")
    assert result["success"] and result["completion"]["responses"]["minutes"] == 30
    assert result["decision_summary"]["renderer_attempt_count"] == len(calls) == 1
    assert (
        result["decision_summary"]["presentation_attempt_count"]
        == transport.elicit_form.await_count
        == 3
    )
    assert "submission_id" not in result["completion"]
    schemas = [call.args[1] for call in transport.elicit_form.call_args_list]
    assert schemas[0] == schemas[1] == schemas[2]
    assert "outcome" in transport.elicit_form.call_args_list[1].args[0]


async def test_missing_capability_or_evidence_never_renders(runtime, form, monkeypatch):
    import attune.elicitation.surface_runtime as module

    monkeypatch.setattr(
        module, "form_to_elicitation_schema", lambda _: pytest.fail("inadmissible renderer")
    )
    transport = session(accepted())
    transport.client_params.capabilities.elicitation = None
    assert (await runtime.route_form(form, transport, "r"))["error"] == "no_supported_surface"
    transport.client_params.capabilities.elicitation = SimpleNamespace(form=object())
    from dataclasses import replace

    runtime._report = replace(runtime._report, verified_keys=frozenset())
    assert (await runtime.route_form(form, transport, "r"))["error"] == "no_supported_surface"
    transport.elicit_form.assert_not_awaited()


@pytest.mark.parametrize(
    "response",
    [
        RuntimeError("transport down"),
        None,
        SimpleNamespace(action="bogus"),
        SimpleNamespace(action="accept", content=None),
    ],
)
async def test_transport_failure_creates_no_receipt(runtime, form, response):
    result = await runtime.route_form(form, session(response), "r")
    assert result["error"] == "render_failed"
    assert runtime.store._records == {}


async def test_session_close_while_waiting_prevents_commit(runtime, form):
    transport = session()

    async def closing(*_):
        runtime.close_session(transport)
        return accepted()

    transport.elicit_form.side_effect = closing
    result = await runtime.route_form(form, transport, "r")
    assert result["error"] == "session_ended"
    assert runtime.store._records == {}


@pytest.mark.parametrize("failure", [None, OSError("fixture transport failure")])
async def test_stdio_teardown_invalidates_all_owned_sessions(runtime, form, monkeypatch, failure):
    from contextlib import asynccontextmanager

    import attune.mcp.server as server

    transports = [session(accepted()), session(accepted())]
    ids = [runtime.session_id(transport) for transport in transports]

    @asynccontextmanager
    async def streams():
        yield None, None

    async def run(*args):
        if failure is not None:
            raise failure

    monkeypatch.setattr(server, "_app", SimpleNamespace(_surface_runtime=runtime))
    monkeypatch.setattr(server, "stdio_server", streams)
    monkeypatch.setattr(server._mcp_server, "run", run)
    if failure:
        with pytest.raises(OSError, match="fixture transport failure"):
            await server._run_stdio()
    else:
        await server._run_stdio()
    assert set(ids) <= runtime.store._ended
    for transport in transports:
        result = await runtime.route_form(form, transport, "late")
        assert result["error"] == "session_ended"
        transport.elicit_form.assert_not_awaited()


async def test_native_validation_exhaustion_aborts(runtime, form):
    transport = session(*(SimpleNamespace(action="accept", content={}) for _ in range(3)))
    result = await runtime.route_form(form, transport, "r")
    assert result["completion"]["action"] == "abort"
    assert result["completion"]["reason"] == "validation_exhausted"
    assert not runtime.store._active


async def test_mcp_handler_routes_through_server_owned_runtime(
    runtime, form, tmp_path, monkeypatch
):
    from unittest.mock import patch

    from attune.mcp.server import AttuneMCPServer

    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        app = AttuneMCPServer(workspace_root=str(tmp_path), surface_runtime=runtime)
    transport = session(SimpleNamespace(action="accept", content={"outcome": "Working form"}))
    monkeypatch.setattr(app, "_elicitation_session", lambda: (transport, "r"))
    raw = {
        "title": "Planning",
        "fields": [{"id": "outcome", "text": "Outcome", "type": "text_input"}],
    }
    result = await app._handle_elicitation_route_form({"form": raw})
    assert result["success"]
    assert not (await app._handle_elicitation_route_form({"form": raw, "capabilities": {}}))[
        "success"
    ]


@pytest.mark.parametrize("production", [False, True])
async def test_native_route_crosses_real_mcp_stdio(runtime, tmp_path, production):
    """Real SDK transport with fixture answers, not a host-paint assertion."""
    import asyncio
    import json
    import os
    import sys
    from pathlib import Path

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import get_default_environment, stdio_client
    from mcp.types import ElicitResult

    root = Path(__file__).resolve().parents[3]
    if production and os.name != "posix":
        pytest.skip("Windows private key adapter is not implemented")
    registry_path = tmp_path / "fixture-registry.json"
    registry_path.write_text(json.dumps(runtime._registry), encoding="utf-8")
    script = tmp_path / "fixture_server.py"
    script.write_text(
        """import json, sys
from pathlib import Path
from tests._inference_guard import install
install()
from attune.elicitation.surface_policy import SurfaceContextStore
from attune.elicitation.surface_registry import InventoryReport, canonical_digest, required_obligations
from attune.elicitation.surface_runtime import SurfaceFormRuntime
import attune.mcp.server as server
import attune.mcp.version_check as version_check
version_check._cached_status = {}
registry = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
keys = frozenset(required_obligations(registry))
report = InventoryReport(keys, keys, frozenset(), frozenset(), canonical_digest(registry))
runtime = SurfaceFormRuntime(SurfaceContextStore(b"fixture-installation-key-32-bytes"), registry, report, subject_id="form")
server._app = server.AttuneMCPServer(surface_runtime=runtime)
server.main()
""",
        encoding="utf-8",
    )
    if production:
        script.write_text(
            "from tests._inference_guard import install\ninstall()\n"
            "import attune.mcp.version_check as version_check\nversion_check._cached_status = {}\n"
            "from attune.mcp.server import main\nmain()\n",
            encoding="utf-8",
        )
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(script), str(registry_path)],
        cwd=str(tmp_path),
        env={
            **get_default_environment(),
            "PYTHONPATH": os.pathsep.join((str(root / "src"), str(root))),
            "ATTUNE_HOME": str(tmp_path),
            "ATTUNE_FORMS_HOME": str(tmp_path),
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "CLAUDE_CONFIG_DIR": str(tmp_path / "claude"),
        },
    )
    observations = []

    async def answer(ctx, request):
        observations.append(request.requestedSchema)
        return ElicitResult(action="accept", content={"outcome": "A working form"})

    async def exchange():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write, elicitation_callback=answer) as client:
                await client.initialize()
                result = await client.call_tool(
                    "elicitation_route_form",
                    {
                        "form": {
                            "title": "Planning",
                            "fields": [
                                {
                                    "id": "outcome",
                                    "text": "Outcome",
                                    "type": "text_input",
                                    "required": True,
                                }
                            ],
                        }
                    },
                )
                payload = json.loads(
                    next(item.text for item in result.content if item.type == "text")
                )
                assert payload["success"]
                assert payload["completion"]["responses"] == {"outcome": "A working form"}
                assert payload["completion"]["provenance_status"] == "server_observed_completion"
                assert len(observations) == 1 and "outcome" in observations[0]["properties"]

    await asyncio.wait_for(exchange(), timeout=30)


@pytest.mark.parametrize("content", [[], {"outcome": object()}, {"outcome": float("nan")}])
async def test_malformed_completion_never_changes_receipt_state(runtime, form, content):
    transport = session(SimpleNamespace(action="accept", content=content))
    assert (await runtime.route_form(form, transport, "r"))["error"] == "render_failed"
    assert not runtime.store._active and not runtime.store._records


async def test_unhashable_action_and_closed_session(runtime, form):
    transport = session(SimpleNamespace(action=[]))
    assert (await runtime.route_form(form, transport, "r"))["error"] == "render_failed"
    runtime.close_session(transport)
    assert (await runtime.route_form(form, transport, "r"))["error"] == "session_ended"


async def test_cancellation_and_deadline_leave_no_receipt(runtime, form):
    import asyncio

    transport = session()

    async def wait(*_):
        await asyncio.sleep(1)

    transport.elicit_form.side_effect = wait
    runtime._deadline = 0.001
    assert (await runtime.route_form(form, transport, "r"))["error"] == "render_failed"
    assert not runtime.store._records
    transport.elicit_form.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await runtime.route_form(form, transport, "r")
    assert not runtime.store._records


async def test_unconfigured_public_route_is_discoverable_but_fails_closed(tmp_path):
    from unittest.mock import patch

    from attune.mcp.server import AttuneMCPServer

    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        app = AttuneMCPServer(workspace_root=str(tmp_path))
    assert "elicitation_route_form" in app.tools
    result = await app.call_tool(
        "elicitation_route_form",
        {
            "form": {
                "title": "Planning",
                "fields": [{"id": "outcome", "text": "Outcome", "type": "text_input"}],
            }
        },
    )
    assert result["error"] == "no_supported_surface"
    assert result["selected_route"] is None
    assert result["decision_summary"]["renderer_attempt_count"] == 0
    invalid = await app._handle_elicitation_route_form({"form": {"fields": [{"type": "bogus"}]}})
    assert not invalid["success"] and invalid["problems"]


async def test_native_terminal_transition_race_fails_closed(runtime, form, monkeypatch):
    runtime._max_attempts = 1
    original = runtime.store.transition

    def closing(receipt, binding, *, terminal):
        if terminal:
            runtime.store.close_session(binding.session_id)
        return original(receipt, binding, terminal=terminal)

    monkeypatch.setattr(runtime.store, "transition", closing)
    result = await runtime.route_form(
        form, session(SimpleNamespace(action="accept", content={})), "r"
    )
    assert result["error"] == "session_ended"
    assert result["completion"] is None


async def test_closed_public_result_contract_rejects_authority_and_token_leaks(runtime, form):
    import copy

    import jsonschema

    from attune.elicitation.surface_contract import route_output_schema

    result = await runtime.route_form(form, session(accepted()), "r")
    schema = route_output_schema()
    jsonschema.validate(result, schema)
    for field, value in (
        ("submission_id", "forged"),
        ("receipt_id", "winner"),
        ("selected_route", None),
    ):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**result, field: value}, schema)
    altered = copy.deepcopy(result)
    altered["decision_summary"]["capabilities"] = {"RICH": True}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(altered, schema)
    altered["decision_summary"].pop("capabilities")
    altered["decision_summary"]["renderer_attempt_count"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(altered, schema)


async def test_selected_native_arm_refuses_different_route(runtime, form):
    from dataclasses import asdict

    from attune.elicitation.surface_policy import SurfaceBinding, SurfaceDecision
    from attune.elicitation.surface_runtime import _present_native

    binding = SurfaceBinding(
        runtime.store.server_instance_id,
        "s",
        "c",
        "interactive_form",
        form.form_id,
        form.form_id,
        canonical_digest(asdict(form)),
    )
    decision = SurfaceDecision("RICH", "missing_receipt", 0, (), "fixture", "fixture")
    transport = session(accepted())
    with pytest.raises(ValueError, match="different selected route"):
        await _present_native(runtime.store, form, transport, "r", binding, decision)
    transport.elicit_form.assert_not_awaited()
    runtime.close()
    runtime.close()
    assert not runtime._sessions


async def test_session_close_between_feedback_and_retry_is_public_disposition(
    runtime, form, monkeypatch
):
    original = runtime.store.complete_challenge
    transport = session(SimpleNamespace(action="accept", content={}))

    def completing(challenge, raw):
        result = original(challenge, raw)
        runtime.close_session(transport)
        return result

    monkeypatch.setattr(runtime.store, "complete_challenge", completing)
    result = await runtime.route_form(form, transport, "r")
    assert result["error"] == "session_ended"
    assert result["completion"] is None
    assert transport.elicit_form.await_count == 1
