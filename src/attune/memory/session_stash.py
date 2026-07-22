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

#: Default retention for a stashed finding (days). Applied consistently by
#: both searchable backends (file age-prune + AMS forget). 30d covers
#: realistic project-revisit gaps so recall isn't empty when you return to a
#: project after a couple weeks; the curated ``/remember`` tier is the
#: truly-durable layer for promoted keepers. Keep in sync with
#: ``file_stash.DEFAULT_TTL_DAYS``.
DEFAULT_TTL_DAYS = 30


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

    An explicitly injected ``backend`` always wins. Otherwise backends are
    instantiated from the ``attune.memory_backends`` entry point and chosen
    by preference (D8): a **connected upgrade** backend (e.g. the Redis AMS
    when it's actually running) is preferred over the always-available
    **fallback** (the local file backend, which marks itself
    ``is_fallback=True``). This makes cross-session memory work out-of-box on
    a plain install while transparently upgrading to AMS when present.

    Any failure — no plugin installed, construction error, missing search
    capability — degrades to the fallback or ``None`` rather than raising.
    """
    if backend is not None:
        return backend
    try:
        from importlib.metadata import entry_points

        from attune.memory.backend import SearchableMemoryBackend as _Searchable

        fallback: SearchableMemoryBackend | None = None
        for ep in entry_points(group=_BACKEND_GROUP):
            try:
                instance = ep.load()()
            except Exception as exc:  # noqa: BLE001
                # INTENTIONAL: a misconfigured/unavailable backend must not
                # break the host session — recall simply yields nothing.
                logger.debug("memory backend %s unavailable: %s", ep.name, exc)
                continue
            if not (
                isinstance(instance, _Searchable)
                or (hasattr(instance, "search") and hasattr(instance, "stash"))
            ):
                continue
            # Connectivity gate: skip an upgrade backend that isn't actually
            # reachable. Backends without is_connected() are assumed available.
            connected = True
            check = getattr(instance, "is_connected", None)
            if callable(check):
                try:
                    connected = bool(check())
                except Exception:  # noqa: BLE001
                    connected = False
            if not connected:
                continue
            if getattr(instance, "is_fallback", False):
                fallback = fallback or instance  # remember; keep looking for an upgrade
                continue
            return instance  # connected upgrade backend wins
        if fallback is not None:
            return fallback
        logger.debug("no searchable memory backend registered under %s", _BACKEND_GROUP)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: resolution is best-effort; never propagate.
        logger.debug("backend resolution failed: %s", exc)
    return None


def backend_status() -> dict:
    """Report which backend recall resolves to, for health surfacing.

    Returns a dict with:

    - ``backend``: class name of the resolved backend, or ``None``
    - ``fallback``: True when the resolved backend marks itself as the
      always-available local fallback (e.g. the file tier)
    - ``unreachable_upgrade``: entry-point name of a registered upgrade
      backend (e.g. the Redis AMS) that failed construction or its
      connectivity check — i.e. recall is silently degraded and findings
      stored in that tier are dark. ``None`` when no upgrade is registered
      or the upgrade is the resolved backend.

    Additive caller-scoped fields (cross-provider-memory-transport R2/D4;
    existing keys above are preserved unchanged):

    - ``ok``: True when a usable write/recall path exists *for this
      caller*.
    - ``transport``: ``"direct"`` (in-process upgrade backend),
      ``"file"`` (local file tier), or ``"none"``. MCP adapters report
      ``"mcp"`` at their own layer.
    - ``reachability``: ``"reachable"`` / ``"unreachable_local"`` /
      ``"unknown"`` — describes THIS caller's boundary only. A sandboxed
      process that cannot write the stash directory is
      ``unreachable_local``; that is never evidence the backing service
      is down globally.
    - ``reason``: stable machine-readable code when ``ok`` is False
      (e.g. ``file_write_denied``, ``no_backend``), else ``None``.

    The file tier's reachability comes from a real temporary-write probe
    (``FileStashBackend.probe_write``), not an assumption — the 2026-07-22
    Codex diagnosis found an unwritable sandbox fallback reporting success.

    Motivation: the 2026-06-11 triage found AMS had been down for a week
    with 51 records unreachable and nothing surfacing it — degradation was
    too graceful. Consumers (the ``/recall`` skill, the SessionStart recall
    hook) print a one-line warning when ``unreachable_upgrade`` is set.
    Never raises.
    """
    status: dict = {
        "backend": None,
        "fallback": False,
        "unreachable_upgrade": None,
        "ok": False,
        "transport": "none",
        "reachability": "unknown",
        "reason": None,
    }
    resolved = resolve_backend(None)
    if resolved is not None:
        status["backend"] = type(resolved).__name__
        status["fallback"] = bool(getattr(resolved, "is_fallback", False))
    if resolved is not None and not status["fallback"]:
        # Upgrade backend healthy — nothing to warn about. resolve_backend
        # already gated on is_connected(), so this caller can reach it.
        status.update(ok=True, transport="direct", reachability="reachable")
        return status
    if resolved is None:
        status["reason"] = "no_backend"
    else:
        # Fallback (file) tier: verify writability with a real probe when
        # the backend offers one. A failed probe is a CALLER-LOCAL denial.
        probe = getattr(resolved, "probe_write", None)
        writable: bool | None = None
        if callable(probe):
            try:
                writable = bool(probe())
            except Exception:  # noqa: BLE001
                # INTENTIONAL: status probing is best-effort; never raise.
                writable = False
        if writable is None:
            # Backend predates probe_write — usable as far as we know.
            status.update(ok=True, transport="file")
        elif writable:
            status.update(ok=True, transport="file", reachability="reachable")
        else:
            status.update(reachability="unreachable_local", reason="file_write_denied")
    try:
        from importlib.metadata import entry_points

        for ep in entry_points(group=_BACKEND_GROUP):
            try:
                instance = ep.load()()
            except Exception:  # noqa: BLE001
                # INTENTIONAL: construction failure IS the signal here.
                status["unreachable_upgrade"] = ep.name
                continue
            if getattr(instance, "is_fallback", False):
                continue
            check = getattr(instance, "is_connected", None)
            if callable(check):
                try:
                    if not check():
                        status["unreachable_upgrade"] = ep.name
                except Exception:  # noqa: BLE001
                    status["unreachable_upgrade"] = ep.name
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: health reporting is best-effort; never propagate.
        logger.debug("backend status probe failed: %s", exc)
    return status


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


def _record_rejection(count: int, source: str, cwd: str | None) -> None:
    """Best-effort ``memory_feedback`` event for a deletion (never raises).

    A deletion is an explicit "this surfaced finding was wrong /
    irrelevant / resolved" verdict — the noise signal the insurance
    frame needs (see ``project_memory_as_insurance``). Emitted from the
    single ``forget_entries`` chokepoint so every deletion path
    (``/recall drop``, review, reconciler) is captured exactly once.
    """
    try:
        from attune.telemetry.memory_events import log_memory_event

        log_memory_event(
            "memory_feedback",
            verdict="rejected",
            source=source,
            count=count,
            cwd=cwd,
        )
    except Exception:  # noqa: BLE001
        # INTENTIONAL: feedback telemetry must never break a deletion.
        pass


def forget_entries(
    ids: list[str],
    backend: SearchableMemoryBackend | None = None,
    *,
    source: str = "forget",
    cwd: str | None = None,
) -> int:
    """Delete stashed findings by record ID. 0 when unavailable.

    The precise-removal correction path (vs. ``prune``'s age sweep):
    used by the recall reconciler when a task note's referent (e.g. a
    PR) has since resolved, and by per-finding review deletion. Returns
    the number of entries deleted. Never raises — safe to call from a
    hook. Backends predating ``forget`` degrade to 0.

    A successful deletion (count > 0) emits one ``memory_feedback``
    event tagged with ``source``/``cwd`` — the noise denominator for
    the memory analyzer. This is the single emit point; delegating
    callers (``forget_by_prefix``) pass ``source``/``cwd`` through and
    must NOT emit again.

    Args:
        ids: Record IDs (the ``id`` values from ``search``/``recent``).
        backend: Optional injected backend; resolved from the entry
            point when omitted.
        source: Rejection origin for the feedback event
            (``recall_drop`` / ``review`` / ``reconciler`` / ``forget``).
        cwd: Optional project path recorded on the feedback event.

    Returns:
        Count of deleted entries (best-effort).
    """
    if not ids:
        return 0
    target = resolve_backend(backend)
    if target is None:
        return 0
    forget = getattr(target, "forget", None)
    if not callable(forget):
        return 0
    try:
        count = int(forget(list(ids)) or 0)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: forget is best-effort; never break the host session.
        logger.warning("session stash forget failed: %s", exc)
        return 0
    if count > 0:
        _record_rejection(count=count, source=source, cwd=cwd)
    return count


def forget_by_prefix(
    prefixes: list[str],
    limit: int = 100,
    cwd: str | None = None,
    backend: SearchableMemoryBackend | None = None,
    *,
    source: str = "recall_drop",
) -> int:
    """Delete stashed findings by short (unique) ID prefix. 0 when none.

    The review-affordance path: the Stop-hook chip shows each finding
    with a short id prefix; this resolves those prefixes against the
    most-recent records and deletes exact, UNAMBIGUOUS matches. An
    ambiguous prefix (two records match) or an unknown one is skipped —
    deletion must never guess. Never raises.

    Args:
        prefixes: Short id prefixes (e.g. the first 8 chars shown in
            the stash chip). Full ids work too.
        limit: How many recent records to resolve against.
        cwd: Optional project filter passed to ``recent``; also
            recorded on the emitted feedback event.
        backend: Optional injected backend; resolved from the entry
            point when omitted.
        source: Rejection origin threaded to ``forget_entries`` for the
            feedback event (defaults to ``recall_drop``).

    Returns:
        Count of deleted entries (best-effort).
    """
    wanted = [p.strip() for p in prefixes if p and p.strip()]
    if not wanted:
        return 0
    target = resolve_backend(backend)
    if target is None:
        return 0
    recent = getattr(target, "recent", None)
    if not callable(recent):
        return 0
    try:
        records = recent(limit=limit, cwd=cwd) or []
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: resolution is best-effort; never break the caller.
        logger.warning("forget_by_prefix recent-listing failed: %s", exc)
        return 0
    ids = [str(r.get("id")) for r in records if isinstance(r, dict) and r.get("id")]
    full_ids: list[str] = []
    for prefix in wanted:
        matches = [i for i in ids if i.startswith(prefix)]
        if len(matches) == 1:
            full_ids.append(matches[0])
        else:
            logger.info("forget_by_prefix: prefix %r skipped (%d matches)", prefix, len(matches))
    # forget_entries is the single emit point; pass source/cwd through.
    return forget_entries(full_ids, backend=target, source=source, cwd=cwd)


def recent_entries(
    top_k: int = 5,
    cwd: str | None = None,
    backend: SearchableMemoryBackend | None = None,
) -> list[dict[str, Any]]:
    """Query-less recall of the most-recent findings (for SessionStart).

    SessionStart has no query, so recall is recency-driven: the newest
    stashed findings, with same-``cwd`` findings surfaced first. Returns
    an empty list when no backend is available or the backend predates the
    ``recent`` method. Never raises — safe to call from a hook.

    Args:
        top_k: Max results.
        cwd: When set, prefer entries from this project root (soft filter).
        backend: Optional injected backend; resolved from the entry point
            when omitted.

    Returns:
        Ranked memory records as dicts (newest first), or ``[]``.
    """
    target = resolve_backend(backend)
    if target is None:
        return []
    recent = getattr(target, "recent", None)
    if not callable(recent):
        # Backend predates query-less recall — degrade quietly.
        return []
    try:
        results = recent(limit=top_k, cwd=cwd)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: recall is best-effort; never break the host session.
        logger.warning("session recent-recall failed: %s", exc)
        return []
    return results if isinstance(results, list) else []
