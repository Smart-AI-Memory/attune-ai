"""Discovery-sweep source reader — queue + questions buckets.

Walks persisted sweep results at ``<attune_home>/ops/sweep-results/``
and emits one ``SourceItem`` per finding in the ``queue`` and
``questions`` buckets. The ``rejected`` bucket is excluded — it's
already-filtered noise.

Each scope hashes to its own ``<digest>.json`` file (latest-only
semantics). Reader is read-only and tolerant of missing dir,
malformed JSON, and unknown schema versions.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.ops.config import attune_home

from ..result import SourceItem, SourceSummary

logger = logging.getLogger(__name__)

_SOURCE_ID = "sweep"
_DETAIL_CHAR_LIMIT = 500
_RESULTS_SUBDIR = ("ops", "sweep-results")
_MAX_ITEMS = 50  # mirror tasks.md "max 50 rows per source" guidance


def read(
    *,
    project_root: Path,
    since: datetime | None = None,
) -> SourceSummary:
    """Read sweep results across all scopes."""
    del since  # noqa: F841 — sweep results are latest-only, no since-window
    del project_root  # noqa: F841 — attune_home is per-user, not per-project

    started = time.perf_counter()
    results_dir = attune_home().joinpath(*_RESULTS_SUBDIR)

    if not results_dir.is_dir():
        return _empty_summary(started)

    try:
        files = sorted(results_dir.glob("*.json"))
    except OSError as exc:
        logger.warning("sweep: cannot list %s: %s", results_dir, exc)
        return _empty_summary(started)

    items: list[SourceItem] = []
    for path in files:
        items.extend(_items_from_file(path))
        if len(items) >= _MAX_ITEMS:
            items = items[:_MAX_ITEMS]
            break

    state_hash = _hash_items(items)
    fetch_ms = int((time.perf_counter() - started) * 1000)
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=state_hash,
        items=items,
        fetch_ms=fetch_ms,
    )


def _items_from_file(path: Path) -> list[SourceItem]:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("sweep: skipping malformed %s: %s", path, exc)
        return []
    if not isinstance(data, dict):
        return []

    scope_digest = path.stem
    out: list[SourceItem] = []
    for finding in _iter_findings(data, bucket="queue"):
        out.append(_finding_to_item(finding, bucket="queue", scope=scope_digest))
    for finding in _iter_findings(data, bucket="questions"):
        out.append(_finding_to_item(finding, bucket="questions", scope=scope_digest))
    return out


def _iter_findings(data: dict[str, Any], *, bucket: str):
    rows = data.get(bucket)
    if not isinstance(rows, list):
        return
    for row in rows:
        # Question entries wrap the finding; queue entries are findings directly.
        if isinstance(row, dict) and "finding" in row and isinstance(row["finding"], dict):
            payload = dict(row["finding"])
            payload["_question_reason"] = str(row.get("reason", ""))
            payload["_question_next_step"] = str(row.get("next_step", ""))
            yield payload
        elif isinstance(row, dict):
            yield row


def _finding_to_item(finding: dict[str, Any], *, bucket: str, scope: str) -> SourceItem:
    title = str(finding.get("title") or "(untitled finding)")
    source = str(finding.get("source") or "unknown")
    severity = str(finding.get("severity") or "info")
    description = str(finding.get("description") or "")
    file_ref = finding.get("file")
    line_ref = finding.get("line")

    detail_parts = [f"[{source}/{severity}] {description}"]
    if file_ref:
        location = f"{file_ref}:{line_ref}" if line_ref else str(file_ref)
        detail_parts.append(f"at {location}")
    if bucket == "questions":
        reason = finding.get("_question_reason")
        if reason:
            detail_parts.append(f"question: {reason}")
    detail = " ".join(detail_parts)

    metadata = {
        "bucket": bucket,
        "source": source,
        "severity": severity,
        "scope": scope,
    }
    if file_ref:
        metadata["file"] = str(file_ref)

    item_id = _stable_finding_id(scope, bucket, finding)
    return SourceItem(
        item_id=item_id,
        title=_truncate(title, 150),
        detail=_truncate(detail, _DETAIL_CHAR_LIMIT),
        link=f"/sweep-results/{scope}#{bucket}",
        metadata=metadata,
    )


def _stable_finding_id(scope: str, bucket: str, finding: dict[str, Any]) -> str:
    """Build a stable id from scope + bucket + finding signature.

    Findings don't carry a server-side id, so we hash the salient
    fields. Same finding across reads → same id.
    """
    sig = "|".join(
        [
            scope,
            bucket,
            str(finding.get("source") or ""),
            str(finding.get("title") or ""),
            str(finding.get("file") or ""),
            str(finding.get("line") or ""),
        ]
    )
    digest = hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]
    return f"sweep:{bucket}:{digest}"


def _hash_items(items: list[SourceItem]) -> str:
    rows = sorted(item.item_id for item in items)
    return hashlib.sha256("|".join(rows).encode("utf-8")).hexdigest()[:16]


def _empty_summary(started: float) -> SourceSummary:
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=hashlib.sha256(b"").hexdigest()[:16],
        items=[],
        fetch_ms=int((time.perf_counter() - started) * 1000),
    )


def _truncate(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[: limit - 1] + "…"
