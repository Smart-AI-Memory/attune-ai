"""Telemetry source reader — cost spikes + recent errors.

Two cheap heuristics over ``<attune_home>/telemetry/usage.jsonl``:

* per-workflow cost spike: today's total spend on a workflow is >2σ
  above its 7-day mean (skip workflows with <3 events in the window —
  too few samples to reason about variance);
* recent error: any event in the last hour with ``error`` truthy or
  ``status`` matching an HTTP 4xx/5xx code.

Both signals cap at 10 items per :class:`SourceSummary` to keep the
prompt budget bounded.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from attune.ops.config import attune_home

from ..result import SourceItem, SourceSummary

logger = logging.getLogger(__name__)

_SOURCE_ID = "telemetry"
_DETAIL_CHAR_LIMIT = 500
_MAX_ITEMS = 10
_WINDOW_DAYS = 7


def read(
    *,
    project_root: Path,
    since: datetime | None = None,
) -> SourceSummary:
    """Surface cost + error anomalies from usage.jsonl."""
    del project_root  # noqa: F841 — telemetry is per-user, not per-project

    started = time.perf_counter()
    path = attune_home() / "telemetry" / "usage.jsonl"
    cutoff = since if since is not None else _default_since()

    if not path.is_file():
        return _empty_summary(started)

    events = _read_events(path, cutoff)
    if not events:
        return _empty_summary(started)

    items: list[SourceItem] = []
    items.extend(_cost_spike_items(events))
    items.extend(_recent_error_items(events))
    items = items[:_MAX_ITEMS]

    state_hash = _hash_items(items)
    fetch_ms = int((time.perf_counter() - started) * 1000)
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=state_hash,
        items=items,
        fetch_ms=fetch_ms,
    )


def _read_events(path: Path, cutoff: datetime) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                ts_str = event.get("ts") or event.get("timestamp")
                dt = _parse_iso(str(ts_str)) if ts_str else None
                if dt is None or dt < cutoff:
                    continue
                event["_dt"] = dt
                out.append(event)
    except OSError as exc:
        logger.warning("telemetry: read %s failed: %s", path, exc)
    return out


def _cost_spike_items(events: list[dict[str, Any]]) -> list[SourceItem]:
    """Emit one item per workflow whose today's spend is >2σ above the
    7-day mean. Skips workflows with <3 events (insufficient samples)."""
    now = datetime.now(timezone.utc)
    today = now.date()
    daily_by_workflow: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for event in events:
        workflow = str(event.get("workflow") or event.get("event_type") or "unknown")
        cost = _safe_float(event.get("total_cost") or event.get("cost") or 0.0)
        dt: datetime = event["_dt"]
        day_iso = dt.date().isoformat()
        daily_by_workflow[workflow][day_iso] += cost

    out: list[SourceItem] = []
    today_iso = today.isoformat()
    for workflow, by_day in daily_by_workflow.items():
        today_cost = by_day.get(today_iso, 0.0)
        prior = [c for day, c in by_day.items() if day != today_iso]
        if len(prior) < 3:
            continue
        mean = sum(prior) / len(prior)
        variance = sum((c - mean) ** 2 for c in prior) / len(prior)
        stddev = math.sqrt(variance) if variance > 0 else 0.0
        if stddev == 0:
            continue
        z = (today_cost - mean) / stddev
        if z <= 2.0:
            continue
        detail = (
            f"Today's {workflow} spend ${today_cost:.2f} is {z:.1f}σ above "
            f"the 7-day mean ${mean:.2f} (stddev ${stddev:.2f})."
        )
        out.append(
            SourceItem(
                item_id=f"telemetry:cost-spike:{workflow}:{today_iso}",
                title=f"{workflow}: cost spike (+{z:.1f}σ)",
                detail=_truncate(detail, _DETAIL_CHAR_LIMIT),
                link="/telemetry",
                metadata={
                    "kind": "cost_spike",
                    "workflow": workflow,
                    "today_cost_usd": f"{today_cost:.4f}",
                    "mean_cost_usd": f"{mean:.4f}",
                    "z_score": f"{z:.2f}",
                },
            )
        )
    return out


def _recent_error_items(events: list[dict[str, Any]]) -> list[SourceItem]:
    """Emit items for 4xx/5xx or ``error`` events in the last hour."""
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    out: list[SourceItem] = []
    for event in events:
        dt: datetime = event["_dt"]
        if dt < one_hour_ago:
            continue
        if not _is_error(event):
            continue
        workflow = str(event.get("workflow") or event.get("event_type") or "unknown")
        status = event.get("status")
        error_msg = event.get("error") or event.get("error_message") or ""
        ts_iso = dt.isoformat()
        detail = f"{workflow} error at {ts_iso} (status={status}): {str(error_msg)[:300]}"
        digest = hashlib.sha256(f"{workflow}|{ts_iso}|{status}".encode()).hexdigest()[:12]
        out.append(
            SourceItem(
                item_id=f"telemetry:error:{digest}",
                title=f"{workflow}: error (status={status})",
                detail=_truncate(detail, _DETAIL_CHAR_LIMIT),
                link="/telemetry",
                metadata={
                    "kind": "error",
                    "workflow": workflow,
                    "status": str(status) if status is not None else "",
                    "timestamp": ts_iso,
                },
            )
        )
    return out


def _is_error(event: dict[str, Any]) -> bool:
    if event.get("error"):
        return True
    status = event.get("status")
    if isinstance(status, int) and 400 <= status < 600:
        return True
    if isinstance(status, str) and status.isdigit():
        n = int(status)
        if 400 <= n < 600:
            return True
    return False


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _parse_iso(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _default_since() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=_WINDOW_DAYS)


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
