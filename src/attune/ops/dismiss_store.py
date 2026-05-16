"""Persistence for dismissed spec completion candidates.

Spec: ``docs/specs/ops-specs-completion-candidates/`` (T1 in tasks).

Stores user "dismiss this candidate" decisions in a single JSON file
at ``<attune_home>/ops/spec_completion_dismissed.json``. Each entry
records when the candidate was dismissed, the snapshot hash of the
signals at dismissal time, and the TTL.

A dismiss is "active" (i.e. suppresses the candidate) iff all of:

1. The slug exists in the store.
2. The stored snapshot hash matches the current snapshot hash. When
   it differs, new signal has landed since dismissal — the candidate
   should re-surface immediately, regardless of TTL.
3. ``now < entry.dismissed_at + entry.ttl_days``.

Any condition's failure → not active → candidate re-surfaces.

Schema (v1)::

    {
      "version": 1,
      "dismissed": {
        "<slug>": {
          "dismissed_at": "2026-05-15T18:30:00+00:00",
          "snapshot_hash": "<hex>",
          "ttl_days": 14
        }
      }
    }

Writes are atomic via ``tempfile`` + ``os.replace`` in the same
directory (cross-platform safe per
``.claude/CLAUDE.md`` "Path.rename Windows" lesson). Reads are
lazy per call — the file is small enough that re-reading per call
is cheaper than coordinating cache invalidation.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from attune.ops.config import Config

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
STORE_FILENAME = "spec_completion_dismissed.json"
STORE_SUBDIR = ("ops",)
DEFAULT_TTL_DAYS = 14


@dataclass(frozen=True)
class DismissEntry:
    """One dismissed candidate's persisted state."""

    dismissed_at: datetime  # timezone-aware UTC
    snapshot_hash: str
    ttl_days: int


def store_path(config: Config) -> Path:
    """Return the absolute path to the dismiss-store JSON file.

    Does NOT create the file or its parent directory — that's the
    save side's responsibility, so reads on a fresh install don't
    spuriously mkdir.
    """
    return config.attune_home.joinpath(*STORE_SUBDIR, STORE_FILENAME)


def load(config: Config) -> dict[str, DismissEntry]:
    """Read the dismiss store. Missing or corrupt file → ``{}``.

    Corruption modes handled (all log at WARN and return ``{}`` —
    a corrupt store should never block the dashboard):

    - File doesn't exist
    - Unreadable (PermissionError / OSError)
    - Not valid JSON
    - Wrong schema version
    - Missing top-level ``dismissed`` key
    - Per-entry malformed fields (bad date, missing keys, wrong types)
      — that entry is skipped, other entries still load
    """
    path = store_path(config)
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("dismiss store unreadable at %s: %s", path, exc)
        return {}
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("dismiss store has invalid JSON at %s: %s", path, exc)
        return {}
    if not isinstance(raw, dict):
        logger.warning("dismiss store at %s is not a JSON object", path)
        return {}
    version = raw.get("version")
    if version != SCHEMA_VERSION:
        logger.warning(
            "dismiss store at %s has unsupported version %r (expected %r)",
            path,
            version,
            SCHEMA_VERSION,
        )
        return {}
    dismissed = raw.get("dismissed")
    if not isinstance(dismissed, dict):
        logger.warning("dismiss store at %s missing 'dismissed' object", path)
        return {}

    entries: dict[str, DismissEntry] = {}
    for slug, payload in dismissed.items():
        entry = _parse_entry(payload)
        if entry is None:
            logger.warning("dismiss store entry for %r is malformed, skipping", slug)
            continue
        entries[slug] = entry
    return entries


def save(
    slug: str,
    snapshot_hash: str,
    config: Config,
    *,
    ttl_days: int = DEFAULT_TTL_DAYS,
    now: datetime | None = None,
) -> None:
    """Persist a dismiss entry for ``slug`` (overwrites prior entry).

    Atomic via temp file + ``os.replace`` in the same directory so a
    partial write never produces a half-readable file. Creates the
    parent directory if missing.

    ``now`` is an injection point for tests; production callers leave
    it ``None`` so we use timezone-aware UTC.
    """
    if not slug or not isinstance(slug, str):
        raise ValueError("slug must be a non-empty string")
    if not snapshot_hash or not isinstance(snapshot_hash, str):
        raise ValueError("snapshot_hash must be a non-empty string")
    if ttl_days < 0:
        raise ValueError("ttl_days must be non-negative")

    if now is None:
        now = datetime.now(timezone.utc)

    current = load(config)
    current[slug] = DismissEntry(
        dismissed_at=now,
        snapshot_hash=snapshot_hash,
        ttl_days=ttl_days,
    )
    _write_atomic(current, config)


def clear(slug: str, config: Config) -> None:
    """Remove the entry for ``slug``. No-op if absent."""
    current = load(config)
    if slug not in current:
        return
    del current[slug]
    _write_atomic(current, config)


def is_active(
    slug: str,
    current_hash: str,
    config: Config,
    *,
    now: datetime | None = None,
) -> bool:
    """True iff a dismiss for ``slug`` is currently suppressing it.

    See module docstring for the three conditions. Any failure mode
    (missing entry, hash mismatch, TTL expired, store unreadable)
    returns False — re-surfacing is always the safer default.

    ``now`` is an injection point for tests.
    """
    current = load(config)
    entry = current.get(slug)
    if entry is None:
        return False
    if entry.snapshot_hash != current_hash:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    expires_at = entry.dismissed_at + timedelta(days=entry.ttl_days)
    return now < expires_at


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _parse_entry(payload: Any) -> DismissEntry | None:
    """Convert a JSON-decoded entry dict into a DismissEntry.

    Returns ``None`` for any malformed input — the caller logs and
    skips. Strict about types (no implicit string→int) so a corrupted
    store doesn't surface garbage.
    """
    if not isinstance(payload, dict):
        return None
    raw_dt = payload.get("dismissed_at")
    raw_hash = payload.get("snapshot_hash")
    raw_ttl = payload.get("ttl_days")
    if not isinstance(raw_dt, str) or not isinstance(raw_hash, str):
        return None
    if not isinstance(raw_ttl, int) or isinstance(raw_ttl, bool):
        # bool is a subclass of int in Python; explicitly reject.
        return None
    if raw_ttl < 0:
        return None
    try:
        dt = datetime.fromisoformat(raw_dt)
    except ValueError:
        return None
    if dt.tzinfo is None:
        # Tz-naive timestamps can't be safely compared with
        # tz-aware `now`. Treat as malformed.
        return None
    return DismissEntry(
        dismissed_at=dt,
        snapshot_hash=raw_hash,
        ttl_days=raw_ttl,
    )


def _write_atomic(entries: dict[str, DismissEntry], config: Config) -> None:
    """Serialize ``entries`` and atomically replace the store file."""
    path = store_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": SCHEMA_VERSION,
        "dismissed": {
            slug: {
                "dismissed_at": entry.dismissed_at.isoformat(),
                "snapshot_hash": entry.snapshot_hash,
                "ttl_days": entry.ttl_days,
            }
            for slug, entry in entries.items()
        },
    }
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    # Write to a temp file in the SAME directory so os.replace is atomic
    # (cross-filesystem rename is not). delete=False because we close
    # before replace; the replace removes the temp name.
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{STORE_FILENAME}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(serialized)
        os.replace(tmp_name, path)
    except OSError:
        # Clean up the temp file if the replace failed; re-raise so
        # the caller knows the persist did not happen.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
