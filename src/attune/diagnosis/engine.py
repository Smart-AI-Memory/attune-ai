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
    """Find a run record by id in the canonical stream (newest wins)."""
    path = stream if stream is not None else _canonical_runs_file()
    if not path.is_file():
        return None
    found: WorkflowRunRecord | None = None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("diagnosis: run-stream read failed: %s", exc)
        return None
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
    return found


def diagnose(
    run_id: str,
    config: DiagnosisConfig | None = None,
    *,
    store: TelemetryStore | None = None,
    run_stream: Path | None = None,
    redis_client: Any = None,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] | None = None,
    repo_root: Path | None = None,
) -> DiagnosisRecord:
    """Diagnose one failed run end-to-end and persist the record.

    Raises:
        DiagnosisSourceError: Unknown run, non-failed run, or an
            ``attune-heal`` self-record (no diagnose-the-diagnosis).
    """
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
    )
    (store or TelemetryStore()).log_diagnosis(record)
    return record
