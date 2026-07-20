"""Opt-in failed-run triage (advanced-debugging-plugin RR-7, Phase D).

Manual command ONLY in v1 (the panel's 2-1 binding): batch-diagnose
the newest undiagnosed failures, cluster repeated hypotheses without
merging conflicting evidence, and post a digest thread to the board.
R8 is absolute — the routine never promotes, never writes tracked
files, and never touches ``attune-heal`` self-records.

Run it with::

    python -m attune.diagnosis.triage [--limit N] [--dry-run]

Deviation from tasks.md (recorded in decisions.md): NOT registered in
``attune.roundtable.routine.ROUTINES`` — the routine runner's
check-battery shape doesn't fit a diagnosis batch, and standalone
keeps the manual-only binding structurally true (no scheduler can
discover it).
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path

from attune.models.telemetry.data_models import DiagnosisRecord, WorkflowRunRecord
from attune.models.telemetry.storage import _canonical_runs_file

from .config import DiagnosisConfig
from .store import records_for_run

logger = logging.getLogger(__name__)


def select_failed_runs(
    stream: Path | None = None,
    *,
    limit: int = 5,
    already_diagnosed: Callable[[str], bool] | None = None,
) -> list[WorkflowRunRecord]:
    """Newest-first undiagnosed failures, excluding attune-heal (RR-7).

    Args:
        stream: Run stream override (tests); default canonical.
        limit: Batch cap (``triage_batch_max``).
        already_diagnosed: Predicate; default checks the diagnosis store.
    """
    path = stream if stream is not None else _canonical_runs_file()
    if already_diagnosed is None:
        already_diagnosed = lambda run_id: bool(records_for_run(run_id))  # noqa: E731
    if not path.is_file():
        return []
    selected: list[WorkflowRunRecord] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("triage: run-stream read failed: %s", exc)
        return []
    for line in reversed(lines):  # newest first
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or data.get("success") is not False:
            continue
        if data.get("trigger") == "attune-heal":
            continue  # self-records are never triaged
        run_id = data.get("run_id")
        if not isinstance(run_id, str) or already_diagnosed(run_id):
            continue
        try:
            selected.append(WorkflowRunRecord.from_dict(data))
        except (TypeError, ValueError):
            continue
        if len(selected) >= limit:
            break
    return selected


def cluster_by_hypothesis(records: list[DiagnosisRecord]) -> list[list[DiagnosisRecord]]:
    """Group diagnoses whose TOP hypotheses materially agree.

    Conflicting evidence is never merged — clustering only groups
    records for digest layout; every record keeps its own entry.
    """
    from .panel import _overlaps  # noqa: PLC0415 — shared token heuristic

    clusters: list[list[DiagnosisRecord]] = []
    for record in records:
        top = record.hypotheses[0].statement if record.hypotheses else record.symptom
        for cluster in clusters:
            head = cluster[0]
            head_top = head.hypotheses[0].statement if head.hypotheses else head.symptom
            if _overlaps(top, head_top):
                cluster.append(record)
                break
        else:
            clusters.append([record])
    return clusters


def render_digest(clusters: list[list[DiagnosisRecord]], *, selected: int) -> str:
    """Deterministic digest — every conclusion links its DiagnosisRecord."""
    lines = [f"failed-run triage: {selected} run(s) diagnosed, {len(clusters)} cluster(s)"]
    for i, cluster in enumerate(clusters, 1):
        head = cluster[0]
        top = head.hypotheses[0].statement if head.hypotheses else head.symptom
        lines.append(f"\n## Cluster {i} ({len(cluster)} run(s)): {top}")
        for record in cluster:
            lines.append(
                f"- diagnosis {record.diagnosis_id} <- run {record.source_run_id} "
                f"({record.workflow_name}); dissent: {len(record.dissent)}"
            )
    lines.append("\nNo promotion: chair review required for every conclusion (R8).")
    return "\n".join(lines)


def run_triage(
    config: DiagnosisConfig | None = None,
    *,
    stream: Path | None = None,
    diagnose_fn: Callable[..., DiagnosisRecord] | None = None,
    post_to_board: bool = True,
    now: datetime | None = None,
) -> str:
    """Diagnose the batch and post the digest thread. Returns the digest."""
    from .engine import DiagnosisSourceError, diagnose  # noqa: PLC0415 — avoid cycle

    config = config or DiagnosisConfig.from_env()
    diagnose_fn = diagnose_fn or diagnose
    selected = select_failed_runs(stream, limit=config.triage_batch_max)
    diagnosed: list[DiagnosisRecord] = []
    for run in selected:
        try:
            diagnosed.append(diagnose_fn(run.run_id, config))
        except DiagnosisSourceError as exc:
            logger.warning("triage: skipping %s: %s", run.run_id, exc)
    digest = render_digest(cluster_by_hypothesis(diagnosed), selected=len(diagnosed))

    if post_to_board and diagnosed:
        stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
        try:
            from attune.roundtable import Board  # noqa: PLC0415 — optional dep

            Board().post_message(
                f"routine-failed-run-triage-{stamp}", "moderator", "synthesis", digest
            )
        except Exception as exc:  # noqa: BLE001 — board-down never loses the digest
            logger.warning("triage: board post failed (digest printed only): %s", exc)
    return digest


def main(argv: Sequence[str] | None = None) -> int:
    """Manual entry point — the ONLY v1 invocation surface."""
    parser = argparse.ArgumentParser(description="Batch-diagnose recent failed runs")
    parser.add_argument("--limit", type=int, default=None, help="Batch cap override")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Select and print the batch without diagnosing (no LLM spend)",
    )
    args = parser.parse_args(argv)
    config = DiagnosisConfig.from_env()
    if args.limit and args.limit > 0:
        config.triage_batch_max = args.limit
    if args.dry_run:
        selected = select_failed_runs(limit=config.triage_batch_max)
        print(f"would diagnose {len(selected)} run(s):")
        for run in selected:
            print(f"- {run.run_id} ({run.workflow_name}): {run.error}")
        return 0
    print(run_triage(config))
    return 0


if __name__ == "__main__":  # pragma: no cover — manual entry point
    raise SystemExit(main())
