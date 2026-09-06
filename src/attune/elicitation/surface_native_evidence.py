"""Executable local MCP receipts; protocol/validation evidence, never host paint."""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from dataclasses import asdict
from importlib.metadata import version
from typing import Any

import anyio
from mcp import ClientSession
from mcp.server import Server
from mcp.types import ElicitResult, TextContent, Tool

from attune.elicitation import form_from_dict
from attune.elicitation.surface_policy import SurfaceBinding, SurfaceContextStore, SurfaceDecision
from attune.elicitation.surface_registry import (
    SurfaceRegistryError,
    canonical_digest,
    required_obligations,
)
from attune.elicitation.surface_runtime import NATIVE_ROUTE, _present_native

SUBJECT_ID = "surface-runtime-route-form"
TRANSPORT_ID = "surface-native-elicitation"
FORM = {
    "title": "Plan this task",
    "form_id": "native-planning-receipt",
    "fields": [
        {
            "id": "decision",
            "text": "Scope",
            "type": "single_select",
            "options": ["Focused", "Broad"],
        },
        {"id": "minutes", "text": "Time budget", "type": "number", "minimum": 1, "maximum": 120},
        {"id": "outcome", "text": "Desired outcome", "type": "text_input", "required": True},
    ],
}
ANSWERS = {"decision": "Focused", "minutes": 30, "outcome": "A working form"}


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise SurfaceRegistryError(f"native evidence: {message}")


async def _exchange(case: str) -> dict[str, Any]:
    """Exchange messages over fixture-owned paired SDK streams; no network/model."""
    form = form_from_dict(FORM)
    store = SurfaceContextStore(b"native-receipt-fixture-key-32-bytes")
    binding = SurfaceBinding(
        store.server_instance_id,
        "fixture-session",
        "fixture-chain",
        "interactive_form",
        form.form_id,
        form.form_id,
        canonical_digest(asdict(form)),
    )
    decision = SurfaceDecision(NATIVE_ROUTE, "missing_receipt", 0.0, (), "fixture", "fixture")
    server = Server("native-receipt-fixture")
    transcript: list[dict[str, Any]] = []
    finished = asyncio.Event()

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="fixture-present",
                inputSchema={"type": "object", "additionalProperties": False},
            )
        ]

    @server.call_tool()
    async def present(name, arguments):
        result = await _present_native(
            store,
            form,
            server.request_context.session,
            server.request_context.request_id,
            binding,
            decision,
            response_deadline_seconds=0.1 if case == "timeout" else 5,
        )
        finished.set()
        return [TextContent(type="text", text=json.dumps(result))]

    async def answer(ctx, request):
        transcript.append({"message": request.message, "schema": request.requestedSchema})
        if case == "timeout":
            await finished.wait()
            return ElicitResult(action="cancel")
        if case == "abort":
            return ElicitResult(action="cancel")
        if case == "feedback" and len(transcript) == 1:
            return ElicitResult(action="accept", content={"decision": "Wrong", "minutes": 0})
        return ElicitResult(action="accept", content=ANSWERS)

    client_send, server_read = anyio.create_memory_object_stream(10)
    server_send, client_read = anyio.create_memory_object_stream(10)
    async with client_send, server_read, server_send, client_read:
        task = asyncio.create_task(
            server.run(server_read, server_send, server.create_initialization_options())
        )
        try:
            async with ClientSession(
                client_read, client_send, elicitation_callback=answer
            ) as client:
                await client.initialize()
                raw = await client.call_tool("fixture-present", {})
                result = json.loads(raw.content[0].text)
                finished.set()
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    _check(bool(transcript), f"{case}: no elicitation crossed the stream")
    first_schema = transcript[0]["schema"]
    _check(set(first_schema["properties"]) == set(ANSWERS), "field identity changed")
    _check(set(first_schema["required"]) == set(ANSWERS), "required fields changed")
    properties = first_schema["properties"]
    _check(properties["decision"]["enum"] == ["Focused", "Broad"], "enum changed")
    _check(
        properties["minutes"]["minimum"] == 1 and properties["minutes"]["maximum"] == 120,
        "range changed",
    )
    _check(properties["outcome"]["type"] == "string", "text type changed")
    _check(result["decision_summary"]["renderer_attempt_count"] == 1, "projection count changed")
    _check(not store._active, f"{case}: terminal result left an active interaction")
    if case == "timeout":
        _check(
            result.get("error") == "render_failed" and not store._records, "timeout created receipt"
        )
        return {
            "transcript": transcript,
            "error": result["error"],
            "cause": "server_deadline",
            "records": 0,
        }
    completion = result["completion"]
    _check(completion["provenance_status"] == "server_observed_completion", "provenance lost")
    if case == "abort":
        _check(completion["action"] == "abort", "cancel did not abort")
    else:
        _check(
            completion["action"] == "accept" and completion["responses"] == ANSWERS,
            "validated answers changed",
        )
    if case == "feedback":
        _check(
            len(transcript) == 2 and transcript[1]["schema"] == first_schema,
            "retry changed projection",
        )
        _check(
            all(field in transcript[1]["message"] for field in ANSWERS),
            "validation feedback missing",
        )
    return {
        "transcript": transcript,
        "action": completion["action"],
        "responses": completion.get("responses"),
        "provenance_status": completion["provenance_status"],
        "renderer_attempt_count": result["decision_summary"]["renderer_attempt_count"],
        "presentation_attempt_count": result["decision_summary"]["presentation_attempt_count"],
    }


