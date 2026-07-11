#!/usr/bin/env python
"""Diagnostic hook: dump the raw Claude Code hook payload + shell env.

Purpose: resolve the one open question from the 2026-07 cross-platform
work — what the hook payload ACTUALLY contains on native Windows
(Bash-via-Git-Bash vs the opt-in PowerShell tool), so
``security_guard.detect_shell_family()`` can be tightened from
defensive guesses to observed fields.

Register it temporarily as a PreToolUse hook (see
.github/workflows/windows-payload-capture.yml), run one tool call,
and read the capture file. Never blocks anything: always exits 0.

Output: one JSON line per invocation appended to
``$ATTUNE_PAYLOAD_CAPTURE_FILE`` (default: ./hook_payload_capture.jsonl),
containing the raw payload plus the environment markers the detector
relies on.

Stdlib only. Cross-platform (UTF-8 stdin/stdout, atomic-enough
single-write append).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ENV_MARKERS = (
    "CLAUDE_CODE_USE_POWERSHELL_TOOL",
    "CLAUDE_CODE_GIT_BASH_PATH",
    "CLAUDE_PROJECT_DIR",
    "COMSPEC",
    "PSModulePath",
    "SHELL",
)


def main() -> int:
    """Capture stdin payload and environment markers to a JSONL file."""
    buffer = getattr(sys.stdin, "buffer", None)
    raw = (
        buffer.read().decode("utf-8", errors="replace")
        if buffer is not None
        else sys.stdin.read()
    )

    try:
        payload: object = json.loads(raw) if raw.strip() else None
    except json.JSONDecodeError:
        payload = {"_undecodable_raw": raw[:2000]}

    record = {
        "os_name": os.name,
        "sys_platform": sys.platform,
        "env": {k: os.environ.get(k) for k in ENV_MARKERS},
        "payload": payload,
    }

    target = Path(
        os.environ.get("ATTUNE_PAYLOAD_CAPTURE_FILE", "hook_payload_capture.jsonl"),
    )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        with target.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        # Diagnostics must never break the session.
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
