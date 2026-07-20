"""Bounded, deterministic evidence-pack assembly
(advanced-debugging-plugin RR-4/RR-5).

The pack is what every panel seat sees — identical, bounded, and
assembled in a fixed value order so truncation is deterministic:
run-record fields first (highest value), then the ops log tail, then
source excerpts, then recent git context. Priors are NOT part of this
module's output — they are a distinct evidence kind added by the
engine, never merged with observed evidence (RR-4).
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from attune.models.telemetry.data_models import DiagnosisEvidence, WorkflowRunRecord

logger = logging.getLogger(__name__)

#: Max lines of ops-run log carried as evidence.
LOG_TAIL_LINES = 40


def ops_log_tail(run_id: str, *, ops_runs_dir: Path | None = None) -> str | None:
    """Log tail from the ops dashboard's persisted run record, if any."""
    if ops_runs_dir is None:
        import os  # noqa: PLC0415

        home = os.environ.get("ATTUNE_HOME")
        attune_dir = Path(home).expanduser() if home else Path.home() / ".attune"
        ops_runs_dir = attune_dir / "ops" / "runs"
    if not ops_runs_dir.is_dir():
        return None
    for candidate in ops_runs_dir.glob(f"*/{run_id}.json"):
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        lines = data.get("lines")
        if isinstance(lines, list):
            return "\n".join(str(ln) for ln in lines[-LOG_TAIL_LINES:])
    return None


def recent_git_context(repo_root: Path | None = None, *, count: int = 5) -> str | None:
    """``git log --oneline -<count>`` for the repo, or None off-repo."""
    try:
        proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
            ["git", "log", "--oneline", f"-{count}"],
            cwd=str(repo_root) if repo_root else None,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def build_evidence_pack(
    run: WorkflowRunRecord,
    *,
    log_tail: str | None = None,
    source_excerpts: dict[str, str] | None = None,
    git_context: str | None = None,
    budget_bytes: int = 64 * 1024,
) -> list[DiagnosisEvidence]:
    """Assemble observed-evidence entries under a hard byte budget.

    Fixed value order: run record, log tail, source excerpts (sorted by
    path for determinism), git context. The entry that crosses the
    budget is truncated with a visible marker; later entries are
    dropped entirely — bounded beats complete for seat context.
    """
    candidates: list[tuple[str, str]] = [
        (
            "run-record",
            json.dumps(
                {
                    "run_id": run.run_id,
                    "workflow": run.workflow_name,
                    "trigger": run.trigger,
                    "started_at": run.started_at,
                    "success": run.success,
                    "error": run.error,
                    "tiers_used": run.tiers_used,
                },
                indent=2,
            ),
        )
    ]
    if log_tail:
        candidates.append(("log-tail", log_tail))
    for path in sorted(source_excerpts or {}):
        candidates.append((f"source:{path}", (source_excerpts or {})[path]))
    if git_context:
        candidates.append(("git-log", git_context))

    entries: list[DiagnosisEvidence] = []
    remaining = budget_bytes
    for source, content in candidates:
        size = len(content.encode("utf-8"))
        if size <= remaining:
            entries.append(DiagnosisEvidence(kind="observed", source=source, content=content))
            remaining -= size
            continue
        if remaining > 200:  # room for a useful truncated head
            clipped = content.encode("utf-8")[: remaining - 60].decode("utf-8", "ignore")
            entries.append(
                DiagnosisEvidence(
                    kind="observed",
                    source=source,
                    content=clipped + f"\n<TRUNCATED — budget {budget_bytes}B>",
                )
            )
        break  # budget exhausted: later entries dropped, deterministically
    return entries
