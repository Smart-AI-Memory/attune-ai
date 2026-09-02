"""Shared-renderer adapter for classified memory operations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from attune_forms import WorkspaceActionResponse, workspace_from_dict

from attune.elicitation.command_workspace import (
    CommandWorkspaceError,
    CommandWorkspaceProjection,
    CommandWorkspaceTransition,
)

_OPERATIONS = frozenset({"store", "retrieve", "search", "forget"})
_CLASSIFICATIONS = frozenset({"PUBLIC", "INTERNAL", "SENSITIVE"})
_SCOPES = frozenset({"session", "persistent", "all"})


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise CommandWorkspaceError(["Memory value must be JSON serializable"]) from exc


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


@dataclass(frozen=True)
class MemoryContextWorkspaceState:
    """Memory-operation-owned canonical state without rendered secret values."""

    operation: str
    key_or_query: str
    stage: str = "preview"
    value_json: str = ""
    classification: str = "PUBLIC"
    pattern_type: str = ""
    scope: str = "all"
    success: bool | None = None
    found: bool | None = None
    result_count: int = 0
    source: str = ""
    value_digest: str = ""
    removed_from: tuple[str, ...] = ()
    error: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "removed_from", tuple(self.removed_from))
        problems: list[str] = []
        if self.operation not in _OPERATIONS:
            problems.append("Memory operation is invalid")
        if not self.key_or_query.strip():
            problems.append("Memory key or query must not be empty")
        if self.stage not in {"preview", "running", "verifying", "receipt"}:
            problems.append("Memory workspace stage is invalid")
        if self.classification not in _CLASSIFICATIONS:
            problems.append("Memory classification is invalid")
        if self.scope not in _SCOPES:
            problems.append("Memory forget scope is invalid")
        if self.operation == "store" and not self.value_json:
            problems.append("Memory store requires a value")
        if self.value_json:
            try:
                json.loads(self.value_json)
            except json.JSONDecodeError:
                problems.append("Memory value_json is invalid")
        if isinstance(self.result_count, bool) or not isinstance(self.result_count, int):
            problems.append("Memory result_count must be an integer")
        elif self.result_count < 0:
            problems.append("Memory result_count must not be negative")
        if not set(self.removed_from).issubset(_SCOPES - {"all"}):
            problems.append("Memory removed_from scope is invalid")
        if self.success is False and not self.error.strip():
            problems.append("Failed memory operation requires an error receipt")
        if self.success is True and self.error:
            problems.append("Successful memory operation cannot carry an error")
        if problems:
            raise CommandWorkspaceError(problems)


class MemoryContextWorkspaceAdapter:
    """Classified store/read/search plus confirmed forget and verification."""

    adapter_id = "memory-and-context"
    schema_version = 1

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> MemoryContextWorkspaceState:
        """Create a scoped memory operation preview."""
        if prior_state is not None:
            raise CommandWorkspaceError(["Memory workspaces cannot be replaced"])
        allowed = {
            "operation",
            "key",
            "query",
            "value",
            "classification",
            "pattern_type",
            "scope",
        }
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError([f"unknown memory intake key {key!r}" for key in unknown])
        operation = str(intake.get("operation", "")).lower()
        key_name = "query" if operation == "search" else "key"
        key_or_query = str(intake.get(key_name, "")).strip()
        if operation == "store" and ("value" not in intake or intake.get("value") is None):
            raise CommandWorkspaceError(["Memory store requires a non-null value"])
        value_json = _canonical_json(intake.get("value")) if operation == "store" else ""
        return MemoryContextWorkspaceState(
            operation=operation,
            key_or_query=key_or_query,
            value_json=value_json,
            classification=str(intake.get("classification", "PUBLIC")).upper(),
            pattern_type=str(intake.get("pattern_type", "")).strip(),
            scope=str(intake.get("scope", "all")).lower(),
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render a privacy-safe operation checkpoint or receipt."""
        if not isinstance(state, MemoryContextWorkspaceState):
            raise CommandWorkspaceError(["memory adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "operation": state.operation,
            "stage": state.stage,
            "key_or_query": state.key_or_query,
            "classification": state.classification,
            "scope": state.scope,
            "actions": [action.id for action in view.actions],
        }
        digest = hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return CommandWorkspaceProjection(view, digest if view.actions else "")

    def apply(
        self,
        state: object,
        response: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition:
        """Authorize the selected memory operation."""
        if not isinstance(state, MemoryContextWorkspaceState):
            raise CommandWorkspaceError(["memory adapter received incompatible state"])
        if state.stage != "preview":
            raise CommandWorkspaceError(["Memory action requires preview stage"])
        expected = f"{state.operation}_memory"
        if response.action != expected:
            raise CommandWorkspaceError([f"Memory action {response.action!r} is not legal"])
        if state.operation in {"store", "forget"} and not response.confirmed:
            raise CommandWorkspaceError(
                [f"Memory {state.operation} requires explicit confirmation"]
            )
        args: dict[str, object]
        if state.operation == "store":
            args = {
                "key": state.key_or_query,
                "value": json.loads(state.value_json),
                "classification": state.classification,
            }
            if state.pattern_type:
                args["pattern_type"] = state.pattern_type
        elif state.operation == "search":
            args = {"query": state.key_or_query}
            if state.pattern_type:
                args["pattern_type"] = state.pattern_type
        else:
            args = {"key": state.key_or_query}
            if state.operation == "forget":
                args["scope"] = state.scope
        return CommandWorkspaceTransition(
            replace(state, stage="running"),
            result={"delegate": f"memory_{state.operation}", "args": args},
        )

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish a tool result and require post-write/delete verification."""
        if not isinstance(state, MemoryContextWorkspaceState):
            raise CommandWorkspaceError(["memory adapter received incompatible state"])
        if state.stage == "running" and event.get("kind") == "operation_result":
            return self._operation_result(state, event)
        if state.stage == "verifying" and event.get("kind") == "verification_result":
            return self._verification_result(state, event)
        raise CommandWorkspaceError(["Memory receipt is not legal in the current stage"])

    def _operation_result(
        self,
        state: MemoryContextWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Memory operation success must be boolean"])
        if not success:
            return self._failure(state, str(event.get("error", "")).strip())
        if state.operation == "store":
            if str(event.get("key", "")) != state.key_or_query:
                raise CommandWorkspaceError(["Memory store receipt key does not match"])
            if str(event.get("classification", "")) != state.classification:
                raise CommandWorkspaceError(["Memory store receipt classification does not match"])
            return CommandWorkspaceTransition(
                replace(state, stage="verifying"),
                result={"delegate": "memory_retrieve", "args": {"key": state.key_or_query}},
            )
        if state.operation == "forget":
            removed = event.get("removed_from", ())
            if not isinstance(removed, Sequence) or isinstance(removed, str | bytes):
                raise CommandWorkspaceError(["Memory forget removed_from must be a list"])
            removed_from = tuple(str(item) for item in removed)
            return CommandWorkspaceTransition(
                replace(state, stage="verifying", removed_from=removed_from),
                result={"delegate": "memory_retrieve", "args": {"key": state.key_or_query}},
            )
        if state.operation == "retrieve":
            data = event.get("data")
            found = data is not None
            return self._terminal(
                state,
                found=found,
                source=str(event.get("source", "")),
                value_digest=_digest(data) if found else "",
            )
        results = event.get("results", ())
        if not isinstance(results, Sequence) or isinstance(results, str | bytes):
            raise CommandWorkspaceError(["Memory search results must be a list"])
        count = event.get("count", len(results))
        if isinstance(count, bool) or not isinstance(count, int) or count != len(results):
            raise CommandWorkspaceError(["Memory search count must match results"])
        return self._terminal(state, result_count=count, value_digest=_digest(list(results)))

    def _verification_result(
        self,
        state: MemoryContextWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Memory verification success must be boolean"])
        if not success:
            return self._failure(state, str(event.get("error", "")).strip())
        data = event.get("data")
        if state.operation == "store":
            if not isinstance(data, Mapping) or "value" not in data:
                return self._failure(state, "stored key was not retrieved")
            stored_value = json.loads(state.value_json)
            if _digest(data["value"]) != _digest(stored_value):
                return self._failure(state, "retrieved value did not match stored value")
            if str(data.get("classification", "")) != state.classification:
                return self._failure(state, "retrieved classification did not match")
            return self._terminal(
                state,
                found=True,
                source=str(event.get("source", "")),
                value_digest=_digest(stored_value),
            )
        if data is not None:
            return self._failure(state, "forgotten key is still retrievable")
        return self._terminal(state, found=False)

    @staticmethod
    def _failure(
        state: MemoryContextWorkspaceState,
        error: str,
    ) -> CommandWorkspaceTransition:
        if not error:
            raise CommandWorkspaceError(["Failed memory receipt requires error"])
        successor = replace(state, stage="receipt", success=False, error=error)
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={"success": False, "operation": state.operation, "error": error},
        )

    @staticmethod
    def _terminal(
        state: MemoryContextWorkspaceState,
        *,
        found: bool | None = None,
        result_count: int = 0,
        source: str = "",
        value_digest: str = "",
    ) -> CommandWorkspaceTransition:
        successor = replace(
            state,
            stage="receipt",
            success=True,
            found=found,
            result_count=result_count,
            source=source,
            value_digest=value_digest,
        )
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={
                "success": True,
                "operation": state.operation,
                "key_or_query": state.key_or_query,
                "found": found,
                "count": result_count,
                "value_digest": value_digest,
                "removed_from": list(state.removed_from),
            },
        )

    @staticmethod
    def _view_data(state: MemoryContextWorkspaceState) -> dict[str, object]:
        if state.stage == "preview":
            subject = "query" if state.operation == "search" else "key"
            items = [
                {"label": "Operation", "value": state.operation},
                {"label": subject.title(), "value": state.key_or_query},
            ]
            if state.operation == "store":
                items.append({"label": "Classification", "value": state.classification})
                items.append({"label": "Value", "value": "redacted from workspace"})
            if state.operation == "forget":
                items.append({"label": "Scope", "value": state.scope})
            action: dict[str, object] = {
                "id": f"{state.operation}_memory",
                "label": f"{state.operation.title()} memory",
            }
            if state.operation in {"store", "forget"}:
                action.update(
                    {
                        "consequence": (
                            "Persist classified memory."
                            if state.operation == "store"
                            else "Delete the selected memory scope."
                        ),
                        "requires_explicit_choice": True,
                    }
                )
            return {
                "id": "preview",
                "title": "Memory operation preview",
                "summary": f"Review {state.operation} scope before execution.",
                "sections": [
                    {
                        "heading": "Scope",
                        "blocks": [{"kind": "key_value", "items": items}],
                    }
                ],
                "actions": [action],
            }
        if state.stage in {"running", "verifying"}:
            summary = (
                "Verifying the external-state change by retrieving the same key."
                if state.stage == "verifying"
                else f"Calling memory_{state.operation}."
            )
            return {"id": "execution", "title": "Memory operation running", "summary": summary}
        if state.success is False:
            summary = f"Memory {state.operation} did not complete: {state.error}"
        elif state.operation == "store":
            summary = (
                f"Stored and retrieved {state.key_or_query}; digest {state.value_digest[:12]}."
            )
        elif state.operation == "forget":
            summary = f"Forgot {state.key_or_query}; post-delete retrieval found no value."
        elif state.operation == "retrieve":
            summary = f"Retrieve completed; found: {state.found}."
        else:
            summary = f"Search completed with {state.result_count} matches."
        return {
            "id": "receipt",
            "title": "Memory operation receipt",
            "summary": summary,
            "sections": [
                {
                    "heading": "Receipt",
                    "blocks": [
                        {
                            "kind": "key_value",
                            "items": [
                                {"label": "Operation", "value": state.operation},
                                {"label": "Classification", "value": state.classification},
                                {"label": "Source", "value": state.source or "not returned"},
                            ],
                        }
                    ],
                }
            ],
        }
