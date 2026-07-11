"""Lessons Learned Reminder Hook

Runs on Stop to prompt Claude to append new lessons to the
canonical corpus (.claude/lessons.md post-T5-cutover; CLAUDE.md
on pre-cutover layouts) before ending the session.

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
    """Write the sentinel file to suppress repeat reminders."""
    SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    SENTINEL.touch()


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
        "Before ending the session, review what was learned and append "
        "any new patterns, fixes, or insights worth remembering to the "
        "## Lessons Learned section in .claude/lessons.md (the canonical "
        "corpus; use .claude/CLAUDE.md only on pre-cutover layouts where "
        "lessons.md doesn't exist). Mirror into CLAUDE.md's 'Lessons — "
        "core' ONLY if core-worthy — then keep both copies in sync. "
        "If nothing new was learned, reply 'No new lessons' and stop.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
