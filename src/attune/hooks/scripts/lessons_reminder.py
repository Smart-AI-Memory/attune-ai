"""Lessons Learned Reminder Hook

Runs on Stop to prompt Claude to route new lessons through the
docs outbox (docs/specs/docs-outbox R2) instead of appending
.claude/lessons.md directly — concurrent sessions never conflict,
and the curating sweep batches everything into ONE PR.

Exit code 2 blocks the stop and injects the message into the
conversation so Claude acts on it automatically. A sentinel
file prevents it from firing more than once per session.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import subprocess
import sys
import time
from pathlib import Path

SENTINEL = Path.home() / ".attune" / "lessons_reminded"
SENTINEL_TTL = 3600  # seconds — one hour


def already_reminded() -> bool:
    """Return True if the reminder already fired within this session."""
    if not SENTINEL.exists():
        return False
    age = time.time() - SENTINEL.stat().st_mtime
    return age < SENTINEL_TTL


def mark_reminded() -> None:
    """Write the sentinel file to suppress repeat reminders.

    Best-effort: on an unwritable home (read-only FS, a permissions
    problem) the write is skipped rather than raised. The cost is a
    repeat reminder on the next Stop — the fail-safe direction for a
    nudge — never a crashed Stop hook that drops the reminder entirely.
    """
    try:
        SENTINEL.parent.mkdir(parents=True, exist_ok=True)
        SENTINEL.touch()
    except OSError:
        # INTENTIONAL: the sentinel is an optimization, not a correctness
        # requirement — if it can't be written we simply remind again.
        pass


def has_session_work() -> bool:
    """Return True if this session produced git commits or file edits."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--since=8 hours ago"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        if result.returncode != 0:
            # Not a git repo, or git failed — same "can't check" case as
            # the exception below, so remind rather than silently skip.
            return True
        return bool(result.stdout.strip())
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Fallback — always remind if we can't check
        return True


def main() -> int:
    """Check if a lessons reminder should be shown and print it."""
    if already_reminded() or not has_session_work():
        return 0

    mark_reminded()
    print(
        "Before ending the session, review what was learned and route "
        "any new patterns, fixes, or insights through the docs outbox "
        "— do NOT append .claude/lessons.md directly: "
        "`python -m attune.docs_outbox write --kind lesson --slug "
        "<kebab-slug> --file <body.md>` (one artifact per lesson; the "
        "curating sweep dedupes and batches them into ONE PR). "
        "decisions.md rulings and spec status flips still merge now. "
        "Mirror into CLAUDE.md's 'Lessons — core' ONLY if core-worthy. "
        "If nothing new was learned, reply 'No new lessons' and stop.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: a Stop hook must never crash the session with a
        # traceback. main() returning 2 (remind) raises SystemExit, which
        # passes through; only an unexpected error is caught, and it exits
        # 0 (allow the stop) — the fail-safe direction for a nudge.
        print(
            f"[lessons-reminder] hook error (continuing): {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(0)
