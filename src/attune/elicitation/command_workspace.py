"""Canonical host runtime for renderer-backed command workspaces.

Adapters own command state and semantics. The host owns adapter registration,
workspace identity, revision and nonce issuance, canonical storage, structural
action validation, and at-most-once transition publication. Rendered HTML and
Markdown are disposable projections of the same ``WorkspaceView``.
"""

from __future__ import annotations

import asyncio
import copy
import hmac
import logging
import re
import secrets
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from attune_forms import (
    WorkspaceActionBinding,
    WorkspaceActionResponse,
    WorkspaceView,
    collect_workspace_action,
    workspace_to_markdown,
    workspace_to_widget_html,
)

try:
    from attune_forms.form_events import log_workspace_stage
except ImportError:
    log_workspace_stage = None  # Older public forms wheels still render and collect.
    logging.getLogger(__name__).warning(
        "Workspace timing unavailable: installed attune-forms lacks workspace stage telemetry"
    )

_ADAPTER_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class CommandWorkspaceError(ValueError):
    """A host, adapter, workspace, or action failed closed."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


@dataclass(frozen=True)
class CommandWorkspaceProjection:
    """One adapter-issued view and its normalized authority digest."""

    view: WorkspaceView
    contract_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.view, WorkspaceView):
            raise TypeError("command workspace projection requires a WorkspaceView")
        if not isinstance(self.contract_hash, str):
            raise TypeError("command workspace contract hash must be a string")
        needs_binding = bool(self.view.actions) and self.view.form is None
        if needs_binding and not _HASH_RE.fullmatch(self.contract_hash):
            raise ValueError(
                "action-bearing workspace projection requires a lowercase SHA-256 digest"
            )
        if self.contract_hash and not _HASH_RE.fullmatch(self.contract_hash):
            raise ValueError("command workspace contract hash must be a SHA-256 digest")


@dataclass(frozen=True)
class CommandWorkspaceTransition:
    """Adapter-owned successor state plus portable result evidence."""

    state: object
    terminal: bool = False
    result: Mapping[str, object] = field(default_factory=dict)
    authority_changed: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.terminal, bool):
            raise TypeError("command workspace terminal flag must be a boolean")
        if not isinstance(self.result, Mapping):
            raise TypeError("command workspace transition result must be a mapping")
        if not isinstance(self.authority_changed, bool):
            raise TypeError("command workspace authority_changed must be a boolean")
        object.__setattr__(self, "result", dict(self.result))


@runtime_checkable
class CommandWorkspaceAdapter(Protocol):
    """Small command-owned seam; shared code never inspects domain state."""

    adapter_id: str
    schema_version: int

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> object:
        """Create state from intake, optionally replacing adapter-approved state."""
        ...

    def project(self, state: object) -> CommandWorkspaceProjection:
        """Return the exact current view and normalized authority digest."""
        ...

    def apply(
        self,
        state: object,
        action: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition:
        """Apply one structurally validated action to canonical state."""
        ...


@runtime_checkable
class CommandWorkspacePublisher(Protocol):
    """Optional adapter capability for server-originated progress/events."""

    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition:
        """Apply one trusted moderator/executor event."""
        ...


@dataclass(frozen=True)
class CommandWorkspaceRecord:
    """Server-owned canonical envelope for one command interaction."""

    workspace_id: str
    adapter_id: str
    adapter_version: int
    revision: int
    state: object
    view: WorkspaceView
    contract_hash: str
    action_nonce: str
    terminal: bool = False
    event_sequence: int = 0

    @property
    def binding(self) -> WorkspaceActionBinding:
        """Return the exact one-time authority issued for this record."""
        if not self.action_nonce:
            raise CommandWorkspaceError(["command workspace is not awaiting a bound action"])
        return WorkspaceActionBinding(
            workspace_id=self.workspace_id,
            revision=self.revision,
            action_nonce=self.action_nonce,
            contract_hash=self.contract_hash,
        )


@dataclass(frozen=True)
class CommandWorkspaceRender:
    """Disposable widget and Markdown projections for one record."""

    record: CommandWorkspaceRecord
    html: str
    markdown: str

    def to_dict(self) -> dict[str, object]:
        """Return the command-neutral render result."""
        return {
            "workspace_id": self.record.workspace_id,
            "adapter_id": self.record.adapter_id,
            "adapter_version": self.record.adapter_version,
            "revision": self.record.revision,
            "view": self.record.view.id.value,
            "contract_hash": self.record.contract_hash,
            "action_nonce": self.record.action_nonce,
            "terminal": self.record.terminal,
            "event_sequence": self.record.event_sequence,
            "html": self.html,
            "markdown": self.markdown,
        }


@dataclass(frozen=True)
class CommandWorkspaceActionResult:
    """One accepted action after its successor was stored canonically."""

    action: str
    render: CommandWorkspaceRender
    result: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "result", dict(self.result))

    @property
    def record(self) -> CommandWorkspaceRecord:
        return self.render.record

    def to_dict(self) -> dict[str, object]:
        """Return the command-neutral action result."""
        return {
            "action": self.action,
            **self.render.to_dict(),
            "result": dict(self.result),
        }


class CommandWorkspaceHost:
    """Register adapters and serialize canonical workspace mutations."""

    def __init__(self) -> None:
        self._adapters: dict[str, CommandWorkspaceAdapter] = {}
        self._records: dict[str, CommandWorkspaceRecord] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def register(self, adapter: CommandWorkspaceAdapter) -> None:
        """Register one adapter, rejecting malformed or duplicate identity."""
        if not isinstance(adapter, CommandWorkspaceAdapter):
            raise CommandWorkspaceError(
                ["command workspace adapter does not implement the required protocol"]
            )
        if not _ADAPTER_ID_RE.fullmatch(adapter.adapter_id):
            raise CommandWorkspaceError(["command workspace adapter_id is invalid"])
        if isinstance(adapter.schema_version, bool) or not isinstance(adapter.schema_version, int):
            raise CommandWorkspaceError(
                ["command workspace adapter schema_version must be an integer"]
            )
        if adapter.schema_version < 1:
            raise CommandWorkspaceError(
                ["command workspace adapter schema_version must be positive"]
            )
        if adapter.adapter_id in self._adapters:
            raise CommandWorkspaceError(
                [f"duplicate command workspace adapter {adapter.adapter_id!r}"]
            )
        self._adapters[adapter.adapter_id] = adapter

    def adapter(self, adapter_id: str) -> CommandWorkspaceAdapter:
        """Return a registered adapter or fail explicitly."""
        adapter = self._adapters.get(adapter_id)
        if adapter is None:
            raise CommandWorkspaceError([f"unknown command workspace adapter {adapter_id!r}"])
        return adapter

    def get(self, workspace_id: str) -> CommandWorkspaceRecord | None:
        """Return the canonical record for read-only inspection."""
        return self._records.get(workspace_id)

    async def open(
        self,
        adapter_id: str,
        intake: Mapping[str, object],
        *,
        workspace_id: str | None = None,
    ) -> CommandWorkspaceRender:
        """Create a workspace or replace adapter-approved intake state."""
        if not isinstance(intake, Mapping):
            raise CommandWorkspaceError(["command workspace intake must be a mapping"])
        adapter = self.adapter(adapter_id)
        resolved_id = workspace_id or f"{adapter_id}-{uuid.uuid4().hex}"
        lock = self._locks.setdefault(resolved_id, asyncio.Lock())
        async with lock:
            current = self._records.get(resolved_id)
            if workspace_id is not None and current is None:
                raise CommandWorkspaceError(["unknown command workspace_id"])
            if current is not None and current.adapter_id != adapter_id:
                raise CommandWorkspaceError(
                    ["command workspace adapter does not match canonical state"]
                )
            if current is not None and current.adapter_version != adapter.schema_version:
                raise CommandWorkspaceError(
                    ["command workspace adapter version changed during the interaction"]
                )
            if current is not None and current.terminal:
                raise CommandWorkspaceError(["terminal command workspace cannot be replaced"])
            prior_state = copy.deepcopy(current.state) if current is not None else None
            state = adapter.create(intake, prior_state=prior_state)
            projection = adapter.project(state)
            revision = current.revision + 1 if current is not None else 0
            record = self._record(
                workspace_id=resolved_id,
                adapter=adapter,
                revision=revision,
                state=state,
                projection=projection,
                terminal=False,
                event_sequence=current.event_sequence if current is not None else 0,
            )
            self._records[resolved_id] = record
            return self._render(record)

    async def collect(
        self,
        payload: Mapping[str, object],
        *,
        expected_adapter_id: str | None = None,
    ) -> CommandWorkspaceActionResult:
        """Validate and consume one action against canonical server state."""
        if not isinstance(payload, Mapping):
            raise CommandWorkspaceError(["command workspace action response must be a mapping"])
        workspace_id = payload.get("workspace_id")
        if not isinstance(workspace_id, str):
            raise CommandWorkspaceError(["command workspace action response requires workspace_id"])
        lock = self._locks.setdefault(workspace_id, asyncio.Lock())
        async with lock:
            current = self._records.get(workspace_id)
            if current is None:
                raise CommandWorkspaceError(["unknown or expired command workspace_id"])
            if expected_adapter_id is not None and current.adapter_id != expected_adapter_id:
                raise CommandWorkspaceError(
                    ["command workspace adapter does not match the requested tool"]
                )
            if current.terminal:
                raise CommandWorkspaceError(
                    ["command workspace action authority was already consumed"]
                )
            adapter = self.adapter(current.adapter_id)
            if current.adapter_version != adapter.schema_version:
                raise CommandWorkspaceError(
                    ["command workspace adapter version changed during the interaction"]
                )
            fresh = adapter.project(current.state)
            if fresh.view != current.view:
                raise CommandWorkspaceError(
                    ["canonical command workspace view changed after rendering"]
                )
            if not hmac.compare_digest(fresh.contract_hash, current.contract_hash):
                raise CommandWorkspaceError(
                    ["canonical command workspace contract changed after rendering"]
                )
            try:
                response = collect_workspace_action(
                    current.view,
                    payload,
                    current.binding,
                )
            except ValueError as exc:
                problems = getattr(exc, "problems", [str(exc)])
                raise CommandWorkspaceError(list(problems)) from exc
            transition = adapter.apply(copy.deepcopy(current.state), response)
            projection = adapter.project(transition.state)
            if transition.terminal and projection.view.actions:
                raise CommandWorkspaceError(
                    ["terminal command workspace view cannot expose actions"]
                )
            successor = self._record(
                workspace_id=current.workspace_id,
                adapter=adapter,
                revision=current.revision + 1,
                state=transition.state,
                projection=projection,
                terminal=transition.terminal,
                event_sequence=current.event_sequence,
            )
            self._records[workspace_id] = successor
            if log_workspace_stage is not None:
                log_workspace_stage(
                    "accepted",
                    workspace_id=current.workspace_id,
                    revision=current.revision,
                    instance_id=payload.get("instance_id", ""),
                    adapter_id=current.adapter_id,
                    action=response.action,
                )
            render = self._render(successor)
            return CommandWorkspaceActionResult(
                response.action,
                render,
                transition.result,
            )

    async def publish(
        self,
        workspace_id: str,
        event: Mapping[str, object],
    ) -> CommandWorkspaceActionResult:
        """Publish one trusted adapter event without client action authority."""
        if not isinstance(event, Mapping):
            raise CommandWorkspaceError(["command workspace event must be a mapping"])
        lock = self._locks.setdefault(workspace_id, asyncio.Lock())
        async with lock:
            current = self._records.get(workspace_id)
            if current is None:
                raise CommandWorkspaceError(["unknown or expired command workspace_id"])
            if current.terminal:
                raise CommandWorkspaceError(["terminal command workspace cannot accept events"])
            adapter = self.adapter(current.adapter_id)
            if current.adapter_version != adapter.schema_version:
                raise CommandWorkspaceError(
                    ["command workspace adapter version changed during the interaction"]
                )
            if not isinstance(adapter, CommandWorkspacePublisher):
                raise CommandWorkspaceError(
                    [f"command workspace adapter {adapter.adapter_id!r} does not accept events"]
                )
            transition = adapter.publish(copy.deepcopy(current.state), event)
            projection = adapter.project(transition.state)
            if transition.terminal and not transition.authority_changed:
                raise CommandWorkspaceError(
                    ["terminal workspace publication must change authority"]
                )
            if transition.terminal and projection.view.actions:
                raise CommandWorkspaceError(
                    ["terminal command workspace view cannot expose actions"]
                )
            if transition.authority_changed:
                successor = self._record(
                    workspace_id=current.workspace_id,
                    adapter=adapter,
                    revision=current.revision + 1,
                    state=transition.state,
                    projection=projection,
                    terminal=transition.terminal,
                    event_sequence=current.event_sequence + 1,
                )
            else:
                if (
                    projection.view.id != current.view.id
                    or projection.view.actions != current.view.actions
                    or projection.view.form != current.view.form
                    or not hmac.compare_digest(
                        projection.contract_hash,
                        current.contract_hash,
                    )
                ):
                    raise CommandWorkspaceError(
                        ["progress-only publication changed action authority"]
                    )
                successor = CommandWorkspaceRecord(
                    workspace_id=current.workspace_id,
                    adapter_id=current.adapter_id,
                    adapter_version=current.adapter_version,
                    revision=current.revision,
                    state=transition.state,
                    view=projection.view,
                    contract_hash=current.contract_hash,
                    action_nonce=current.action_nonce,
                    terminal=False,
                    event_sequence=current.event_sequence + 1,
                )
            self._records[workspace_id] = successor
            return CommandWorkspaceActionResult(
                "publish",
                self._render(successor),
                transition.result,
            )

    @staticmethod
    def _record(
        *,
        workspace_id: str,
        adapter: CommandWorkspaceAdapter,
        revision: int,
        state: object,
        projection: CommandWorkspaceProjection,
        terminal: bool,
        event_sequence: int = 0,
    ) -> CommandWorkspaceRecord:
        needs_binding = (
            bool(projection.view.actions) and projection.view.form is None and not terminal
        )
        return CommandWorkspaceRecord(
            workspace_id=workspace_id,
            adapter_id=adapter.adapter_id,
            adapter_version=adapter.schema_version,
            revision=revision,
            state=state,
            view=projection.view,
            contract_hash=projection.contract_hash,
            action_nonce=secrets.token_urlsafe(24) if needs_binding else "",
            terminal=terminal,
            event_sequence=event_sequence,
        )

    @staticmethod
    def _render(record: CommandWorkspaceRecord) -> CommandWorkspaceRender:
        binding = record.binding if record.action_nonce else None
        instance_id = uuid.uuid4().hex
        start = time.perf_counter()
        if log_workspace_stage is None:
            html = workspace_to_widget_html(record.view, binding=binding)
        else:
            html = workspace_to_widget_html(
                record.view,
                binding=binding,
                telemetry_instance_id=instance_id,
            )
        if binding is not None and log_workspace_stage is not None:
            log_workspace_stage(
                "rendered",
                workspace_id=record.workspace_id,
                revision=record.revision,
                instance_id=instance_id,
                adapter_id=record.adapter_id,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        return CommandWorkspaceRender(
            record=record,
            html=html,
            markdown=workspace_to_markdown(record.view, binding=binding),
        )
