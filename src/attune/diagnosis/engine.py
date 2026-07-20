"""Diagnosis engine — load, priors, evidence, panel, persist
(advanced-debugging-plugin RR-4/RR-5, design.md §3).

``diagnose(run_id)`` is the one entry point the CLI, the ops endpoint
(Phase C), and the triage routine (Phase D) all call. Every stage
writes into the DiagnosisRecord as it goes; the record persists even
when later stages degrade — a diagnosis with an absent panel is still
a diagnosis.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attune.models.telemetry.data_models import (
    DiagnosisEvidence,
    DiagnosisRecord,
    WorkflowRunRecord,
)
from attune.models.telemetry.storage import TelemetryStore, _canonical_runs_file

from .config import DiagnosisConfig
from .evidence import build_evidence_pack, ops_log_tail, recent_git_context
from .panel import convene_panel
from .priors import extract_error_terms, recall_priors

logger = logging.getLogger(__name__)


class DiagnosisSourceError(ValueError):
    """The named run cannot be diagnosed (missing, succeeded, or heal)."""


def find_source_run(run_id: str, *, stream: Path | None = None) -> WorkflowRunRecord | None:
    """Find a run record by id — canonical stream first, ops store second.

    Dashboard (ops) run ids and telemetry run ids are DIFFERENT id
    spaces: the runner allocates 12-hex ids while the telemetry seam
    allocates uuid4. The run-view "Why did this fail?" button hands us
    an ops id, so a miss in the canonical stream falls back to the
    persisted ops record, synthesized into a ``WorkflowRunRecord``
    (design deviation recorded in decisions.md, Phase C).
    """
    path = stream if stream is not None else _canonical_runs_file()
    found: WorkflowRunRecord | None = None
    if path.is_file():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            logger.warning("diagnosis: run-stream read failed: %s", exc)
            lines = []
        for line in lines:
            if not line.strip() or f'"{run_id}"' not in line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("run_id") == run_id:
                try:
                    found = WorkflowRunRecord.from_dict(data)
                except (TypeError, ValueError):
                    continue
    if found is not None or stream is not None:
        return found
    return _source_from_ops_record(run_id)


def _source_from_ops_record(run_id: str) -> WorkflowRunRecord | None:
    """Synthesize a source record from a persisted ops dashboard run."""
    import os  # noqa: PLC0415

    home = os.environ.get("ATTUNE_HOME")
    attune_dir = Path(home).expanduser() if home else Path.home() / ".attune"
    for candidate in (attune_dir / "ops" / "runs").glob(f"*/{run_id}.json"):
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        exit_code = data.get("exit_code")
        return WorkflowRunRecord(
            run_id=run_id,
            workflow_name=str(data.get("workflow") or "unknown"),
            started_at=str(data.get("started_at") or ""),
            trigger=(data.get("trigger") if isinstance(data.get("trigger"), str) else None),
            success=data.get("status") == "completed" and exit_code == 0,
            error=(
                str(data.get("sdk_stderr"))
                if data.get("sdk_stderr")
                else f"ops run failed (exit {exit_code}, sdk_error_kind="
                f"{data.get('sdk_error_kind')})"
            ),
        )
    return None


def _emit_heal_run_record(store: TelemetryStore, started: datetime, completed: datetime) -> None:
    """Emit the engine's own heal-stamped canonical run record.

    ``attune diagnose`` is a CLI command, not a workflow — RC-2's
    execute-wrapper seam has nothing to stamp, so the engine emits its
    own ``WorkflowRunRecord`` after a diagnosis persists (v1.1 backlog
    item (a)): without it the mining exclusion guards an empty set.
    ``trigger`` is the ``attune-heal`` CONSTANT, never the env
    resolver — a diagnostic run is a self-record by construction,
    regardless of how it was launched. Best-effort: an emission
    failure never fails the diagnosis itself.
    """
    from attune.models.telemetry.run_context import (  # noqa: PLC0415
        resolve_project_identity,
    )

    record = WorkflowRunRecord(
        run_id=str(uuid.uuid4()),
        workflow_name="diagnose",
        started_at=started.isoformat(),
        completed_at=completed.isoformat(),
        trigger="attune-heal",
        project=resolve_project_identity(),
        success=True,
        total_duration_ms=max(0, int((completed - started).total_seconds() * 1000)),
    )
    try:
        store.log_workflow(record)
    except OSError as exc:
        logger.warning("diagnosis: heal run-record emission failed: %s", exc)


def diagnose(
    run_id: str,
    config: DiagnosisConfig | None = None,
    *,
    store: TelemetryStore | None = None,
    run_stream: Path | None = None,
    redis_client: Any = None,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] | None = None,
    repo_root: Path | None = None,
    origin: str = "operational",
) -> DiagnosisRecord:
    """Diagnose one failed run end-to-end and persist the record.

    A completed diagnosis also emits a heal-stamped run record into
    the canonical stream; a diagnose that raises emits nothing —
    not a run (RC-2's precedent).

    Raises:
        DiagnosisSourceError: Unknown run, non-failed run, or an
            ``attune-heal`` self-record (no diagnose-the-diagnosis).
    """
    started = datetime.now(timezone.utc)
    config = config or DiagnosisConfig.from_env()
    run = find_source_run(run_id, stream=run_stream)
    if run is None:
        raise DiagnosisSourceError(f"run {run_id!r} not found in the canonical stream")
    if run.success:
        raise DiagnosisSourceError(f"run {run_id!r} succeeded — nothing to diagnose")
    if run.trigger == "attune-heal":
        raise DiagnosisSourceError(f"run {run_id!r} is a diagnostic self-record")

    symptom = str(run.error or f"workflow {run.workflow_name} failed")

    # Priors BEFORE evidence gathering (RR-4) — degraded is explicit.
    priors = recall_priors(
        extract_error_terms(f"{symptom} {run.workflow_name}"), client=redis_client
    )

    evidence = build_evidence_pack(
        run,
        log_tail=ops_log_tail(run_id),
        git_context=recent_git_context(repo_root),
        budget_bytes=config.evidence_budget_bytes,
    )
    # Priors ride as a DISTINCT evidence kind — never merged (RR-4).
    prior_entries = [
        DiagnosisEvidence(kind="prior", source="lesson", content=lesson)
        for lesson in priors.lessons
    ]

    panel_kwargs: dict[str, Any] = {}
    if invoke_seat is not None:
        panel_kwargs["invoke_seat"] = invoke_seat
    panel = convene_panel(evidence, priors, config, **panel_kwargs)

    record = DiagnosisRecord(
        diagnosis_id=uuid.uuid4().hex[:12],
        source_run_id=run_id,
        workflow_name=run.workflow_name,
        created_at=datetime.now(timezone.utc).isoformat(),
        symptom=symptom,
        prior_lessons=priors.lessons,
        priors_degraded=priors.degraded,
        evidence=prior_entries + evidence,
        hypotheses=panel.hypotheses,
        synthesis=panel.synthesis,
        dissent=panel.dissent,
        panel=panel.meta,
        config_used=config.to_config_used(),
        origin=origin,
    )
    telemetry_store = store or TelemetryStore()
    telemetry_store.log_diagnosis(record)
    _emit_heal_run_record(telemetry_store, started, datetime.now(timezone.utc))
    return record