def _implementation_digest() -> str:
    from attune_forms import renderer_registry as rr

    from attune.elicitation import surface_policy, surface_registry, surface_runtime

    form_record = next(record for record in rr.RENDERER_REGISTRY if record.family == "form")
    return canonical_digest(
        {
            "local": {
                module.__name__: inspect.getsource(module)
                for module in (surface_policy, surface_registry, surface_runtime)
            },
            "headless": rr.implementation_digest(form_record.target("headless")),
            "collector": rr.implementation_digest(
                rr.RendererTarget(
                    "collector", "headless", "attune_forms.bridge", "collect_form_response"
                )
            ),
            "mcp_version": version("mcp"),
        }
    )


async def replay_native_evidence(registry: dict[str, Any]) -> tuple[list[dict], dict[str, dict]]:
    """Execute and digest five exact obligations; never construct a routing report."""
    observations = {
        case: await _exchange(case) for case in ("accept", "abort", "timeout", "feedback")
    }
    subjects = {s["id"]: s for s in registry["subjects"]}
    owner = subjects[SUBJECT_ID]
    _check(
        subjects[TRANSPORT_ID].get("lifecycle_contract")
        == {
            "timeout": {
                "trigger": "server_response_deadline",
                "public_disposition": "render_failed",
                "creates_active_receipt": False,
                "preserves_predecessor": True,
            }
        },
        "timeout contract changed",
    )
    _check(
        owner["route_projection_targets"][NATIVE_ROUTE] == "headless",
        "native target binding changed",
    )
    keys = {
        f"route:{SUBJECT_ID}:{NATIVE_ROUTE}:production_projection": "accept",
        f"lifecycle:subject:{SUBJECT_ID}:accept": "accept",
        f"lifecycle:subject:{TRANSPORT_ID}:abort": "abort",
        f"lifecycle:subject:{TRANSPORT_ID}:timeout": "timeout",
        f"lifecycle:subject:{TRANSPORT_ID}:validation_feedback_delivery": "feedback",
    }
    required = required_obligations(registry)
    common = {
        "evidence_mode": "local_mcp_roundtrip",
        "fixture": "attune.elicitation.surface_native_evidence.replay_native_evidence",
        "implementation_digest": _implementation_digest(),
        "fixture_digest": canonical_digest(
            {"form": FORM, "answers": ANSWERS, "runner": inspect.getsource(sys.modules[__name__])}
        ),
        "record_digest": canonical_digest({"form": owner, "transport": subjects[TRANSPORT_ID]}),
        "normalization_digest": canonical_digest(
            {
                "omitted": [
                    "opaque receipt/submission/server IDs",
                    "wall-clock timestamps",
                    "selection elapsed time",
                ],
                "preserved": [
                    "schema",
                    "messages",
                    "action",
                    "responses",
                    "provenance",
                    "attempt counts",
                ],
            }
        ),
    }
    declarations, evidence = [], {}
    for key, case in keys.items():
        rid = key.replace(":", ".")
        observation = {**common, "result_digest": canonical_digest(observations[case])}
        declarations.append({"id": rid, "key": key, **required[key], **observation})
        evidence[rid] = observation
    return declarations, evidence
