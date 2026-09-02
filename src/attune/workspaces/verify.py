"""Shared-renderer adapter for deterministic claim verification."""

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

_KINDS = frozenset({"unresolved_import", "unknown_flag", "dead_link", "count_mismatch"})
_SEVERITIES = frozenset({"error", "warning"})


@dataclass(frozen=True)
class VerificationFinding:
    """One claim with its exact evidence and source location."""

    layer: str
    kind: str
    severity: str
    detail: str
    evidence: str
    location: str

    def __post_init__(self) -> None:
        problems: list[str] = []
        if self.layer not in {"deterministic", "cross_check"}:
            problems.append("Verification finding layer is invalid")
        if self.layer == "deterministic" and self.kind not in _KINDS:
            problems.append("Deterministic verification kind is invalid")
        if self.layer == "cross_check" and self.kind != "semantic_cross_check":
            problems.append("Cross-check verification kind is invalid")
        if self.severity not in _SEVERITIES:
            problems.append("Verification finding severity is invalid")
        if self.layer == "cross_check" and self.severity != "warning":
            problems.append("Ambient cross-check findings must remain warnings")
        if not self.detail.strip() or not self.evidence.strip() or not self.location.strip():
            problems.append("Verification detail, evidence, and location are required")
        if problems:
            raise CommandWorkspaceError(problems)

    def to_dict(self) -> dict[str, str]:
        """Return the full evidence chain for terminal results."""
        return {
            "layer": self.layer,
            "kind": self.kind,
            "severity": self.severity,
            "detail": self.detail,
            "evidence": self.evidence,
            "location": self.location,
        }


@dataclass(frozen=True)
class VerifyWorkspaceState:
    """Verify-owned deterministic and ambient cross-check state."""

    target_path: str
    hard_gate: bool
    stage: str = "running"
    checked: tuple[str, ...] = ()
    deterministic_ok: bool | None = None
    deterministic_findings: tuple[VerificationFinding, ...] = ()
    cross_check_findings: tuple[VerificationFinding, ...] = ()
    completed: bool = False
    error: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "deterministic_findings", tuple(self.deterministic_findings))
        object.__setattr__(self, "cross_check_findings", tuple(self.cross_check_findings))
        object.__setattr__(self, "checked", tuple(self.checked))
        problems: list[str] = []
        if not self.target_path.strip():
            problems.append("Verify target_path must not be empty")
        if not isinstance(self.hard_gate, bool):
            problems.append("Verify hard_gate must be boolean")
        if self.stage not in {"running", "cross_check", "receipt"}:
            problems.append("Verify stage is invalid")
        if any(not item.strip() for item in self.checked) or len(self.checked) != len(
            set(self.checked)
        ):
            problems.append("Verify checked categories must be non-empty and unique")
        if any(item.layer != "deterministic" for item in self.deterministic_findings):
            problems.append("Verify deterministic finding layer is invalid")
        if any(item.layer != "cross_check" for item in self.cross_check_findings):
            problems.append("Verify cross-check finding layer is invalid")
        if self.completed and self.deterministic_ok is None:
            problems.append("Completed verification requires deterministic outcome")
        if self.error and self.completed:
            problems.append("Failed verification cannot be marked completed")
        if problems:
            raise CommandWorkspaceError(problems)


def _finding(raw: Mapping[str, object], *, layer: str) -> VerificationFinding:
    return VerificationFinding(
        layer=layer,
        kind=(str(raw.get("kind", "")) if layer == "deterministic" else "semantic_cross_check"),
        severity=(str(raw.get("severity", "")).lower() if layer == "deterministic" else "warning"),
        detail=str(raw.get("detail", "")),
        evidence=str(raw.get("evidence", "")),
        location=str(raw.get("location", "")),
    )


