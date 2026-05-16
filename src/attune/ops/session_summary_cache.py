"""On-disk cache for Haiku-summarized session starter prompts.

Defined by the ops-sessions-page spec (decisions.md, Decisions 6 + 7).
Keyed by ``(filename, mtime_ns, sha256_of_last_4kb)`` — the last-4KB
hash is the freshest content in a monotonically-growing JSONL and
changes every time the session does. Hashing the head would collide
on the byte-identical opening block (two sessions whose opening
prompts look similar) and rely on mtime alone for freshness, which
ticks spuriously on filesystem touches.

Cache files live at::

    <attune_home>/ops/session_summaries/<session-id>.json

Each holds the redaction-already-applied summary text plus the key
it was computed against. A cache hit returns the redacted form
directly — sensitive material never lands in either the LLM
provider's context or this on-disk cache.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Bytes hashed from the JSONL tail to form the cache-key digest.
# 4 KiB matches decisions.md Decision 6. Files smaller than this are
# fully hashed (short-session edge case, rare and cheap).
_TAIL_BYTES = 4096


@dataclass(frozen=True)
class CacheKey:
    """Stable key that invalidates a cached summary when the source moves.

    ``filename`` is the JSONL basename (not a full path) so a session
    that's relocated to a different encoded-key dir still hits the
    cache as long as its content tail matches. Two-of-three matching
    is not enough: all three components must match for a hit.
    """

    filename: str
    mtime_ns: int
    sha256: str


@dataclass(frozen=True)
class CachedSummary:
    """One persisted session summary plus the metadata to validate it."""

    key: CacheKey
    summary: str
    source: str  # "haiku" | "cached" — at write time always "haiku";
    # ``load()`` returns "cached" for hit semantics.
    tokens_in: int
    tokens_out: int
    cost_usd: float
    created_at: str  # ISO 8601 UTC


def _hash_tail(jsonl_path: Path) -> str | None:
    """Return the SHA-256 hex digest of the file's last ``_TAIL_BYTES``.

    For files smaller than the tail size, the whole file is hashed —
    this collapses to "hash the file" and is correct for the
    short-session edge case. Returns ``None`` on any I/O failure
    (callers should treat this as cache-miss-by-design).
    """
    try:
        size = jsonl_path.stat().st_size
    except OSError:
        return None
    try:
        with jsonl_path.open("rb") as fh:
            if size > _TAIL_BYTES:
                fh.seek(size - _TAIL_BYTES)
            data = fh.read(_TAIL_BYTES)
    except OSError:
        return None
    return hashlib.sha256(data).hexdigest()


def compute_cache_key(jsonl_path: Path) -> CacheKey | None:
    """Build a :class:`CacheKey` for one JSONL file. ``None`` on I/O failure."""
    try:
        st = jsonl_path.stat()
    except OSError:
        return None
    digest = _hash_tail(jsonl_path)
    if digest is None:
        return None
    return CacheKey(
        filename=jsonl_path.name,
        mtime_ns=st.st_mtime_ns,
        sha256=digest,
    )


def cache_path_for(attune_home: Path, session_id: str) -> Path:
    """Return the on-disk cache path for one session id.

    The directory is created on first ``save()``; this function does
    not create it (callers may want to test "is there a cache for X?"
    without forcing the dir into existence).
    """
    return attune_home / "ops" / "session_summaries" / f"{session_id}.json"


def load(attune_home: Path, session_id: str, expected: CacheKey) -> CachedSummary | None:
    """Return the cached summary iff the on-disk record matches ``expected``.

    Returns ``None`` on:

    - File doesn't exist
    - File is malformed JSON
    - Stored key doesn't match all three components of ``expected``
    - File is missing required fields

    A returned :class:`CachedSummary` always has ``source == "cached"``
    so the caller can distinguish hits from fresh writes (which use
    ``source == "haiku"``). The cached text itself is unchanged.
    """
    path = cache_path_for(attune_home, session_id)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("ops.sessions.cache: malformed JSON at %s — ignoring", path)
        return None
    if not isinstance(raw, dict):
        return None
    raw_key = raw.get("key")
    if not isinstance(raw_key, dict):
        return None
    try:
        stored_key = CacheKey(
            filename=str(raw_key["filename"]),
            mtime_ns=int(raw_key["mtime_ns"]),
            sha256=str(raw_key["sha256"]),
        )
    except (KeyError, TypeError, ValueError):
        return None
    if stored_key != expected:
        return None
    try:
        return CachedSummary(
            key=stored_key,
            summary=str(raw["summary"]),
            source="cached",
            tokens_in=int(raw.get("tokens_in", 0)),
            tokens_out=int(raw.get("tokens_out", 0)),
            cost_usd=float(raw.get("cost_usd", 0.0)),
            created_at=str(raw.get("created_at", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def save(
    attune_home: Path,
    session_id: str,
    *,
    key: CacheKey,
    summary: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
) -> Path:
    """Write a summary to the on-disk cache, atomically.

    Always writes ``source = "haiku"`` — the "cached" flavor is
    emitted by :func:`load` to mark a hit. Returns the path the
    record was written to. Atomic via temp-file + rename so a
    concurrent reader never observes a half-written JSON.

    Raises :class:`OSError` on filesystem errors. Callers that want
    silent best-effort caching should wrap the call in a try/except
    rather than burying the failure here.
    """
    path = cache_path_for(attune_home, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "key": asdict(key),
        "summary": summary,
        "source": "haiku",
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
        "cost_usd": float(cost_usd),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"

    # Temp file in the same dir → ``Path.replace`` is atomic on POSIX
    # and Windows (per the existing CLAUDE.md lesson about Windows'
    # rename semantics).
    fd, tmp_str = tempfile.mkstemp(prefix=f".{session_id}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        tmp_path.replace(path)
    except OSError:
        # Best-effort cleanup — don't mask the original error.
        with _suppress_oserror():
            tmp_path.unlink()
        raise
    return path


class _suppress_oserror:
    """Tiny contextlib.suppress equivalent without the import cost."""

    def __enter__(self) -> None:  # noqa: D401
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401
        return exc_type is not None and issubclass(exc_type, OSError)
