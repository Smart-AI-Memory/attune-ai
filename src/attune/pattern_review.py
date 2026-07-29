"""Pattern review queue — a human checkpoint before the active library.

Discovered patterns are *staged* (persisted as :class:`StagedPattern` on
attune's memory backend — the local file backend by default, the Redis
Agent Memory Server when ``attune_redis`` is configured), surfaced for
review (CLI + ops dashboard), and only **promoted** into the active
:class:`~attune.pattern_library.PatternLibrary` on approval, or
**rejected**.

This re-homes the design of the deprecated, Redis-coupled
``PatternStagingMixin`` (stage → list → get → promote → reject) onto the
:class:`~attune.memory.backend.MemoryBackend` abstraction, dropping the
agent-tier permission model in favour of a human reviewer (CLI/dashboard).
It adds no Redis dependency: the queue persists on the same backend
abstraction as the rest of attune memory.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING

from attune.memory.types import StagedPattern
from attune.pattern_library import Pattern, PatternLibrary

if TYPE_CHECKING:
    from attune.memory.backend import MemoryBackend

logger = logging.getLogger(__name__)

#: Key prefix for staged patterns in the backend KV namespace.
STAGED_PREFIX = "staged_pattern:"
#: Key prefix for active (promoted) library patterns in the same store.
ACTIVE_PREFIX = "pattern:"
#: Env var gating opt-in review routing of contributed patterns (R7).
REVIEW_ENABLED_ENV = "ATTUNE_PATTERN_REVIEW"
#: Truthy spellings that turn review routing on.
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _default_backend() -> MemoryBackend:
    """Resolve the memory backend: AMS when connected, else the file backend.

    Mirrors how SessionStart recall and the Memory-tool bridge resolve
    their backend, so the review queue persists in the same store.
    """
    from attune.memory.file_stash import FileStashBackend
    from attune.memory.session_stash import resolve_backend

    backend = resolve_backend(None)
    if backend is None:
        backend = FileStashBackend()
    return backend


class PatternReviewQueue:
    """Stage → review → promote/reject queue over a :class:`MemoryBackend`.

    Args:
        backend: An attune memory backend. Defaults to the resolved backend
            (file by default; AMS when configured).
    """

    def __init__(self, backend: MemoryBackend | None = None) -> None:
        self._backend = backend or _default_backend()

    def stage(self, pattern: StagedPattern) -> str:
        """Persist a :class:`StagedPattern` to the queue.

        Returns the pattern's id. Staging the same id again overwrites the
        prior staged copy (last write wins), matching backend KV semantics.
        """
        self._backend.stash(STAGED_PREFIX + pattern.pattern_id, pattern.to_dict())
        logger.info("staged pattern %s for review", pattern.pattern_id)
        return pattern.pattern_id

    def get(self, pattern_id: str) -> StagedPattern | None:
        """Return one staged pattern, or ``None`` if not staged / unreadable."""
        raw = self._backend.retrieve(STAGED_PREFIX + pattern_id)
        if not raw:
            return None
        return _parse(raw, pattern_id)

    def list(
        self,
        *,
        pattern_type: str | None = None,
        agent_id: str | None = None,
        min_confidence: float | None = None,
    ) -> list[StagedPattern]:
        """Return staged patterns, newest-highest-confidence first.

        Optional filters narrow by ``pattern_type`` / ``agent_id`` /
        ``min_confidence``. Unparseable entries are skipped, not fatal.
        """
        out: list[StagedPattern] = []
        for key in self._backend.keys(STAGED_PREFIX + "*"):
            raw = self._backend.retrieve(key)
            if not raw:
                continue
            staged = _parse(raw, key)
            if staged is None:
                continue
            if pattern_type and staged.pattern_type != pattern_type:
                continue
            if agent_id and staged.agent_id != agent_id:
                continue
            if min_confidence is not None and staged.confidence < min_confidence:
                continue
            out.append(staged)
        out.sort(key=lambda p: p.confidence, reverse=True)
        return out

    def promote(self, pattern_id: str, library: PatternLibrary) -> Pattern | None:
        """Convert + contribute the staged pattern to ``library``, then drop it.

        Returns the promoted :class:`Pattern`, or ``None`` if ``pattern_id``
        isn't staged. If ``contribute_pattern`` raises (e.g. a duplicate id),
        the error propagates and the pattern stays staged so the reviewer can
        retry or reject — the queue is only cleared on a successful contribute.
        """
        staged = self.get(pattern_id)
        if staged is None:
            return None
        pattern = self._to_pattern(staged)
        # May raise ValueError (e.g. duplicate id) — intentionally NOT caught:
        # leave the entry staged so the reviewer can act on the conflict.
        library.contribute_pattern(staged.agent_id, pattern)
        self._backend.delete(STAGED_PREFIX + pattern_id)
        logger.info("promoted staged pattern %s into the library", pattern_id)
        return pattern

    def reject(self, pattern_id: str, reason: str = "") -> bool:
        """Drop a staged pattern. The reason is logged for audit.

        Returns ``True`` if the pattern was present and removed.
        """
        logger.info(
            "rejected staged pattern %s (reason: %s)",
            pattern_id,
            reason or "<none>",
        )
        return self._backend.delete(STAGED_PREFIX + pattern_id)

    @staticmethod
    def _to_pattern(staged: StagedPattern) -> Pattern:
        """Map a :class:`StagedPattern` onto a library :class:`Pattern`."""
        return Pattern(
            id=staged.pattern_id,
            agent_id=staged.agent_id,
            pattern_type=staged.pattern_type,
            name=staged.name,
            description=staged.description,
            context=dict(staged.context),
            code=staged.code,
            confidence=staged.confidence,
        )


def review_routing_enabled() -> bool:
    """True when contributed patterns should route to the review queue (R7).

    Default **OFF** — existing ``contribute_pattern`` behaviour is unchanged
    until a reviewer opts in by setting ``ATTUNE_PATTERN_REVIEW`` to a truthy
    value (``1`` / ``true`` / ``yes`` / ``on``). This keeps the opt-in promise:
    no surprise gating of auto-contribution.
    """
    return os.environ.get(REVIEW_ENABLED_ENV, "").strip().lower() in _TRUTHY


def stage_for_review(
    agent_id: str,
    pattern: Pattern,
    *,
    backend: MemoryBackend | None = None,
) -> str:
    """Stage a would-be-contributed :class:`Pattern` into the review queue.

    Converts the library ``Pattern`` to a :class:`StagedPattern` and stages it
    on the same backend the dashboard/CLI read (file by default, AMS when
    configured), so it surfaces for human review instead of entering the
    active library directly. Returns the staged pattern id.
    """
    staged = StagedPattern(
        pattern_id=pattern.id,
        agent_id=agent_id,
        pattern_type=pattern.pattern_type,
        name=pattern.name,
        description=pattern.description,
        code=pattern.code,
        context=dict(pattern.context),
        confidence=pattern.confidence,
    )
    return PatternReviewQueue(backend).stage(staged)


def _parse(raw: object, key: str) -> StagedPattern | None:
    """Best-effort decode of a stored value into a StagedPattern."""
    if not isinstance(raw, dict):
        logger.warning("staged pattern at %s is not a dict; skipping", key)
        return None
    try:
        return StagedPattern.from_dict(raw)
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("staged pattern at %s is unparseable (%s); skipping", key, exc)
        return None


# ---------------------------------------------------------------------------
# Backend-persisted pattern library
# ---------------------------------------------------------------------------


def _pattern_to_dict(pattern: Pattern) -> dict:
    """Serialize a library :class:`Pattern` to a JSON-safe dict."""
    return {
        "id": pattern.id,
        "agent_id": pattern.agent_id,
        "pattern_type": pattern.pattern_type,
        "name": pattern.name,
        "description": pattern.description,
        "context": pattern.context,
        "code": pattern.code,
        "confidence": pattern.confidence,
        "usage_count": pattern.usage_count,
        "success_count": pattern.success_count,
        "failure_count": pattern.failure_count,
        "tags": pattern.tags,
        "discovered_at": pattern.discovered_at.isoformat(),
        "last_used": pattern.last_used.isoformat() if pattern.last_used else None,
    }


def _pattern_from_dict(data: object) -> Pattern | None:
    """Reconstruct a :class:`Pattern` from a stored dict (best-effort)."""
    if not isinstance(data, dict):
        return None
    try:
        last_used = data.get("last_used")
        return Pattern(
            id=data["id"],
            agent_id=data["agent_id"],
            pattern_type=data["pattern_type"],
            name=data["name"],
            description=data["description"],
            context=data.get("context", {}),
            code=data.get("code"),
            confidence=data.get("confidence", 0.5),
            usage_count=data.get("usage_count", 0),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            tags=data.get("tags", []),
            discovered_at=datetime.fromisoformat(data["discovered_at"]),
            last_used=datetime.fromisoformat(last_used) if last_used else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("stored pattern is unparseable (%s); skipping", exc)
        return None


class PersistentPatternLibrary(PatternLibrary):
    """A :class:`PatternLibrary` that persists on the memory backend.

    Contributions are written under the ``pattern:`` prefix on the same
    :class:`MemoryBackend` the review queue uses — the local file backend by
    default, the **Redis Agent Memory Server when configured**. The library
    is reconstructed from the backend on construction, so promotes survive
    across processes (and are Redis-durable under AMS) without the orphaned
    ``PatternPersistence`` JSON-file path.

    Args:
        backend: An attune memory backend. Defaults to the resolved backend
            (file by default; AMS when configured).
    """

    def __init__(self, backend: MemoryBackend | None = None) -> None:
        super().__init__()
        self._backend = backend or _default_backend()
        self._load()

    def _load(self) -> None:
        """Reconstruct the in-memory library from the backend (no re-persist)."""
        for key in self._backend.keys(ACTIVE_PREFIX + "*"):
            pattern = _pattern_from_dict(self._backend.retrieve(key))
            if pattern is None:
                continue
            try:
                # Base method: in-memory bookkeeping only (our override persists).
                PatternLibrary.contribute_pattern(self, pattern.agent_id, pattern)
            except ValueError:
                # Duplicate id already loaded — skip the redundant copy.
                continue

    def contribute_pattern(self, agent_id: str, pattern: Pattern) -> None:
        """Validate + add in memory (base behaviour), then persist to the backend."""
        PatternLibrary.contribute_pattern(self, agent_id, pattern)
        self._backend.stash(ACTIVE_PREFIX + pattern.id, _pattern_to_dict(pattern))

    def record_pattern_outcome(self, pattern_id: str, success: bool) -> None:
        """Record the outcome (base behaviour), then re-persist the pattern.

        Without the re-stash, usage/success/failure counts survive only for
        the life of the process and every reload resets ``success_rate``.
        """
        PatternLibrary.record_pattern_outcome(self, pattern_id, success)
        self._backend.stash(ACTIVE_PREFIX + pattern_id, _pattern_to_dict(self.patterns[pattern_id]))
