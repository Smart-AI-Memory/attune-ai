"""File-based searchable session stash — the zero-infra default backend.

Per decision **D8** (claude-cross-session-memory): cross-session memory
works out-of-box with no Redis / AMS / Ollama. This backend implements the
:class:`attune.memory.backend.SearchableMemoryBackend` protocol over a local
JSONL stash, so :func:`attune.memory.session_stash.stash_entry` /
``recall_entries`` function on a plain ``pip install attune-ai``.

Recall is the cheap **keyword + recency + cwd** filter D4 specified — the
stash is one user with short retention, small enough that semantic search is
unnecessary. AMS (``attune_redis.AMSMemoryBackend``) remains the optional
upgrade for higher-quality recall at scale; ``resolve_backend`` prefers it
when it is connected and falls back to this backend otherwise.

Storage: ``~/.attune/session_stash/findings.jsonl`` (one JSON record per
line). Key/value ``stash``/``retrieve`` use a sibling ``kv.json``. Records
past the TTL are pruned lazily on read/write.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from attune.memory.atomic_io import append_line, atomic_write_text, file_lock

logger = structlog.get_logger(__name__)

#: Default working-stash retention (days); keep in sync with
#: session_stash.DEFAULT_TTL_DAYS. 30d covers realistic project-revisit gaps.
DEFAULT_TTL_DAYS = 30

_DAY_SECONDS = 86_400
#: Recency half-life for the recall score (newer findings rank higher).
_RECENCY_HALFLIFE_SECONDS = 3 * _DAY_SECONDS


def _tokenize(text: str) -> set[str]:
    """Lowercase alphanumeric tokens of length >= 2."""
    out: set[str] = set()
    token: list[str] = []
    for ch in text.lower():
        if ch.isalnum():
            token.append(ch)
        elif token:
            if len(token) >= 2:
                out.add("".join(token))
            token = []
    if len(token) >= 2:
        out.add("".join(token))
    return out


def _cwd_from_topics(topics: list[str]) -> str | None:
    """Extract the ``cwd:<path>`` marker session_stash writes into topics."""
    for t in topics:
        if t.startswith("cwd:"):
            return t[len("cwd:") :]
    return None


def _record_ts(rec: dict[str, Any]) -> float | None:
    """The record's epoch timestamp, or None when it cannot be read.

    Library-review G2: the per-record ``try`` caught ``JSONDecodeError``
    but the coercion that follows it — ``float(rec["ts"])`` — sat
    OUTSIDE it. One hand-edited timestamp therefore escaped to store
    level, where the best-effort excepts turned it into ``search`` and
    ``recent`` returning nothing and ``remember`` returning False
    forever: a permanently bricked store with no error surfaced.

    Returning None instead lets one poison record be skipped like an
    expired one while the rest of the store keeps working.
    """
    try:
        return float(rec.get("ts", 0) or 0)
    except (TypeError, ValueError):
        logger.warning("file_stash_unreadable_ts", record_id=rec.get("id"))
        return None


def _iso_from_ts(ts: Any) -> str | None:
    """ISO-8601 UTC string for an epoch-seconds value, or ``None``."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


