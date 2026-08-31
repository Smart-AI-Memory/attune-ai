"""Shared-renderer adapter for read-only bug prediction reports."""

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

_SEVERITIES = frozenset({"HIGH", "MEDIUM", "LOW"})


def _risk_score_problem(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return "Bug prediction risk_score must be between 0 and 100"
    if not 0 <= value <= 100:
        return "Bug prediction risk_score must be between 0 and 100"
    return ""


@dataclass(frozen=True)
class BugFindingReceipt:
    """One exact read-only bug prediction finding."""

    path: str
    line: int
    pattern: str
    severity: str
    description: str

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise CommandWorkspaceError(["Bug finding path must not be empty"])
        if isinstance(self.line, bool) or not isinstance(self.line, int) or self.line < 1:
            raise CommandWorkspaceError(["Bug finding line must be a positive integer"])
        if not self.pattern.strip():
            raise CommandWorkspaceError(["Bug finding pattern must not be empty"])
        if self.severity not in _SEVERITIES:
            raise CommandWorkspaceError(["Bug finding severity is invalid"])
        if not self.description.strip():
            raise CommandWorkspaceError(["Bug finding description must not be empty"])


@dataclass(frozen=True)
class BugPredictWorkspaceState:
    """Bug-predict-owned running or terminal report state."""

    target_path: str
    severity_filter: str
    stage: str = "running"
    progress_detail: str = "Starting read-only analysis."
    success: bool | None = None
    risk_score: float | None = None
    findings: tuple[BugFindingReceipt, ...] = ()
    suggestions: tuple[str, ...] = ()
    error: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", tuple(self.findings))
        object.__setattr__(self, "suggestions", tuple(self.suggestions))
        problems: list[str] = []
        if not self.target_path.strip():
            problems.append("Bug prediction target_path must not be empty")
        if self.severity_filter not in {"all", "high"}:
            problems.append("Bug prediction severity_filter is invalid")
        if self.stage not in {"running", "receipt"}:
            problems.append("Bug prediction stage is invalid")
        if self.stage == "receipt" and self.success is None:
            problems.append("Bug prediction receipt requires a success result")
        score_problem = _risk_score_problem(self.risk_score)
        if score_problem:
            problems.append(score_problem)
        if self.success is False and not self.error.strip():
            problems.append("Failed bug prediction requires an error receipt")
        if self.success is True and self.risk_score is None:
            problems.append("Successful bug prediction requires a risk_score")
        if self.success is True and self.error:
            problems.append("Successful bug prediction cannot carry an error")
        if any(not item.strip() for item in self.suggestions):
            problems.append("Bug prediction suggestions must not be empty")
        if problems:
            raise CommandWorkspaceError(problems)


def _finding(raw: Mapping[str, object]) -> BugFindingReceipt:
    line = raw.get("line")
    return BugFindingReceipt(
        path=raw.get("path", "") if isinstance(raw.get("path", ""), str) else "",
        line=line,  # type: ignore[arg-type]
        pattern=(raw.get("pattern", "") if isinstance(raw.get("pattern", ""), str) else ""),
        severity=str(raw.get("severity", "")).upper(),
        description=(
            raw.get("description", "") if isinstance(raw.get("description", ""), str) else ""
        ),
    )


class BugPredictWorkspaceAdapter:
    """Immediate read-only execution with a truthful terminal report."""

    adapter_id = "bug-predict"
    schema_version = 1

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> BugPredictWorkspaceState:
        """Validate a target and enter running state without confirmation."""
        if prior_state is not None:
            raise CommandWorkspaceError(["Bug prediction workspaces cannot be replaced"])
        allowed = {"path", "severity_filter"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError(
                [f"unknown bug-predict intake key {key!r}" for key in unknown]
            )
        raw_path_value = intake.get("path", "src/")
        if not isinstance(raw_path_value, str):
            raise CommandWorkspaceError(["Bug prediction path must be a string"])
        raw_path = raw_path_value.strip()
        candidate = (self.repo_root / raw_path).resolve()
        try:
            relative = candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise CommandWorkspaceError(["Bug prediction path escapes the repository"]) from exc
        validated = _validate_file_path(str(candidate), str(self.repo_root))
        if not validated.exists():
            raise CommandWorkspaceError(["Bug prediction path does not exist"])
        return BugPredictWorkspaceState(
            target_path=relative.as_posix() or ".",
            severity_filter=str(intake.get("severity_filter", "all")).lower(),
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render running progress or the terminal report."""
        if not isinstance(state, BugPredictWorkspaceState):
            raise CommandWorkspaceError(["bug-predict adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "stage": state.stage,
            "target": state.target_path,
            "filter": state.severity_filter,
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
        """Reject client actions: invocation already authorized this read-only run."""
        raise CommandWorkspaceError(["bug-predict is read-only and has no confirmation actions"])

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish progress or one truthful terminal scan receipt."""
        if not isinstance(state, BugPredictWorkspaceState):
            raise CommandWorkspaceError(["bug-predict adapter received incompatible state"])
        if state.stage != "running":
            raise CommandWorkspaceError(["terminal bug prediction cannot accept events"])
        kind = event.get("kind")
        if kind == "progress":
            detail = str(event.get("detail", "")).strip()
            if not detail:
                raise CommandWorkspaceError(["Bug prediction progress detail is required"])
            return CommandWorkspaceTransition(
                replace(state, progress_detail=detail),
                authority_changed=False,
            )
        if kind == "scan_result":
            success = event.get("success")
            if not isinstance(success, bool):
                raise CommandWorkspaceError(["Bug prediction success must be boolean"])
            raw_findings = event.get("findings", ())
            if not isinstance(raw_findings, Sequence) or isinstance(raw_findings, str | bytes):
                raise CommandWorkspaceError(["Bug prediction findings must be a list"])
            findings = tuple(_finding(raw) for raw in raw_findings if isinstance(raw, Mapping))
            if len(findings) != len(raw_findings):
                raise CommandWorkspaceError(["Bug prediction finding must be a mapping"])
            if state.severity_filter == "high":
                findings = tuple(item for item in findings if item.severity == "HIGH")
            raw_suggestions = event.get("suggestions", ())
            if not isinstance(raw_suggestions, Sequence) or isinstance(
                raw_suggestions, str | bytes
            ):
                raise CommandWorkspaceError(["Bug prediction suggestions must be a list"])
            if any(not isinstance(item, str) for item in raw_suggestions):
                raise CommandWorkspaceError(["Bug prediction suggestion must be text"])
            suggestions = tuple(item.strip() for item in raw_suggestions)
            error = str(event.get("error", "")).strip()
            score = event.get("risk_score")
            successor = BugPredictWorkspaceState(
                target_path=state.target_path,
                severity_filter=state.severity_filter,
                stage="receipt",
                progress_detail="",
                success=success,
                risk_score=score,  # type: ignore[arg-type]
                findings=findings,
                suggestions=suggestions,
                error=error,
            )
            return CommandWorkspaceTransition(
                successor,
                terminal=True,
                result={
                    "success": success,
                    "finding_count": len(findings),
                    "risk_score": successor.risk_score,
                    "error": error,
                },
            )
        raise CommandWorkspaceError([f"unknown bug-predict event {kind!r}"])

    @staticmethod
    def _view_data(state: BugPredictWorkspaceState) -> dict[str, object]:
        if state.stage == "running":
            return {
                "id": "execution",
                "title": "Bug prediction running",
                "summary": state.progress_detail,
                "sections": [
                    {
                        "heading": "Read-only scope",
                        "blocks": [
                            {
                                "kind": "key_value",
                                "items": [
                                    {"label": "Path", "value": state.target_path},
                                    {"label": "Filter", "value": state.severity_filter},
                                ],
                            }
                        ],
                    }
                ],
            }
        if state.success is False:
            return {
                "id": "receipt",
                "title": "Bug prediction did not complete",
                "summary": state.error,
                "sections": [
                    {
                        "heading": "Failure receipt",
                        "tone": "danger",
                        "blocks": [{"kind": "disclosure", "title": "Error", "body": state.error}],
                    }
                ],
            }
        findings = sorted(
            state.findings,
            key=lambda item: (
                {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[item.severity],
                item.path,
                item.line,
            ),
        )
        finding_block: dict[str, object]
        if findings:
            finding_block = {
                "kind": "evidence",
                "items": [
                    {
                        "label": f"{finding.severity} {finding.pattern}",
                        "value": f"{finding.path}:{finding.line} — {finding.description}",
                        "status": "failed" if finding.severity == "HIGH" else "warning",
                    }
                    for finding in findings
                ],
            }
        else:
            finding_block = {
                "kind": "disclosure",
                "title": "Findings",
                "body": "No findings matched the selected severity filter.",
            }
        blocks: list[dict[str, object]] = [finding_block]
        if state.suggestions:
            blocks.append(
                {
                    "kind": "action_list",
                    "items": [{"label": item} for item in state.suggestions],
                }
            )
        return {
            "id": "receipt",
            "title": "Bug prediction receipt",
            "summary": f"Risk score {state.risk_score:g}; {len(findings)} findings.",
            "sections": [
                {
                    "heading": "Predicted bugs",
                    "tone": "warning" if findings else "success",
                    "blocks": blocks,
                }
            ],
        }
