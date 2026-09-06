"""Closed public response schema for the unified form route."""

from __future__ import annotations

from typing import Any

CONTEXT_REASONS = (
    "empty_form_id",
    "missing_receipt",
    "invalid_receipt",
    "foreign_receipt",
    "session_ended",
    "superseded_receipt",
    "terminal",
    "record_shape_mismatch",
    "server_instance_mismatch",
    "session_mismatch",
    "chain_mismatch",
    "subject_mismatch",
    "schema_mismatch",
    "workspace_mismatch",
    "adapter_id_mismatch",
    "adapter_version_mismatch",
    "revision_mismatch",
    "event_sequence_mismatch",
    "contract_hash_mismatch",
    "action_nonce_mismatch",
    "future_timestamp",
    "expired",
    "warm",
)


def route_output_schema() -> dict[str, Any]:
    """Describe native completion/error arms without exposing internal authority."""
    null = {"type": "null"}
    route = {"type": "string", "minLength": 1}
    summary = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "context_reason": {"enum": list(CONTEXT_REASONS)},
            "selection_elapsed_ms": {"type": "number", "minimum": 0},
            "renderer_attempt_count": {"type": "integer", "enum": [0, 1]},
            "presentation_attempt_count": {"type": "integer", "minimum": 0},
        },
        "required": [
            "context_reason",
            "selection_elapsed_ms",
            "renderer_attempt_count",
            "presentation_attempt_count",
        ],
    }
    completion = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "success": {"type": "boolean"},
            "action": {"enum": ["accept", "abort", "timeout"]},
            "receipt_id": null,
            "provenance_status": {"const": "server_observed_completion"},
            "responses": {"type": "object"},
            "response_id": {"type": "string"},
            "reason": {"const": "validation_exhausted"},
        },
        "required": ["success", "action"],
    }
    common = {
        "selected_route": route,
        "payload_kind": null,
        "payload": null,
        "receipt_id": null,
        "submission_id": null,
        "completion": null,
        "decision_summary": summary,
    }
    arms = []
    for properties in (
        {
            **common,
            "success": {"const": True},
            "payload_kind": {"const": "completion"},
            "completion": completion,
        },
        {
            **common,
            "success": {"const": False},
            "error": {"const": "no_supported_surface"},
            "selected_route": null,
        },
        {
            **common,
            "success": {"const": False},
            "error": {
                "enum": [
                    "render_failed",
                    "session_ended",
                    "challenge_invalidated",
                    "challenge_consumed",
                ]
            },
        },
    ):
        unsupported = properties.get("error", {}).get("const") == "no_supported_surface"
        properties["decision_summary"] = {
            **summary,
            "properties": {
                **summary["properties"],
                "renderer_attempt_count": {"const": 0 if unsupported else 1, "type": "integer"},
                "presentation_attempt_count": (
                    {"const": 0, "type": "integer"}
                    if unsupported
                    else {
                        "type": "integer",
                        "minimum": 1 if properties["success"].get("const") else 0,
                    }
                ),
            },
        }
        arms.append(
            {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
                "required": list(properties),
            }
        )
    return {"type": "object", "oneOf": arms}
