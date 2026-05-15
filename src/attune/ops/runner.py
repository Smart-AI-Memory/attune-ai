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
import re
import shlex
import sys
import time
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# Log-byte cap for persisted records. Records with logs larger than this
# get truncated and a trailing ``<TRUNCATED — N bytes more>`` marker is
# appended so the user knows output was clipped. 200 KB is enough for
# all observed real-world runs (the largest in telemetry was ~80 KB);
# the cap is a defense against runaway loops filling the disk.
_PERSIST_LOG_BUDGET_BYTES = 200_000

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
EventKind = Literal["line", "done", "error"]
Event = tuple[EventKind, object]


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
    # Full command line (argv list) the subprocess was invoked with.
    # Captured at execute time so the persistence record can reproduce
    # exactly what ran. ``None`` for runs that never executed.
    command: list[str] | None = None
    lines: list[str] = field(default_factory=list)
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
            "command": list(self.command) if self.command else None,
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
        return cls(
            id=str(data.get("id", "")),
            workflow=str(data.get("workflow", "")),
            status=_coerce_status(data.get("status")),
            exit_code=_coerce_int(data.get("exit_code")),
            started_at=_parse_dt(data.get("started_at")),
            completed_at=_parse_dt(data.get("completed_at")),
            path=str(data["path"]) if isinstance(data.get("path"), str) else None,
            command=command,
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
        self._broadcast(("done", {"exit_code": exit_code, "status": self.status}))

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
        if self.is_terminal:
            queue.put_nowait(("done", {"exit_code": self.exit_code, "status": self.status}))
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
    """
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
    ) -> None:
        self._runs: OrderedDict[str, Run] = OrderedDict()
        self._history_limit = history_limit
        self._command_builder = command_builder or _default_command
        self._lock = asyncio.Lock()
        self._executor = executor or self._execute
        self._persistence_dir = persistence_dir

    @property
    def persistence_dir(self) -> Path | None:
        return self._persistence_dir

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

    async def start(self, workflow: str, *, path: str | None = None) -> Run:
        async with self._lock:
            current = self.current
            if current is not None:
                raise RunnerBusyError(current.id)
            run = Run(id=uuid.uuid4().hex[:12], workflow=workflow, path=path)
            self._runs[run.id] = run
            while len(self._runs) > self._history_limit:
                self._runs.popitem(last=False)
        # Fire and forget — execution streams events via the run's subscribers
        asyncio.create_task(self._executor(run))
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

    async def _execute(self, run: Run) -> None:
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        cmd = list(self._command_builder(run.workflow))
        # Append ``--path <scope>`` after the builder's output so test
        # fixtures (with simple ``workflow -> command`` signatures) don't
        # need to know about scoping. The CLI accepts ``--path`` uniformly
        # and rewrites it into the workflow-specific kwarg via
        # PATH_ARG_REGISTRY at the workflow layer.
        if run.path:
            cmd.extend(["--path", run.path])
        run.command = list(cmd)
        run.append_line(f"$ {' '.join(shlex.quote(c) for c in cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
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
                run.append_line(raw.decode("utf-8", errors="replace").rstrip("\n"))
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
    tmp = workflow_dir / f"{run.id}.json.tmp"
    try:
        workflow_dir.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(record, indent=2), encoding="utf-8")
        tmp.replace(dest)
    except OSError as exc:
        logger.warning("ops.persist: write failed for %s/%s: %s", run.workflow, run.id, exc)
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
