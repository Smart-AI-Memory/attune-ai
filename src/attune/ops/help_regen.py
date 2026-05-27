"""Async subprocess runner for ``attune-author`` regen jobs.

Used by the ``/help/admin`` page to trigger help-template
regeneration without leaving the dashboard. Each job runs
``attune-author <action> ...`` in a subprocess, captures stdout
line-by-line, and exposes status via the in-memory ``HelpRegenRunner``.

Lives separate from :class:`attune.ops.runner.RunnerService` —
that runner builds ``attune workflow run <name>`` commands and
its workflow-registry lookups don't fit help-regen jobs cleanly.
Mirroring the simpler shape here keeps the surface focused.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)

JobStatus = Literal["pending", "running", "completed", "failed"]

# Strip ANSI escape sequences before storing log lines. attune-author
# (and the structlog renderer it uses) emit ``\x1b[36m...\x1b[0m``
# color codes which render as garbage in the dashboard's <pre>.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# Feature slug shape — same as attune.ops.help_data._safe_slug
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")

# Max captured output bytes per job. attune-author regens are
# usually <50 KB of console output; 500 KB is generous and
# protects against runaway loops filling memory.
_OUTPUT_CAP_BYTES = 500_000


@dataclass
class HelpRegenJob:
    """One regen invocation — status, captured stdout, exit code."""

    id: str
    action: Literal["generate", "regenerate", "status"]
    feature: str | None
    command: list[str]
    status: JobStatus = "pending"
    exit_code: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    lines: list[str] = field(default_factory=list)
    bytes_captured: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "feature": self.feature,
            "command": list(self.command),
            "status": self.status,
            "exit_code": self.exit_code,
            "started_at": (self.started_at.isoformat() if self.started_at else None),
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "lines": list(self.lines),
            "line_count": len(self.lines),
        }


class HelpRegenRunner:
    """Owns the regen-job history + active subprocess.

    Single concurrent job by design — attune-author regens touch
    ``.help/templates/`` and parallel writes could collide. Trying
    to start a second job while one is running raises
    :class:`HelpRegenBusyError` with the active job id.
    """

    def __init__(
        self,
        *,
        history_limit: int = 20,
        attune_author_path: str | None = None,
    ) -> None:
        self._jobs: OrderedDict[str, HelpRegenJob] = OrderedDict()
        self._history_limit = history_limit
        self._lock = asyncio.Lock()
        # Allow injection for tests; production resolves at start time.
        self._attune_author_path = attune_author_path

    def _resolve_command(self) -> str | None:
        """Find the ``attune-author`` executable on PATH."""
        if self._attune_author_path:
            return self._attune_author_path
        return shutil.which("attune-author")

    @property
    def current(self) -> HelpRegenJob | None:
        for job in reversed(self._jobs.values()):
            if job.status in ("pending", "running"):
                return job
        return None

    def get(self, job_id: str) -> HelpRegenJob | None:
        return self._jobs.get(job_id)

    def recent(self, limit: int = 5) -> list[HelpRegenJob]:
        return list(reversed(list(self._jobs.values())))[:limit]

    async def start(
        self,
        action: Literal["generate", "regenerate", "status"],
        *,
        feature: str | None = None,
        project_root: str | None = None,
        help_dir: str | None = None,
        all_kinds: bool = True,
        dry_run: bool = False,
    ) -> HelpRegenJob:
        """Start a regen job. Returns the created HelpRegenJob.

        Raises:
            HelpRegenBusyError: if a job is already in flight.
            ValueError: invalid feature slug.
            FileNotFoundError: attune-author not on PATH.
        """
        if action == "generate" and not feature:
            raise ValueError("feature required for generate action")
        if feature is not None and not _SLUG_RE.match(feature):
            raise ValueError(f"invalid feature slug: {feature!r}")

        binary = self._resolve_command()
        if binary is None:
            raise FileNotFoundError("attune-author not found on PATH — install it to use regen")

        # Build argv.
        cmd: list[str] = [binary, action]
        if action == "generate":
            cmd.append(feature)  # type: ignore[arg-type]
            if all_kinds:
                cmd.append("--all-kinds")
        elif action == "regenerate":
            if dry_run:
                cmd.append("--dry-run")
        if project_root:
            cmd.extend(["--project-root", project_root])
        if help_dir:
            cmd.extend(["--help-dir", help_dir])

        async with self._lock:
            if self.current is not None:
                raise HelpRegenBusyError(self.current.id)
            job = HelpRegenJob(
                id=uuid.uuid4().hex[:12],
                action=action,
                feature=feature,
                command=cmd,
            )
            self._jobs[job.id] = job
            while len(self._jobs) > self._history_limit:
                self._jobs.popitem(last=False)
        # Fire and forget. The executor captures output and marks
        # the job done; the caller polls /api/help/regen/<id> for
        # status.
        asyncio.create_task(self._execute(job))
        return job

    async def _execute(self, job: HelpRegenJob) -> None:
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        try:
            proc = await asyncio.create_subprocess_exec(
                *job.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError as exc:
            self._append(job, f"[regen error] command not found: {exc}")
            self._finish(job, -1)
            return
        except Exception as exc:  # noqa: BLE001
            # INTENTIONAL: any subprocess startup failure is reflected
            # as exit code -1 and a captured error line. The runner
            # itself never raises to the route handler.
            self._append(job, f"[regen error] {exc}")
            self._finish(job, -1)
            return

        assert proc.stdout is not None
        try:
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                self._append(job, line)
            await proc.wait()
            self._finish(job, proc.returncode if proc.returncode is not None else -1)
        except Exception as exc:  # noqa: BLE001
            self._append(job, f"[regen error] {exc}")
            self._finish(job, -1)

    def _append(self, job: HelpRegenJob, line: str) -> None:
        # Strip ANSI color codes before storing — the dashboard renders
        # the log in a plain <pre>, not a terminal emulator.
        clean = _ANSI_RE.sub("", line)
        encoded = clean.encode("utf-8", errors="replace")
        if job.bytes_captured + len(encoded) > _OUTPUT_CAP_BYTES:
            if not job.lines or not job.lines[-1].startswith("[output truncated"):
                job.lines.append(
                    f"[output truncated — {len(encoded)} bytes more would have followed]"
                )
            return
        job.lines.append(clean)
        job.bytes_captured += len(encoded) + 1  # +1 for newline

    def _finish(self, job: HelpRegenJob, exit_code: int) -> None:
        job.exit_code = exit_code
        job.completed_at = datetime.now(timezone.utc)
        job.status = "completed" if exit_code == 0 else "failed"


class HelpRegenBusyError(RuntimeError):
    """Raised when a regen job is requested while one is already running."""

    def __init__(self, current_id: str) -> None:
        super().__init__(f"regen job already in flight: {current_id}")
        self.current_id = current_id
