"""Shared-renderer adapter for asynchronous batch submissions."""

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

_MODEL_TIERS = frozenset({"cheap", "capable", "premium"})
_PROVIDER_STATUSES = frozenset({"submitted", "pending", "completed", "failed"})


@dataclass(frozen=True)
class BulkRequest:
    """One immutable, provider-ready batch request."""

    task_id: str
    task_type: str
    input_data_json: str
    model_tier: str = "capable"

    def __post_init__(self) -> None:
        problems: list[str] = []
        if not self.task_id.strip():
            problems.append("Bulk task_id must not be empty")
        if not self.task_type.strip():
            problems.append("Bulk task_type must not be empty")
        if self.model_tier not in _MODEL_TIERS:
            problems.append("Bulk model_tier is invalid")
        try:
            decoded = json.loads(self.input_data_json)
        except json.JSONDecodeError:
            decoded = None
        if not isinstance(decoded, dict):
            problems.append("Bulk input_data must be a JSON object")
        if problems:
            raise CommandWorkspaceError(problems)

    def to_payload(self) -> dict[str, object]:
        """Return the provider request without mutable canonical state."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "input_data": json.loads(self.input_data_json),
            "model_tier": self.model_tier,
        }


@dataclass(frozen=True)
class BulkWorkspaceState:
    """Batch-owned submission or reconnect state."""

    mode: str
    stage: str = "preview"
    requests: tuple[BulkRequest, ...] = ()
    batch_id: str = ""
    accepted_count: int = 0
    provider_status: str = ""
    success: bool | None = None
    detail: str = ""
    error: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "requests", tuple(self.requests))
        problems: list[str] = []
        if self.mode not in {"submit", "resume"}:
            problems.append("Bulk workspace mode is invalid")
        if self.stage not in {"preview", "running", "receipt"}:
            problems.append("Bulk workspace stage is invalid")
        if self.mode == "submit" and not self.requests:
            problems.append("Bulk submission requires requests")
        if self.mode == "resume" and not self.batch_id.strip():
            problems.append("Bulk reconnect requires batch_id")
        task_ids = [request.task_id for request in self.requests]
        if len(task_ids) != len(set(task_ids)):
            problems.append("Bulk task_id values must be unique")
        if (
            isinstance(self.accepted_count, bool)
            or not isinstance(self.accepted_count, int)
            or self.accepted_count < 0
        ):
            problems.append("Bulk accepted_count must be a non-negative integer")
        if self.provider_status and self.provider_status not in _PROVIDER_STATUSES:
            problems.append("Bulk provider status is invalid")
        if self.success is False and not self.error.strip():
            problems.append("Failed bulk operation requires an error receipt")
        if self.success is True and self.error:
            problems.append("Successful bulk operation cannot carry an error")
        if problems:
            raise CommandWorkspaceError(problems)


def _request(raw: Mapping[str, object]) -> BulkRequest:
    input_data = raw.get("input_data")
    if not isinstance(input_data, Mapping):
        raise CommandWorkspaceError(["Bulk input_data must be a mapping"])
    try:
        encoded = json.dumps(
            dict(input_data),
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise CommandWorkspaceError(["Bulk input_data must be JSON serializable"]) from exc
    return BulkRequest(
        task_id=str(raw.get("task_id", "")).strip(),
        task_type=str(raw.get("task_type", "")).strip(),
        input_data_json=encoded,
        model_tier=str(raw.get("model_tier", "capable")).lower(),
    )


class BulkWorkspaceAdapter:
    """Confirm paid submission once and reconnect by provider batch id."""

    adapter_id = "bulk"
    schema_version = 1

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> BulkWorkspaceState:
        """Create a new submission preview or a status reconnect preview."""
        if prior_state is not None:
            raise CommandWorkspaceError(["Bulk workspaces cannot be replaced"])
        allowed = {"requests", "batch_id"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError([f"unknown bulk intake key {key!r}" for key in unknown])
        batch_id = str(intake.get("batch_id", "")).strip()
        raw_requests = intake.get("requests")
        if batch_id and raw_requests is not None:
            raise CommandWorkspaceError(["Bulk intake accepts requests or batch_id, not both"])
        if batch_id:
            return BulkWorkspaceState(mode="resume", batch_id=batch_id)
        if not isinstance(raw_requests, Sequence) or isinstance(raw_requests, str | bytes):
            raise CommandWorkspaceError(["Bulk requests must be a non-empty list"])
        if not raw_requests or len(raw_requests) > 100:
            raise CommandWorkspaceError(["Bulk requests must contain 1 to 100 items"])
        requests = tuple(_request(item) for item in raw_requests if isinstance(item, Mapping))
        if len(requests) != len(raw_requests):
            raise CommandWorkspaceError(["Each bulk request must be a mapping"])
        return BulkWorkspaceState(mode="submit", requests=requests)

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render submission, reconnect, running, or terminal state."""
        if not isinstance(state, BulkWorkspaceState):
            raise CommandWorkspaceError(["bulk adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "mode": state.mode,
            "stage": state.stage,
            "task_ids": [request.task_id for request in state.requests],
            "batch_id": state.batch_id,
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
        """Authorize one provider submission or read-only reconnect."""
        if not isinstance(state, BulkWorkspaceState):
            raise CommandWorkspaceError(["bulk adapter received incompatible state"])
        if state.stage != "preview":
            raise CommandWorkspaceError(["Bulk action requires preview stage"])
        if state.mode == "submit" and response.action == "submit_batch":
            if not response.confirmed:
                raise CommandWorkspaceError(["Bulk submission requires explicit confirmation"])
            return CommandWorkspaceTransition(
                replace(state, stage="running", detail="Submitting batch to provider."),
                result={
                    "delegate": "bulk.submit",
                    "requests": [request.to_payload() for request in state.requests],
                },
            )
        if state.mode == "resume" and response.action == "check_batch":
            return CommandWorkspaceTransition(
                replace(state, stage="running", detail="Checking provider batch status."),
                result={"delegate": "bulk.status", "batch_id": state.batch_id},
            )
        raise CommandWorkspaceError([f"Bulk action {response.action!r} is not legal"])

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish a truthful provider submission or status receipt."""
        if not isinstance(state, BulkWorkspaceState):
            raise CommandWorkspaceError(["bulk adapter received incompatible state"])
        if state.stage != "running":
            raise CommandWorkspaceError(["Bulk provider receipt requires running stage"])
        kind = event.get("kind")
        expected = "submission_result" if state.mode == "submit" else "status_result"
        if kind != expected:
            raise CommandWorkspaceError([f"Bulk {state.mode} requires {expected}"])
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Bulk provider success must be boolean"])
        batch_id = str(event.get("batch_id", state.batch_id)).strip()
        default_status = (
            "failed" if not success else "submitted" if state.mode == "submit" else "pending"
        )
        status = str(event.get("status", default_status)).lower()
        if status not in _PROVIDER_STATUSES:
            raise CommandWorkspaceError(["Bulk provider status is invalid"])
        if state.mode == "resume" and success and "accepted_count" not in event:
            raise CommandWorkspaceError(["Successful bulk status receipt requires accepted_count"])
        accepted = event.get("accepted_count", len(state.requests) if success else 0)
        if isinstance(accepted, bool) or not isinstance(accepted, int) or accepted < 0:
            raise CommandWorkspaceError(["Bulk accepted_count must be a non-negative integer"])
        if state.mode == "submit" and accepted > len(state.requests):
            raise CommandWorkspaceError(["Bulk accepted_count exceeds requested task count"])
        if success and not batch_id:
            raise CommandWorkspaceError(["Successful bulk provider receipt requires batch_id"])
        if state.mode == "submit" and success and accepted != len(state.requests):
            raise CommandWorkspaceError(["Successful bulk submission must accept every task"])
        error = str(event.get("error", "")).strip()
        if not success and not error:
            raise CommandWorkspaceError(["Failed bulk provider receipt requires error"])
        detail = str(event.get("detail", "")).strip() or status
        successor = BulkWorkspaceState(
            mode=state.mode,
            stage="receipt",
            requests=state.requests,
            batch_id=batch_id,
            accepted_count=accepted,
            provider_status=status,
            success=success,
            detail=detail,
            error=error,
        )
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={
                "success": success,
                "batch_id": batch_id,
                "accepted_count": accepted,
                "status": status,
                "error": error,
            },
        )

    @staticmethod
    def _view_data(state: BulkWorkspaceState) -> dict[str, object]:
        if state.stage == "preview":
            if state.mode == "resume":
                return {
                    "id": "preview",
                    "title": "Reconnect to batch",
                    "summary": f"Check provider status for {state.batch_id}.",
                    "actions": [{"id": "check_batch", "label": "Check batch status"}],
                }
            return {
                "id": "preview",
                "title": "Bulk submission preview",
                "summary": (
                    f"Submit {len(state.requests)} non-urgent tasks asynchronously; "
                    "processing can take up to 24 hours."
                ),
                "sections": [
                    {
                        "heading": "Requests",
                        "blocks": [
                            {
                                "kind": "action_list",
                                "items": [
                                    {
                                        "label": request.task_id,
                                        "detail": f"{request.task_type} · {request.model_tier}",
                                    }
                                    for request in state.requests
                                ],
                            }
                        ],
                    }
                ],
                "actions": [
                    {
                        "id": "submit_batch",
                        "label": "Submit batch",
                        "consequence": "Create paid asynchronous provider work.",
                        "requires_explicit_choice": True,
                    }
                ],
            }
        if state.stage == "running":
            return {
                "id": "execution",
                "title": "Bulk provider request running",
                "summary": state.detail,
            }
        success = state.success is True
        if state.mode == "submit":
            summary = (
                f"Submitted {state.accepted_count}/{len(state.requests)} tasks as {state.batch_id}."
                if success
                else f"Batch did not submit all tasks: {state.error}"
            )
        else:
            summary = (
                f"Batch {state.batch_id} is {state.provider_status}."
                if success
                else f"Batch status check did not complete: {state.error}"
            )
        return {
            "id": "receipt",
            "title": "Bulk batch receipt",
            "summary": summary,
            "sections": [
                {
                    "heading": "Provider receipt",
                    "blocks": [
                        {
                            "kind": "key_value",
                            "items": [
                                {"label": "Batch id", "value": state.batch_id or "not issued"},
                                {"label": "Status", "value": state.provider_status},
                                {"label": "Accepted", "value": str(state.accepted_count)},
                            ],
                        }
                    ],
                }
            ],
        }
