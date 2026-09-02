"""Shared-renderer adapter for multi-gate release preparation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace

from attune_forms import WorkspaceActionResponse, workspace_from_dict

from attune.elicitation.command_workspace import (
    CommandWorkspaceError,
    CommandWorkspaceProjection,
    CommandWorkspaceTransition,
)

GATE_ORDER = ("Security", "Testing", "Documentation", "Versioning")
_CRITICAL_GATES = frozenset({"Security", "Testing", "Versioning"})
_STATUSES = frozenset({"PASS", "FAIL", "ERROR", "MISSING"})
_STAGES = frozenset({"preview", "intake", "running", "gate_review", "approval", "receipt"})


@dataclass(frozen=True)
class ReleaseGateReceipt:
    """One gatekeeper result; success is derived rather than trusted."""

    name: str
    status: str
    detail: str
    probe: str

    def __post_init__(self) -> None:
        if self.name not in GATE_ORDER:
            raise CommandWorkspaceError(["Release gate name is invalid"])
        if self.status not in _STATUSES:
            raise CommandWorkspaceError(["Release gate status is invalid"])
        if not self.detail.strip():
            raise CommandWorkspaceError(["Release gate detail must not be empty"])
        if not self.probe.strip():
            raise CommandWorkspaceError(["Release gate probe must not be empty"])

    @property
    def passed(self) -> bool:
        """Return true only for an explicit PASS receipt."""
        return self.status == "PASS"

    @property
    def critical(self) -> bool:
        """Return whether this gate can block final release approval."""
        return self.name in _CRITICAL_GATES


@dataclass(frozen=True)
class ReleasePrepWorkspaceState:
    """Release-prep-owned canonical state."""

    version: str
    scope: str
    project_path: str
    stage: str = "preview"
    gates: tuple[ReleaseGateReceipt, ...] = ()
    accepted_gates: tuple[str, ...] = ()
    review_gate: str = ""
    recommendations: tuple[str, ...] = ()
    final_approved: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "gates", tuple(self.gates))
        object.__setattr__(self, "accepted_gates", tuple(self.accepted_gates))
        object.__setattr__(self, "recommendations", tuple(self.recommendations))
        problems: list[str] = []
        if not self.version.strip():
            problems.append("Release version must not be empty")
        if self.scope not in {"full", "security", "testing", "documentation", "versioning"}:
            problems.append("Release scope is invalid")
        if not self.project_path.strip():
            problems.append("Release project_path must not be empty")
        if self.stage not in _STAGES:
            problems.append("Release workspace stage is invalid")
        gate_names = [gate.name for gate in self.gates]
        if len(gate_names) != len(set(gate_names)):
            problems.append("Release gate receipts must be unique")
        if not set(self.accepted_gates).issubset(GATE_ORDER):
            problems.append("Release accepted gate is invalid")
        if self.review_gate and self.review_gate not in GATE_ORDER:
            problems.append("Release review gate is invalid")
        if problems:
            raise CommandWorkspaceError(problems)

    def gate(self, name: str) -> ReleaseGateReceipt | None:
        """Return the current receipt for a named gate."""
        return next((gate for gate in self.gates if gate.name == name), None)

    @property
    def blockers(self) -> tuple[ReleaseGateReceipt, ...]:
        """Return critical non-passing gatekeeper receipts."""
        return tuple(gate for gate in self.gates if gate.critical and not gate.passed)


def _gate_receipt(raw: Mapping[str, object]) -> ReleaseGateReceipt:
    return ReleaseGateReceipt(
        name=str(raw.get("name", "")),
        status=str(raw.get("status", "")),
        detail=str(raw.get("detail", "")),
        probe=str(raw.get("probe", "")),
    )


class ReleasePrepWorkspaceAdapter:
    """Repeated release gates plus final go/no-go authority."""

    adapter_id = "release-prep"
    schema_version = 1

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> ReleasePrepWorkspaceState:
        """Create or explicitly replace a release preparation preview."""
        if prior_state is not None and (
            not isinstance(prior_state, ReleasePrepWorkspaceState) or prior_state.stage != "intake"
        ):
            raise CommandWorkspaceError(["select edit_release before replacing release intake"])
        allowed = {"version", "scope", "project_path"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError(
                [f"unknown release-prep intake key {key!r}" for key in unknown]
            )
        return ReleasePrepWorkspaceState(
            version=str(intake.get("version", "check")).strip(),
            scope=str(intake.get("scope", "full")).lower(),
            project_path=str(intake.get("project_path", ".")).strip(),
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Project the current release checkpoint."""
        if not isinstance(state, ReleasePrepWorkspaceState):
            raise CommandWorkspaceError(["release-prep adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "stage": state.stage,
            "release": state.version,
            "gates": [(gate.name, gate.status) for gate in state.gates],
            "accepted": state.accepted_gates,
            "review_gate": state.review_gate,
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
        """Apply one start, gate, retry, or final approval decision."""
        if not isinstance(state, ReleasePrepWorkspaceState):
            raise CommandWorkspaceError(["release-prep adapter received incompatible state"])
        action = response.action
        if state.stage == "preview":
            if action == "edit_release":
                return CommandWorkspaceTransition(replace(state, stage="intake"))
            if action == "start_release_prep":
                return CommandWorkspaceTransition(
                    replace(state, stage="running"),
                    result={"delegate": "release-prep.run", "scope": state.scope},
                )
        if state.stage == "gate_review":
            return self._apply_gate_review(state, response)
        if state.stage == "approval":
            if action == "rerun_all":
                return CommandWorkspaceTransition(
                    replace(
                        state,
                        stage="running",
                        gates=(),
                        accepted_gates=(),
                        review_gate="",
                    ),
                    result={"delegate": "release-prep.run", "scope": state.scope},
                )
            if action == "approve_release":
                if state.blockers:
                    raise CommandWorkspaceError(
                        ["Release approval is blocked by a critical gatekeeper"]
                    )
                if not response.confirmed:
                    raise CommandWorkspaceError(["Release approval requires explicit confirmation"])
                return CommandWorkspaceTransition(
                    replace(state, stage="receipt", final_approved=True),
                    terminal=True,
                    result={
                        "approved": True,
                        "version": state.version,
                        "gate_receipts": [gate.name for gate in state.gates],
                    },
                )
        raise CommandWorkspaceError(
            [f"release-prep action {action!r} is not legal in stage {state.stage!r}"]
        )

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish deterministic gatekeeper progress and completion."""
        if not isinstance(state, ReleasePrepWorkspaceState):
            raise CommandWorkspaceError(["release-prep adapter received incompatible state"])
        kind = event.get("kind")
        if kind == "gate_result":
            return self._publish_gate_result(state, event)
        if kind == "assessment_complete":
            return self._publish_assessment_complete(state, event)
        raise CommandWorkspaceError([f"unknown release-prep event {kind!r}"])

    @staticmethod
    def _publish_gate_result(
        state: ReleasePrepWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        if state.stage != "running":
            raise CommandWorkspaceError(["Release gate result requires running stage"])
        raw = event.get("receipt")
        if not isinstance(raw, Mapping):
            raise CommandWorkspaceError(["Release gate result requires receipt mapping"])
        receipt = _gate_receipt(raw)
        retained = tuple(gate for gate in state.gates if gate.name != receipt.name)
        return CommandWorkspaceTransition(
            replace(state, gates=(*retained, receipt)),
            result={"gate": receipt.name, "status": receipt.status},
            authority_changed=False,
        )

    @staticmethod
    def _publish_assessment_complete(
        state: ReleasePrepWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        if state.stage != "running":
            raise CommandWorkspaceError(["Release completion requires running stage"])
        gates = list(state.gates)
        present = {gate.name for gate in gates}
        for name in GATE_ORDER:
            if name not in present:
                gates.append(
                    ReleaseGateReceipt(
                        name,
                        "MISSING",
                        "gatekeeper did not return a receipt",
                        "no probe receipt",
                    )
                )
        ordered = tuple(sorted(gates, key=lambda gate: GATE_ORDER.index(gate.name)))
        recommendations_raw = event.get("recommendations", [])
        if not isinstance(recommendations_raw, list) or any(
            not str(item).strip() for item in recommendations_raw
        ):
            raise CommandWorkspaceError(["Release recommendations must be a list"])
        review_gate = next(
            (name for name in GATE_ORDER if name not in state.accepted_gates),
            "",
        )
        return CommandWorkspaceTransition(
            replace(
                state,
                stage="gate_review" if review_gate else "approval",
                gates=ordered,
                review_gate=review_gate,
                recommendations=tuple(str(item) for item in recommendations_raw),
            ),
            result={
                "blocker_count": len(
                    [gate for gate in ordered if gate.critical and not gate.passed]
                )
            },
        )

    def _apply_gate_review(
        self,
        state: ReleasePrepWorkspaceState,
        response: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition:
        gate = state.gate(state.review_gate)
        if gate is None:
            raise CommandWorkspaceError(["Release gate review has no current receipt"])
        if response.action == "rerun_gate":
            retained = tuple(item for item in state.gates if item.name != gate.name)
            return CommandWorkspaceTransition(
                replace(state, stage="running", gates=retained, review_gate=""),
                result={"delegate": "release-prep.rerun_gate", "gate": gate.name},
            )
        if gate.passed and response.action == "accept_gate":
            return self._accept_gate(state, gate.name)
        if not gate.passed and not gate.critical and response.action == "accept_warning":
            if not response.confirmed:
                raise CommandWorkspaceError(
                    ["Release warning acceptance requires explicit confirmation"]
                )
            return self._accept_gate(state, gate.name)
        if gate.passed:
            raise CommandWorkspaceError(
                [f"Release gate action {response.action!r} is not legal for a passed gate"]
            )
        if not gate.critical:
            raise CommandWorkspaceError(
                [
                    f"Release gate action {response.action!r} is not legal "
                    "for a non-critical failed gate"
                ]
            )
        raise CommandWorkspaceError(
            ["Failed critical gatekeeper cannot be accepted; rerun it after fixing"]
        )

    @staticmethod
    def _accept_gate(
        state: ReleasePrepWorkspaceState,
        gate_name: str,
    ) -> CommandWorkspaceTransition:
        accepted = (*state.accepted_gates, gate_name)
        next_gate = next((name for name in GATE_ORDER if name not in accepted), "")
        return CommandWorkspaceTransition(
            replace(
                state,
                stage="gate_review" if next_gate else "approval",
                accepted_gates=accepted,
                review_gate=next_gate,
            ),
            result={"accepted_gate": gate_name, "remaining": len(GATE_ORDER) - len(accepted)},
        )

    def _view_data(self, state: ReleasePrepWorkspaceState) -> dict[str, object]:
        if state.stage == "preview":
            return {
                "id": "preview",
                "title": "Release preparation preview",
                "summary": f"Version {state.version}; {state.scope} advisory.",
                "sections": [
                    {
                        "heading": "Gatekeepers",
                        "blocks": [
                            {
                                "kind": "action_list",
                                "items": [{"label": name} for name in GATE_ORDER],
                            }
                        ],
                    }
                ],
                "actions": [
                    {"id": "edit_release", "label": "Edit release"},
                    {
                        "id": "start_release_prep",
                        "label": "Run release prep",
                        "consequence": "Run the selected release checks.",
                        "requires_explicit_choice": True,
                    },
                ],
            }
        if state.stage == "intake":
            return {"id": "intake", "title": "Release intake", "summary": "Submit revised scope."}
        if state.stage == "running":
            return {
                "id": "execution",
                "title": "Release checks running",
                "summary": f"{len(state.gates)}/{len(GATE_ORDER)} gatekeeper receipts recorded.",
                "sections": [self._gate_section(state.gates)],
            }
        if state.stage == "gate_review":
            gate = state.gate(state.review_gate)
            if gate is None:
                raise CommandWorkspaceError(["Release gate review has no current receipt"])
            actions = [{"id": "rerun_gate", "label": "Fix and rerun gate"}]
            if gate.passed:
                actions.insert(0, {"id": "accept_gate", "label": "Accept gate"})
            elif not gate.critical:
                actions.insert(
                    0,
                    {
                        "id": "accept_warning",
                        "label": "Accept warning",
                        "consequence": "Carry this non-critical warning into the release receipt.",
                        "requires_explicit_choice": True,
                    },
                )
            return {
                "id": "execution",
                "title": f"Release gate: {gate.name}",
                "summary": f"{gate.status}: {gate.detail}",
                "sections": [self._gate_section((gate,))],
                "actions": actions,
            }
        if state.stage == "approval":
            return {
                "id": "execution",
                "title": "Release go/no-go",
                "summary": "All four gatekeeper receipts were reviewed.",
                "sections": [self._gate_section(state.gates)],
                "actions": [
                    {"id": "rerun_all", "label": "Rerun all checks"},
                    {
                        "id": "approve_release",
                        "label": "Approve release",
                        "consequence": f"Record version {state.version} as release-ready.",
                        "requires_explicit_choice": True,
                    },
                ],
            }
        return {
            "id": "receipt",
            "title": "Release readiness receipt",
            "summary": f"Version {state.version} approved: {state.final_approved}.",
            "sections": [self._gate_section(state.gates)],
        }

    @staticmethod
    def _gate_section(gates: tuple[ReleaseGateReceipt, ...]) -> dict[str, object]:
        if not gates:
            return {
                "heading": "Gate receipts",
                "tone": "recommendation",
                "blocks": [
                    {
                        "kind": "action_list",
                        "items": [
                            {"label": name, "detail": "awaiting receipt"} for name in GATE_ORDER
                        ],
                    }
                ],
            }
        return {
            "heading": "Gate receipts",
            "tone": "recommendation",
            "blocks": [
                {
                    "kind": "evidence",
                    "items": [
                        {
                            "label": gate.name,
                            "value": f"{gate.status}: {gate.detail} ({gate.probe})",
                            "status": "complete" if gate.passed else "failed",
                        }
                        for gate in gates
                    ],
                }
            ],
        }
