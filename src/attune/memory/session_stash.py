"""Cross-session memory stash — write/recall over a SearchableMemoryBackend.

Part of the ``claude-cross-session-memory`` spec. Per decision D6, this
release backs recall with the Redis Agent Memory Server (AMS) via
``attune_redis.AMSMemoryBackend``. This module stays **backend-agnostic**:
it targets the :class:`attune.memory.backend.SearchableMemoryBackend`
protocol and resolves a concrete backend from the ``attune.memory_backends``
entry point (or an injected instance), degrading to a **silent no-op** when
no searchable backend is available.

Tiers (D4/D6):

- **Write** — raw session findings stashed via ``backend.stash`` (working
  memory). A PII/secrets gate runs *before* any write (R3); polish is
  deferred to user-gated promotion.
- **Recall** — ``backend.search`` (semantic, over AMS long-term memory).
- **Promote to curated** — stays the review-gated ``/remember`` flow,
  independent of this module (D2).

The hooks that drive this (``~/.claude/hooks/session_recall.py`` and the
Stop-hook stash) live outside the package and are intentionally NOT shipped
here; they register against the user's live ``settings.json``.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.memory.backend import SearchableMemoryBackend

logger = logging.getLogger(__name__)

#: Entry kinds mirror PersonalMemory's vocabulary plus a generic "note".
VALID_TYPES = frozenset({"decision", "pattern", "bug", "reference", "note"})

#: Stash entries are short by design (raw findings, not polished docs).
MAX_CONTENT_CHARS = 500

#: Entry-point group attune plugins register a memory backend under.
_BACKEND_GROUP = "attune.memory_backends"

#: Default working-memory TTL for a stashed finding.
DEFAULT_TTL_DAYS = 7


@dataclass
class SessionStashEntry:
    """A single raw cross-session finding awaiting recall or promotion.

    Attributes:
        id: UUID4 string, used as the backend stash key.
        session_id: Originating Claude Code session id.
        cwd: Project root at write time (used for cwd-scoped recall).
        timestamp: ISO-8601 UTC creation time.
        type: One of :data:`VALID_TYPES`.
        content: The finding text (truncated to :data:`MAX_CONTENT_CHARS`).
        tags: Free-form tags for filtering.
        ttl_days: Working-memory TTL in days.
    """

    id: str
    session_id: str
    cwd: str
    timestamp: str
    type: str
    content: str
    tags: list[str] = field(default_factory=list)
    ttl_days: int = DEFAULT_TTL_DAYS

    def __post_init__(self) -> None:
        if self.type not in VALID_TYPES:
            raise ValueError(f"invalid type {self.type!r}; expected one of {sorted(VALID_TYPES)}")
        if not self.content or not self.content.strip():
            raise ValueError("content must be a non-empty string")
        if len(self.content) > MAX_CONTENT_CHARS:
            logger.warning(
                "session stash content truncated %d -> %d chars",
                len(self.content),
                MAX_CONTENT_CHARS,
            )
            self.content = self.content[:MAX_CONTENT_CHARS]

    @classmethod
    def create(
        cls,
        session_id: str,
        cwd: str,
        type: str,
        content: str,
        tags: list[str] | None = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> SessionStashEntry:
        """Build an entry with a fresh id + UTC timestamp."""
        return cls(
            id=str(uuid.uuid4()),
            session_id=session_id,
            cwd=cwd,
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=type,
            content=content,
            tags=list(tags or []),
            ttl_days=ttl_days,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for backend storage."""
        return asdict(self)


