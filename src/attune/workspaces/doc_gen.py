"""Shared-renderer adapter for previewed documentation writes."""

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


@dataclass(frozen=True)
class DocumentationFileReceipt:
    """One documentation artifact verified from disk."""

    path: str
    sha256: str


@dataclass(frozen=True)
class DocGenWorkspaceState:
    """Documentation audit, proposal, write, and reality-check state."""

    target_path: str
    stage: str = "preview"
    gaps: tuple[str, ...] = ()
    proposed_files: tuple[str, ...] = ()
    changed_files: tuple[DocumentationFileReceipt, ...] = ()
    validation_probe: str = ""
    success: bool | None = None
    error: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "gaps", tuple(self.gaps))
        object.__setattr__(self, "proposed_files", tuple(self.proposed_files))
        object.__setattr__(self, "changed_files", tuple(self.changed_files))
        problems: list[str] = []
        if not self.target_path.strip():
            problems.append("Doc-gen target_path must not be empty")
        if self.stage not in {
            "preview",
            "auditing",
            "proposal",
            "generating",
            "validating",
            "receipt",
        }:
            problems.append("Doc-gen stage is invalid")
        if any(not gap.strip() for gap in self.gaps):
            problems.append("Doc-gen gaps must not be empty")
        if len(self.proposed_files) != len(set(self.proposed_files)):
            problems.append("Doc-gen proposed files must be unique")
        if len(self.changed_files) != len({item.path for item in self.changed_files}):
            problems.append("Doc-gen changed files must be unique")
        if self.success is False and not self.error.strip():
            problems.append("Failed doc-gen operation requires an error receipt")
        if self.success is True and self.error:
            problems.append("Successful doc-gen operation cannot carry an error")
        if problems:
            raise CommandWorkspaceError(problems)


