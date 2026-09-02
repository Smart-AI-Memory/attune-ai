"""Shared-renderer adapter for audited, confirmed test generation."""

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

_APPROACHES = frozenset({"gap", "generate", "both"})
_RISKS = frozenset({"HIGH", "MEDIUM", "LOW"})


@dataclass(frozen=True)
class TestGapReceipt:
    """One exact uncovered test target."""

    path: str
    symbol: str
    risk: str
    detail: str

    def __post_init__(self) -> None:
        if not self.path.strip() or not self.symbol.strip() or not self.detail.strip():
            raise CommandWorkspaceError(["Test gap path, symbol, and detail are required"])
        if self.risk not in _RISKS:
            raise CommandWorkspaceError(["Test gap risk is invalid"])


@dataclass(frozen=True)
class WrittenTestReceipt:
    """One test file verified from disk after generation."""

    path: str
    sha256: str


@dataclass(frozen=True)
class SmartTestWorkspaceState:
    """Smart-test-owned audit, mutation, and validation state."""

    target_path: str
    approach: str
    stage: str = "preview"
    gaps: tuple[TestGapReceipt, ...] = ()
    proposed_files: tuple[str, ...] = ()
    written_files: tuple[WrittenTestReceipt, ...] = ()
    validation_probe: str = ""
    validation_exit_code: int | None = None
    success: bool | None = None
    error: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "gaps", tuple(self.gaps))
        object.__setattr__(self, "proposed_files", tuple(self.proposed_files))
        object.__setattr__(self, "written_files", tuple(self.written_files))
        problems: list[str] = []
        if not self.target_path.strip():
            problems.append("Smart-test target_path must not be empty")
        if self.approach not in _APPROACHES:
            problems.append("Smart-test approach is invalid")
        if self.stage not in {
            "preview",
            "auditing",
            "proposal",
            "generating",
            "validating",
            "receipt",
        }:
            problems.append("Smart-test stage is invalid")
        if len(self.proposed_files) != len(set(self.proposed_files)):
            problems.append("Smart-test proposed files must be unique")
        if len(self.written_files) != len({item.path for item in self.written_files}):
            problems.append("Smart-test written files must be unique")
        if self.validation_exit_code is not None and (
            isinstance(self.validation_exit_code, bool)
            or not isinstance(self.validation_exit_code, int)
        ):
            problems.append("Smart-test validation exit code must be an integer")
        if self.success is False and not self.error.strip():
            problems.append("Failed smart-test operation requires an error receipt")
        if self.success is True and self.error:
            problems.append("Successful smart-test operation cannot carry an error")
        if problems:
            raise CommandWorkspaceError(problems)


def _gap(raw: Mapping[str, object]) -> TestGapReceipt:
    return TestGapReceipt(
        path=str(raw.get("path", "")),
        symbol=str(raw.get("symbol", "")),
        risk=str(raw.get("risk", "")).upper(),
        detail=str(raw.get("detail", "")),
    )


