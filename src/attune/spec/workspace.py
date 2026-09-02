"""Shared-renderer adapter for resumable Spec Ladders."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from attune_forms import WorkspaceActionResponse, workspace_from_dict

from attune.elicitation.command_workspace import (
    CommandWorkspaceError,
    CommandWorkspaceProjection,
    CommandWorkspaceTransition,
)
from attune.elicitation.spec_intake import (
    OTHER,
    area_candidates,
    compose_spec_contract,
    existing_spec_slugs,
)
from attune.pipeline.spec_reader import read_spec
from attune.security.path_validation import _validate_file_path
from attune.spec.state import load_state

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_STAGES = frozenset(
    {
        "preview",
        "intake",
        "creating",
        "gate_running",
        "review",
        "approval",
        "chair_required",
        "blocked",
        "executing",
        "task_gate",
        "receipt",
    }
)
_GATE_STATES = frozenset({"PASS", "REVISE", "CHAIR_REQUIRED", "BLOCKED"})
_BOUNDARIES = frozenset({"tasks", "execution"})
_SEVERITIES = frozenset({"low", "medium", "high"})


def _portable_path(raw: object, label: str) -> str:
    value = str(raw).strip()
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise CommandWorkspaceError([f"Spec {label} must be a project-relative path"])
    return path.as_posix()


def _string_list(raw: object, label: str, *, required: bool = False) -> tuple[str, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        raise CommandWorkspaceError([f"Spec {label} must be a list"])
    values = tuple(str(item).strip() for item in raw)
    if any(not item for item in values) or (required and not values):
        raise CommandWorkspaceError([f"Spec {label} must contain non-empty values"])
    if len(values) != len(set(values)):
        raise CommandWorkspaceError([f"Spec {label} must be unique"])
    return values


@dataclass(frozen=True)
class SpecArtifactReceipt:
    """One exact artifact link emitted by the spec creator/executor."""

    path: str
    kind: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _portable_path(self.path, "artifact"))
        if not self.kind.strip():
            raise CommandWorkspaceError(["Spec artifact kind must not be empty"])


@dataclass(frozen=True)
class SpecLifecycleReceipt:
    """One lifecycle-gate verdict presented without reinterpretation."""

    gate_id: str
    boundary: str
    state: str
    detail: str

    def __post_init__(self) -> None:
        if not self.gate_id.strip():
            raise CommandWorkspaceError(["Spec lifecycle gate_id must not be empty"])
        if self.boundary not in _BOUNDARIES:
            raise CommandWorkspaceError(["Spec lifecycle boundary is invalid"])
        if self.state not in _GATE_STATES:
            raise CommandWorkspaceError(["Spec lifecycle state is invalid"])
        if not self.detail.strip():
            raise CommandWorkspaceError(["Spec lifecycle detail must not be empty"])


@dataclass(frozen=True)
class SpecTaskGateReceipt:
    """The failure-sensitive quality receipt for one executed task."""

    task_id: str
    severity: str
    score: float
    probes: tuple[str, ...]
    detail: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "probes", tuple(self.probes))
        if not self.task_id.strip():
            raise CommandWorkspaceError(["Spec task receipt requires task_id"])
        if self.severity not in _SEVERITIES:
            raise CommandWorkspaceError(["Spec task severity is invalid"])
        if isinstance(self.score, bool) or not isinstance(self.score, int | float):
            raise CommandWorkspaceError(["Spec task score must be numeric"])
        if self.score < 0 or self.score > 100:
            raise CommandWorkspaceError(["Spec task score must be between 0 and 100"])
        if not self.probes or any(not probe.strip() for probe in self.probes):
            raise CommandWorkspaceError(["Spec task receipt requires exact probes"])
        if not self.detail.strip():
            raise CommandWorkspaceError(["Spec task receipt detail must not be empty"])


@dataclass(frozen=True)
class SpecWorkspaceState:
    """Spec-owned canonical state; the host never interprets these fields."""

    outcome: str
    done_when: str
    area: str
    slug: str
    contract: str
    area_options: tuple[str, ...]
    taken_slugs: tuple[str, ...]
    stage: str = "preview"
    plan_path: str = ""
    task_ids: tuple[str, ...] = ()
    completed: tuple[str, ...] = ()
    current: str = ""
    auto_run: bool = False
    artifacts: tuple[SpecArtifactReceipt, ...] = ()
    probes: tuple[str, ...] = ()
    gate_boundary: str = ""
    gate_next_stage: str = ""
    lifecycle_receipts: tuple[SpecLifecycleReceipt, ...] = ()
    task_receipt: SpecTaskGateReceipt | None = None
    blocked_reason: str = ""
    progress_detail: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "area_options",
            "taken_slugs",
            "task_ids",
            "completed",
            "artifacts",
            "probes",
            "lifecycle_receipts",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        problems: list[str] = []
        if not self.outcome.strip():
            problems.append("Spec outcome must not be empty")
        if not self.done_when.strip():
            problems.append("Spec done_when must not be empty")
        if self.slug and not _SLUG_RE.fullmatch(self.slug):
            problems.append("Spec slug must be kebab-case")
        if self.stage not in _STAGES:
            problems.append("Spec workspace stage is invalid")
        if len(self.task_ids) != len(set(self.task_ids)):
            problems.append("Spec task ids must be unique")
        if not set(self.completed).issubset(self.task_ids):
            problems.append("Spec completed ids must belong to the plan")
        if self.current and self.current not in self.task_ids:
            problems.append("Spec current task must belong to the plan")
        if self.current and self.current in self.completed:
            problems.append("Spec current task cannot already be completed")
        if self.gate_boundary and self.gate_boundary not in _BOUNDARIES:
            problems.append("Spec gate boundary is invalid")
        if self.gate_next_stage and self.gate_next_stage not in _STAGES:
            problems.append("Spec gate successor stage is invalid")
        artifact_paths = [artifact.path for artifact in self.artifacts]
        if len(artifact_paths) != len(set(artifact_paths)):
            problems.append("Spec artifact paths must be unique")
        if problems:
            raise CommandWorkspaceError(problems)

    @property
    def pending(self) -> tuple[str, ...]:
        """Return ordered task ids that still require approval."""
        completed = set(self.completed)
        return tuple(task_id for task_id in self.task_ids if task_id not in completed)


def _artifact(raw: Mapping[str, object]) -> SpecArtifactReceipt:
    return SpecArtifactReceipt(str(raw.get("path", "")), str(raw.get("kind", "")))


def _lifecycle_receipt(raw: Mapping[str, object], boundary: str) -> SpecLifecycleReceipt:
    return SpecLifecycleReceipt(
        gate_id=str(raw.get("gate_id", "")),
        boundary=str(raw.get("boundary", boundary)),
        state=str(raw.get("state", "")),
        detail=str(raw.get("detail", "")),
    )


class SpecWorkspaceAdapter:
    """Spec creation, review, lifecycle, task-gate, and resume semantics."""

    adapter_id = "spec"
    schema_version = 1

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> SpecWorkspaceState:
        """Create a new-spec preview or resume a tree-backed plan."""
        if prior_state is not None and (
            not isinstance(prior_state, SpecWorkspaceState) or prior_state.stage != "intake"
        ):
            raise CommandWorkspaceError(["select edit_spec before replacing Spec intake"])
        route = str(intake.get("route", "new"))
        if route == "resume":
            if prior_state is not None:
                raise CommandWorkspaceError(["Spec resume cannot replace edited intake"])
            return self._resume(intake)
        if route != "new":
            raise CommandWorkspaceError(["Spec route must be new or resume"])
        allowed = {"route", "outcome", "done_when", "area", "slug"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError([f"unknown Spec intake key {key!r}" for key in unknown])
        answers = {key: intake.get(key, "") for key in ("outcome", "done_when", "area", "slug")}
        areas = tuple(area_candidates(self.repo_root))
        taken = tuple(existing_spec_slugs(self.repo_root))
        return SpecWorkspaceState(
            outcome=str(answers["outcome"]).strip(),
            done_when=str(answers["done_when"]).strip(),
            area=str(answers["area"]).strip(),
            slug=str(answers["slug"]).strip(),
            contract=compose_spec_contract(answers, list(taken)),
            area_options=areas,
            taken_slugs=taken,
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render one canonical Spec stage."""
        if not isinstance(state, SpecWorkspaceState):
            raise CommandWorkspaceError(["Spec adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "stage": state.stage,
            "plan": state.plan_path,
            "tasks": state.task_ids,
            "completed": state.completed,
            "current": state.current,
            "gate": state.gate_boundary,
            "task_severity": state.task_receipt.severity if state.task_receipt else None,
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
        """Apply one bound review, approval, gate, or task decision."""
        if not isinstance(state, SpecWorkspaceState):
            raise CommandWorkspaceError(["Spec adapter received incompatible state"])
        action = response.action
        if state.stage == "preview":
            if action == "edit_spec":
                return CommandWorkspaceTransition(replace(state, stage="intake"))
            if action == "create_spec":
                return CommandWorkspaceTransition(
                    replace(state, stage="creating"),
                    result={"delegate": "spec.create", "contract": state.contract},
                )
        if state.stage == "review":
            if action == "redo_plan":
                return CommandWorkspaceTransition(
                    replace(state, stage="creating"),
                    result={"delegate": "spec.redo", "plan_path": state.plan_path},
                )
            if action == "approve_plan":
                return CommandWorkspaceTransition(replace(state, stage="approval"))
        if state.stage == "approval":
            if action == "redo_plan":
                return CommandWorkspaceTransition(
                    replace(state, stage="creating"),
                    result={"delegate": "spec.redo", "plan_path": state.plan_path},
                )
            if action == "start_execution":
                return CommandWorkspaceTransition(
                    replace(
                        state,
                        stage="gate_running",
                        gate_boundary="execution",
                        gate_next_stage="executing",
                    ),
                    result={"delegate": "spec.lifecycle_gate", "boundary": "execution"},
                )
        if state.stage == "chair_required" and action == "acknowledge_gate":
            if not response.confirmed:
                raise CommandWorkspaceError(
                    ["Spec lifecycle acknowledgment requires explicit chair confirmation"]
                )
            return CommandWorkspaceTransition(
                replace(
                    state,
                    stage=state.gate_next_stage,
                    gate_boundary="",
                    gate_next_stage="",
                ),
                result={"acknowledged": True},
            )
        if state.stage == "blocked" and action == "retry_gate":
            return CommandWorkspaceTransition(
                replace(state, stage="gate_running", blocked_reason=""),
                result={"delegate": "spec.lifecycle_gate", "boundary": state.gate_boundary},
            )
        if state.stage == "task_gate":
            return self._apply_task_gate(state, response)
        raise CommandWorkspaceError(
            [f"Spec action {action!r} is not legal in stage {state.stage!r}"]
        )

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Apply one creator, lifecycle, or executor receipt."""
        if not isinstance(state, SpecWorkspaceState):
            raise CommandWorkspaceError(["Spec adapter received incompatible state"])
        kind = event.get("kind")
        if kind == "artifacts_created":
            return self._publish_artifacts(state, event)
        if kind == "lifecycle_gate":
            return self._publish_lifecycle(state, event)
        if kind == "task_started":
            return self._publish_task_started(state, event)
        if kind == "execution_progress":
            if state.stage != "executing":
                raise CommandWorkspaceError(["Spec progress requires execution stage"])
            return CommandWorkspaceTransition(
                replace(state, progress_detail=str(event.get("detail", "")).strip()),
                authority_changed=False,
            )
        if kind == "task_result":
            return self._publish_task_result(state, event)
        raise CommandWorkspaceError([f"unknown Spec event {kind!r}"])

    def _resume(self, intake: Mapping[str, object]) -> SpecWorkspaceState:
        allowed = {"route", "plan_path"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError([f"unknown Spec resume key {key!r}" for key in unknown])
        raw_path = _portable_path(intake.get("plan_path", ""), "plan_path")
        candidate = (self.repo_root / raw_path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise CommandWorkspaceError(["Spec plan_path escapes the repository"]) from exc
        validated = _validate_file_path(str(candidate))
        if not validated.is_file():
            raise CommandWorkspaceError(["Spec resume plan does not exist"])
        tasks = read_spec(str(validated))
        if not tasks:
            raise CommandWorkspaceError(["Spec resume plan has no XML tasks"])
        persisted = load_state(str(validated))
        completed = tuple(persisted.completed) if persisted else ()
        task_ids = tuple(task.task_id for task in tasks)
        if set(completed) >= set(task_ids):
            raise CommandWorkspaceError(["Spec resume plan is already complete"])
        current = persisted.current if persisted and persisted.current not in completed else ""
        return SpecWorkspaceState(
            outcome=f"Resume {validated.stem}",
            done_when="All remaining XML tasks have approved receipts.",
            area=str(validated.parent.relative_to(self.repo_root)),
            slug=validated.stem.replace("_", "-").lower(),
            contract=f"Resume `{raw_path}` with canonical persisted progress.",
            area_options=tuple(area_candidates(self.repo_root)),
            taken_slugs=tuple(existing_spec_slugs(self.repo_root)),
            stage="executing",
            plan_path=raw_path,
            task_ids=task_ids,
            completed=completed,
            current=current,
            auto_run=persisted.auto_run if persisted else False,
            artifacts=(SpecArtifactReceipt(raw_path, "plan"),),
        )

    def _publish_artifacts(
        self,
        state: SpecWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        if state.stage != "creating":
            raise CommandWorkspaceError(["Spec artifact receipt requires creation stage"])
        raw_artifacts = event.get("artifacts")
        if not isinstance(raw_artifacts, Sequence) or isinstance(raw_artifacts, str | bytes):
            raise CommandWorkspaceError(["Spec artifacts must be a list"])
        artifacts = tuple(_artifact(raw) for raw in raw_artifacts if isinstance(raw, Mapping))
        if not artifacts or len(artifacts) != len(raw_artifacts):
            raise CommandWorkspaceError(["Spec artifacts require receipt mappings"])
        task_ids = _string_list(event.get("task_ids"), "task_ids", required=True)
        probes = _string_list(event.get("probes"), "probes", required=True)
        plan_path = _portable_path(event.get("plan_path", ""), "plan_path")
        if plan_path not in {artifact.path for artifact in artifacts}:
            raise CommandWorkspaceError(["Spec plan_path must name a received artifact"])
        return CommandWorkspaceTransition(
            replace(
                state,
                stage="gate_running",
                plan_path=plan_path,
                task_ids=task_ids,
                artifacts=artifacts,
                probes=probes,
                gate_boundary="tasks",
                gate_next_stage="review",
            ),
            result={"delegate": "spec.lifecycle_gate", "boundary": "tasks"},
        )

    def _publish_lifecycle(
        self,
        state: SpecWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        if state.stage != "gate_running":
            raise CommandWorkspaceError(["Spec lifecycle receipt requires gate-running stage"])
        boundary = str(event.get("boundary", ""))
        if boundary != state.gate_boundary:
            raise CommandWorkspaceError(["Spec lifecycle receipt boundary does not match"])
        raw_receipts = event.get("receipts")
        if not isinstance(raw_receipts, Sequence) or isinstance(raw_receipts, str | bytes):
            raise CommandWorkspaceError(["Spec lifecycle receipts must be a list"])
        receipts = tuple(
            _lifecycle_receipt(raw, boundary) for raw in raw_receipts if isinstance(raw, Mapping)
        )
        if not receipts or len(receipts) != len(raw_receipts):
            raise CommandWorkspaceError(["Spec lifecycle receipts require mappings"])
        states = {receipt.state for receipt in receipts}
        if "BLOCKED" in states or "REVISE" in states:
            successor_stage = "blocked"
            blocked_reason = "; ".join(
                receipt.detail for receipt in receipts if receipt.state in {"BLOCKED", "REVISE"}
            )
        elif "CHAIR_REQUIRED" in states:
            successor_stage = "chair_required"
            blocked_reason = ""
        else:
            successor_stage = state.gate_next_stage
            blocked_reason = ""
        return CommandWorkspaceTransition(
            replace(
                state,
                stage=successor_stage,
                lifecycle_receipts=receipts,
                blocked_reason=blocked_reason,
                gate_boundary=(
                    "" if successor_stage not in {"blocked", "chair_required"} else boundary
                ),
                gate_next_stage=(
                    ""
                    if successor_stage not in {"blocked", "chair_required"}
                    else state.gate_next_stage
                ),
            ),
            result={"gate_state": successor_stage, "boundary": boundary},
        )

    def _publish_task_started(
        self,
        state: SpecWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        if state.stage != "executing":
            raise CommandWorkspaceError(["Spec task start requires execution stage"])
        task_id = str(event.get("task_id", ""))
        if task_id not in state.pending:
            raise CommandWorkspaceError(["Spec task start must name a pending task"])
        expected = state.pending[0]
        if task_id != expected:
            raise CommandWorkspaceError(["Spec tasks must start in plan order"])
        return CommandWorkspaceTransition(replace(state, current=task_id, progress_detail=""))

    def _publish_task_result(
        self,
        state: SpecWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        if state.stage != "executing" or not state.current:
            raise CommandWorkspaceError(["Spec task result requires a current execution task"])
        task_id = str(event.get("task_id", ""))
        if task_id != state.current:
            raise CommandWorkspaceError(["Spec task result does not match current task"])
        probes = _string_list(event.get("probes"), "task probes", required=True)
        score = event.get("score")
        receipt = SpecTaskGateReceipt(
            task_id=task_id,
            severity=str(event.get("severity", "")),
            score=score,  # type: ignore[arg-type]
            probes=probes,
            detail=str(event.get("detail", "")),
        )
        pending_gate = replace(state, stage="task_gate", task_receipt=receipt)
        if state.auto_run and receipt.severity != "high":
            return self._complete_task(pending_gate, disposition="auto")
        return CommandWorkspaceTransition(pending_gate)

    def _apply_task_gate(
        self,
        state: SpecWorkspaceState,
        response: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition:
        receipt = state.task_receipt
        if receipt is None or not state.current:
            raise CommandWorkspaceError(["Spec task gate has no current receipt"])
        action = response.action
        legal = (
            {"fix_retry", "acknowledge_risk"}
            if receipt.severity == "high"
            else {"approve_task", "redo_task", "auto_run_remaining"}
        )
        if action not in legal:
            raise CommandWorkspaceError(["Spec task decision is not legal for this severity"])
        if action in {"acknowledge_risk", "auto_run_remaining"} and not response.confirmed:
            raise CommandWorkspaceError(["Spec task decision requires explicit confirmation"])
        if action in {"fix_retry", "redo_task"}:
            return CommandWorkspaceTransition(
                replace(state, stage="executing", task_receipt=None, progress_detail=""),
                result={"delegate": "spec.retry_task", "task_id": state.current},
            )
        if action == "auto_run_remaining":
            state = replace(state, auto_run=True)
        return self._complete_task(state, disposition=action)

    def _complete_task(
        self,
        state: SpecWorkspaceState,
        *,
        disposition: str,
    ) -> CommandWorkspaceTransition:
        completed = (*state.completed, state.current)
        terminal = len(completed) == len(state.task_ids)
        successor = replace(
            state,
            stage="receipt" if terminal else "executing",
            completed=completed,
            current="",
            task_receipt=None,
            progress_detail="",
        )
        return CommandWorkspaceTransition(
            successor,
            terminal=terminal,
            result={
                "disposition": disposition,
                "completed": list(completed),
                "save_state": {
                    "plan_path": state.plan_path,
                    "completed": list(completed),
                    "auto_run": successor.auto_run,
                },
            },
        )

    def _view_data(self, state: SpecWorkspaceState) -> dict[str, object]:
        if state.stage == "preview":
            collision = state.slug in state.taken_slugs if state.slug else False
            return {
                "id": "preview",
                "title": "Spec creation preview",
                "summary": "Review the exact contract before creating artifacts.",
                "sections": [
                    {
                        "heading": "Session contract",
                        "tone": "warning" if collision else "recommendation",
                        "blocks": [
                            {"kind": "disclosure", "title": "Contract", "body": state.contract},
                            {
                                "kind": "action_list",
                                "items": [
                                    {"label": option, "detail": "tree-derived area"}
                                    for option in (*state.area_options, OTHER)
                                ],
                            },
                        ],
                    }
                ],
                "actions": [
                    {"id": "edit_spec", "label": "Edit intake"},
                    {
                        "id": "create_spec",
                        "label": "Create spec",
                        "consequence": "Authorize creation from this exact contract.",
                        "requires_explicit_choice": True,
                    },
                ],
            }
        if state.stage == "intake":
            return {"id": "intake", "title": "Spec intake", "summary": "Submit revised intake."}
        if state.stage in {"creating", "gate_running", "executing"}:
            progress = len(state.completed)
            total = len(state.task_ids)
            return {
                "id": "execution",
                "title": "Spec in progress",
                "summary": state.progress_detail or f"{progress}/{total} tasks approved.",
                "sections": [
                    {
                        "heading": "Canonical progress",
                        "blocks": [
                            {
                                "kind": "key_value",
                                "items": [
                                    {"label": "Plan", "value": state.plan_path or "creating"},
                                    {"label": "Current task", "value": state.current or "none"},
                                    {"label": "Boundary", "value": state.gate_boundary or "none"},
                                ],
                            }
                        ],
                    }
                ],
            }
        if state.stage == "review":
            return {
                "id": "execution",
                "title": "Spec review",
                "summary": f"Review {len(state.task_ids)} parsed XML tasks.",
                "sections": [self._artifact_section(state)],
                "actions": [
                    {"id": "redo_plan", "label": "Redo plan"},
                    {"id": "approve_plan", "label": "Approve plan"},
                ],
            }
        if state.stage == "approval":
            return {
                "id": "execution",
                "title": "Spec execution approval",
                "summary": f"{len(state.pending)} tasks remain.",
                "actions": [
                    {"id": "redo_plan", "label": "Back to plan"},
                    {
                        "id": "start_execution",
                        "label": "Start execution",
                        "consequence": "Run the execution lifecycle boundary before any task.",
                        "requires_explicit_choice": True,
                    },
                ],
            }
        if state.stage == "chair_required":
            return {
                "id": "execution",
                "title": "Spec lifecycle acknowledgment",
                "summary": "A CHAIR_REQUIRED receipt must be acknowledged before advancing.",
                "sections": [self._lifecycle_section(state)],
                "actions": [
                    {
                        "id": "acknowledge_gate",
                        "label": "Acknowledge and continue",
                        "consequence": "Record chair acknowledgment of these exact receipts.",
                        "requires_explicit_choice": True,
                    }
                ],
            }
        if state.stage == "blocked":
            return {
                "id": "execution",
                "title": "Spec lifecycle blocked",
                "summary": state.blocked_reason,
                "sections": [self._lifecycle_section(state)],
                "actions": [{"id": "retry_gate", "label": "Fix and rerun gate"}],
            }
        if state.stage == "task_gate":
            receipt = state.task_receipt
            assert receipt is not None
            high = receipt.severity == "high"
            actions = (
                [
                    {"id": "fix_retry", "label": "Fix and retry"},
                    {
                        "id": "acknowledge_risk",
                        "label": "Acknowledge risk and continue",
                        "consequence": "Move this high-severity risk downstream.",
                        "requires_explicit_choice": True,
                    },
                ]
                if high
                else [
                    {"id": "approve_task", "label": "Approve and continue"},
                    {"id": "redo_task", "label": "Redo task"},
                    {
                        "id": "auto_run_remaining",
                        "label": "Auto-run remaining tasks",
                        "consequence": "Approve later non-high task receipts automatically.",
                        "requires_explicit_choice": True,
                    },
                ]
            )
            return {
                "id": "execution",
                "title": f"Task {receipt.task_id} gate",
                "summary": f"{receipt.severity} severity, score {receipt.score:g}.",
                "sections": [
                    {
                        "heading": "Failure-sensitive receipt",
                        "tone": "danger" if high else "recommendation",
                        "blocks": [
                            {"kind": "disclosure", "title": "Finding", "body": receipt.detail},
                            {
                                "kind": "action_list",
                                "items": [{"label": probe} for probe in receipt.probes],
                            },
                        ],
                    }
                ],
                "actions": actions,
            }
        return {
            "id": "receipt",
            "title": "Spec receipt",
            "summary": "Terminal record of approved tasks, artifacts, and probes.",
            "sections": [self._artifact_section(state)],
        }

    @staticmethod
    def _artifact_section(state: SpecWorkspaceState) -> dict[str, object]:
        return {
            "heading": "Artifacts and probes",
            "tone": "success",
            "blocks": [
                {
                    "kind": "evidence",
                    "items": [
                        {"label": artifact.kind, "value": artifact.path, "status": "complete"}
                        for artifact in state.artifacts
                    ],
                },
                {"kind": "action_list", "items": [{"label": probe} for probe in state.probes]},
            ],
        }

    @staticmethod
    def _lifecycle_section(state: SpecWorkspaceState) -> dict[str, object]:
        return {
            "heading": f"{state.gate_boundary} lifecycle receipts",
            "tone": "danger" if state.stage == "blocked" else "warning",
            "blocks": [
                {
                    "kind": "evidence",
                    "items": [
                        {
                            "label": receipt.gate_id,
                            "value": receipt.detail,
                            "status": "failed" if receipt.state == "BLOCKED" else "warning",
                        }
                        for receipt in state.lifecycle_receipts
                    ],
                }
            ],
        }
