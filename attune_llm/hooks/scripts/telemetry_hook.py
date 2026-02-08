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
        raw = sys.stdin.read().strip()
        if raw:
            return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug("Could not parse stdin JSON: %s", e)
    return {}


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    ctx = _read_stdin_context()
    record_telemetry(ctx)
    # Telemetry is fire-and-forget — always exit 0
    sys.exit(0)
