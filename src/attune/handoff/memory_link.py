"""D5 memory linkage — session-stash handoff pointers, degrade-silent.

``handoff_create`` stashes a topic-``handoff`` pointer through the same
session-stash helpers the ``session_memory_capture`` MCP handler wraps;
``handoff_resume`` recalls pointers for the slug. Every failure path
returns ``{"status": "skipped", "reason": <stable code>}`` — the
``memory`` report key is always present and this module never raises
(R3: degrade silently, but say so). Spec:
docs/specs/cross-provider-session-handoff/ (D5).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Pointers are recall aids, not the packet — keep resume results short.
RECALL_TOP_K = 3

#: Keys surfaced from backend-shaped recall records (bounded report).
#: Matches the searchable backends' search() shape (file tier: id/text/
#: topics/cwd/session_id/score); volatile keys are dropped.
_RESULT_KEYS = ("id", "text", "content", "topics", "score", "provenance")


def _skip_reason(session_stash: Any) -> str:
    """Stable machine-readable reason for a failed write (never raises)."""
    try:
        status = session_stash.backend_status()
        reason = status.get("reason") if isinstance(status, dict) else None
        return str(reason) if reason else "write_failed"
    except Exception:  # noqa: BLE001
        # INTENTIONAL: reason lookup is best-effort; the skip itself is
        # already truthful.
        return "write_failed"


def link_create(slug: str, *, goal: str, path: str, cwd: str) -> dict[str, Any]:
    """Stash a handoff pointer for ``slug``; report the outcome.

    Args:
        slug: Packet slug (branch with ``/`` as ``-``).
        goal: Caller-asserted goal, quoted in the pointer content.
        path: Written packet path (the pointer's referent).
        cwd: Repo root at create time (cwd-scoped recall).

    Returns:
        ``{"status": "captured", "id": ...}`` on a durable write, else
        ``{"status": "skipped", "reason": <stable code>}``.
    """
    try:
        from attune.memory import session_stash
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: memory linkage must never break packet creation.
        logger.debug("handoff memory link unavailable: %s", exc)
        return {"status": "skipped", "reason": "session_stash_unavailable"}
    try:
        content = f"Handoff packet {slug}: {goal or 'no goal recorded'} ({path})"
        entry = session_stash.SessionStashEntry.create(
            session_id="handoff",
            cwd=cwd,
            type="reference",
            content=content,
            tags=["handoff", f"slug:{slug}"],
        )
        if session_stash.stash_entry(entry):
            return {"status": "captured", "id": entry.id}
        return {"status": "skipped", "reason": _skip_reason(session_stash)}
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: a backend/sanitizer error is a skip, not a failure
        # of handoff_create itself.
        logger.warning("handoff memory link failed: %s", exc)
        return {"status": "skipped", "reason": "stash_error"}


def link_resume(slug: str, *, cwd: str) -> dict[str, Any]:
    """Recall handoff pointers for ``slug``; report the outcome.

    Returns:
        ``{"status": "recalled", "count": N, "results": [...]}`` when a
        backend answered (``count`` may be 0 — an honest empty recall),
        else ``{"status": "skipped", "reason": <stable code>}``.
    """
    try:
        from attune.memory import session_stash
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: memory linkage must never break packet resume.
        logger.debug("handoff memory link unavailable: %s", exc)
        return {"status": "skipped", "reason": "session_stash_unavailable"}
    try:
        # recall_entries returns [] both for "no backend" and "no hits";
        # distinguish them so an unreachable backend is a stated skip,
        # not a silent empty recall.
        status = session_stash.backend_status()
        if not (isinstance(status, dict) and status.get("ok")):
            reason = status.get("reason") if isinstance(status, dict) else None
            return {"status": "skipped", "reason": str(reason or "no_backend")}
        results = session_stash.recall_entries(f"handoff {slug}", top_k=RECALL_TOP_K, cwd=cwd)
        trimmed = [
            {k: r[k] for k in _RESULT_KEYS if k in r} for r in results if isinstance(r, dict)
        ]
        return {"status": "recalled", "count": len(trimmed), "results": trimmed}
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: recall is best-effort; the report stays truthful.
        logger.warning("handoff memory recall failed: %s", exc)
        return {"status": "skipped", "reason": "recall_error"}
