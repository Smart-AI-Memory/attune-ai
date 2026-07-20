"""Canonical DiagnosisRecord loader (advanced-debugging-plugin RR-1).

Reads ``<ATTUNE_HOME|~/.attune>/telemetry/diagnosis_records.jsonl``
with the same purity discipline as the pipeline-learner corpus:
malformed lines and fixture-named workflows are counted drops, never
silent; records predating the cutover are ineligible. Writing goes
through ``TelemetryStore.log_diagnosis`` — this module never writes.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from attune.models.telemetry.data_models import DiagnosisRecord
from attune.models.telemetry.storage import _canonical_diagnoses_file
from attune.pipeline_learner.corpus import FIXTURE_NAMES

logger = logging.getLogger(__name__)

#: Diagnosis-stream cutover: the purity discipline exists from this
#: spec's Phase A ship date; nothing legitimate can predate it.
DIAGNOSIS_CUTOVER = datetime(2026, 7, 20, 0, 0, 0, tzinfo=timezone.utc)


@dataclass
class DiagnosisLoadStats:
    """Counted drops — drops are counted, never silent (RC-4 idiom)."""

    total_lines: int = 0
    eligible: int = 0
    dropped_malformed: int = 0
    dropped_fixture: int = 0
    dropped_pre_cutover: int = 0


def _parse_created_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _classify_line(line: str, cutover: datetime) -> DiagnosisRecord | str:
    """Parse one JSONL line, or return the drop-counter name."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return "dropped_malformed"
    if not isinstance(data, dict):
        return "dropped_malformed"
    name = data.get("workflow_name")
    created = _parse_created_at(data.get("created_at"))
    if not isinstance(name, str) or not name or created is None:
        return "dropped_malformed"
    if name in FIXTURE_NAMES:
        return "dropped_fixture"
    if created < cutover:
        return "dropped_pre_cutover"
    try:
        return DiagnosisRecord.from_dict(data)
    except (TypeError, ValueError):
        return "dropped_malformed"


def load_diagnoses(
    path: Path | None = None,
    *,
    cutover: datetime = DIAGNOSIS_CUTOVER,
) -> tuple[list[DiagnosisRecord], DiagnosisLoadStats]:
    """Load eligible diagnosis records plus counted drop stats."""
    stream = path if path is not None else _canonical_diagnoses_file()
    stats = DiagnosisLoadStats()
    records: list[DiagnosisRecord] = []
    if not stream.is_file():
        return records, stats
    try:
        lines = stream.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("diagnosis: store read failed: %s", exc)
        return records, stats
    for line in lines:
        if not line.strip():
            continue
        stats.total_lines += 1
        outcome = _classify_line(line, cutover)
        if isinstance(outcome, str):
            setattr(stats, outcome, getattr(stats, outcome) + 1)
            continue
        stats.eligible += 1
        records.append(outcome)
    return records, stats


def records_for_run(
    source_run_id: str,
    path: Path | None = None,
) -> list[DiagnosisRecord]:
    """Eligible diagnoses for one source run (RR-3 idempotency lookup)."""
    records, _stats = load_diagnoses(path)
    return [r for r in records if r.source_run_id == source_run_id]