class VerifyWorkspaceAdapter:
    """Run authoritative checkers first, then a non-authoritative cross-check."""

    adapter_id = "verify"
    schema_version = 1

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> VerifyWorkspaceState:
        """Validate the generated content path and enter immediate read-only work."""
        if prior_state is not None:
            raise CommandWorkspaceError(["Verify workspaces cannot be replaced"])
        allowed = {"path", "hard_gate"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError([f"unknown verify intake key {key!r}" for key in unknown])
        candidate = (self.repo_root / str(intake.get("path", ""))).resolve()
        try:
            relative = candidate.relative_to(self.repo_root).as_posix()
        except ValueError as exc:
            raise CommandWorkspaceError(["Verify path escapes the repository"]) from exc
        validated = _validate_file_path(str(candidate), str(self.repo_root))
        if not validated.is_file():
            raise CommandWorkspaceError(["Verify target path does not exist"])
        hard_gate = intake.get("hard_gate", False)
        if not isinstance(hard_gate, bool):
            raise CommandWorkspaceError(["Verify hard_gate must be boolean"])
        return VerifyWorkspaceState(target_path=relative, hard_gate=hard_gate)

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render checker progress or a claim-by-claim terminal report."""
        if not isinstance(state, VerifyWorkspaceState):
            raise CommandWorkspaceError(["verify adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "target": state.target_path,
            "hard_gate": state.hard_gate,
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
        """Reject actions because verification is read-only and already authorized."""
        raise CommandWorkspaceError(["verify is read-only and has no actions"])

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish deterministic results followed by a labeled ambient cross-check."""
        if not isinstance(state, VerifyWorkspaceState):
            raise CommandWorkspaceError(["verify adapter received incompatible state"])
        kind = event.get("kind")
        if state.stage == "running" and kind == "deterministic_result":
            return self._deterministic_result(state, event)
        if state.stage == "cross_check" and kind == "cross_check_result":
            return self._cross_check_result(state, event)
        raise CommandWorkspaceError(["Verification receipt is not legal in the current stage"])

    def _deterministic_result(
        self,
        state: VerifyWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Deterministic verification success must be boolean"])
        if not success:
            return self._failure(state, str(event.get("error", "")).strip())
        ok = event.get("ok")
        checked = event.get("checked")
        raw_findings = event.get("findings", ())
        if not isinstance(ok, bool):
            raise CommandWorkspaceError(["Deterministic verification ok must be boolean"])
        if not isinstance(checked, Sequence) or isinstance(checked, str | bytes):
            raise CommandWorkspaceError(["Deterministic checked must be a list"])
        checked_categories = tuple(str(item).strip() for item in checked)
        if any(not item for item in checked_categories) or len(checked_categories) != len(
            set(checked_categories)
        ):
            raise CommandWorkspaceError(
                ["Deterministic checked categories must be non-empty and unique"]
            )
        if not isinstance(raw_findings, Sequence) or isinstance(raw_findings, str | bytes):
            raise CommandWorkspaceError(["Deterministic findings must be a list"])
        findings = tuple(
            _finding(item, layer="deterministic")
            for item in raw_findings
            if isinstance(item, Mapping)
        )
        if len(findings) != len(raw_findings):
            raise CommandWorkspaceError(["Each deterministic finding must be a mapping"])
        derived_ok = not any(item.severity == "error" for item in findings)
        if ok != derived_ok:
            raise CommandWorkspaceError(["Deterministic ok disagrees with error findings"])
        return CommandWorkspaceTransition(
            replace(
                state,
                stage="cross_check",
                checked=checked_categories,
                deterministic_ok=ok,
                deterministic_findings=findings,
            ),
            result={"delegate": "verify.ambient_cross_check", "path": state.target_path},
        )

    def _cross_check_result(
        self,
        state: VerifyWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Ambient cross-check success must be boolean"])
        if not success:
            return self._failure(state, str(event.get("error", "")).strip())
        raw_findings = event.get("findings", ())
        if not isinstance(raw_findings, Sequence) or isinstance(raw_findings, str | bytes):
            raise CommandWorkspaceError(["Ambient cross-check findings must be a list"])
        findings = tuple(
            _finding(item, layer="cross_check")
            for item in raw_findings
            if isinstance(item, Mapping)
        )
        if len(findings) != len(raw_findings):
            raise CommandWorkspaceError(["Each ambient finding must be a mapping"])
        successor = replace(
            state,
            stage="receipt",
            cross_check_findings=findings,
            completed=True,
        )
        hard_gate_passed = state.deterministic_ok if state.hard_gate else None
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={
                "completed": True,
                "deterministic_ok": state.deterministic_ok,
                "hard_gate_passed": hard_gate_passed,
                "checked": list(state.checked),
                "findings": [item.to_dict() for item in (*state.deterministic_findings, *findings)],
                "error": "",
            },
        )

    @staticmethod
    def _failure(state: VerifyWorkspaceState, error: str) -> CommandWorkspaceTransition:
        if not error:
            raise CommandWorkspaceError(["Failed verification receipt requires error"])
        successor = replace(state, stage="receipt", completed=False, error=error)
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={
                "completed": False,
                "deterministic_ok": state.deterministic_ok,
                "hard_gate_passed": False if state.hard_gate else None,
                "checked": list(state.checked),
                "findings": [item.to_dict() for item in state.deterministic_findings],
                "error": error,
            },
        )

    @staticmethod
    def _finding_section(state: VerifyWorkspaceState) -> dict[str, object]:
        findings = (*state.deterministic_findings, *state.cross_check_findings)
        items = [
            {
                "label": f"{item.severity.upper()} · {item.kind}",
                "value": f"{item.detail} | {item.evidence} | {item.location} | {item.layer}",
                "status": "failed" if item.severity == "error" else "pending",
            }
            for item in findings
        ] or [{"label": "Findings", "value": "None", "status": "complete"}]
        return {"heading": "Claim evidence", "blocks": [{"kind": "evidence", "items": items}]}

    @classmethod
    def _view_data(cls, state: VerifyWorkspaceState) -> dict[str, object]:
        if state.stage == "running":
            return {
                "id": "execution",
                "title": "Deterministic verification running",
                "summary": f"Checking named entities in {state.target_path}.",
            }
        if state.stage == "cross_check":
            return {
                "id": "execution",
                "title": "Ambient semantic cross-check",
                "summary": (
                    f"Deterministic layer ran {len(state.checked)} checker categories; "
                    f"authoritative ok: {state.deterministic_ok}."
                ),
                "sections": [cls._finding_section(state)],
            }
        if state.error:
            summary = f"Verification did not complete: {state.error}"
        elif state.hard_gate and state.deterministic_ok is False:
            summary = "Verification completed; hard gate failed on deterministic errors."
        elif state.deterministic_ok is False:
            summary = "Verification completed with deterministic errors."
        else:
            summary = "Verification completed; deterministic checks passed."
        return {
            "id": "receipt",
            "title": "Verification receipt",
            "summary": summary,
            "sections": [cls._finding_section(state)],
        }
