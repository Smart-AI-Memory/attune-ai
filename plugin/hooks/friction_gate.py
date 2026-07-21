"""PreToolUse Adaptive Friction gate for Bash commands.

Scores each proposed Bash command with the Adaptive Friction Matrix
(`attune.orchestration.friction`). PreToolUse payloads carry no user
prompt, so intent clarity bottoms out at 1 and the gate keys off
blast radius alone: high-risk commands land in zone 4.

Modes:
    advisory (default): zone-3/4 commands print a one-line warning to
        stdout and the call proceeds (exit 0).
    enforce (``ATTUNE_FRICTION_ENFORCE=1``): zone-4 commands are
        blocked (exit 2, reason on stderr); everything else proceeds.

The gate degrades silently: if the friction module is unavailable or
the payload is malformed, the tool call is allowed (exit 0). Hard
security invariants stay in ``security_guard.py`` — this hook is a
risk-awareness layer, not the security boundary.

Claude Code Protocol:
    stdin: JSON with tool_name and tool_input
    exit 0: allow tool call
    exit 2: block tool call (reason printed to stderr)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HOOK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOK_DIR))

from _bootstrap import ensure_utf8_stdio, read_stdin_utf8  # noqa: E402


def _load_matrix_cls():
    """Import FrictionMatrix from the installed package or a repo src/ tree."""
    try:
        from attune.orchestration.friction import FrictionMatrix

        return FrictionMatrix
    except ImportError:
        pass

    src = Path.cwd() / "src"
    if (src / "attune" / "__init__.py").is_file():
        sys.path.insert(0, str(src))
        try:
            from attune.orchestration.friction import FrictionMatrix

            return FrictionMatrix
        except ImportError:
            return None
    return None


def main() -> int:
    """Evaluate the incoming Bash command; return the hook exit code."""
    ensure_utf8_stdio()

    try:
        payload = json.loads(read_stdin_utf8(100_000))
    except (json.JSONDecodeError, ValueError):
        return 0

    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0

    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not command:
        return 0

    matrix_cls = _load_matrix_cls()
    if matrix_cls is None:
        return 0

    try:
        result = matrix_cls().evaluate_action(user_prompt="", command_line=command)
    except Exception as exc:  # noqa: BLE001 — hook must never crash a tool call
        print(f"[friction-gate] evaluation skipped: {exc}", file=sys.stderr)
        return 0

    directive = result.get("directive", "")
    reason = result.get("reason", "")

    if directive == "socratic_gate" and os.environ.get("ATTUNE_FRICTION_ENFORCE") == "1":
        print(f"[friction-gate] BLOCKED: {reason}", file=sys.stderr)
        return 2

    if directive in ("plan_review_gate", "socratic_gate"):
        print(f"[friction-gate] high blast radius: {reason}")

    return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    sys.exit(main())
