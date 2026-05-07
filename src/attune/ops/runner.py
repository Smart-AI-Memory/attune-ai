"""In-memory workflow runner for the ops dashboard.

Spawns ``attune workflow run <name>`` as a subprocess, captures merged
stdout+stderr line-by-line, and broadcasts lines to SSE subscribers.

Single concurrent run by design. History is in-memory only (last N runs).
"""

from __future__ import annotations

import asyncio
import shlex
import sys
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


class RunnerBusyError(RuntimeError):
    """Raised when a run is already pending/running."""

    def __init__(self, current_run_id: str) -> None:
        super().__init__(f"runner busy: run {current_run_id} is active")
        self.current_run_id = current_run_id


RunStatus = Literal["pending", "running", "completed", "failed"]
EventKind = Literal["line", "done", "error"]
Event = tuple[EventKind, object]


@dataclass
class Run:
    """Single workflow execution + its broadcast state."""

    id: str
    workflow: str
    status: RunStatus = "pending"
    exit_code: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
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
        }

    def _broadcast(self, event: Event) -> None:
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # INTENTIONAL: drop slow subscriber rather than block the run
                pass

    def append_line(self, line: str) -> None:
        self.lines.append(line)
        self._broadcast(("line", line))

    def mark_done(self, exit_code: int) -> None:
        self.exit_code = exit_code
        self.status = "completed" if exit_code == 0 else "failed"
        self.completed_at = datetime.now(timezone.utc)
        self._broadcast(("done", {"exit_code": exit_code, "status": self.status}))

    async def subscribe(self) -> AsyncIterator[Event]:
        """Yield buffered + live events. Caller iterates until it sees ``done``."""
        queue: asyncio.Queue[Event] = asyncio.Queue()
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
    """Default subprocess command — shells out to the user's `attune` CLI."""
    return ("attune", "workflow", "run", workflow)


class RunnerService:
    """Owns the run history + concurrency lock."""

    def __init__(
        self,
        *,
        history_limit: int = 20,
        command_builder: CommandBuilder | None = None,
        executor: Callable[[Run], Awaitable[None]] | None = None,
    ) -> None:
        self._runs: OrderedDict[str, Run] = OrderedDict()
        self._history_limit = history_limit
        self._command_builder = command_builder or _default_command
        self._lock = asyncio.Lock()
        self._executor = executor or self._execute

    @property
    def current(self) -> Run | None:
        for run in reversed(self._runs.values()):
            if not run.is_terminal:
                return run
        return None

    def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    def recent(self, limit: int = 5) -> list[Run]:
        return list(reversed(list(self._runs.values())))[:limit]

    async def start(self, workflow: str) -> Run:
        async with self._lock:
            current = self.current
            if current is not None:
                raise RunnerBusyError(current.id)
            run = Run(id=uuid.uuid4().hex[:12], workflow=workflow)
            self._runs[run.id] = run
            while len(self._runs) > self._history_limit:
                self._runs.popitem(last=False)
        # Fire and forget — execution streams events via the run's subscribers
        asyncio.create_task(self._executor(run))
        return run

    async def _execute(self, run: Run) -> None:
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        cmd = list(self._command_builder(run.workflow))
        run.append_line(f"$ {' '.join(shlex.quote(c) for c in cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError as exc:
            run.append_line(f"[runner error] command not found: {exc}")
            run.mark_done(-1)
            return
        except Exception as exc:  # noqa: BLE001
            run.append_line(f"[runner error] {exc}")
            run.mark_done(-1)
            return

        assert proc.stdout is not None
        try:
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    break
                run.append_line(raw.decode("utf-8", errors="replace").rstrip("\n"))
            await proc.wait()
            run.mark_done(proc.returncode if proc.returncode is not None else -1)
        except Exception as exc:  # noqa: BLE001
            run.append_line(f"[runner error] {exc}")
            run.mark_done(-1)


def echo_command_builder(workflow: str) -> Sequence[str]:
    """Test helper: produce a portable subprocess that prints two lines + exits 0."""
    script = f"import sys; print('starting {workflow}'); print('done {workflow}')"
    return (sys.executable, "-c", script)
