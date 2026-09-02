"""Shared-renderer adapter for multi-workflow fan-out and fan-in."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from attune_forms import WorkspaceActionResponse, workspace_from_dict

from attune.elicitation.command_workspace import (
    CommandWorkspaceError,
    CommandWorkspaceProjection,
    CommandWorkspaceTransition,
)
from attune.security.path_validation import _validate_file_path

WORKFLOW_TOOLS = {
    "security": "security_audit",
    "review": "code_review",
    "bugs": "bug_predict",
    "performance": "performance_audit",
    "tests": "test_audit",
    "docs": "doc_audit",
    "release": "release_notes",
}
_STATUSES = frozenset({"PASS", "WARNING", "FAIL", "ERROR", "MISSING"})
_BLOCKING = frozenset({"FAIL", "ERROR", "MISSING"})


@dataclass(frozen=True)
class ChildWorkflowReceipt:
    """One exact child workflow outcome."""

    name: str
    status: str
    detail: str
    probe: str

    def __post_init__(self) -> None:
        if self.name not in WORKFLOW_TOOLS:
            raise CommandWorkspaceError(["Child workflow name is invalid"])
        if self.status not in _STATUSES:
            raise CommandWorkspaceError(["Child workflow status is invalid"])
        if not self.detail.strip() or not self.probe.strip():
            raise CommandWorkspaceError(["Child workflow detail and probe are required"])


@dataclass(frozen=True)
class WorkflowOrchestrationState:
    """Orchestration-owned request order and child receipts."""

    goal: str
    target_path: str
    workflows: tuple[str, ...]
    stage: str = "preview"
    receipts: tuple[ChildWorkflowReceipt, ...] = ()
    success: bool | None = None
    degraded: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflows", tuple(self.workflows))
        object.__setattr__(self, "receipts", tuple(self.receipts))
        problems: list[str] = []
        if not self.goal.strip():
            problems.append("Orchestration goal must not be empty")
        if not self.target_path.strip():
            problems.append("Orchestration target_path must not be empty")
        if self.stage not in {"preview", "running", "receipt"}:
            problems.append("Orchestration stage is invalid")
        if not 2 <= len(self.workflows) <= len(WORKFLOW_TOOLS):
            problems.append("Orchestration requires 2 to 7 workflows")
        if len(self.workflows) != len(set(self.workflows)):
            problems.append("Orchestration workflows must be unique")
        if not set(self.workflows).issubset(WORKFLOW_TOOLS):
            problems.append("Orchestration workflow is invalid")
        receipt_names = [receipt.name for receipt in self.receipts]
        if len(receipt_names) != len(set(receipt_names)):
            problems.append("Child workflow receipts must be unique")
        if not set(receipt_names).issubset(self.workflows):
            problems.append("Child workflow receipt was not requested")
        if problems:
            raise CommandWorkspaceError(problems)


def _receipt(raw: Mapping[str, object]) -> ChildWorkflowReceipt:
    return ChildWorkflowReceipt(
        name=str(raw.get("name", "")).lower(),
        status=str(raw.get("status", "")).upper(),
        detail=str(raw.get("detail", "")),
        probe=str(raw.get("probe", "")),
    )


class WorkflowOrchestrationAdapter:
    """Fan out named children and fail aggregation on absent gatekeepers."""

    adapter_id = "workflow-orchestration"
    schema_version = 1

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> WorkflowOrchestrationState:
        """Create a path-validated multi-workflow preview."""
        if prior_state is not None:
            raise CommandWorkspaceError(["Orchestration workspaces cannot be replaced"])
        allowed = {"goal", "path", "workflows"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError(
                [f"unknown orchestration intake key {key!r}" for key in unknown]
            )
        raw_workflows = intake.get("workflows")
        if not isinstance(raw_workflows, Sequence) or isinstance(raw_workflows, str | bytes):
            raise CommandWorkspaceError(["Orchestration workflows must be a list"])
        workflows = tuple(str(item).lower() for item in raw_workflows)
        candidate = (self.repo_root / str(intake.get("path", "."))).resolve()
        try:
            relative = candidate.relative_to(self.repo_root).as_posix() or "."
        except ValueError as exc:
            raise CommandWorkspaceError(["Orchestration path escapes the repository"]) from exc
        validated = _validate_file_path(str(candidate), str(self.repo_root))
        if not validated.exists():
            raise CommandWorkspaceError(["Orchestration target path does not exist"])
        return WorkflowOrchestrationState(
            goal=str(intake.get("goal", "")).strip(),
            target_path=relative,
            workflows=workflows,
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render ordered child progress or the aggregate receipt."""
        if not isinstance(state, WorkflowOrchestrationState):
            raise CommandWorkspaceError(["orchestration adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "goal": state.goal,
            "target": state.target_path,
            "workflows": state.workflows,
            "stage": state.stage,
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
        """Authorize the selected multi-workflow fan-out."""
        if not isinstance(state, WorkflowOrchestrationState):
            raise CommandWorkspaceError(["orchestration adapter received incompatible state"])
        if state.stage != "preview" or response.action != "run_workflows":
            raise CommandWorkspaceError(["Orchestration action is not legal"])
        if not response.confirmed:
            raise CommandWorkspaceError(["Multi-workflow execution requires explicit confirmation"])
        return CommandWorkspaceTransition(
            replace(state, stage="running"),
            result={
                "delegate": "workflow-orchestration.run",
                "children": [
                    {
                        "name": name,
                        "tool": WORKFLOW_TOOLS[name],
                        "args": {"path": state.target_path},
                    }
                    for name in state.workflows
                ],
            },
        )

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish a child receipt or synthesize a fail-closed aggregate."""
        if not isinstance(state, WorkflowOrchestrationState):
            raise CommandWorkspaceError(["orchestration adapter received incompatible state"])
        if state.stage != "running":
            raise CommandWorkspaceError(["Orchestration receipt requires running stage"])
        kind = event.get("kind")
        if kind == "child_result":
            raw = event.get("receipt")
            if not isinstance(raw, Mapping):
                raise CommandWorkspaceError(["Child result requires receipt mapping"])
            receipt = _receipt(raw)
            if receipt.name not in state.workflows:
                raise CommandWorkspaceError(["Child workflow was not requested"])
            if any(existing.name == receipt.name for existing in state.receipts):
                raise CommandWorkspaceError(["Child workflow receipt already exists"])
            return CommandWorkspaceTransition(
                replace(state, receipts=(*state.receipts, receipt)),
                result={"child": receipt.name, "status": receipt.status},
                authority_changed=False,
            )
        if kind == "orchestration_complete":
            by_name = {receipt.name: receipt for receipt in state.receipts}
            ordered: list[ChildWorkflowReceipt] = []
            for name in state.workflows:
                ordered.append(
                    by_name.get(
                        name,
                        ChildWorkflowReceipt(
                            name,
                            "MISSING",
                            "child workflow did not return a receipt",
                            "no child probe receipt",
                        ),
                    )
                )
            blockers = [receipt for receipt in ordered if receipt.status in _BLOCKING]
            degraded = any(receipt.status == "WARNING" for receipt in ordered)
            successor = replace(
                state,
                stage="receipt",
                receipts=tuple(ordered),
                success=not blockers,
                degraded=degraded,
            )
            return CommandWorkspaceTransition(
                successor,
                terminal=True,
                result={
                    "success": not blockers,
                    "degraded": degraded,
                    "statuses": {receipt.name: receipt.status for receipt in ordered},
                    "blockers": [receipt.name for receipt in blockers],
                },
            )
        raise CommandWorkspaceError([f"Unknown orchestration event {kind!r}"])

    @staticmethod
    def _receipt_section(state: WorkflowOrchestrationState) -> dict[str, object]:
        by_name = {receipt.name: receipt for receipt in state.receipts}
        return {
            "heading": "Child receipts",
            "blocks": [
                {
                    "kind": "evidence",
                    "items": [
                        {
                            "label": name,
                            "value": (
                                f"{by_name[name].status}: {by_name[name].detail} "
                                f"({by_name[name].probe})"
                                if name in by_name
                                else "awaiting receipt"
                            ),
                            "status": (
                                "complete"
                                if name in by_name and by_name[name].status in {"PASS", "WARNING"}
                                else "failed" if name in by_name else "pending"
                            ),
                        }
                        for name in state.workflows
                    ],
                }
            ],
        }

    @classmethod
    def _view_data(cls, state: WorkflowOrchestrationState) -> dict[str, object]:
        if state.stage == "preview":
            return {
                "id": "preview",
                "title": "Workflow orchestration preview",
                "summary": f"Run {len(state.workflows)} workflows for {state.goal}.",
                "sections": [cls._receipt_section(state)],
                "actions": [
                    {
                        "id": "run_workflows",
                        "label": "Run workflows",
                        "consequence": "Invoke every named child workflow.",
                        "requires_explicit_choice": True,
                    }
                ],
            }
        if state.stage == "running":
            return {
                "id": "execution",
                "title": "Workflow orchestration running",
                "summary": f"{len(state.receipts)}/{len(state.workflows)} child receipts recorded.",
                "sections": [cls._receipt_section(state)],
            }
        if state.success:
            summary = (
                "All child workflows returned; aggregate is degraded by warnings."
                if state.degraded
                else "All child workflows passed."
            )
        else:
            summary = "Orchestration did not complete cleanly; one or more children failed or are missing."
        return {
            "id": "receipt",
            "title": "Workflow orchestration receipt",
            "summary": summary,
            "sections": [cls._receipt_section(state)],
        }
