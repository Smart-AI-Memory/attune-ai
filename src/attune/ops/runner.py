"""In-memory workflow runner for the ops dashboard.

Spawns ``attune workflow run <name>`` as a subprocess, captures merged
stdout+stderr line-by-line, and broadcasts lines to SSE subscribers.

Single concurrent run by design. In-memory history holds the last N
runs; completed runs may also be persisted to
``<attune_home>/ops/runs/<workflow>/<run-id>.json`` so history survives
a server restart. See docs/specs/ops-runner-tier2/ Phase 3.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shlex
import sys
import tempfile
import time
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from attune.bulletin import BulletinBackend, BulletinEntry, resolve_actor
from attune.bulletin.protocol import ActorKind

logger = logging.getLogger(__name__)

# Heartbeat cadence (seconds) — matches the bulletin's 90s stale GC
# threshold; missing 3 ticks marks an actor dead. Lives in the wrapper
# process per multi-actor-bulletin/decisions.md so blocked SDK calls
# inside a workflow don't look like crashes to other actors.
_BULLETIN_HEARTBEAT_INTERVAL_SEC = 30.0

# Log-byte cap for persisted records. Records with logs larger than this
# get truncated and a trailing ``<TRUNCATED — N bytes more>`` marker is
# appended so the user knows output was clipped. 200 KB is enough for
# all observed real-world runs (the largest in telemetry was ~80 KB);
# the cap is a defense against runaway loops filling the disk.
_PERSIST_LOG_BUDGET_BYTES = 200_000

# Per-line ceiling for the child's stdout stream. asyncio's default
# StreamReader limit is 64 KiB and readline() RAISES past it — a
# run-meta ``report_b64`` line (base64 of a full WorkflowReport) can
# exceed that, which would stamp a succeeded run failed. 8 MiB is far
# above any real report while still bounding a runaway line.
_STDOUT_LINE_LIMIT = 8 * 1024 * 1024

# Workflow name shape — matches PATH_ARG_REGISTRY keys. Used to validate
# the directory segment in the persistence path so a malformed workflow
# name can't escape ``<runs_dir>``.
_WORKFLOW_NAME_RE = re.compile(r"^[a-z][a-z0-9-]+$")

# Run-id shape — UUID hex from ``uuid.uuid4().hex[:12]``. Validated when
# loading records from disk so a stray file with a hostile name can't
# bypass directory containment.
_RUN_ID_RE = re.compile(r"^[a-f0-9]{1,64}$")


class RunnerBusyError(RuntimeError):
    """Raised when a run is already pending/running."""

    def __init__(self, current_run_id: str) -> None:
        super().__init__(f"runner busy: run {current_run_id} is active")
        self.current_run_id = current_run_id


RunStatus = Literal["pending", "running", "completed", "failed"]
EventKind = Literal["line", "done", "error", "recommendation"]
Event = tuple[EventKind, object]

# Workflows emit structured recommendations by printing a stdout line
# prefixed with this marker followed by a JSON object. The runner
# parses and routes these to the ``recommendation`` SSE channel; the
# marker line itself is dropped from the visible log to keep the
# user-facing output clean. See docs/specs/ops-runner-tier2/ Phase 5.
_RECOMMENDATION_MARKER = "ATTUNE_REC "
_VALID_REC_KINDS: frozenset[str] = frozenset(("next-workflow", "open-url"))
# Open-URL recommendations are restricted to plain http(s) — no
# javascript:, file://, data:, or vbscript: schemes. Defensive even
# though the client also gates window.open on the same check.
_VALID_URL_SCHEMES: tuple[str, ...] = ("http://", "https://")


_VALID_STATUSES: frozenset[str] = frozenset(("pending", "running", "completed", "failed"))


def _coerce_status(value: object) -> RunStatus:
    if isinstance(value, str) and value in _VALID_STATUSES:
        return value  # type: ignore[return-value]
    return "completed"


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return None


@dataclass
class Run:
    """Single workflow execution + its broadcast state."""

    id: str
    workflow: str
    status: RunStatus = "pending"
    exit_code: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    # Optional scope path passed to the workflow as ``--path <value>``.
    # ``None`` means the workflow runs project-wide (no ``--path`` flag).
    # See docs/specs/ops-runner-tier2/ Phase 2.
    path: str | None = None
    # Run provenance (run-record-corpus RC-3): ``"attune-rec"`` when the
    # client launched this run from a next-workflow recommendation
    # (chain pill, rec card, suggestion chip), ``"manual"`` or ``None``
    # otherwise. Exported to the subprocess as ``ATTUNE_RUN_TRIGGER`` so
    # the workflow's run record carries the attribution.
    trigger: str | None = None
    # Extra argv appended after the command builder's output (and after
    # ``--path``). Used by non-workflow dispatches like ``diagnose
    # <source_run_id>`` (advanced-debugging-plugin T5). Ephemeral —
    # ``command`` captures the full argv for persistence.
    extra_args: list[str] | None = None
    # Full command line (argv list) the subprocess was invoked with.
    # Captured at execute time so the persistence record can reproduce
    # exactly what ran. ``None`` for runs that never executed.
    command: list[str] | None = None
    # Captured stderr from the underlying ``claude`` CLI subprocess
    # when an SDK-backed workflow fails. Already redacted by the
    # workflow before reaching this field. Populated by Phase 3b's
    # stdout side-channel; ``None`` until 3b lands and for any run
    # that didn't fail at the SDK boundary. Part of the
    # ``docs/specs/sdk-error-message-fidelity/`` flow.
    sdk_stderr: str | None = None
    # Classifier kind (one of ``SdkErrorKind`` literals — ``api_quota``,
    # ``auth``, ``rate_limit``, ``not_found``, ``schema_rejected``,
    # ``unknown``). ``None`` when no SDK failure was captured.
    sdk_error_kind: str | None = None
    # Serialized ``WorkflowReport`` dict (``_type: WorkflowReport``)
    # delivered via the ``report_b64`` run-meta side-channel when the
    # workflow's ``final_output`` carried one. Drives the run view's
    # structured report panel — workflow-result-formatting T6.
    report: dict[str, object] | None = None
    lines: list[str] = field(default_factory=list)
    # Buffered recommendations replayed to late subscribers so a user
    # who opens /runs/<id>/view after the run finished still sees the
    # cards. Bounded to avoid unbounded growth on a misbehaving workflow.
    recommendations: list[dict[str, object]] = field(default_factory=list)
    subscribers: set[asyncio.Queue[Event]] = field(default_factory=set)

    @property
    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed")

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "workflow": self.workflow,
            "status": self.status,
            "exit_code": self.exit_code,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "line_count": len(self.lines),
            "path": self.path,
            "trigger": self.trigger,
            "command": list(self.command) if self.command else None,
            "sdk_stderr": self.sdk_stderr,
            "sdk_error_kind": self.sdk_error_kind,
            "report": self.report,
        }

    def to_record(self) -> dict[str, object]:
        """Serialize the full record (metadata + log) for disk persistence.

        Mirrors :meth:`to_dict` but adds the line buffer. Used by the
        ``ops/runs/<workflow>/<run-id>.json`` writer in Phase 3.
        """
        record = self.to_dict()
        record["lines"] = list(self.lines)
        return record

    @classmethod
    def from_record(cls, data: dict[str, object]) -> Run:
        """Rebuild a Run from a persisted record.

        The returned Run has no subscribers (subscribers are tied to a
        live SSE stream; replay from disk is read-only). ``started_at``
        and ``completed_at`` are restored from ISO strings.
        """

        def _parse_dt(value: object) -> datetime | None:
            if not isinstance(value, str) or not value:
                return None
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None

        lines_raw = data.get("lines") or []
        lines = [str(line) for line in lines_raw] if isinstance(lines_raw, list) else []
        command_raw = data.get("command")
        command = [str(c) for c in command_raw] if isinstance(command_raw, list) else None
        # SDK error fields (Phase 3a) — old records read back as None.
        sdk_stderr_raw = data.get("sdk_stderr")
        sdk_stderr = str(sdk_stderr_raw) if isinstance(sdk_stderr_raw, str) else None
        sdk_kind_raw = data.get("sdk_error_kind")
        sdk_error_kind = str(sdk_kind_raw) if isinstance(sdk_kind_raw, str) else None
        # Structured report (T6) — old records read back as None.
        report_raw = data.get("report")
        report = report_raw if isinstance(report_raw, dict) else None
        return cls(
            id=str(data.get("id", "")),
            workflow=str(data.get("workflow", "")),
            status=_coerce_status(data.get("status")),
            exit_code=_coerce_int(data.get("exit_code")),
            started_at=_parse_dt(data.get("started_at")),
            completed_at=_parse_dt(data.get("completed_at")),
            path=str(data["path"]) if isinstance(data.get("path"), str) else None,
            trigger=(str(data["trigger"]) if isinstance(data.get("trigger"), str) else None),
            command=command,
            sdk_stderr=sdk_stderr,
            sdk_error_kind=sdk_error_kind,
            report=report,
            lines=lines,
        )

    def _broadcast(self, event: Event) -> None:
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # INTENTIONAL: drop slow subscriber rather than block the run.
                # Before the queue gained maxsize, this branch was dead code
                # (unbounded queue → put_nowait never raises). See
                # docs/specs/ops-security-hardening/.
                self.subscribers.discard(q)

    def append_line(self, line: str) -> None:
        self.lines.append(line)
        self._broadcast(("line", line))

    def mark_done(self, exit_code: int) -> None:
        self.exit_code = exit_code
        self.status = "completed" if exit_code == 0 else "failed"
        self.completed_at = datetime.now(timezone.utc)
        # Phase 4.3 of docs/specs/sdk-error-message-fidelity/ — include
        # typed sdk_error_kind + redacted sdk_stderr in the done payload
        # so the dashboard chip classifier can read the typed value
        # instead of regex-scanning the log buffer. The fields are set
        # via the run_meta_stdout side-channel during line processing,
        # so they're already populated by the time mark_done fires.
        self._broadcast(
            (
                "done",
                {
                    "exit_code": exit_code,
                    "status": self.status,
                    "sdk_error_kind": self.sdk_error_kind,
                    "sdk_stderr": self.sdk_stderr,
                    # Signals the run view to fetch /runs/<id>/report and
                    # render the structured panel (T6). A boolean rather
                    # than the report itself keeps the SSE frame small.
                    "has_report": self.report is not None,
                },
            )
        )

    # Per-run recommendation cap. Workflows that hit this cap have
    # something pathological going on (or are emitting one per finding
    # without dedup). 50 is generous; the dashboard would already be
    # unusable with that many cards.
    _RECOMMENDATION_CAP = 50

    def emit_recommendation(self, payload: dict[str, object]) -> None:
        """Broadcast a validated recommendation payload to subscribers.

        Validation happens at the :class:`RunnerService` layer (which
        knows ``project_root`` for path validation) — by the time the
        payload reaches this method it is trusted. The method exists
        on :class:`Run` rather than the service so tests can drive the
        SSE channel directly without spinning up a service.
        """
        if len(self.recommendations) >= self._RECOMMENDATION_CAP:
            return
        self.recommendations.append(payload)
        self._broadcast(("recommendation", payload))

    # Per-subscriber queue size. Realistic runs are 1k-5k log lines; if a
    # subscriber falls 1000 events behind, dropping it is correct. The
    # `except QueueFull` block in `_broadcast` was dead code before this
    # bound was added (unbounded queue → put_nowait never raises). See
    # docs/specs/ops-security-hardening/.
    _SUBSCRIBER_QUEUE_MAXSIZE = 1000

    async def subscribe(self) -> AsyncIterator[Event]:
        """Yield buffered + live events. Caller iterates until it sees ``done``."""
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=self._SUBSCRIBER_QUEUE_MAXSIZE)
        # Replay buffered state to this subscriber
        for line in self.lines:
            queue.put_nowait(("line", line))
        for rec in self.recommendations:
            queue.put_nowait(("recommendation", rec))
        if self.is_terminal:
            queue.put_nowait(
                (
                    "done",
                    {
                        "exit_code": self.exit_code,
                        "status": self.status,
                        "sdk_error_kind": self.sdk_error_kind,
                        "sdk_stderr": self.sdk_stderr,
                        "has_report": self.report is not None,
                    },
                )
            )
        self.subscribers.add(queue)
        try:
            while True:
                event = await queue.get()
                yield event
                if event[0] == "done":
                    return
        finally:
            self.subscribers.discard(queue)


CommandBuilder = Callable[[str], Sequence[str]]


def _default_command(workflow: str) -> Sequence[str]:
    """Default subprocess command — runs the same attune that's hosting ops.

    Uses ``sys.executable -m attune.cli_minimal`` instead of bare ``attune``
    because ``attune`` on PATH may resolve to a different install (e.g. a
    system pyenv shim) than the one the dashboard is running. That mismatch
    silently runs old code, which is the kind of bug that wastes 30 minutes
    of debugging before someone notices ``which attune`` doesn't point where
    they think it does.

    Scope (``--path``) is appended by :meth:`RunnerService._execute` after
    the builder's output, so custom builders (test fixtures, alternative
    CLIs) don't need to know about it.

    ``diagnose`` is a top-level CLI command, not a workflow — the
    diagnosis engine (advanced-debugging-plugin T5) dispatches through
    the runner to inherit SSE streaming, the busy-lock, and run
    persistence; its source-run argument arrives via ``Run.extra_args``.
    """
    if workflow == "diagnose":
        return (sys.executable, "-m", "attune.cli_minimal", "diagnose")
    return (sys.executable, "-m", "attune.cli_minimal", "workflow", "run", workflow)


class RunnerService:
    """Owns the run history + concurrency lock.

    When ``persistence_dir`` is supplied, completed runs are written to
    ``<persistence_dir>/<workflow>/<run-id>.json`` so the dashboard's
    recent-runs strip can survive a server restart. ``None`` disables
    persistence — used in read-only mode and tests that don't care about
    disk side effects.
    """

    def __init__(
        self,
        *,
        history_limit: int = 20,
        command_builder: CommandBuilder | None = None,
        executor: Callable[[Run], Awaitable[None]] | None = None,
        persistence_dir: Path | None = None,
        project_root: Path | None = None,
        bulletin: BulletinBackend | None = None,
        actor_id: str | None = None,
        actor_kind: ActorKind = "dashboard",
    ) -> None:
        self._runs: OrderedDict[str, Run] = OrderedDict()
        self._history_limit = history_limit
        self._command_builder = command_builder or _default_command
        self._lock = asyncio.Lock()
        self._executor = executor or self._execute
        self._persistence_dir = persistence_dir
        # ``project_root`` is used to validate path-bearing recommendation
        # payloads against the same allowed_dir the runner enforces for
        # /workflows/<name>/run requests. ``None`` disables path
        # validation, which is fine for test fixtures that only exercise
        # the SSE channel; production wiring in ``server.py`` always
        # supplies it.
        self._project_root = project_root
        # Bulletin wiring. ``bulletin=None`` disables all writes — the
        # runner behaves exactly as before. Production server.py wires
        # a FileBulletinBackend; tests inject a fake to assert calls.
        self._bulletin = bulletin
        if actor_id is None:
            actor_id, _ = resolve_actor(actor_kind=actor_kind)
        self._actor_id = actor_id
        self._actor_kind: ActorKind = actor_kind
        # Maps run_id -> heartbeat asyncio task so _finish_run can
        # cancel cleanly. Pruned when the task is cancelled.
        self._heartbeat_tasks: dict[str, asyncio.Task[None]] = {}
        # Maps run_id -> the workflow-executor asyncio task. The event
        # loop only holds *weak* references to tasks created via
        # ``asyncio.create_task``; if we discard the return value the GC
        # can reap the task mid-flight (cpython.discard-task-issue). A
        # ``done_callback`` pops the entry on completion so the dict
        # stays bounded at ``len(active_runs)``.
        self._executor_tasks: dict[str, asyncio.Task[None]] = {}

    @property
    def persistence_dir(self) -> Path | None:
        return self._persistence_dir

    def _validate_recommendation(self, payload: object) -> dict[str, object] | None:
        """Return a sanitized recommendation payload or ``None`` if invalid.

        Validation rules (see docs/specs/ops-runner-tier2/ Phase 5):

        - ``payload`` must be a JSON object.
        - ``kind`` must be one of :data:`_VALID_REC_KINDS`.
        - For ``next-workflow``: ``name`` must be a registered workflow.
          Optional ``args.path``, when present, must pass
          ``_validate_file_path(allowed_dir=project_root)``.
        - For ``open-url``: ``url`` must start with ``http://`` or
          ``https://``.
        - Optional ``label`` and ``severity`` fields are coerced to
          str / lowercased and pass through.

        Invalid payloads return ``None`` after a warning log — the
        caller drops them silently from the SSE channel.
        """
        if not isinstance(payload, dict):
            logger.warning("recommendation rejected: payload not a JSON object")
            return None
        kind = payload.get("kind")
        if not isinstance(kind, str) or kind not in _VALID_REC_KINDS:
            logger.warning("recommendation rejected: bad kind %r", kind)
            return None

        sanitized: dict[str, object] = {"kind": kind}
        if "label" in payload and isinstance(payload["label"], str):
            sanitized["label"] = payload["label"][:200]
        if "severity" in payload and isinstance(payload["severity"], str):
            sanitized["severity"] = payload["severity"].lower()[:20]

        if kind == "next-workflow":
            return self._validate_next_workflow_rec(payload, sanitized)
        return self._validate_open_url_rec(payload, sanitized)

    def _validate_next_workflow_rec(
        self, payload: dict[str, object], sanitized: dict[str, object]
    ) -> dict[str, object] | None:
        """Finish validating a ``next-workflow`` recommendation."""
        name = payload.get("name")
        if not isinstance(name, str) or not name:
            logger.warning("recommendation rejected: next-workflow name missing")
            return None
        # Verify against the live registry. Cheap: ~25 entries, no I/O.
        from attune.ops import data as _data

        valid_names = {w.name for w in _data.list_workflows()}
        if name not in valid_names:
            logger.warning("recommendation rejected: unknown workflow %r", name)
            return None
        sanitized["name"] = name

        args = payload.get("args")
        if args is not None and not isinstance(args, dict):
            logger.warning("recommendation rejected: args not an object")
            return None
        if isinstance(args, dict) and "path" in args:
            validated_path = self._validate_rec_path(args["path"])
            if validated_path is None:
                return None
            sanitized["args"] = {"path": validated_path}
        return sanitized

    def _validate_rec_path(self, raw_path: object) -> str | None:
        """Validate a recommendation ``args.path`` value.

        Returns the validated path string, or ``None`` (after a warning
        log) when it is rejected. ``project_root=None`` disables
        validation — the raw string passes through (test-fixture
        wiring; production server.py always supplies a root).
        """
        if not isinstance(raw_path, str) or not raw_path:
            logger.warning("recommendation rejected: bad args.path")
            return None
        if self._project_root is None:
            return raw_path
        from attune.security.path_validation import _validate_file_path

        try:
            validated = _validate_file_path(raw_path, allowed_dir=str(self._project_root))
        except ValueError as exc:
            logger.warning(
                "recommendation rejected: args.path failed validation (%s)",
                exc,
            )
            return None
        return str(validated)

    @staticmethod
    def _validate_open_url_rec(
        payload: dict[str, object], sanitized: dict[str, object]
    ) -> dict[str, object] | None:
        """Finish validating an ``open-url`` recommendation."""
        url = payload.get("url")
        if not isinstance(url, str) or not url.startswith(_VALID_URL_SCHEMES):
            logger.warning("recommendation rejected: bad open-url url %r", url)
            return None
        sanitized["url"] = url
        return sanitized

    def handle_stdout_line(self, run: Run, line: str) -> None:
        """Route a raw stdout line to either the log, the recommendation
        channel, or the run-metadata side-channel.

        Lines prefixed with :data:`_RECOMMENDATION_MARKER` are parsed as
        JSON, validated, and broadcast as a ``recommendation`` event.
        Bad markers (parse error, validation failure) are dropped — they
        do NOT pollute the visible log so workflows can iterate on the
        protocol without leaking debug noise.

        Lines prefixed with ``ATTUNE_RUN_META`` carry SDK error metadata
        (``sdk_stderr`` / ``sdk_error_kind``) from the CLI's
        ``_print_workflow_result``; they're parsed via
        :mod:`attune.ops.run_meta_stdout` and stashed on the ``Run``
        object before persistence, and filtered out of ``run.lines``
        so the user-facing log stays clean. Part of the
        ``docs/specs/sdk-error-message-fidelity/`` Phase 3b flow.

        Non-marker lines flow to the normal append_line path.
        """
        if line.startswith(_RECOMMENDATION_MARKER):
            raw = line[len(_RECOMMENDATION_MARKER) :]
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("recommendation marker had malformed JSON")
                return
            sanitized = self._validate_recommendation(parsed)
            if sanitized is not None:
                run.emit_recommendation(sanitized)
            return
        if line.startswith("ATTUNE_RUN_META"):
            # Local import keeps the runner module light when the
            # side-channel never fires (the common case — only fails
            # on SDK workflows emit these lines).
            from attune.ops import run_meta_stdout

            parsed_meta = run_meta_stdout.parse_line(line)
            if parsed_meta is None:
                # Malformed marker — drop silently like the
                # recommendation channel does. Don't pollute the
                # visible log; emitters can iterate without leaking
                # debug noise.
                return
            event = parsed_meta.get("event")
            if event == "version":
                # Version line is informational; consumer ignores it
                # after a basic sanity check. The grammar is stable
                # for v1 so unknown versions just drop through.
                return
            if event == "field":
                key = parsed_meta.get("key")
                value = parsed_meta.get("value", "")
                if key == "sdk_error_kind" and value:
                    run.sdk_error_kind = value
                elif key == "sdk_stderr_b64" and value:
                    decoded = run_meta_stdout.decode_stderr(value)
                    if decoded:
                        run.sdk_stderr = decoded
                elif key == "report_b64" and value:
                    decoded_report = run_meta_stdout.decode_report(value)
                    if decoded_report is not None:
                        run.report = decoded_report
            return
        run.append_line(line)

    @property
    def current(self) -> Run | None:
        for run in reversed(self._runs.values()):
            if not run.is_terminal:
                return run
        return None

    def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    def get_or_load(self, run_id: str) -> Run | None:
        """Return ``run_id``'s Run from memory, falling back to disk.

        The dashboard's ``/runs/{id}/view`` route used to 404 whenever a
        run was evicted from the in-memory ring buffer
        (``_history_limit``, default 20) or after a server restart —
        even though the recent-runs strip on Home / Workflows still
        surfaced those runs because it reads disk directly. The disk
        record (``<persistence_dir>/<workflow>/<run-id>.json``) holds
        everything the route needs (status, exit_code, log lines, etc.)
        via :meth:`Run.from_record`.

        Returns ``None`` if neither the in-memory dict nor the
        ``<persistence_dir>/*/<run-id>.json`` lookup finds the run.
        Failures during disk read (missing perm, malformed JSON) are
        logged at WARN and treated as cache miss — the route's 404
        path is preferred over crashing on a corrupt record.

        Note on subscribers: a Run rebuilt from disk has no
        ``subscribers`` set and no live executor attached, so SSE
        replay against it would loop with no events. Callers should
        check ``run.is_terminal`` and skip the stream attempt when
        the run is loaded from disk; the route layer does this by
        emitting an empty ``stream_url`` when ``get()`` returns None
        but ``get_or_load()`` finds a record.

        Performance: walks
        ``<persistence_dir>/<workflow>/<run-id>.json`` across all
        workflow subdirectories on miss. O(workflows-with-runs) per
        call — at the ~20-workflow scale of attune-ai this is well
        under 1ms, so no index file is maintained. If it ever becomes
        a hot path, the cheapest fix is a workflow-name lookup table
        keyed by ``run_id`` populated lazily on first miss.
        """
        run = self._runs.get(run_id)
        if run is not None:
            return run
        # Validate BEFORE the filesystem walk, like the sibling
        # loaders — run_id becomes part of a path below.
        if not _RUN_ID_RE.match(run_id):
            return None
        if self._persistence_dir is None:
            return None
        if not self._persistence_dir.is_dir():
            return None
        target_filename = f"{run_id}.json"
        for workflow_dir in self._persistence_dir.iterdir():
            if not workflow_dir.is_dir():
                continue
            candidate = workflow_dir / target_filename
            if not candidate.is_file():
                continue
            try:
                with candidate.open(encoding="utf-8") as fh:
                    record = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "ops.runner.get_or_load: failed to read %s: %s",
                    candidate,
                    exc,
                )
                return None
            if not isinstance(record, dict):
                return None
            try:
                return Run.from_record(record)
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "ops.runner.get_or_load: malformed record %s: %s",
                    candidate,
                    exc,
                )
                return None
        return None

    def recent(self, limit: int = 5) -> list[Run]:
        return list(reversed(list(self._runs.values())))[:limit]

    async def start(
        self,
        workflow: str,
        *,
        path: str | None = None,
        trigger: str | None = None,
        extra_args: list[str] | None = None,
    ) -> Run:
        async with self._lock:
            current = self.current
            if current is not None:
                raise RunnerBusyError(current.id)
            run = Run(
                id=uuid.uuid4().hex[:12],
                workflow=workflow,
                path=path,
                trigger=trigger,
                extra_args=list(extra_args) if extra_args else None,
            )
            self._runs[run.id] = run
            while len(self._runs) > self._history_limit:
                self._runs.popitem(last=False)
        # Bulletin start record. Errors swallowed by the backend — never
        # blocks workflow start. See multi-actor-bulletin spec.
        self._bulletin_write(run, "running")
        # Fire and forget — execution streams events via the run's
        # subscribers. The task is pinned in ``self._executor_tasks``
        # because the event loop only holds weak references to tasks
        # created via ``asyncio.create_task``; a discarded reference can
        # be GC'd mid-flight and the workflow silently dies. The
        # done-callback pops the entry on completion (success, failure,
        # or cancellation), so the dict stays bounded at ``len(active_runs)``.
        task = asyncio.create_task(self._executor(run))
        self._executor_tasks[run.id] = task
        task.add_done_callback(lambda _t, rid=run.id: self._executor_tasks.pop(rid, None))
        return run

    def _finish_run(self, run: Run, exit_code: int) -> None:
        """Mark a run done + persist it (best-effort) when configured.

        Exactly one terminal call per run — replaces direct
        ``run.mark_done(...)`` invocations inside ``_execute``. The
        persistence write is synchronous on the executor's thread; it's
        bounded (200 KB log cap, atomic-rename, JSON encode) so the
        added latency is negligible relative to a workflow's runtime.
        """
        run.mark_done(exit_code)
        if self._persistence_dir is not None:
            _persist_run(run, self._persistence_dir)
        # Cancel the wrapper-process heartbeat task (no-op if absent).
        task = self._heartbeat_tasks.pop(run.id, None)
        if task is not None:
            task.cancel()
        # Write the terminal bulletin record. ``mark_done`` already set
        # status to ``completed`` or ``failed``.
        self._bulletin_write(run, run.status)

    def _bulletin_write(self, run: Run, status: str) -> None:
        """Best-effort bulletin write — never raises to the caller.

        ``status`` is one of ``running``, ``completed``, ``failed``,
        ``cancelled``. ``mark_done`` only produces ``completed`` or
        ``failed``; the runner doesn't emit ``cancelled`` today, but
        the bulletin entry schema accepts it for future use.
        """
        if self._bulletin is None:
            return
        coerced_status = (
            status if status in ("running", "completed", "failed", "cancelled") else "running"
        )
        try:
            self._bulletin.append(
                BulletinEntry(
                    actor_id=self._actor_id,
                    actor_kind=self._actor_kind,
                    workflow=run.workflow,
                    run_id=run.id,
                    current_status=coerced_status,  # type: ignore[arg-type]
                    scope=run.path,
                )
            )
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: bulletin is advisory; backend bugs must not
            # take down a workflow run. Log and continue.
            logger.warning("bulletin: write failed for run %s: %s", run.id, exc)

    async def _heartbeat_loop(self, run: Run) -> None:
        """Tick every ``_BULLETIN_HEARTBEAT_INTERVAL_SEC`` until cancelled.

        Lives in the wrapper process (this method), not inside the
        workflow loop — so an SDK call blocking >60s inside the
        subprocess doesn't look like a crash to other actors. See
        multi-actor-bulletin/decisions.md.
        """
        try:
            while True:
                await asyncio.sleep(_BULLETIN_HEARTBEAT_INTERVAL_SEC)
                if run.is_terminal:
                    return
                self._bulletin_write(run, "running")
        except asyncio.CancelledError:
            # Normal path: _finish_run cancels us at terminal status.
            raise

    async def _execute(self, run: Run) -> None:
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        # Start the wrapper-process heartbeat. ``None`` when the
        # bulletin isn't wired — keeps test fixtures and read-only
        # mode behaving exactly as before.
        if self._bulletin is not None:
            self._heartbeat_tasks[run.id] = asyncio.create_task(self._heartbeat_loop(run))
        cmd = list(self._command_builder(run.workflow))
        # Append ``--path <scope>`` after the builder's output so test
        # fixtures (with simple ``workflow -> command`` signatures) don't
        # need to know about scoping. The CLI accepts ``--path`` uniformly
        # and rewrites it into the workflow-specific kwarg via
        # PATH_ARG_REGISTRY at the workflow layer.
        if run.path:
            cmd.extend(["--path", run.path])
        if run.extra_args:
            cmd.extend(run.extra_args)
        run.command = list(cmd)
        run.append_line(f"$ {' '.join(shlex.quote(c) for c in cmd)}")
        # Opt the spawned CLI process into the ATTUNE_RUN_META
        # stdout side-channel so SDK error metadata (sdk_stderr +
        # sdk_error_kind) flows back into Run.sdk_stderr / .sdk_error_kind
        # for persistence + the run-view collapsible details block.
        # See docs/specs/sdk-error-message-fidelity/ Phase 3b. The
        # env var is the consumer's signal — without it, the CLI's
        # _print_workflow_result skips the emit, so users who pipe
        # `attune workflow run X > out.md` outside the daemon don't
        # see the marker lines.
        import os as _os

        # The dashboard runner spawns the CLI non-interactively, so the
        # spend gate (collaboration-gates) would block it by default
        # (D10 fail-safe). Until the dashboard grows its own confirm
        # modal (a later phase of the gates spec), opt the daemon's
        # subprocess in explicitly — the machine-context equivalent of
        # the human "go". The per-workflow ATTUNE_MAX_BUDGET_USD cap
        # still bounds any run, so this is bounded authorization.
        proc_env = {
            **_os.environ,
            "ATTUNE_RUN_META_EMIT": "1",
            "ATTUNE_SPEND_GATE_AUTHORIZED": "1",
            # On an SDK subprocess failure the argv isn't recoverable, so
            # opt this daemon-spawned run into the live `claude` health
            # probe — surfaces the real auth/quota error in the run-view
            # details instead of a generic "no stderr" note. Off by
            # default elsewhere (keeps unit tests deterministic).
            "ATTUNE_SDK_ERROR_PROBE": "1",
        }
        # Run provenance for the workflow's run record (run-record-corpus
        # RC-3). Only known values cross the boundary; the child's
        # ``resolve_run_trigger`` treats anything else as ``manual``.
        if run.trigger in ("manual", "attune-rec", "attune-heal"):
            from attune.models.telemetry.run_context import TRIGGER_ENV

            proc_env[TRIGGER_ENV] = run.trigger
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=proc_env,
                # asyncio's default StreamReader limit is 64 KiB and
                # readline() RAISES on a longer line — run-meta
                # report_b64 lines routinely approach/exceed that, and
                # the except below would stamp a succeeded run failed.
                # Match the emitter's worst case with generous headroom.
                limit=_STDOUT_LINE_LIMIT,
            )
        except FileNotFoundError as exc:
            run.append_line(f"[runner error] command not found: {exc}")
            self._finish_run(run, -1)
            return
        except Exception as exc:  # noqa: BLE001
            run.append_line(f"[runner error] {exc}")
            self._finish_run(run, -1)
            return

        assert proc.stdout is not None
        try:
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    break
                self.handle_stdout_line(run, raw.decode("utf-8", errors="replace").rstrip("\n"))
            await proc.wait()
            self._finish_run(run, proc.returncode if proc.returncode is not None else -1)
        except Exception as exc:  # noqa: BLE001
            run.append_line(f"[runner error] {exc}")
            self._finish_run(run, -1)


def echo_command_builder(workflow: str) -> Sequence[str]:
    """Test helper: produce a portable subprocess that prints two lines + exits 0."""
    script = f"import sys; print('starting {workflow}'); print('done {workflow}')"
    return (sys.executable, "-c", script)


# ---------------------------------------------------------------------------
# Run persistence (Phase 3) — disk read/write helpers
# ---------------------------------------------------------------------------


def _truncate_lines_for_persist(lines: list[str]) -> list[str]:
    """Clamp the on-disk log to ``_PERSIST_LOG_BUDGET_BYTES``.

    Keeps the FIRST N bytes (the preamble + early output where most
    errors surface). Appends a ``<TRUNCATED — N bytes more>`` marker
    line when bytes are dropped. Returns a NEW list — the live ``Run``
    object is never mutated by persistence.
    """
    encoded = [line.encode("utf-8", errors="replace") for line in lines]
    sizes = [len(b) + 1 for b in encoded]  # +1 for the newline separator
    total = sum(sizes)
    if total <= _PERSIST_LOG_BUDGET_BYTES:
        return list(lines)
    kept: list[str] = []
    running = 0
    for line, size in zip(lines, sizes, strict=False):
        if running + size > _PERSIST_LOG_BUDGET_BYTES:
            break
        kept.append(line)
        running += size
    dropped_bytes = total - running
    kept.append(f"<TRUNCATED — {dropped_bytes} bytes more>")
    return kept


def _persist_run(run: Run, runs_dir: Path) -> Path | None:
    """Atomically write a run record under ``<runs_dir>/<workflow>/<id>.json``.

    Best-effort: returns the destination path on success, ``None`` on
    failure (logged at WARNING). Validation rejects malformed workflow
    names and run IDs so a hostile value can't escape ``runs_dir``.
    """
    if not _WORKFLOW_NAME_RE.match(run.workflow):
        logger.warning("ops.persist: refusing to write — bad workflow name %r", run.workflow)
        return None
    if not _RUN_ID_RE.match(run.id):
        logger.warning("ops.persist: refusing to write — bad run id %r", run.id)
        return None

    record = run.to_record()
    record["lines"] = _truncate_lines_for_persist(run.lines)
    record["persisted_at"] = datetime.now(timezone.utc).isoformat()

    workflow_dir = runs_dir / run.workflow
    dest = workflow_dir / f"{run.id}.json"
    tmp: Path | None = None
    try:
        workflow_dir.mkdir(parents=True, exist_ok=True)
        # mkstemp names the temp file uniquely per call: deriving it from
        # the run id lets two writers for the same run pick the same path,
        # so one truncates the other's partial write before the rename
        # publishes it (class G1).
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{run.id}.json.", suffix=".tmp", dir=str(workflow_dir)
        )
        tmp = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(record, indent=2))
        tmp.replace(dest)
    except OSError as exc:
        logger.warning("ops.persist: write failed for %s/%s: %s", run.workflow, run.id, exc)
        if tmp is not None:
            with _suppress_oserror():
                tmp.unlink()
        return None
    return dest


def _load_run_record(runs_dir: Path, workflow: str, run_id: str) -> dict | None:
    """Load a persisted run record. Returns ``None`` on missing/malformed."""
    if not _WORKFLOW_NAME_RE.match(workflow) or not _RUN_ID_RE.match(run_id):
        return None
    path = runs_dir / workflow / f"{run_id}.json"
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("ops.persist: read failed for %s: %s", path, exc)
        return None
    return data if isinstance(data, dict) else None


def _list_persisted_runs(runs_dir: Path, workflow: str, *, limit: int = 20) -> list[dict]:
    """Return up to ``limit`` newest persisted run records for ``workflow``.

    Newest first, sorted by file mtime. Malformed files are skipped with
    a warning log. Records include the full ``lines`` buffer — callers
    that only need metadata should drop the field.
    """
    if not _WORKFLOW_NAME_RE.match(workflow):
        return []
    workflow_dir = runs_dir / workflow
    if not workflow_dir.is_dir():
        return []
    try:
        entries = sorted(
            workflow_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return []
    out: list[dict] = []
    for entry in entries[: max(limit * 2, limit)]:  # over-fetch then filter
        if not entry.is_file() or entry.name.endswith(".tmp"):
            continue
        run_id = entry.stem
        if not _RUN_ID_RE.match(run_id):
            continue
        record = _load_run_record(runs_dir, workflow, run_id)
        if record is None:
            continue
        out.append(record)
        if len(out) >= limit:
            break
    return out


def prune_old_runs(runs_dir: Path, *, days: int) -> int:
    """Delete persisted run files older than ``days``. Returns the deletion count.

    Safe to call on a missing directory (returns 0). Errors per file
    are logged at WARNING and don't abort the sweep.
    """
    if days <= 0 or not runs_dir.is_dir():
        return 0
    cutoff = time.time() - days * 86_400
    deleted = 0
    try:
        workflow_dirs = list(runs_dir.iterdir())
    except OSError:
        return 0
    for workflow_dir in workflow_dirs:
        if not workflow_dir.is_dir():
            continue
        try:
            entries = list(workflow_dir.glob("*.json"))
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.stat().st_mtime < cutoff:
                    entry.unlink()
                    deleted += 1
            except OSError as exc:
                logger.warning("ops.persist: prune failed for %s: %s", entry, exc)
    return deleted


class _suppress_oserror:
    """Context-manager replacement for ``contextlib.suppress(OSError)``.

    Inline class avoids an extra import for a 4-line cleanup path.
    """

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        return isinstance(exc, OSError)
