"""Shared-renderer adapter for read-only security audit triage."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
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

_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
_REMEDIATION_SEVERITIES = frozenset({"CRITICAL", "HIGH"})


def _health_score_problem(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return "Security health score must be between 0 and 100"
    if not 0 <= value <= 100:
        return "Security health score must be between 0 and 100"
    return ""


@dataclass(frozen=True)
class SecurityFindingReceipt:
    """One exact categorized security finding."""

    path: str
    line: int
    severity: str
    category: str
    detail: str
    cwe: str = ""

    def __post_init__(self) -> None:
        problems: list[str] = []
        if not self.path.strip() or not self.category.strip() or not self.detail.strip():
            problems.append("Security finding path, category, and detail are required")
        if isinstance(self.line, bool) or not isinstance(self.line, int) or self.line < 1:
            problems.append("Security finding line must be a positive integer")
        if self.severity not in _SEVERITIES:
            problems.append("Security finding severity is invalid")
        if problems:
            raise CommandWorkspaceError(problems)

    def to_dict(self) -> dict[str, object]:
        """Return a Fix-handoff-safe finding receipt."""
        return {
            "path": self.path,
            "line": self.line,
            "severity": self.severity,
            "category": self.category,
            "detail": self.detail,
            "cwe": self.cwe,
        }


@dataclass(frozen=True)
class SecurityAuditWorkspaceState:
    """Security-audit-owned scan, pagination, and handoff state."""

    target_path: str
    focus: str
    stage: str = "running"
    health_score: float | None = None
    files_scanned: int = 0
    findings: tuple[SecurityFindingReceipt, ...] = ()
    review_index: int = 0
    success: bool | None = None
    handoff_prepared: bool = False
    error: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", tuple(self.findings))
        problems: list[str] = []
        if not self.target_path.strip() or not self.focus.strip():
            problems.append("Security target path and focus are required")
        if self.stage not in {"running", "review", "receipt"}:
            problems.append("Security workspace stage is invalid")
        score_problem = _health_score_problem(self.health_score)
        if score_problem:
            problems.append(score_problem)
        if isinstance(self.files_scanned, bool) or not isinstance(self.files_scanned, int):
            problems.append("Security files_scanned must be an integer")
        elif self.files_scanned < 0:
            problems.append("Security files_scanned must not be negative")
        remediation_count = len(self.remediation_findings)
        if self.stage == "review" and not 0 <= self.review_index < remediation_count:
            problems.append("Security review index is invalid")
        if self.success is False and not self.error.strip():
            problems.append("Failed security audit requires an error receipt")
        if self.success is True and self.error:
            problems.append("Successful security audit cannot carry an error")
        if self.handoff_prepared and self.success is not True:
            problems.append("Security handoff requires a successful scan")
        if problems:
            raise CommandWorkspaceError(problems)

    @property
    def remediation_findings(self) -> tuple[SecurityFindingReceipt, ...]:
        """Return critical/high findings in stable severity order."""
        return tuple(item for item in self.findings if item.severity in _REMEDIATION_SEVERITIES)


class SecurityAuditWorkspaceAdapter:
    """Immediate read-only scan with paginated, explicit Fix handoff."""

    adapter_id = "security-audit"
    schema_version = 1

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def _relative(self, raw_path: object, *, require_exists: bool = True) -> str:
        raw_text = str(raw_path).strip()
        if not raw_text:
            raise CommandWorkspaceError(["Security path must not be empty"])
        candidate = (self.repo_root / raw_text).resolve()
        try:
            relative = candidate.relative_to(self.repo_root).as_posix() or "."
        except ValueError as exc:
            raise CommandWorkspaceError(["Security path escapes the repository"]) from exc
        validated = _validate_file_path(str(candidate), str(self.repo_root))
        if require_exists and not validated.exists():
            raise CommandWorkspaceError(["Security path does not exist"])
        return relative

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> SecurityAuditWorkspaceState:
        """Validate scope and enter immediate read-only scan state."""
        if prior_state is not None:
            raise CommandWorkspaceError(["Security-audit workspaces cannot be replaced"])
        allowed = {"path", "focus"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError(
                [f"unknown security-audit intake key {key!r}" for key in unknown]
            )
        return SecurityAuditWorkspaceState(
            target_path=self._relative(intake.get("path", ".")),
            focus=str(intake.get("focus", "full sweep")).strip(),
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render scan progress, one high-risk finding, or a receipt."""
        if not isinstance(state, SecurityAuditWorkspaceState):
            raise CommandWorkspaceError(["security-audit adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "target": state.target_path,
            "stage": state.stage,
            "review_index": state.review_index,
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
        """Navigate high-risk findings or explicitly prepare a Fix handoff."""
        if not isinstance(state, SecurityAuditWorkspaceState):
            raise CommandWorkspaceError(["security-audit adapter received incompatible state"])
        if state.stage != "review":
            raise CommandWorkspaceError(["Security review action requires review stage"])
        if response.action == "previous_finding" and state.review_index > 0:
            return CommandWorkspaceTransition(replace(state, review_index=state.review_index - 1))
        if response.action == "next_finding" and state.review_index + 1 < len(
            state.remediation_findings
        ):
            return CommandWorkspaceTransition(replace(state, review_index=state.review_index + 1))
        if response.action == "finish_security_audit":
            return self._terminal(state)
        if response.action == "handoff_to_fix":
            terminal = self._terminal(replace(state, handoff_prepared=True))
            return replace(
                terminal,
                result={
                    **dict(terminal.result),
                    "delegate": "fix.open",
                    "findings": [item.to_dict() for item in state.remediation_findings],
                },
            )
        raise CommandWorkspaceError([f"Security review action {response.action!r} is not legal"])

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish one complete scan result; incomplete scans fail visibly."""
        if not isinstance(state, SecurityAuditWorkspaceState):
            raise CommandWorkspaceError(["security-audit adapter received incompatible state"])
        if state.stage != "running" or event.get("kind") != "scan_result":
            raise CommandWorkspaceError(["Security scan result requires running stage"])
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Security scan success must be boolean"])
        if not success:
            error = str(event.get("error", "")).strip()
            if not error:
                raise CommandWorkspaceError(["Failed security scan requires error"])
            successor = replace(state, stage="receipt", success=False, error=error)
            return CommandWorkspaceTransition(
                successor,
                terminal=True,
                result={"success": False, "error": error, "findings": []},
            )
        score = event.get("health_score")
        files_scanned = event.get("files_scanned")
        if isinstance(score, bool) or not isinstance(score, int | float):
            raise CommandWorkspaceError(["Security health_score must be numeric"])
        if isinstance(files_scanned, bool) or not isinstance(files_scanned, int):
            raise CommandWorkspaceError(["Security files_scanned must be an integer"])
        raw_findings = event.get("findings", ())
        if not isinstance(raw_findings, Sequence) or isinstance(raw_findings, str | bytes):
            raise CommandWorkspaceError(["Security findings must be a list"])
        findings: list[SecurityFindingReceipt] = []
        for raw in raw_findings:
            if not isinstance(raw, Mapping):
                raise CommandWorkspaceError(["Each security finding must be a mapping"])
            findings.append(
                SecurityFindingReceipt(
                    path=self._relative(raw.get("path", "")),
                    line=raw.get("line"),  # type: ignore[arg-type]
                    severity=str(raw.get("severity", "")).upper(),
                    category=str(raw.get("category", "")),
                    detail=str(raw.get("detail", "")),
                    cwe=str(raw.get("cwe", "")),
                )
            )
        findings.sort(key=lambda item: (_SEVERITIES.index(item.severity), item.path, item.line))
        successor = SecurityAuditWorkspaceState(
            target_path=state.target_path,
            focus=state.focus,
            stage=(
                "review"
                if any(item.severity in _REMEDIATION_SEVERITIES for item in findings)
                else "receipt"
            ),
            health_score=float(score),
            files_scanned=files_scanned,
            findings=tuple(findings),
            success=True,
        )
        if successor.stage == "review":
            return CommandWorkspaceTransition(
                successor,
                result={
                    "success": True,
                    "finding_count": len(findings),
                    "review_count": len(successor.remediation_findings),
                },
            )
        return self._terminal(successor)

    @staticmethod
    def _terminal(state: SecurityAuditWorkspaceState) -> CommandWorkspaceTransition:
        successor = replace(state, stage="receipt", success=True)
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={
                "success": True,
                "health_score": state.health_score,
                "files_scanned": state.files_scanned,
                "finding_count": len(state.findings),
                "handoff_prepared": state.handoff_prepared,
                "error": "",
            },
        )

    @staticmethod
    def _summary_section(state: SecurityAuditWorkspaceState) -> dict[str, object]:
        counts = Counter(item.severity for item in state.findings)
        return {
            "heading": "Scan summary",
            "blocks": [
                {
                    "kind": "key_value",
                    "items": [
                        {"label": "Health score", "value": str(state.health_score)},
                        {"label": "Files scanned", "value": str(state.files_scanned)},
                        *[
                            {"label": severity.title(), "value": str(counts[severity])}
                            for severity in _SEVERITIES
                        ],
                    ],
                }
            ],
        }

    @classmethod
    def _view_data(cls, state: SecurityAuditWorkspaceState) -> dict[str, object]:
        if state.stage == "running":
            return {
                "id": "execution",
                "title": "Security audit running",
                "summary": f"Read-only {state.focus} of {state.target_path}.",
            }
        if state.stage == "review":
            findings = state.remediation_findings
            finding = findings[state.review_index]
            actions: list[dict[str, object]] = []
            if state.review_index > 0:
                actions.append({"id": "previous_finding", "label": "Previous"})
            if state.review_index + 1 < len(findings):
                actions.append({"id": "next_finding", "label": "Next"})
            actions.extend(
                [
                    {"id": "finish_security_audit", "label": "Finish audit"},
                    {"id": "handoff_to_fix", "label": "Prepare Fix handoff"},
                ]
            )
            return {
                "id": "execution",
                "title": f"Security finding {state.review_index + 1}/{len(findings)}",
                "summary": f"{finding.severity}: {finding.category}",
                "sections": [
                    {
                        "heading": f"{finding.path}:{finding.line}",
                        "blocks": [
                            {
                                "kind": "key_value",
                                "items": [
                                    {"label": "Detail", "value": finding.detail},
                                    {"label": "CWE", "value": finding.cwe or "not returned"},
                                ],
                            }
                        ],
                    }
                ],
                "actions": actions,
            }
        if state.success is False:
            return {
                "id": "receipt",
                "title": "Security audit receipt",
                "summary": f"Security audit did not complete: {state.error}",
            }
        summary = (
            "Security scan completed; Fix handoff prepared, no remediation executed."
            if state.handoff_prepared
            else f"Security scan completed with {len(state.findings)} findings."
        )
        return {
            "id": "receipt",
            "title": "Security audit receipt",
            "summary": summary,
            "sections": [cls._summary_section(state)],
        }
