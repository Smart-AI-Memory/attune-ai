"""Canonical state and approval validation for the Fix workspace.

The browser/widget is a disposable projection.  This module owns the
versioned Fix state, rebuilds the executable contract from validated
answers at action time, and consumes each action nonce once.  It never
executes the Fix workflow; the existing ``attune fix --run`` boundary
remains the only executor.
"""

from __future__ import annotations

import hmac
import json
import re
import secrets
import shlex
import uuid
from argparse import Namespace
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from attune_forms import WorkspaceActionResponse, workspace_from_dict

from attune.cli_commands.fix_commands import StructuredFixPreview, build_structured_preview
from attune.elicitation.command_workspace import (
    CommandWorkspaceProjection,
    CommandWorkspaceRecord,
    CommandWorkspaceTransition,
)

_STATE_KEYS = frozenset(
    {
        "schema_version",
        "workspace_id",
        "revision",
        "view",
        "validated_answers",
        "preview",
        "contract_hash",
        "approved_contract_hash",
        "action_nonce",
    }
)
_ANSWER_KEYS = frozenset({"request", "scope", "probes"})
_WORKSPACE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class FixWorkspaceError(ValueError):
    """A state, preview, or returned action failed closed."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


def _normalize_answers(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Return the only accepted Fix intake vocabulary."""
    if not isinstance(raw, Mapping):
        raise FixWorkspaceError(["validated Fix answers must be a mapping"])
    unknown = sorted(set(raw) - _ANSWER_KEYS, key=repr)
    missing = sorted(_ANSWER_KEYS - set(raw))
    problems = [f"validated Fix answers have unknown key {key!r}" for key in unknown]
    problems.extend(f"validated Fix answers require {key!r}" for key in missing)

    request = raw.get("request")
    scope = raw.get("scope")
    probes_raw = raw.get("probes")
    if not isinstance(request, str) or not request.strip():
        problems.append("validated Fix request must be a non-empty string")
    if not isinstance(scope, str) or not scope.strip():
        problems.append("validated Fix scope must be a non-empty string")
    if isinstance(probes_raw, str):
        probes = [probes_raw]
    elif isinstance(probes_raw, list | tuple):
        probes = list(probes_raw)
    else:
        probes = []
        problems.append("validated Fix probes must be a string or list")
    if not probes or not all(isinstance(probe, str) and probe.strip() for probe in probes):
        problems.append("validated Fix probes must contain non-empty strings")
    if problems:
        raise FixWorkspaceError(problems)
    return {
        "request": request.strip(),
        "scope": scope.strip(),
        "probes": [probe.strip() for probe in probes],
    }


