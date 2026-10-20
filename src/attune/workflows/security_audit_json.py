"""Validate and export the security audit's structured SDK result.

This contract belongs only to ``security-audit --json``. Human reports and
the generic workflow JSON emitter retain their existing behavior.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from .output_schemas import WORKFLOW_OUTPUT_SCHEMA

if TYPE_CHECKING:
    from attune.models.sdk_adapter import AgentRunResult

SECURITY_AUDIT_JSON_SCHEMA = deepcopy(WORKFLOW_OUTPUT_SCHEMA)
_SCHEMA = SECURITY_AUDIT_JSON_SCHEMA["schema"]
_SCHEMA["additionalProperties"] = False
_SCHEMA["properties"]["audit_complete"] = {"type": "boolean", "const": True}
_SCHEMA["required"] = ["summary", "findings", "suggestions", "audit_complete"]
_SCHEMA["properties"]["summary"]["additionalProperties"] = False
_SCHEMA["properties"]["summary"]["properties"]["text"]["minLength"] = 1
_SCHEMA["properties"]["summary"]["properties"]["score"].update(minimum=0, maximum=100)
_FINDING = _SCHEMA["properties"]["findings"]["additionalProperties"]["items"]
_FINDING["additionalProperties"] = False
_FINDING["required"] = ["file", "line", "severity", "description"]
_FINDING["properties"]["file"]["minLength"] = 1
_FINDING["properties"]["line"]["minimum"] = 1
_FINDING["properties"]["description"]["minLength"] = 1
_FINDING["properties"]["severity"]["enum"] = ["critical", "high", "medium", "low"]
_SUGGESTION = _SCHEMA["properties"]["suggestions"]["items"]
_SUGGESTION["additionalProperties"] = False
_SUGGESTION["properties"]["description"]["minLength"] = 1
_SUGGESTION["properties"]["priority"]["enum"] = ["high", "medium", "low"]

SECURITY_AUDIT_JSON_INSTRUCTION = (
    " Return the security audit's structured output. Set audit_complete to true "
    "only after the full audit and all subagent findings are complete. Include "
    "every finding, with its category, file, positive line number, severity "
    "(critical/high/medium/low), and description. An empty findings object is "
    "valid only for a completed audit with no findings. If the audit cannot "
    "finish, report the failure; do not emit a completed empty audit."
)


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _flatten_findings(categories: Any) -> list[dict[str, Any]]:
    """Validate category lists and retain each normalized finding in order."""
    if not isinstance(categories, dict):
        raise ValueError("SDK audit findings must be a category-to-list object")
    findings: list[dict[str, Any]] = []
    for category, items in categories.items():
        if not _nonempty_text(category) or not isinstance(items, list):
            raise ValueError("SDK audit finding category is malformed")
        for item in items:
            if (
                not isinstance(item, dict)
                or set(item) != {"file", "line", "severity", "description"}
                or not _nonempty_text(item["file"])
                or type(item["line"]) is not int
                or item["line"] < 1
                or not _nonempty_text(item["description"])
                or not isinstance(item["severity"], str)
                or item["severity"].lower() not in {"critical", "high", "medium", "low"}
            ):
                raise ValueError("SDK audit finding is incomplete or has an unsupported severity")
            findings.append(
                {
                    **item,
                    "severity": item["severity"].lower(),
                    "category": category,
                    "type": category,
                }
            )
    return findings


def _validate_suggestions(suggestions: Any) -> None:
    """Refuse malformed suggestions using the existing security contract."""
    if not isinstance(suggestions, list) or any(
        not isinstance(item, dict)
        or not set(item).issubset({"description", "priority"})
        or not _nonempty_text(item.get("description"))
        or (
            "priority" in item
            and (
                not isinstance(item["priority"], str)
                or item["priority"] not in {"high", "medium", "low"}
            )
        )
        for item in suggestions
    ):
        raise ValueError("SDK audit suggestions are malformed")


def security_audit_json(run: AgentRunResult) -> str:
    """Serialize a completed, supported SDK audit or raise ``ValueError``.

    A successful terminal subtype is necessary, and error/cutoff signals or
    missing structured output still refuse. The explicit completion marker
    is the agent's assertion, not proof of model quality or exhaustive review.
    This function never parses report text, repr strings, or nested envelopes.
    """
    if (
        run.subtype != "success"
        or run.is_error is not False
        or run.errors not in (None, [])
        or run.stop_reason not in (None, "end_turn")
    ):
        raise ValueError("SDK audit has no successful, error-free terminal result")

    data = run.structured_output
    required = {"summary", "findings", "suggestions", "audit_complete"}
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("SDK audit must provide the complete structured output object")
    if data["audit_complete"] is not True:
        raise ValueError("SDK audit did not affirm completion")

    summary = data["summary"]
    if (
        not isinstance(summary, dict)
        or not set(summary).issubset({"text", "score"})
        or not _nonempty_text(summary.get("text"))
    ):
        raise ValueError("SDK audit summary is malformed")
    if "score" in summary and (
        type(summary["score"]) is not int or not 0 <= summary["score"] <= 100
    ):
        raise ValueError("SDK audit score must be an integer from 0 to 100")

    findings = _flatten_findings(data["findings"])

    suggestions = data["suggestions"]
    _validate_suggestions(suggestions)

    payload = {
        "schema_version": "security-audit/v1",
        "workflow": "security-audit",
        "success": True,
        "audit_complete": True,
        "sdk_completion": {"subtype": "success", "is_error": False, "stop_reason": run.stop_reason},
        "summary": summary,
        "findings": findings,
        "suggestions": suggestions,
    }
    try:
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("SDK audit output is not serializable JSON") from exc