def resolve_backend(
    backend: SearchableMemoryBackend | None = None,
) -> SearchableMemoryBackend | None:
    """Return a searchable backend, or ``None`` if none is available.

    Resolution order: an explicitly injected ``backend`` wins; otherwise the
    first entry registered under the ``attune.memory_backends`` entry point
    is instantiated (env-configured). Any failure — no plugin installed,
    construction error, missing search capability — returns ``None`` so the
    caller degrades to a no-op rather than raising.
    """
    if backend is not None:
        return backend
    try:
        from importlib.metadata import entry_points

        from attune.memory.backend import SearchableMemoryBackend as _Searchable

        eps = entry_points(group=_BACKEND_GROUP)
        for ep in eps:
            try:
                instance = ep.load()()
            except Exception as exc:  # noqa: BLE001
                # INTENTIONAL: a misconfigured/unavailable backend must not
                # break the host session — recall simply yields nothing.
                logger.debug("memory backend %s unavailable: %s", ep.name, exc)
                continue
            if isinstance(instance, _Searchable) or (
                hasattr(instance, "search") and hasattr(instance, "stash")
            ):
                return instance
        logger.debug("no searchable memory backend registered under %s", _BACKEND_GROUP)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: resolution is best-effort; never propagate.
        logger.debug("backend resolution failed: %s", exc)
    return None


def _sanitize(content: str) -> str | None:
    """Run the PII/secrets gate before any write (R3). Fail closed.

    Returns the sanitized content, or ``None`` if the gate is unavailable so
    the caller refuses the write rather than persisting unsanitized text.
    """
    try:
        from attune.memory.short_term.security import DataSanitizer
    except Exception as exc:  # noqa: BLE001
        logger.error("PII/secrets gate unavailable; refusing stash write: %s", exc)
        return None
    sanitizer = DataSanitizer()
    sanitized, redactions = sanitizer.sanitize(content)
    if redactions:
        logger.info("session stash: %d sensitive value(s) redacted before write", redactions)
    return sanitized if isinstance(sanitized, str) else str(sanitized)


def stash_entry(
    entry: SessionStashEntry,
    backend: SearchableMemoryBackend | None = None,
) -> bool:
    """Write a finding to the searchable recall tier after the PII gate.

    Per D7, findings are written as long-term memories (recallable via
    :func:`recall_entries`) through ``backend.remember`` when available.
    Backends without a searchable write path fall back to the key/value
    ``stash`` (not recallable, but non-fatal). No-op (returns ``False``)
    when no backend is available or the gate can't run. Never raises —
    safe to call from a Stop hook.
    """
    target = resolve_backend(backend)
    if target is None:
        return False
    safe_content = _sanitize(entry.content)
    if safe_content is None:
        return False
    entry.content = safe_content
    topics = list(entry.tags) + [f"type:{entry.type}", f"cwd:{entry.cwd}"]
    remember = getattr(target, "remember", None)
    try:
        if remember is not None:
            return bool(
                remember(
                    safe_content,
                    memory_id=entry.id,
                    session_id=entry.session_id,
                    topics=topics,
                )
            )
        # Backend without a searchable write path: key/value stash only
        # (not recallable, but the host session must not break).
        ttl_seconds = max(1, entry.ttl_days) * 86_400
        return bool(
            target.stash(entry.id, entry.to_dict(), ttl=ttl_seconds, agent_id=entry.session_id)
        )
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: write is best-effort; a backend error must not break
        # the host session.
        logger.warning("session stash write failed: %s", exc)
        return False


def recall_entries(
    query: str,
    top_k: int = 5,
    cwd: str | None = None,
    backend: SearchableMemoryBackend | None = None,
) -> list[dict[str, Any]]:
    """Semantic recall over stashed findings. Empty list when unavailable.

    Args:
        query: Natural-language recall query.
        top_k: Max results.
        cwd: When set, prefer entries from this project root (soft filter;
            cross-cwd results still returned, cwd matches first).
        backend: Optional injected backend; resolved from the entry point
            when omitted.

    Returns:
        Ranked memory records as dicts (backend-shaped), or ``[]``.
    """
    target = resolve_backend(backend)
    if target is None:
        return []
    try:
        results = target.search(query, limit=top_k)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: recall is best-effort; never break the host session.
        logger.warning("session recall failed: %s", exc)
        return []
    if not isinstance(results, list):
        return []
    if cwd:
        results.sort(key=lambda r: 0 if (isinstance(r, dict) and r.get("cwd") == cwd) else 1)
    return results
