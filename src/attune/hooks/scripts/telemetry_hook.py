"""PostToolUse Telemetry Hook.

Records tool usage telemetry for cost tracking and session analytics.
Runs after each Bash, Edit, or Write tool call.

Claude Code Protocol:
    stdin: JSON with tool_name, tool_input, and tool_output
    exit 0: always (telemetry is fire-and-forget)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import json
import logging
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)


def record_telemetry(context: dict[str, Any]) -> None:
    """Record tool usage telemetry.

    Args:
        context: Hook context with tool_name, tool_input, tool_output.

    """
    tool_name = context.get("tool_name", "unknown")
    timestamp = time.time()

    # Log tool usage for session analytics
    logger.info(
        "tool_usage",
        extra={
            "tool_name": tool_name,
            "timestamp": timestamp,
        },
    )


def _read_stdin_context() -> dict[str, Any]:
    """Read hook context from stdin (Claude Code protocol).

    Returns:
        Parsed context dict, or empty dict if stdin is empty/invalid.

    """
    if sys.stdin.isatty():
        return {}
    try:
        _buf = getattr(sys.stdin, "buffer", None)  # None when tests patch stdin
        raw = (_buf.read().decode("utf-8", errors="replace") if _buf else sys.stdin.read()).strip()
        if raw:
            parsed = json.loads(raw)
            # A non-dict payload (list/int/str/null) has no telemetry
            # fields; degrade to {} so record_telemetry's .get calls
            # can't crash the exit-0 contract (library-review L2).
            if isinstance(parsed, dict):
                return parsed
    except (json.JSONDecodeError, ValueError, RecursionError) as e:
        logger.debug("Could not parse stdin JSON: %s", e)
    return {}


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    ctx = _read_stdin_context()
    try:
        record_telemetry(ctx)
    except Exception as e:  # noqa: BLE001
        # Telemetry is fire-and-forget; the PostToolUse contract is
        # exit-0-always, so no internal error may crash it (L2).
        logger.debug("telemetry_hook error (ignored): %s", e)
    sys.exit(0)