class FileStashBackend:
    """Searchable, zero-infra session stash backed by a local JSONL file.

    No-arg constructable (so it resolves from the ``attune.memory_backends``
    entry point), and marked :data:`is_fallback` so ``resolve_backend``
    prefers a connected AMS upgrade when one is available.
    """

    #: Marks this as the always-available default, not an upgrade backend.
    is_fallback = True

    def __init__(
        self,
        base_dir: str | Path | None = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> None:
        """Initialize the file stash.

        Args:
            base_dir: Stash directory. Defaults to ``~/.attune/session_stash``.
            ttl_days: Retention; records older than this are pruned on access.
        """
        if base_dir is None:
            base_dir = Path.home() / ".attune" / "session_stash"
        self._dir = Path(base_dir)
        self._findings = self._dir / "findings.jsonl"
        self._kv = self._dir / "kv.json"
        self._ttl_seconds = max(1, ttl_days) * _DAY_SECONDS
        self._closed = False
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("file_stash_mkdir_failed", error=str(e))

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #

    def _load_records(self) -> list[dict[str, Any]]:
        """Load all non-expired finding records (lazy TTL prune on read)."""
        if not self._findings.exists():
            return []
        cutoff = time.time() - self._ttl_seconds
        records: list[dict[str, Any]] = []
        try:
            for line in self._findings.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                ts = _record_ts(rec)
                if ts is not None and ts >= cutoff:
                    records.append(rec)
        except OSError as e:
            logger.warning("file_stash_read_failed", error=str(e))
        return records

    def _rewrite(self, records: list[dict[str, Any]]) -> bool:
        """Atomically rewrite the findings file (used for append + prune).

        Returns ``True`` only when the durable replace landed. Callers must
        propagate ``False`` — reporting success for a write that never
        persisted is the false-success data-loss bug this guards against
        (cross-provider-memory-transport R1).
        """
        try:
            atomic_write_text(
                self._findings,
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
            )
            return True
        except OSError as e:
            logger.warning("file_stash_write_failed", error=str(e))
            return False

    # ------------------------------------------------------------------ #
    # SearchableMemoryBackend — searchable write/read
    # ------------------------------------------------------------------ #

    def remember(
        self,
        content: str,
        *,
        memory_id: str | None = None,
        session_id: str | None = None,
        topics: list[str] | None = None,
    ) -> bool:
        """Append a searchable finding to the local stash (prunes expired)."""
        topics = list(topics or [])
        record = {
            "id": memory_id or os.urandom(8).hex(),
            "text": content,
            "session_id": session_id,
            "topics": topics,
            "cwd": _cwd_from_topics(topics),
            "ts": time.time(),
        }
        try:
            # APPEND, never read-modify-write: rewriting the whole file to
            # add one record is what let concurrent writers erase each
            # other while both reported success (library-review G1).
            # Expired records are pruned lazily on read and by prune().
            #
            # Still under the lock: prune/forget DO rewrite the whole file,
            # and an append landing between their read and their replace is
            # erased just the same (codex D11 lane, 2026-08-20). Appends are
            # small and rare, so serialising them costs nothing.
            with file_lock(self._findings) as locked:
                if not locked:
                    logger.warning("file_stash_remember_locked")
                    return False
                append_line(self._findings, json.dumps(record, ensure_ascii=False))
            return True
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: stash is best-effort; never break the host session.
            logger.warning("file_stash_remember_failed", error=str(e))
            return False

    def search(self, query: str, limit: int = 10, **filters: Any) -> list[dict]:
        """Keyword + recency + cwd recall over the stash (D4's cheap tier)."""
        terms = _tokenize(query)
        if not terms:
            return []
        cwd = filters.get("cwd")
        now = time.time()
        scored: list[tuple[float, dict[str, Any]]] = []
        for rec in self._load_records():
            doc_terms = _tokenize(rec.get("text", "")) | {
                t for top in rec.get("topics", []) for t in _tokenize(top)
            }
            overlap = len(terms & doc_terms)
            if overlap == 0:
                continue
            age = max(0.0, now - (_record_ts(rec) or now))
            recency = 0.5 ** (age / _RECENCY_HALFLIFE_SECONDS)
            score = overlap + recency
            if cwd and rec.get("cwd") == cwd:
                score += 1.0  # soft boost for same-project findings
            scored.append(
                (
                    score,
                    {
                        "id": rec.get("id"),
                        "text": rec.get("text"),
                        "topics": rec.get("topics", []),
                        "cwd": rec.get("cwd"),
                        "session_id": rec.get("session_id"),
                        "score": round(score, 4),
                    },
                )
            )
        scored.sort(key=lambda s: s[0], reverse=True)
        return [d for _, d in scored[:limit]]

    def recent(self, limit: int = 5, **filters: Any) -> list[dict]:
        """Most-recent findings (no query) — powers SessionStart recall.

        Sorted newest-first; when ``cwd`` is given, same-project findings
        are surfaced ahead of others (soft priority, mirroring ``search``).
        Returns the ``search`` record shape (minus ``score``) plus ``ts``
        (epoch float) and ``created_at`` (ISO-8601) — the recency keys
        promotion consumers order and display by.
        """
        cwd = filters.get("cwd")
        records = self._load_records()  # already TTL-pruned
        records.sort(key=lambda r: _record_ts(r) or 0.0, reverse=True)
        if cwd:
            # Stable secondary sort: cwd matches first, recency preserved within.
            records.sort(key=lambda r: 0 if r.get("cwd") == cwd else 1)
        return [
            {
                "id": r.get("id"),
                "text": r.get("text"),
                "topics": r.get("topics", []),
                "cwd": r.get("cwd"),
                "session_id": r.get("session_id"),
                "ts": r.get("ts"),
                "created_at": _iso_from_ts(r.get("ts")),
            }
            for r in records[:limit]
        ]

    def promote(self, session_id: str | None = None) -> bool:
        """No-op for the file backend (findings are already durable here)."""
        return True

    def prune(self, max_age_days: int | None = None) -> int:
        """Drop findings older than ``max_age_days`` (default: backend TTL).

        The file backend also prunes lazily on every read/write, so this is
        an explicit forced sweep for parity with the AMS backend (which the
        Stop hook can call uniformly on either backend). Best-effort.
        """
        ttl_seconds = (
            self._ttl_seconds if max_age_days is None else max(1, max_age_days) * _DAY_SECONDS
        )
        cutoff = time.time() - ttl_seconds
        if not self._findings.exists():
            return 0
        try:
            with file_lock(self._findings) as locked:
                if not locked:
                    logger.warning("file_stash_prune_locked")
                    return 0
                return self._sweep(cutoff)
        except OSError as e:
            logger.warning("file_stash_prune_failed", error=str(e))
            return 0

    def _sweep(self, cutoff: float) -> int:
        """Drop records older than ``cutoff``. Caller holds the lock."""
        kept: list[dict[str, Any]] = []
        dropped = 0
        try:
            for line in self._findings.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = _record_ts(rec) if isinstance(rec, dict) else None
                if ts is not None and ts >= cutoff:
                    kept.append(rec)
                else:
                    dropped += 1
            if dropped and not self._rewrite(kept):
                return 0  # nothing actually pruned — the rewrite never landed
        except OSError as e:
            logger.warning("file_stash_prune_failed", error=str(e))
        return dropped

    def forget(self, ids: list[str]) -> int:
        """Delete specific findings by record ID.

        The IDs are the ``id`` values returned by :meth:`search` /
        :meth:`recent`. Complements :meth:`prune` (age-based sweep) with
        precise removal — the correction path when a stashed finding is
        wrong or stale. Best-effort; returns the number of findings
        deleted (0 on failure or empty input), never raises. Parity with
        ``AMSMemoryBackend.forget``.
        """
        if not ids or not self._findings.exists():
            return 0
        targets = set(ids)
        try:
            with file_lock(self._findings) as locked:
                if not locked:
                    logger.warning("file_stash_forget_locked")
                    return 0
                return self._drop(targets)
        except OSError as e:
            logger.warning("file_stash_forget_failed", error=str(e))
            return 0

    def _drop(self, targets: set[str]) -> int:
        """Remove records whose id is in ``targets``. Caller holds the lock."""
        kept: list[dict[str, Any]] = []
        dropped = 0
        try:
            for line in self._findings.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and rec.get("id") in targets:
                    dropped += 1
                else:
                    kept.append(rec)
            if dropped and not self._rewrite(kept):
                return 0  # nothing actually deleted — the rewrite never landed
        except OSError as e:
            logger.warning("file_stash_forget_failed", error=str(e))
            return 0
        return dropped

    # ------------------------------------------------------------------ #
    # MemoryBackend — key/value
    # ------------------------------------------------------------------ #

    def _load_kv(self) -> dict[str, Any]:
        if not self._kv.exists():
            return {}
        try:
            data = json.loads(self._kv.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def stash(
        self, key: str, value: Any, ttl: int | None = None, agent_id: str | None = None
    ) -> bool:
        """Store a key/value pair (separate from the searchable findings)."""
        try:
            with file_lock(self._kv) as locked:
                if not locked:
                    logger.warning("file_stash_kv_set_locked", key=key)
                    return False
                # Re-read INSIDE the lock: a value read before it would be
                # a lost update the moment a peer wrote (library-review G1).
                data = self._load_kv()
                data[key] = value
                atomic_write_text(self._kv, json.dumps(data, ensure_ascii=False))
            return True
        except (OSError, TypeError) as e:
            logger.warning("file_stash_kv_set_failed", key=key, error=str(e))
            return False

    def retrieve(self, key: str, agent_id: str | None = None) -> Any | None:
        """Retrieve a key/value pair."""
        return self._load_kv().get(key)

    def retrieve_many(self, keys: list[str], agent_id: str | None = None) -> dict[str, Any]:
        """Retrieve several key/value pairs in one KV-file read.

        Batch counterpart of :meth:`retrieve`, which re-reads the KV file
        on every call. Missing keys map to ``None``.
        """
        data = self._load_kv()
        return {k: data.get(k) for k in keys}

    def delete(self, key: str) -> bool:
        """Delete a key/value pair. Returns False if absent."""
        try:
            with file_lock(self._kv) as locked:
                if not locked:
                    logger.warning("file_stash_kv_delete_locked", key=key)
                    return False
                data = self._load_kv()
                if key not in data:
                    return False
                del data[key]
                atomic_write_text(self._kv, json.dumps(data, ensure_ascii=False))
            return True
        except OSError as e:
            logger.warning("file_stash_kv_delete_failed", key=key, error=str(e))
            return False

    def keys(self, pattern: str = "*") -> list[str]:
        """List key/value keys (optionally glob-filtered)."""
        import fnmatch

        ks = list(self._load_kv().keys())
        return ks if pattern == "*" else [k for k in ks if fnmatch.fnmatch(k, pattern)]

    def probe_write(self) -> bool:
        """Real writability probe — write and remove a temp artifact.

        Used by ``session_stash.backend_status`` to distinguish a
        caller-local write denial (e.g. a sandboxed process where the
        stash directory is read-only) from a healthy file tier. Says
        nothing about any remote service. The probe artifact is removed
        on both the success and failure paths.
        """
        probe = self._dir / f".write-probe-{os.getpid()}-{os.urandom(4).hex()}"
        try:
            probe.write_text("probe", encoding="utf-8")
            return True
        except OSError as e:
            logger.warning("file_stash_probe_write_failed", error=str(e))
            return False
        finally:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass

    def is_connected(self) -> bool:
        """Always available — the stash directory is local and writable."""
        return self._dir.exists() or not self._closed

    def get_stats(self) -> dict:
        """Backend statistics."""
        return {
            "backend": "file",
            "findings": len(self._load_records()),
            "base_dir": str(self._dir),
            "ttl_days": self._ttl_seconds // _DAY_SECONDS,
        }

    def close(self) -> None:
        """No-op close (no persistent connection to release)."""
        self._closed = True

    def supports_realtime(self) -> bool:
        """File backend has no realtime pub/sub."""
        return False

    def supports_distributed(self) -> bool:
        """File backend is single-host."""
        return False