class SmartTestWorkspaceAdapter:
    """Audit read-only, confirm writes, then require an actual test probe."""

    adapter_id = "smart-test"
    schema_version = 1

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def _relative(self, raw_path: object) -> str:
        candidate = (self.repo_root / str(raw_path)).resolve()
        try:
            return candidate.relative_to(self.repo_root).as_posix()
        except ValueError as exc:
            raise CommandWorkspaceError(["Smart-test path escapes the repository"]) from exc

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> SmartTestWorkspaceState:
        """Create a path-validated gap-audit preview."""
        if prior_state is not None:
            raise CommandWorkspaceError(["Smart-test workspaces cannot be replaced"])
        allowed = {"path", "approach"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError(
                [f"unknown smart-test intake key {key!r}" for key in unknown]
            )
        relative = self._relative(intake.get("path", "src"))
        validated = _validate_file_path(str(self.repo_root / relative), str(self.repo_root))
        if not validated.exists():
            raise CommandWorkspaceError(["Smart-test target path does not exist"])
        return SmartTestWorkspaceState(
            target_path=relative or ".",
            approach=str(intake.get("approach", "both")).lower(),
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render the current audit, write, or validation checkpoint."""
        if not isinstance(state, SmartTestWorkspaceState):
            raise CommandWorkspaceError(["smart-test adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "target": state.target_path,
            "approach": state.approach,
            "stage": state.stage,
            "proposed": state.proposed_files,
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
        """Apply audit start, stop-after-audit, or confirmed generation."""
        if not isinstance(state, SmartTestWorkspaceState):
            raise CommandWorkspaceError(["smart-test adapter received incompatible state"])
        if state.stage == "preview" and response.action == "audit_test_gaps":
            return CommandWorkspaceTransition(
                replace(state, stage="auditing"),
                result={"delegate": "test_audit", "args": {"path": state.target_path}},
            )
        if state.stage == "proposal" and response.action == "finish_audit":
            return self._terminal(state, success=True)
        if state.stage == "proposal" and response.action == "generate_tests":
            if not response.confirmed:
                raise CommandWorkspaceError(["Test generation requires explicit confirmation"])
            return CommandWorkspaceTransition(
                replace(state, stage="generating"),
                result={
                    "delegate": "test_generation",
                    "args": {"module": state.target_path},
                    "approved_paths": list(state.proposed_files),
                },
            )
        raise CommandWorkspaceError(
            [f"Smart-test action {response.action!r} is not legal in {state.stage!r}"]
        )

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish exact audit, generated-file, and test-process receipts."""
        if not isinstance(state, SmartTestWorkspaceState):
            raise CommandWorkspaceError(["smart-test adapter received incompatible state"])
        kind = event.get("kind")
        if state.stage == "auditing" and kind == "audit_result":
            return self._audit_result(state, event)
        if state.stage == "generating" and kind == "generation_result":
            return self._generation_result(state, event)
        if state.stage == "validating" and kind == "validation_result":
            return self._validation_result(state, event)
        raise CommandWorkspaceError(["Smart-test receipt is not legal in the current stage"])

    def _audit_result(
        self,
        state: SmartTestWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Test audit success must be boolean"])
        if not success:
            return self._terminal(
                state,
                success=False,
                error=str(event.get("error", "")).strip(),
            )
        raw_gaps = event.get("gaps", ())
        if not isinstance(raw_gaps, Sequence) or isinstance(raw_gaps, str | bytes):
            raise CommandWorkspaceError(["Test audit gaps must be a list"])
        gaps = tuple(_gap(item) for item in raw_gaps if isinstance(item, Mapping))
        if len(gaps) != len(raw_gaps):
            raise CommandWorkspaceError(["Each test gap must be a mapping"])
        if not gaps or state.approach == "gap":
            return self._terminal(replace(state, gaps=gaps), success=True)
        raw_proposed = event.get("proposed_files", ())
        if not isinstance(raw_proposed, Sequence) or isinstance(raw_proposed, str | bytes):
            raise CommandWorkspaceError(["Proposed test files must be a list"])
        proposed = tuple(self._relative(item) for item in raw_proposed)
        if not proposed:
            raise CommandWorkspaceError(["Test generation requires proposed file paths"])
        return CommandWorkspaceTransition(
            replace(state, stage="proposal", gaps=gaps, proposed_files=proposed),
            result={"gap_count": len(gaps), "proposed_files": list(proposed)},
        )

    def _generation_result(
        self,
        state: SmartTestWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Test generation success must be boolean"])
        if not success:
            return self._terminal(
                state,
                success=False,
                error=str(event.get("error", "")).strip(),
            )
        raw_files = event.get("written_files", ())
        if not isinstance(raw_files, Sequence) or isinstance(raw_files, str | bytes):
            raise CommandWorkspaceError(["Written test files must be a list"])
        paths = tuple(self._relative(item) for item in raw_files)
        if set(paths) != set(state.proposed_files):
            raise CommandWorkspaceError(["Written test files differ from approved paths"])
        receipts: list[WrittenTestReceipt] = []
        for relative in paths:
            validated = _validate_file_path(
                str(self.repo_root / relative),
                str(self.repo_root),
            )
            if not validated.is_file():
                raise CommandWorkspaceError([f"Written test file {relative!r} does not exist"])
            receipts.append(
                WrittenTestReceipt(relative, hashlib.sha256(validated.read_bytes()).hexdigest())
            )
        return CommandWorkspaceTransition(
            replace(state, stage="validating", written_files=tuple(receipts)),
            result={"delegate": "tests.run", "paths": list(paths)},
        )

    def _validation_result(
        self,
        state: SmartTestWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        probe = str(event.get("probe", "")).strip()
        exit_code = event.get("exit_code")
        if not probe:
            raise CommandWorkspaceError(["Test validation probe is required"])
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise CommandWorkspaceError(["Test validation exit_code must be an integer"])
        successor = replace(
            state,
            validation_probe=probe,
            validation_exit_code=exit_code,
        )
        if exit_code != 0:
            return self._terminal(
                successor,
                success=False,
                error=str(event.get("error", "")).strip() or f"test probe exited {exit_code}",
            )
        return self._terminal(successor, success=True)

    @staticmethod
    def _terminal(
        state: SmartTestWorkspaceState,
        *,
        success: bool,
        error: str = "",
    ) -> CommandWorkspaceTransition:
        if not success and not error:
            raise CommandWorkspaceError(["Failed smart-test receipt requires error"])
        successor = replace(state, stage="receipt", success=success, error=error)
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={
                "success": success,
                "gap_count": len(state.gaps),
                "written_files": [
                    {"path": item.path, "sha256": item.sha256} for item in state.written_files
                ],
                "probe": state.validation_probe,
                "exit_code": state.validation_exit_code,
                "error": error,
            },
        )

    @staticmethod
    def _view_data(state: SmartTestWorkspaceState) -> dict[str, object]:
        if state.stage == "preview":
            return {
                "id": "preview",
                "title": "Smart test audit preview",
                "summary": f"Audit {state.target_path}; approach: {state.approach}.",
                "actions": [{"id": "audit_test_gaps", "label": "Audit test gaps"}],
            }
        if state.stage in {"auditing", "generating", "validating"}:
            return {
                "id": "execution",
                "title": "Smart test running",
                "summary": state.stage.title(),
            }
        if state.stage == "proposal":
            return {
                "id": "execution",
                "title": "Generated test proposal",
                "summary": f"{len(state.gaps)} gaps; {len(state.proposed_files)} proposed files.",
                "sections": [
                    {
                        "heading": "Approved write boundary",
                        "blocks": [
                            {
                                "kind": "action_list",
                                "items": [{"label": path} for path in state.proposed_files],
                            }
                        ],
                    }
                ],
                "actions": [
                    {"id": "finish_audit", "label": "Finish with audit"},
                    {
                        "id": "generate_tests",
                        "label": "Generate tests",
                        "consequence": "Write only the proposed test files.",
                        "requires_explicit_choice": True,
                    },
                ],
            }
        if state.success is False:
            summary = f"Smart test did not complete: {state.error}"
        elif state.written_files:
            summary = (
                f"Generated {len(state.written_files)} files; validation exited "
                f"{state.validation_exit_code}."
            )
        else:
            summary = f"Audit completed with {len(state.gaps)} gaps; no files written."
        evidence_items = [
            {
                "label": item.path,
                "value": item.sha256,
                "status": "complete" if state.success else "failed",
            }
            for item in state.written_files
        ]
        if not evidence_items:
            evidence_items.append(
                {
                    "label": "Written files",
                    "value": "None",
                    "status": "complete" if state.success else "failed",
                }
            )
        return {
            "id": "receipt",
            "title": "Smart test receipt",
            "summary": summary,
            "sections": [
                {
                    "heading": "Written file receipts",
                    "blocks": [
                        {
                            "kind": "evidence",
                            "items": evidence_items,
                        }
                    ],
                }
            ],
        }
