"""Recommendations source reader — pending ATTUNE_REC cards.

Walks persisted run records under ``<attune_home>/ops/runs/<workflow>/``
and extracts each run's ``recommendations: [...]`` array. Each
recommendation becomes one ``SourceItem`` so the curator can rank
unresolved cards alongside other signals.

Filters to runs whose newest mtime is within the configured window
(default 24h) — older recommendations have presumably been
seen-and-ignored or actioned.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from attune.ops.config import attune_home

from ..result import SourceItem, SourceSummary

logger = logging.getLogger(__name__)

_SOURCE_ID = "recommendations"
_DETAIL_CHAR_LIMIT = 500
_MAX_ITEMS = 50
_RUNS_SUBDIR = ("ops", "runs")


def read(
    *,
    project_root: Path,
    since: datetime | None = None,
) -> SourceSummary:
    """Surface pending recommendation cards from recent run records."""
    del project_root  # noqa: F841 — runs live under attune_home, not per-project

    started = time.perf_counter()
    runs_dir = attune_home().joinpath(*_RUNS_SUBDIR)
    cutoff = since if since is not None else _default_since()

    if not runs_dir.is_dir():
        return _empty_summary(started)

    try:
        workflow_dirs = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    except OSError as exc:
        logger.warning("recommendations: cannot list %s: %s", runs_dir, exc)
        return _empty_summary(started)

    items: list[SourceItem] = []
    for workflow_dir in workflow_dirs:
        for record_path in _recent_records(workflow_dir, cutoff):
            items.extend(_items_from_record(workflow=workflow_dir.name, record_path=record_path))
            if len(items) >= _MAX_ITEMS:
                items = items[:_MAX_ITEMS]
                break
        if len(items) >= _MAX_ITEMS:
            break

    state_hash = _hash_items(items)
    fetch_ms = int((time.perf_counter() - started) * 1000)
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=state_hash,
        items=items,
        fetch_ms=fetch_ms,
    )


def _recent_records(workflow_dir: Path, cutoff: datetime) -> list[Path]:
    cutoff_ts = cutoff.timestamp()
    try:
        files = list(workflow_dir.glob("*.json"))
    except OSError as exc:
        logger.debug("recommendations: glob %s failed: %s", workflow_dir, exc)
        return []
    fresh: list[Path] = []
    for path in files:
        # `*.json` glob already excludes `*.json.tmp` atomic-write
        # leftovers, so no extra .tmp filter needed here.
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= cutoff_ts:
            fresh.append(path)
    fresh.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return fresh


def _items_from_record(*, workflow: str, record_path: Path) -> list[SourceItem]:
    try:
        raw = record_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("recommendations: skipping %s: %s", record_path, exc)
        return []
    if not isinstance(data, dict):
        return []

    recommendations = data.get("recommendations")
    if not isinstance(recommendations, list) or not recommendations:
        return []

    run_id = record_path.stem
    out: list[SourceItem] = []
    for idx, rec in enumerate(recommendations):
        if not isinstance(rec, dict):
            continue
        kind = str(rec.get("kind") or "open")
        label = str(rec.get("label") or rec.get("title") or "Recommendation")
        detail = _format_detail(rec)
        out.append(
            SourceItem(
                item_id=f"rec:{workflow}:{run_id}:{idx}",
                title=_truncate(f"{workflow}: {label}", 150),
                detail=_truncate(detail, _DETAIL_CHAR_LIMIT),
                link=f"/runs/{run_id}/view",
                metadata={
                    "workflow": workflow,
                    "run_id": run_id,
                    "kind": kind,
                },
            )
        )
    return out


def _format_detail(rec: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("kind", "label", "title", "description", "url", "workflow", "scope"):
        v = rec.get(key)
        if v:
            parts.append(f"{key}={v}")
    return "; ".join(parts) if parts else json.dumps(rec, sort_keys=True)[:_DETAIL_CHAR_LIMIT]


def _default_since() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=24)


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
