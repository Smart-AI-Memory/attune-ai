"""Diagnosis re-annotation (D18): update by re-append, never rewrite.

The canonical stream is append-only and ``store.py`` never writes;
updates go through ``TelemetryStore.log_diagnosis`` as a re-appended
full record with the SAME ``diagnosis_id`` — the loader's last-wins
dedupe makes the newest line authoritative and counts the superseded
one. Tagging a record's ``origin`` as dogfood/live-fire closes it for
briefing purposes (the diagnoses curator source surfaces operational
records only), so nothing is deleted and the status enum stays
closed.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from attune.models.telemetry.data_models import DiagnosisRecord
from attune.models.telemetry.storage import TelemetryStore

from .store import load_diagnoses

ORIGINS = ("operational", "dogfood", "live-fire")


def retag_origin(
    diagnosis_id: str,
    origin: str,
    *,
    store: TelemetryStore | None = None,
    path: Path | None = None,
) -> DiagnosisRecord | None:
    """Re-append the named record with ``origin`` set; return the copy.

    Returns None when the id is unknown. Raises ValueError on an
    origin outside the D18 vocabulary.
    """
    if origin not in ORIGINS:
        raise ValueError(f"unknown origin {origin!r} (D18 vocabulary: {ORIGINS})")
    records, _stats = load_diagnoses(path)
    current = next((r for r in records if r.diagnosis_id == diagnosis_id), None)
    if current is None:
        return None
    updated = dataclasses.replace(current, origin=origin)
    (store or TelemetryStore()).log_diagnosis(updated)
    return updated
