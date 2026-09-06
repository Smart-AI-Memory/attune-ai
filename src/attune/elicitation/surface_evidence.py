"""Keyless, replayable receipts for the installed attune-forms projections.

These fixtures exercise serializers and common collectors. They never claim
host paint, stateful transport lifecycle, or attune-ai route selection.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import json
import re
import sys
from typing import Any

import jsonschema
from attune_forms import canonical_fixtures as cf
from attune_forms import collect_form_response, collect_workspace_action
from attune_forms import renderer_registry as rr

from attune.elicitation.surface_registry import (
    SurfaceRegistryError,
    canonical_digest,
    renderer_record_digest,
)


def installed_renderers() -> list[dict[str, Any]]:
    """Describe each installed target without confusing compatibility with routing."""
    rr.validate_registry()
    return [
        {
            "id": record.record_id,
            "family": record.family,
            "input_type": record.input_type,
            "fixture": record.fixture,
            "targets": [
                {
                    "id": target.target_id,
                    "surface": (
                        "host-native" if target.surface == "host_native" else target.surface.upper()
                    ),
                    **{
                        k: v
                        for k, v in dataclasses.asdict(target).items()
                        if k not in {"target_id", "surface"}
                    },
                }
                for target in record.targets
            ],
        }
        for record in rr.RENDERER_REGISTRY
    ]


def _project(record: rr.RendererRecord, target: rr.RendererTarget) -> Any:
    module, name = record.fixture.rsplit(".", 1)
    fixture = getattr(importlib.import_module(module), name)()
    kwargs: dict[str, Any] = {}
    if target.surface == "rich":
        kwargs["instance_id"] = cf.CANONICAL_INSTANCE_ID
    if record.family == "workspace":
        kwargs["binding"] = cf.canonical_binding()
    result = target.resolve()(fixture, **kwargs)
    if not result:
        raise SurfaceRegistryError(f"{target.target_id}: empty canonical projection")
    return cf.normalize(result) if isinstance(result, str) else result


def _form_collection(
    output: Any, target: rr.RendererTarget, record: rr.RendererRecord
) -> dict[str, Any]:
    module, name = record.fixture.rsplit(".", 1)
    form = getattr(importlib.import_module(module), name)()
    if target.status == "compatibility_only":
        # Derive IDs and values from the specialized output, never reconstruct
        # the expected questions from the input form as a shortcut.
        answers = {}
        if not isinstance(output, list):
            raise SurfaceRegistryError(f"{target.target_id}: invalid question batches")
        for batch in output:
            if not isinstance(batch, list):
                raise SurfaceRegistryError(f"{target.target_id}: invalid question batch")
            for question in batch:
                if not isinstance(question, dict) or not isinstance(
                    question.get("question_id"), str
                ):
                    raise SurfaceRegistryError(f"{target.target_id}: missing question_id")
                choices = question.get("options", [])
                if not isinstance(choices, list):
                    raise SurfaceRegistryError(f"{target.target_id}: invalid options")
                answers[question["question_id"]] = choices[0] if choices else "canonical text"
    else:
        answers = cf.canonical_form_answers()
    response = collect_form_response(form, answers, template_id=form.form_id)
    # The collectors allocate timestamp/response_id. They are telemetry, not
    # form/schema/action authority; only these two paths are omitted.
    observed = {"template_id": response.template_id, "responses": response.responses}
    for surface in ("portable", "headless"):
        twin = record.target(surface)
        projected = _project(record, twin)
        control_answers = _projected_answers(projected, surface, answers)
        control = collect_form_response(form, control_answers, template_id=form.form_id)
        if observed != {"template_id": control.template_id, "responses": control.responses}:
            raise SurfaceRegistryError(f"{target.target_id}: unequal validated FormResponse")
    return observed


def _projected_answers(output: Any, surface: str, answers: dict) -> dict:
    """Consume the emitted reply contract; never silently substitute input field IDs."""
    try:
        if surface == "portable":
            if not isinstance(output, str):
                raise SurfaceRegistryError("PORTABLE: reply contract must be text")
            blocks = re.findall(r"```json\s*(.*?)\s*```", output, re.DOTALL)
            if len(blocks) != 1:
                raise SurfaceRegistryError("PORTABLE: missing canonical reply contract")
            reply = json.loads(blocks[0])
            if not isinstance(reply, dict):
                raise SurfaceRegistryError("PORTABLE: reply contract must be an object")
            fields = reply.get("answers", {})
        else:
            if not isinstance(output, dict):
                raise SurfaceRegistryError("HEADLESS: reply contract must be an object")
            fields = output.get("properties", {})
            jsonschema.validate(answers, output)
    except (json.JSONDecodeError, jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise SurfaceRegistryError(f"{surface}: invalid projected reply contract") from exc
    if not isinstance(fields, dict):
        raise SurfaceRegistryError(f"{surface}: reply fields must be an object")
    if set(fields) != set(answers):
        raise SurfaceRegistryError(f"{surface}: projected reply field IDs differ")
    return {field: answers[field] for field in fields}


def _workspace_collection() -> dict[str, Any]:
    view, binding = cf.canonical_workspace_view(), cf.canonical_binding()
    payload = cf.canonical_workspace_response(view, "apply", binding, {"ruling": "apply"})
    response = collect_workspace_action(view, payload, binding)
    return {
        "view": response.view.value,
        "action": response.action,
        "confirmed": response.confirmed,
        "workspace_id": response.workspace_id,
        "revision": response.revision,
        "action_nonce": response.action_nonce,
        "contract_hash": response.contract_hash,
        "responses": response.responses_payload(),
    }


def replay_renderer_evidence() -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Execute all installed projections and bind each enhanced target plus twins."""
    rr.validate_registry()
    declarations = []
    evidence = {}
    descriptions = {record["id"]: record for record in installed_renderers()}
    for record in rr.RENDERER_REGISTRY:
        outputs = {target.target_id: _project(record, target) for target in record.targets}
        for target in record.targets:
            if target.surface not in {"rich", "host_native"}:
                continue
            suffix = (
                "surface:RICH" if target.surface == "rich" else f"host-native:{target.target_id}"
            )
            key = f"renderer:{record.record_id}:{suffix}"
            if target.status == "route_active":
                raise SurfaceRegistryError(
                    f"{key}: route_roundtrip requires installed adapter/profile evidence"
                )
            bound = [target, record.target("portable"), record.target("headless")]
            collection = (
                _form_collection(outputs[target.target_id], target, record)
                if record.family == "form"
                else _workspace_collection()
            )
            observation = {
                "evidence_mode": target.evidence_mode,
                "fixture": "attune.elicitation.surface_evidence.replay_renderer_evidence",
                "implementation_digest": canonical_digest(
                    {
                        "targets": {t.target_id: rr.implementation_digest(t) for t in bound},
                        "collector": rr.implementation_digest(
                            rr.RendererTarget(
                                "collector",
                                "headless",
                                (
                                    "attune_forms.bridge"
                                    if record.family == "form"
                                    else "attune_forms.workspace"
                                ),
                                (
                                    "collect_form_response"
                                    if record.family == "form"
                                    else "collect_workspace_action"
                                ),
                            )
                        ),
                    }
                ),
                "fixture_digest": canonical_digest(
                    {
                        "inputs": cf.fixture_digest(),
                        "runner": inspect.getsource(sys.modules[__name__]),
                    }
                ),
                "record_digest": renderer_record_digest(
                    descriptions[record.record_id], target.target_id
                ),
                "normalization_digest": canonical_digest(
                    {
                        "projection": [dataclasses.asdict(r) for r in cf.NORMALIZATION_RULES],
                        "collection": {
                            "timestamp": "collector wall-clock telemetry",
                            "response_id": "collector telemetry identifier",
                        },
                    }
                ),
                "result_digest": canonical_digest(
                    {
                        "projections": {t.target_id: outputs[t.target_id] for t in bound},
                        "validated": collection,
                    }
                ),
            }
            rid = key.replace(":", ".")
            declarations.append(
                {
                    "id": rid,
                    "key": key,
                    "kind": "parity",
                    "obligation_key": key,
                    "evidence_mode": target.evidence_mode,
                    "fixture": "attune.elicitation.surface_evidence.replay_renderer_evidence",
                    **observation,
                }
            )
            evidence[rid] = observation
    return declarations, evidence
