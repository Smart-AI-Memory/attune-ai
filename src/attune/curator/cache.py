"""TTL cache for :class:`CuratorResult` objects.

One file per cache key under ``<attune_home>/curator-cache/``. The
key is derived from the source-state hash by the caller; this module
just persists / loads / evicts. Read path: validates the entry's
``cached_at`` against the configured TTL and returns ``None`` if
stale. Write path: serialises the :class:`CuratorResult` as JSON.

Lazy eviction (stale entries are skipped on read but not actively
deleted) plus an explicit ``sweep(older_than_days=...)`` for the
daily housekeeping the spec calls for.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from attune.ops.config import attune_home

from .result import (
    CuratorItem,
    CuratorResult,
    Severity,
    SourceSummary,
    SuggestedAction,
)

logger = logging.getLogger(__name__)

_DEFAULT_TTL_SECONDS = 300
_DEFAULT_SUBDIR = "curator-cache"


class CuratorCache:
    """5-minute TTL cache for :class:`CuratorResult`.

    The cache key is computed via :meth:`key` from the source-state
    hashes; callers can also pass a pre-computed key string directly
    to :meth:`get` / :meth:`put`.
    """

    def __init__(
        self,
        *,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        root: Path | None = None,
    ) -> None:
        self._ttl = max(0, int(ttl_seconds))
        self._root = root if root is not None else attune_home() / _DEFAULT_SUBDIR

    @property
    def root(self) -> Path:
        return self._root

    @property
    def ttl_seconds(self) -> int:
        return self._ttl

    def key(self, summaries: list[SourceSummary]) -> str:
        """Derive a cache key from concatenated source hashes."""
        joined = "|".join(s.state_hash for s in summaries)
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]

    def get(self, key: str) -> CuratorResult | None:
        """Return the cached result for ``key`` if fresh; else ``None``.

        A missing file, malformed JSON, version-mismatched schema,
        or expired ``cached_at`` all surface as ``None`` (cache
        miss). Never raises.
        """
        path = self._path_for(key)
        if not path.is_file():
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("curator-cache: read %s failed: %s", path, exc)
            return None
        if not isinstance(data, dict):
            return None

        cached_at = _parse_iso(str(data.get("cached_at") or ""))
        if cached_at is None:
            return None
        if self._is_stale(cached_at):
            return None

        try:
            return _deserialise(data)
        except (KeyError, TypeError, ValueError) as exc:
            logger.debug("curator-cache: bad schema in %s: %s", path, exc)
            return None

    def put(self, key: str, result: CuratorResult) -> None:
        """Persist ``result`` under ``key``. Best-effort.

        The cached entry stamps ``cached_at`` to ``now`` if the
        caller passed ``None`` so the TTL is always meaningful.
        """
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("curator-cache: cannot create %s: %s", self._root, exc)
            return

        stamp = result.cached_at or datetime.now(timezone.utc)
        snapshot = _serialise(result, cached_at=stamp)
        path = self._path_for(key)
        try:
            # mkstemp names the temp file uniquely per call: deriving it
            # from the target lets two processes pick the same path, so
            # one truncates the other's partial write before the rename
            # publishes it (class G1).
            fd, tmp_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
            )
            tmp_path = Path(tmp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps(snapshot, sort_keys=True))
                tmp_path.replace(path)
            finally:
                if tmp_path.exists():
                    with contextlib.suppress(OSError):
                        tmp_path.unlink()
        except OSError as exc:
            logger.warning("curator-cache: write %s failed: %s", path, exc)

    def sweep(self, *, older_than_days: int = 7) -> int:
        """Delete cache files whose mtime is older than ``older_than_days``.

        Returns the deletion count. Safe to call when the cache dir
        doesn't exist (returns 0).
        """
        if older_than_days <= 0 or not self._root.is_dir():
            return 0
        cutoff = time.time() - older_than_days * 86_400
        deleted = 0
        try:
            entries = list(self._root.glob("*.json"))
        except OSError:
            return 0
        for entry in entries:
            try:
                if entry.stat().st_mtime < cutoff:
                    entry.unlink()
                    deleted += 1
            except OSError as exc:
                logger.debug("curator-cache: sweep %s failed: %s", entry, exc)
        return deleted

    def _path_for(self, key: str) -> Path:
        safe = "".join(ch for ch in key if ch.isalnum() or ch in ("-", "_"))
        if not safe:
            safe = "default"
        return self._root / f"{safe}.json"

    def _is_stale(self, cached_at: datetime) -> bool:
        if self._ttl == 0:
            return True
        age = datetime.now(timezone.utc) - cached_at
        return age > timedelta(seconds=self._ttl)


def _serialise(result: CuratorResult, *, cached_at: datetime) -> dict:
    payload = asdict(result)
    payload["cached_at"] = cached_at.isoformat()
    return payload


def _deserialise(data: dict) -> CuratorResult:
    items_raw = data.get("items") or []
    items: list[CuratorItem] = []
    for entry in items_raw:
        if not isinstance(entry, dict):
            continue
        action_raw = entry.get("suggested_action")
        action: SuggestedAction | None = None
        if isinstance(action_raw, dict) and action_raw.get("kind"):
            action = SuggestedAction(
                kind=action_raw["kind"],  # type: ignore[arg-type]
                label=action_raw.get("label"),
                question=action_raw.get("question"),
                choices=list(action_raw.get("choices") or []),
                url=action_raw.get("url"),
                workflow=action_raw.get("workflow"),
                scope=action_raw.get("scope"),
            )
        items.append(
            CuratorItem(
                id=str(entry["id"]),
                title=str(entry["title"]),
                severity=_coerce_severity(entry.get("severity")),
                rationale=str(entry.get("rationale") or ""),
                sources=list(entry.get("sources") or []),
                suggested_action=action,
            )
        )
    return CuratorResult(
        summary=str(data.get("summary") or ""),
        items=items,
        sources_consulted=list(data.get("sources_consulted") or []),
        cost_usd=float(data.get("cost_usd") or 0.0),
        cached_at=_parse_iso(str(data.get("cached_at") or "")),
        model=str(data.get("model") or ""),
    )


def _coerce_severity(value) -> Severity:
    if value in ("info", "nudge", "warn", "block"):
        return value  # type: ignore[return-value]
    return "info"


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
