"""Spec-drift source reader (spec-lifecycle-gates RR-6).

Surfaces specs whose declared status has drifted from observable
reality, as curator candidates for CHAIR triage — the
starter-reconciler pattern as a `SourceReader`. Non-mutating,
must-not-raise, event-armed by whoever runs the curator (never a
background sweep).

v1 drift classes, derived from the shipped lifecycle buckets
(``attune.ops.specs_data.SpecRecord.lifecycle``):

- ``stale`` — a spec claiming active work with no file activity for
  the staleness window.
- ``approved-not-shipped`` — an approved design/tasks doc with no
  execution evidence.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path

from attune.ops.specs_data import _list_specs_in_root

from ..result import SourceItem, SourceSummary

logger = logging.getLogger(__name__)

_SOURCE_ID = "spec_drift"
_DRIFT_BUCKETS: frozenset[str] = frozenset({"stale", "approved-not-shipped"})


def read(
    *,
    project_root: Path,
    since: datetime | None = None,
) -> SourceSummary:
    """Return drifted specs as candidates (RR-6; must not raise).

    Args:
        project_root: Repository root; specs at ``docs/specs/``.
        since: Unused — Protocol conformance (drift is a state, not
            an event stream).
    """
    started = time.monotonic()
    items: list[SourceItem] = []
    try:
        records = _list_specs_in_root(project_root / "docs" / "specs")
        for record in records:
            bucket = getattr(record, "lifecycle", None)
            if bucket not in _DRIFT_BUCKETS:
                continue
            newest = record.phases[-1] if record.phases else None
            status = getattr(newest, "status", None) or "(no status)"
            items.append(
                SourceItem(
                    item_id=f"spec-drift:{record.slug}",
                    title=f"{record.slug}: {bucket}",
                    detail=(
                        f"lifecycle bucket '{bucket}'; declared status "
                        f"{status!r}; last modified {record.last_modified}"
                    )[:500],
                    link=f"docs/specs/{record.slug}/",
                )
            )
    except Exception:  # noqa: BLE001
        # INTENTIONAL: SourceReader contract — never raise; an
        # unreadable tree yields an empty, stably-hashed summary.
        logger.debug("spec_drift: read failed", exc_info=True)
        items = []
    digest = hashlib.sha256(
        "\n".join(sorted(f"{i.item_id}|{i.title}" for i in items)).encode("utf-8")
    ).hexdigest()[:16]
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=digest,
        items=items,
        fetch_ms=int((time.monotonic() - started) * 1000),
    )
