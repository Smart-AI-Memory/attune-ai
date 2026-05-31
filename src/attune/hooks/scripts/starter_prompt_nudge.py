#!/usr/bin/env python3
"""SessionStart hook: surface ~/.attune/next_session_starter.md when present.

Eliminates the cross-session handoff friction documented in the
``feedback_cross_account_handoff`` memory: previously, the starter
prompt had to be pasted manually at the start of each new session.
This hook reads ``~/.attune/next_session_starter.md`` (if it
exists) and prints a short notice with the file path, last-modified
date, and a one-line hint to read it.

The file content itself is NOT printed inline — keeps the
SessionStart noise floor low. Users / the agent open it
explicitly when they want the handoff context.

Output is informational only. Exit code is always 0 so the
session starts normally regardless of file state.

Lives under the enforcement framework at
``docs/specs/enforcement-vs-documentation/``. This is a small,
mechanical surfacing of a recurring handoff pattern. Not a
hard-blocking enforcement (no exit 2), so it doesn't count
against the soft cap of 10 active enforcements.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

STARTER_PATH = Path.home() / ".attune" / "next_session_starter.md"


def _format_age(mtime_ts: float) -> str:
    """Return a short human-readable age like '2h ago', '3d ago'."""
    now = datetime.now(timezone.utc).timestamp()
    delta = now - mtime_ts
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta / 60)}m ago"
    if delta < 86400:
        return f"{int(delta / 3600)}h ago"
    return f"{int(delta / 86400)}d ago"


def main() -> int:
    """Print the starter-prompt notice if the file exists."""
    if not STARTER_PATH.is_file():
        return 0

    try:
        stat = STARTER_PATH.stat()
    except OSError:
        # File disappeared between is_file() and stat(); just no-op.
        return 0

    if stat.st_size == 0:
        # Empty file — nothing to surface.
        return 0

    age = _format_age(stat.st_mtime)
    size_kb = stat.st_size / 1024

    print(
        f"[starter-prompt] {STARTER_PATH} ({size_kb:.1f} KB, modified {age}) — "
        "read this for cross-session handoff context."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: hook errors must never block session start.
        # Surface the failure to stderr; exit 0 so the session proceeds.
        print(
            f"[starter-prompt] hook error (continuing): " f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(0)
