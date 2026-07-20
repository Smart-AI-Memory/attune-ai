"""Diagnosis source reader (advanced-debugging-plugin RR-8, Phase D).

Read-only curator grounding over eligible ``DiagnosisRecord`` entries:
downstream reporting consumes diagnoses through this seam instead of
reading raw persistence files. Redaction is by ALLOWLIST — proposed
diffs and raw evidence content never appear; only provenance, status,
confidence, verification state, lesson refs, and dissent counts do.
Non-mutating, must-not-raise.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path

from ..result import SourceItem, SourceSummary

logger = logging.getLogger(__name__)

_SOURCE_ID = "diagnoses"


def read(
    *,
    project_root: Path,
    since: datetime | None = None,
) -> SourceSummary:
    """Return eligible diagnoses as curator items (must not raise).

    Args:
        project_root: Unused (the diagnosis store is home-global);
            Protocol conformance.
        since: Unused — eligibility is the store's purity rules.
    """
    started = time.monotonic()
    items: list[SourceItem] = []
    try:
        from attune.diagnosis import load_diagnoses  # noqa: PLC0415

        records, stats = load_diagnoses()
        for record in records:
            top = record.hypotheses[0] if record.hypotheses else None
            # ALLOWLIST rendering — never diff or raw evidence content.
            detail_parts = [
                f"status: {record.status}",
                f"confidence: {top.confidence if top else 'none'}",
                f"hypotheses: {len(record.hypotheses)}",
                f"dissent: {len(record.dissent)}",
                f"fix: {record.proposed_fix.get('disposition', 'none')}",
            ]
            if record.prior_lessons:
                detail_parts.append(f"lesson refs: {len(record.prior_lessons)}")
            if record.priors_degraded:
                detail_parts.append(f"priors degraded: {record.priors_degraded}")
            items.append(
                SourceItem(
                    item_id=f"diagnosis:{record.diagnosis_id}",
                    title=(record.symptom or record.workflow_name)[:80],
                    detail="; ".join(detail_parts),
                    link=f"/runs/{record.source_run_id}/view",
                    metadata={
                        "workflow": record.workflow_name,
                        "source_run_id": record.source_run_id,
                        "created_at": record.created_at,
                    },
                )
            )
        digest = hashlib.sha256(
            "|".join(sorted(i.item_id for i in items)).encode("utf-8")
        ).hexdigest()[:16]
    except Exception:  # noqa: BLE001 — reader must not raise (curator contract)
        logger.exception("diagnoses source read failed")
        return SourceSummary(source_id=_SOURCE_ID, state_hash="error", items=[])
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=digest,
        items=items,
        fetch_ms=int((time.monotonic() - started) * 1000),
    )