def _answers_json(answers: Mapping[str, Any]) -> str:
    return json.dumps(
        _normalize_answers(answers),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _preview_from_answers(answers: Mapping[str, Any]) -> StructuredFixPreview:
    normalized = _normalize_answers(answers)
    preview, error = build_structured_preview(
        Namespace(
            request=normalized["request"],
            scope=normalized["scope"],
            probe=normalized["probes"],
            workflow="fix",
            explain=True,
            run=False,
        )
    )
    if preview is None:
        raise FixWorkspaceError([error or "could not build the Fix preview"])
    return preview


def _identity_problems(
    schema_version: Any,
    workspace_id: Any,
    revision: Any,
    view: Any,
) -> list[str]:
    problems: list[str] = []
    if isinstance(schema_version, bool) or schema_version != 1:
        problems.append("Fix workspace schema_version must be 1")
    if not isinstance(workspace_id, str) or not _WORKSPACE_ID_RE.fullmatch(workspace_id):
        problems.append("Fix workspace_id is invalid")
    if isinstance(revision, bool) or not isinstance(revision, int):
        problems.append("Fix workspace revision must be an integer")
    elif revision < 0:
        problems.append("Fix workspace revision must not be negative")
    if not isinstance(view, str) or view not in ("intake", "preview"):
        problems.append("Fix workspace view must be intake or preview")
    return problems


def _serialized_answer_problems(raw: Any) -> list[str]:
    try:
        answers = json.loads(raw)
        if _answers_json(answers) != raw:
            return ["Fix workspace answers are not canonically serialized"]
    except (json.JSONDecodeError, TypeError, FixWorkspaceError):
        return ["Fix workspace answers are invalid"]
    return []


def _missing_preview_problems(
    view: str,
    contract_hash: Any,
    approved_contract_hash: Any,
    action_nonce: Any,
) -> list[str]:
    problems: list[str] = []
    if view != "intake":
        problems.append("Fix workspace preview view requires a preview")
    if contract_hash or approved_contract_hash or action_nonce:
        problems.append("Fix intake state cannot retain preview authority")
    return problems


def _preview_contract_problems(
    view: str,
    preview: StructuredFixPreview,
    contract_hash: Any,
) -> list[str]:
    problems: list[str] = []
    if view != "preview":
        problems.append("a Fix preview cannot be stored in intake state")
    if not isinstance(preview, StructuredFixPreview):
        problems.append("Fix workspace preview has the wrong type")
    elif (
        not isinstance(contract_hash, str)
        or not _HASH_RE.fullmatch(contract_hash)
        or not hmac.compare_digest(contract_hash, preview.contract_hash())
    ):
        problems.append("Fix workspace contract hash does not match its preview")
    return problems


def _nonce_problems(action_nonce: Any) -> list[str]:
    if not isinstance(action_nonce, str) or (
        action_nonce and not _NONCE_RE.fullmatch(action_nonce)
    ):
        return ["Fix workspace action nonce is invalid"]
    return []


def _approval_problems(
    approved_contract_hash: Any,
    action_nonce: Any,
    contract_hash: Any,
) -> list[str]:
    problems: list[str] = []
    if not isinstance(approved_contract_hash, str):
        problems.append("Fix workspace approval hash must be a string")
    elif approved_contract_hash and (
        not _HASH_RE.fullmatch(approved_contract_hash)
        or not isinstance(contract_hash, str)
        or not hmac.compare_digest(approved_contract_hash, contract_hash)
    ):
        problems.append("Fix workspace approval hash does not match its contract")
    if approved_contract_hash and action_nonce:
        problems.append("an approved Fix workspace cannot retain an action nonce")
    return problems


def _preview_authority_problems(
    view: str,
    preview: StructuredFixPreview | None,
    contract_hash: Any,
    approved_contract_hash: Any,
    action_nonce: Any,
) -> list[str]:
    if preview is None:
        return _missing_preview_problems(
            view,
            contract_hash,
            approved_contract_hash,
            action_nonce,
        )
    return [
        *_preview_contract_problems(view, preview, contract_hash),
        *_nonce_problems(action_nonce),
        *_approval_problems(approved_contract_hash, action_nonce, contract_hash),
    ]


@dataclass(frozen=True)
class FixWorkspaceState:
    """Versioned canonical state for one Fix interaction."""

    schema_version: int
    workspace_id: str
    revision: int
    view: str
    validated_answers_json: str
    preview: StructuredFixPreview | None
    contract_hash: str
    approved_contract_hash: str
    action_nonce: str

    def __post_init__(self) -> None:
        problems = _identity_problems(
            self.schema_version,
            self.workspace_id,
            self.revision,
            self.view,
        )
        problems.extend(_serialized_answer_problems(self.validated_answers_json))
        problems.extend(
            _preview_authority_problems(
                self.view,
                self.preview,
                self.contract_hash,
                self.approved_contract_hash,
                self.action_nonce,
            )
        )
        if problems:
            raise FixWorkspaceError(problems)

    @property
    def validated_answers(self) -> dict[str, Any]:
        """Return a fresh copy so callers cannot mutate canonical state."""
        return json.loads(self.validated_answers_json)

    @classmethod
    def create_preview(
        cls,
        answers: Mapping[str, Any],
        *,
        workspace_id: str | None = None,
        revision: int = 0,
    ) -> FixWorkspaceState:
        """Validate intake and create a fresh, unapproved preview."""
        answers_json = _answers_json(answers)
        preview = _preview_from_answers(json.loads(answers_json))
        return cls(
            schema_version=1,
            workspace_id=(workspace_id if workspace_id is not None else f"fix-{uuid.uuid4().hex}"),
            revision=revision,
            view="preview",
            validated_answers_json=answers_json,
            preview=preview,
            contract_hash=preview.contract_hash(),
            approved_contract_hash="",
            action_nonce=secrets.token_urlsafe(24),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the portable state document."""
        return {
            "schema_version": self.schema_version,
            "workspace_id": self.workspace_id,
            "revision": self.revision,
            "view": self.view,
            "validated_answers": self.validated_answers,
            "preview": self.preview.to_dict() if self.preview else None,
            "contract_hash": self.contract_hash,
            "approved_contract_hash": self.approved_contract_hash,
            "action_nonce": self.action_nonce,
        }

    def to_json(self) -> str:
        """Serialize deterministically for session storage."""
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FixWorkspaceState:
        """Restore state without accepting unknown or coerced fields."""
        if not isinstance(data, dict) or set(data) != _STATE_KEYS:
            raise FixWorkspaceError(["Fix workspace state has missing or unknown keys"])
        raw_preview = data["preview"]
        try:
            preview = (
                StructuredFixPreview.from_dict(raw_preview) if raw_preview is not None else None
            )
            return cls(
                schema_version=data["schema_version"],
                workspace_id=data["workspace_id"],
                revision=data["revision"],
                view=data["view"],
                validated_answers_json=_answers_json(data["validated_answers"]),
                preview=preview,
                contract_hash=data["contract_hash"],
                approved_contract_hash=data["approved_contract_hash"],
                action_nonce=data["action_nonce"],
            )
        except (TypeError, ValueError) as exc:
            if isinstance(exc, FixWorkspaceError):
                raise
            raise FixWorkspaceError([str(exc)]) from exc

    @classmethod
    def from_json(cls, raw: str) -> FixWorkspaceState:
        """Restore a state document from JSON."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise FixWorkspaceError(["Fix workspace state is not valid JSON"]) from exc
        return cls.from_dict(data)


@dataclass(frozen=True)
class FixWorkspaceActionResult:
    """Validated state transition; execution remains explicitly false."""

    action: str
    state: FixWorkspaceState
    approved_command_argv: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "state": self.state.to_dict(),
            "approved": bool(self.approved_command_argv),
            "approved_command_argv": list(self.approved_command_argv),
            "approved_command": (
                shlex.join(self.approved_command_argv) if self.approved_command_argv else ""
            ),
            "execution_started": False,
        }


def preview_workspace_dict(preview: StructuredFixPreview) -> dict[str, Any]:
    """Project canonical authority into the portable workspace grammar."""
    return {
        "id": "preview",
        "title": "Fix preview",
        "summary": "Review the exact scoped command. Nothing has executed.",
        "sections": [
            {
                "heading": "Contract",
                "tone": "recommendation",
                "blocks": [
                    {
                        "kind": "key_value",
                        "items": [
                            {"label": "Goal", "value": preview.goal},
                            {"label": "Scope", "value": preview.scope},
                            {"label": "Workflow", "value": preview.workflow},
                        ],
                    },
                    {
                        "kind": "action_list",
                        "items": [{"label": condition} for condition in preview.done_conditions],
                    },
                    {
                        "kind": "code",
                        "title": "Exact approved command",
                        "body": shlex.join(preview.command_argv),
                        "language": "shell",
                    },
                ],
            },
            {
                "heading": "Safety constraints",
                "tone": "warning",
                "blocks": [
                    {
                        "kind": "disclosure",
                        "title": "What approval permits",
                        "body": "; ".join(preview.constraints),
                    }
                ],
            },
        ],
        "actions": [
            {"id": "edit_contract", "label": "Edit contract", "intent": "secondary"},
            {
                "id": "run_fix",
                "label": "Run Fix",
                "intent": "primary",
                "consequence": (
                    "Authorize the exact hashed command shown above. The approval is one-time."
                ),
                "requires_explicit_choice": True,
            },
        ],
    }


def validate_fix_workspace_action(
    state: FixWorkspaceState,
    payload: Mapping[str, Any],
) -> FixWorkspaceActionResult:
    """Validate, recompute, and consume one preview action.

    No workflow, subprocess, probe, or file mutation is reachable here.
    The returned command is evidence for the later executor boundary.
    """
    if state.preview is None or state.view != "preview":
        raise FixWorkspaceError(["Fix workspace is not awaiting a preview action"])
    if not state.action_nonce:
        raise FixWorkspaceError(["Fix workspace action nonce was already consumed"])

    rebuilt = _preview_from_answers(state.validated_answers)
    rebuilt_hash = rebuilt.contract_hash()
    if not hmac.compare_digest(rebuilt_hash, state.contract_hash):
        raise FixWorkspaceError(["Fix contract changed after it was rendered"])
    if not hmac.compare_digest(state.preview.contract_hash(), state.contract_hash):
        raise FixWorkspaceError(["serialized Fix preview no longer matches canonical state"])

    from attune_forms import (
        WorkspaceActionBinding,
        WorkspaceValidationError,
        collect_workspace_action,
        workspace_from_dict,
    )

    view = workspace_from_dict(preview_workspace_dict(rebuilt))
    binding = WorkspaceActionBinding(
        workspace_id=state.workspace_id,
        revision=state.revision,
        action_nonce=state.action_nonce,
        contract_hash=state.contract_hash,
    )
    try:
        response = collect_workspace_action(view, payload, binding)
    except WorkspaceValidationError as exc:
        raise FixWorkspaceError(exc.problems) from exc

    if response.action == "edit_contract":
        next_state = FixWorkspaceState(
            schema_version=1,
            workspace_id=state.workspace_id,
            revision=state.revision + 1,
            view="intake",
            validated_answers_json=state.validated_answers_json,
            preview=None,
            contract_hash="",
            approved_contract_hash="",
            action_nonce="",
        )
        return FixWorkspaceActionResult(response.action, next_state)
    # The validated view declares exactly two actions, so the only remaining
    # response is run_fix; collect_workspace_action rejected everything else.
    next_state = replace(
        state,
        revision=state.revision + 1,
        approved_contract_hash=state.contract_hash,
        action_nonce="",
    )
    return FixWorkspaceActionResult(response.action, next_state, rebuilt.command_argv)


@dataclass(frozen=True)
class FixAdapterState:
    """Fix-owned domain state stored inside the shared host envelope."""

    validated_answers_json: str
    preview: StructuredFixPreview | None
    status: str
    approved_contract_hash: str = ""

    def __post_init__(self) -> None:
        problems = _serialized_answer_problems(self.validated_answers_json)
        if self.status not in {"preview", "intake", "approved"}:
            problems.append("Fix adapter status is invalid")
        if self.status == "intake" and self.preview is not None:
            problems.append("Fix adapter intake cannot retain a preview")
        if self.status != "intake" and self.preview is None:
            problems.append("Fix adapter preview and approval require a preview")
        if self.status == "approved":
            if self.preview is not None and not hmac.compare_digest(
                self.approved_contract_hash,
                self.preview.contract_hash(),
            ):
                problems.append("Fix adapter approval does not match its preview")
        elif self.approved_contract_hash:
            problems.append("unapproved Fix adapter state cannot retain approval")
        if problems:
            raise FixWorkspaceError(problems)

    @property
    def validated_answers(self) -> dict[str, Any]:
        """Return a fresh copy of the canonical Fix intake."""
        return json.loads(self.validated_answers_json)


class FixWorkspaceAdapter:
    """Command adapter that keeps every Fix semantic outside shared code."""

    adapter_id = "fix"
    schema_version = 1

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> FixAdapterState:
        """Build a preview, allowing replacement only after edit_contract."""
        if prior_state is not None and (
            not isinstance(prior_state, FixAdapterState) or prior_state.status != "intake"
        ):
            raise FixWorkspaceError(["select edit_contract before replacing a Fix preview"])
        answers_json = _answers_json(intake)
        preview = _preview_from_answers(json.loads(answers_json))
        return FixAdapterState(answers_json, preview, "preview")

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Project Fix domain state into renderer data and its exact digest."""
        if not isinstance(state, FixAdapterState):
            raise FixWorkspaceError(["Fix adapter received incompatible state"])
        if state.status == "intake":
            view = workspace_from_dict(
                {
                    "id": "intake",
                    "title": "Fix intake",
                    "summary": "Edit the contract, then request a fresh preview.",
                }
            )
            return CommandWorkspaceProjection(view)
        if state.preview is None:
            raise FixWorkspaceError(["Fix adapter preview is missing"])
        contract_hash = state.preview.contract_hash()
        if state.status == "preview":
            return CommandWorkspaceProjection(
                workspace_from_dict(preview_workspace_dict(state.preview)),
                contract_hash,
            )
        receipt = workspace_from_dict(
            {
                "id": "receipt",
                "title": "Fix approval receipt",
                "summary": "The exact command was approved once; execution has not started.",
                "sections": [
                    {
                        "heading": "Authority consumed",
                        "tone": "success",
                        "blocks": [
                            {
                                "kind": "key_value",
                                "items": [
                                    {"label": "Contract hash", "value": contract_hash},
                                    {"label": "Status", "value": "approved"},
                                ],
                            },
                            {
                                "kind": "code",
                                "title": "Approved command",
                                "body": shlex.join(state.preview.command_argv),
                                "language": "shell",
                            },
                        ],
                    }
                ],
            }
        )
        return CommandWorkspaceProjection(receipt, contract_hash)

    def apply(
        self,
        state: object,
        action: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition:
        """Rebuild the Fix contract and apply one collected action."""
        if not isinstance(state, FixAdapterState) or state.status != "preview":
            raise FixWorkspaceError(["Fix workspace is not awaiting a preview action"])
        if state.preview is None:
            raise FixWorkspaceError(["Fix adapter preview is missing"])
        rebuilt = _preview_from_answers(state.validated_answers)
        rebuilt_hash = rebuilt.contract_hash()
        if not hmac.compare_digest(rebuilt_hash, state.preview.contract_hash()):
            raise FixWorkspaceError(["Fix contract changed after it was rendered"])
        if action.action == "edit_contract":
            successor = FixAdapterState(
                state.validated_answers_json,
                None,
                "intake",
            )
            return CommandWorkspaceTransition(
                successor,
                result={
                    "approved": False,
                    "approved_command_argv": [],
                    "approved_command": "",
                    "execution_started": False,
                },
            )
        if action.action != "run_fix":
            raise FixWorkspaceError([f"unsupported Fix action {action.action!r}"])
        successor = FixAdapterState(
            state.validated_answers_json,
            rebuilt,
            "approved",
            approved_contract_hash=rebuilt_hash,
        )
        return CommandWorkspaceTransition(
            successor,
            terminal=True,
            result={
                "approved": True,
                "approved_command_argv": list(rebuilt.command_argv),
                "approved_command": shlex.join(rebuilt.command_argv),
                "execution_started": False,
            },
        )

    def compatibility_state(
        self,
        record: CommandWorkspaceRecord,
    ) -> FixWorkspaceState:
        """Project a shared record into the legacy Fix state document."""
        if (
            not isinstance(record, CommandWorkspaceRecord)
            or record.adapter_id != self.adapter_id
            or not isinstance(record.state, FixAdapterState)
        ):
            raise FixWorkspaceError(["record is not a Fix command workspace"])
        state = record.state
        if state.status == "intake":
            return FixWorkspaceState(
                schema_version=1,
                workspace_id=record.workspace_id,
                revision=record.revision,
                view="intake",
                validated_answers_json=state.validated_answers_json,
                preview=None,
                contract_hash="",
                approved_contract_hash="",
                action_nonce="",
            )
        if state.preview is None:
            raise FixWorkspaceError(["Fix adapter preview is missing"])
        contract_hash = state.preview.contract_hash()
        approved_hash = contract_hash if state.status == "approved" else ""
        return FixWorkspaceState(
            schema_version=1,
            workspace_id=record.workspace_id,
            revision=record.revision,
            view="preview",
            validated_answers_json=state.validated_answers_json,
            preview=state.preview,
            contract_hash=contract_hash,
            approved_contract_hash=approved_hash,
            action_nonce=record.action_nonce,
        )
