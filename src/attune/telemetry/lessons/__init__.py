"""Self-healing traps for Attune AI.

Deterministic failure capture (pre-commit rejections, pytest failures)
feeding the existing session-stash/recall pipeline. Spec:
docs/specs/self-healing-traps/ (D1: feed the stash — no corpus writes,
no inbox; D2: PostToolUse Bash seam via plugin/hooks/trap_stash.py).
"""

import logging
from typing import TYPE_CHECKING

from .listener import TrapEvent, extract_trap
from .synthesizer import format_trap

if TYPE_CHECKING:
    from attune.memory.backend import SearchableMemoryBackend

__all__ = [
    "TrapEvent",
    "extract_trap",
    "format_trap",
    "process_bash_result",
]


def process_bash_result(
    command: str,
    output: str,
    session_id: str,
    cwd: str,
    backend: "SearchableMemoryBackend | None" = None,
) -> str | None:
    """Extract a trap from a Bash result and stash it (R1/R4).

    The composition the trap_stash hook runs: extract → format →
    PII-gated stash write. Degrades to None (no-op) when nothing
    matches or no backend is available — never raises.

    Args:
        command: The command line that ran.
        output: Combined tool output text.
        session_id: Originating session id.
        cwd: Project root at capture time.
        backend: Optional backend override (tests inject a real
            file backend here).

    Returns:
        The trap signature when an entry was stashed, else None —
        callers use the signature for per-session dedupe.
    """
    event = extract_trap(command, output)
    if event is None:
        return None

    try:
        from attune.memory.session_stash import SessionStashEntry, stash_entry

        entry = SessionStashEntry.create(
            session_id=session_id,
            cwd=cwd,
            type="bug",
            content=format_trap(event),
            tags=["trap", f"trap:{event.family}"],
        )
        if stash_entry(entry, backend=backend):
            return event.signature
    except Exception:  # noqa: BLE001 — memory layer must never break a tool call
        logging.getLogger(__name__).debug("trap stash skipped", exc_info=True)
        return None
    return None
