"""Bulletin source reader — active runs + archived terminal entries.

Reads the multi-actor bulletin under ``<attune_home>/bulletin/``.
Active entries become SourceItems with ``metadata.kind="active"``;
archived entries become items with ``metadata.kind="archived"`` and
their terminal status.

The reader must never raise — a missing bulletin dir, malformed
lines, or unreadable archive files all collapse to an empty
``SourceSummary`` with a stable hash.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from attune.bulletin.file_backend import FileBulletinBackend
from attune.bulletin.protocol import BulletinEntry
from attune.ops.config import attune_home

from ..result import SourceItem, SourceSummary

logger = logging.getLogger(__name__)

_SOURCE_ID = "bulletin"


def read(
    *,
    project_root: Path,
    since: datetime | None = None,
) -> SourceSummary:
    """Read active + archived bulletin entries.

    Args:
        project_root: Project root (unused — bulletin is per-user,
            not per-project). Kept for Protocol conformance.
        since: Optional cutoff for archive scan. Defaults to 24h
            ago when omitted. Active entries are always included
            regardless of ``since``.
    """
    started = time.perf_counter()

    cutoff = since if since is not None else _default_since()
    backend = FileBulletinBackend(attune_home() / "bulletin")

    try:
        active_entries = backend.read_active()
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: A reader that raises is a worse outcome than
        # one that returns empty — the curator orchestrator treats
        # both as "no signal" but only the latter doesn't crash the
        # parallel gather().
        logger.warning("bulletin: read_active failed: %s", exc)
        active_entries = []

    try:
        archived_entries = backend.read_archive(since=cutoff)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: same rationale as above.
        logger.warning("bulletin: read_archive failed: %s", exc)
        archived_entries = []

    items: list[SourceItem] = []
    now = datetime.now(timezone.utc)
    for entry in active_entries:
        items.append(_active_to_item(entry, now=now))
    for entry in archived_entries:
        items.append(_archived_to_item(entry))

    state_hash = _hash_entries(active_entries + archived_entries)
    fetch_ms = int((time.perf_counter() - started) * 1000)
    return SourceSummary(
        source_id=_SOURCE_ID,
        state_hash=state_hash,
        items=items,
        fetch_ms=fetch_ms,
    )


def _default_since() -> datetime:
    """24 hours before now, UTC."""
    from datetime import timedelta

    return datetime.now(timezone.utc) - timedelta(hours=24)


def _active_to_item(entry: BulletinEntry, *, now: datetime) -> SourceItem:
    heartbeat_dt = _parse_iso(entry.last_heartbeat)
    if heartbeat_dt is None:
        age_s = "unknown"
    else:
        age_s = str(int((now - heartbeat_dt).total_seconds()))
    title = f"{entry.workflow} ({entry.actor_kind}, {entry.actor_id})"
    detail = (
        f"Run {entry.run_id} started {entry.started_at}. Last heartbeat: {entry.last_heartbeat}."
    )
    if entry.scope:
        detail += f" Scope: {entry.scope}."
    return SourceItem(
        item_id=f"bulletin:active:{entry.run_id}",
        title=title,
        detail=_truncate(detail, 500),
        link=f"/runs/{entry.run_id}/view",
        metadata={
            "kind": "active",
            "actor_kind": entry.actor_kind,
            "actor_id": entry.actor_id,
            "workflow": entry.workflow,
            "heartbeat_age_s": age_s,
        },
    )


def _archived_to_item(entry: BulletinEntry) -> SourceItem:
    title = f"{entry.workflow} — {entry.current_status} ({entry.actor_kind})"
    detail = (
        f"Run {entry.run_id} terminal status: {entry.current_status}. "
        f"Started {entry.started_at}, last heartbeat {entry.last_heartbeat}."
    )
    if entry.scope:
        detail += f" Scope: {entry.scope}."
    return SourceItem(
        item_id=f"bulletin:archived:{entry.run_id}",
        title=title,
        detail=_truncate(detail, 500),
        link=f"/runs/{entry.run_id}/view",
        metadata={
            "kind": "archived",
            "actor_kind": entry.actor_kind,
            "actor_id": entry.actor_id,
            "workflow": entry.workflow,
            "terminal_status": entry.current_status,
        },
    )


def _hash_entries(entries: list[BulletinEntry]) -> str:
    """Deterministic hash over (run_id, last_heartbeat) pairs.

    Order-independent — sort before hashing so two reads with the
    same logical state always produce the same digest.
    """
    pairs = sorted((e.run_id, e.last_heartbeat) for e in entries)
    joined = "|".join(f"{rid}@{hb}" for rid, hb in pairs)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _truncate(s: str, limit: int) -> str:
    return s if len(s) <= limit else s[: limit - 1] + "…"