class DocGenWorkspaceAdapter:
    """Audit first, authorize exact doc paths, then verify symbol reality."""

    adapter_id = "doc-gen"
    schema_version = 1

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def _relative(self, raw_path: object) -> str:
        candidate = (self.repo_root / str(raw_path)).resolve()
        try:
            return candidate.relative_to(self.repo_root).as_posix()
        except ValueError as exc:
            raise CommandWorkspaceError(["Doc-gen path escapes the repository"]) from exc

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> DocGenWorkspaceState:
        """Create a path-validated documentation audit preview."""
        if prior_state is not None:
            raise CommandWorkspaceError(["Doc-gen workspaces cannot be replaced"])
        allowed = {"path"}
        unknown = sorted(set(intake) - allowed)
        if unknown:
            raise CommandWorkspaceError([f"unknown doc-gen intake key {key!r}" for key in unknown])
        relative = self._relative(intake.get("path", "src"))
        validated = _validate_file_path(str(self.repo_root / relative), str(self.repo_root))
        if not validated.exists():
            raise CommandWorkspaceError(["Doc-gen target path does not exist"])
        return DocGenWorkspaceState(
            target_path=relative or ".",
        )

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Render the current documentation checkpoint."""
        if not isinstance(state, DocGenWorkspaceState):
            raise CommandWorkspaceError(["doc-gen adapter received incompatible state"])
        view = workspace_from_dict(self._view_data(state))
        contract = {
            "adapter": self.adapter_id,
            "version": self.schema_version,
            "target": state.target_path,
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
        """Apply audit, audit-only finish, or confirmed documentation write."""
        if not isinstance(state, DocGenWorkspaceState):
            raise CommandWorkspaceError(["doc-gen adapter received incompatible state"])
        if state.stage == "preview" and response.action == "audit_docs":
            return CommandWorkspaceTransition(
                replace(state, stage="auditing"),
                result={"delegate": "doc_audit", "args": {"path": state.target_path}},
            )
        if state.stage == "proposal" and response.action == "finish_doc_audit":
            return self._terminal(state, success=True)
        if state.stage == "proposal" and response.action == "apply_docs":
            if not response.confirmed:
                raise CommandWorkspaceError(["Documentation writes require explicit confirmation"])
            return CommandWorkspaceTransition(
                replace(state, stage="generating"),
                result={
                    "delegate": "doc_gen",
                    "args": {"source_path": state.target_path},
                    "approved_paths": list(state.proposed_files),
                },
            )
        raise CommandWorkspaceError(
            [f"Doc-gen action {response.action!r} is not legal in {state.stage!r}"]
        )

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Publish exact audit, disk, and documentation-reality receipts."""
        if not isinstance(state, DocGenWorkspaceState):
            raise CommandWorkspaceError(["doc-gen adapter received incompatible state"])
        kind = event.get("kind")
        if state.stage == "auditing" and kind == "audit_result":
            return self._audit_result(state, event)
        if state.stage == "generating" and kind == "generation_result":
            return self._generation_result(state, event)
        if state.stage == "validating" and kind == "validation_result":
            return self._validation_result(state, event)
        raise CommandWorkspaceError(["Doc-gen receipt is not legal in the current stage"])

    def _audit_result(
        self,
        state: DocGenWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Documentation audit success must be boolean"])
        if not success:
            return self._terminal(
                state,
                success=False,
                error=str(event.get("error", "")).strip(),
            )
        raw_gaps = event.get("gaps", ())
        raw_proposed = event.get("proposed_files", ())
        if not isinstance(raw_gaps, Sequence) or isinstance(raw_gaps, str | bytes):
            raise CommandWorkspaceError(["Documentation gaps must be a list"])
        if not isinstance(raw_proposed, Sequence) or isinstance(raw_proposed, str | bytes):
            raise CommandWorkspaceError(["Proposed documentation files must be a list"])
        gaps = tuple(str(item).strip() for item in raw_gaps)
        proposed = tuple(self._relative(item) for item in raw_proposed)
        if any(not gap for gap in gaps):
            raise CommandWorkspaceError(["Documentation gaps must not be empty"])
        if not proposed:
            return self._terminal(replace(state, gaps=gaps), success=True)
        return CommandWorkspaceTransition(
            replace(state, stage="proposal", gaps=gaps, proposed_files=proposed),
            result={"gap_count": len(gaps), "proposed_files": list(proposed)},
        )

    def _generation_result(
        self,
        state: DocGenWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        success = event.get("success")
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Documentation generation success must be boolean"])
        if not success:
            return self._terminal(
                state,
                success=False,
                error=str(event.get("error", "")).strip(),
            )
        raw_files = event.get("changed_files", ())
        if not isinstance(raw_files, Sequence) or isinstance(raw_files, str | bytes):
            raise CommandWorkspaceError(["Changed documentation files must be a list"])
        paths = tuple(self._relative(item) for item in raw_files)
        if set(paths) != set(state.proposed_files):
            raise CommandWorkspaceError(["Changed documentation files differ from approved paths"])
        receipts: list[DocumentationFileReceipt] = []
        for relative in paths:
            validated = _validate_file_path(
                str(self.repo_root / relative),
                str(self.repo_root),
            )
            if not validated.is_file():
                raise CommandWorkspaceError(
                    [f"Changed documentation file {relative!r} does not exist"]
                )
            receipts.append(
                DocumentationFileReceipt(
                    relative,
                    hashlib.sha256(validated.read_bytes()).hexdigest(),
                )
            )
        return CommandWorkspaceTransition(
            replace(state, stage="validating", changed_files=tuple(receipts)),
            result={"delegate": "doc-import-audit", "paths": list(paths)},
        )

    def _validation_result(
        self,
        state: DocGenWorkspaceState,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        success = event.get("success")
        probe = str(event.get("probe", "")).strip()
        if not isinstance(success, bool):
            raise CommandWorkspaceError(["Documentation validation success must be boolean"])
        if not probe:
            raise CommandWorkspaceError(["Documentation validation probe is required"])
        successor = replace(state, validation_probe=probe)
        return self._terminal(
            successor,
            success=success,
            error=(str(event.get("error", "")).strip() if not success else ""),
        )

    @staticmethod
    def _terminal(
        state: DocGenWorkspaceState,
        *,
        success: bool,
        error: str = "",
    ) -> CommandWorkspaceTransition:
        if not success and not error:
            raise CommandWorkspaceError(["Failed doc-gen receipt requires error"])
        successor = replace(state, stage="receipt", success=success, error=error)
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={
                "success": success,
                "gap_count": len(state.gaps),
                "changed_files": [
                    {"path": item.path, "sha256": item.sha256} for item in state.changed_files
                ],
                "probe": state.validation_probe,
                "error": error,
            },
        )

    @staticmethod
    def _view_data(state: DocGenWorkspaceState) -> dict[str, object]:
        if state.stage == "preview":
            return {
                "id": "preview",
                "title": "Documentation audit preview",
                "summary": f"Audit documentation for {state.target_path}.",
                "actions": [{"id": "audit_docs", "label": "Audit documentation"}],
            }
        if state.stage in {"auditing", "generating", "validating"}:
            return {
                "id": "execution",
                "title": "Documentation workflow running",
                "summary": state.stage.title(),
            }
        if state.stage == "proposal":
            return {
                "id": "execution",
                "title": "Documentation write proposal",
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
                    {"id": "finish_doc_audit", "label": "Finish with audit"},
                    {
                        "id": "apply_docs",
                        "label": "Generate documentation",
                        "consequence": "Write only the proposed documentation files.",
                        "requires_explicit_choice": True,
                    },
                ],
            }
        if state.success is False:
            summary = f"Documentation generation did not complete: {state.error}"
        elif state.changed_files:
            summary = (
                f"Generated {len(state.changed_files)} documentation files; "
                "symbol/import validation passed."
            )
        else:
            summary = (
                f"Documentation audit completed with {len(state.gaps)} gaps; no files changed."
            )
        evidence = [
            {"label": item.path, "value": item.sha256, "status": "complete"}
            for item in state.changed_files
        ] or [{"label": "Changed files", "value": "None", "status": "complete"}]
        return {
            "id": "receipt",
            "title": "Documentation receipt",
            "summary": summary,
            "sections": [
                {
                    "heading": "Artifact receipts",
                    "blocks": [{"kind": "evidence", "items": evidence}],
                }
            ],
        }
