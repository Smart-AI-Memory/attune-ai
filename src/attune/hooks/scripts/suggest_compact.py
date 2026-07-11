"""Suggest Compact Hook

Suggests strategic compaction at logical breakpoints to manage context window.
Ported from everything-claude-code/scripts/hooks/suggest-compact.js

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# Configuration
DEFAULT_COMPACT_THRESHOLD = 50  # Tool calls before first suggestion
DEFAULT_REMINDER_INTERVAL = 25  # Interval between reminders


def get_compaction_state_file() -> Path:
    """Get the compaction state file path."""
    return Path.home() / ".attune" / "compaction_state.json"


def load_compaction_state() -> dict[str, Any]:
    """Load compaction tracking state.

    Returns:
        Current compaction state

    """
    state_file = get_compaction_state_file()

    if state_file.exists():
        try:
            with open(state_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "tool_call_count": 0,
        "last_suggestion": None,
        "last_compaction": None,
        "suggestion_count": 0,
    }


def save_compaction_state(state: dict[str, Any]) -> None:
    """Save compaction tracking state.

    Args:
        state: State to save

    """
    state_file = get_compaction_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: tempfile in the same directory + os.replace, so a
    # concurrent session never observes a truncated/partial JSON file.
    fd, tmp_path = tempfile.mkstemp(
        dir=state_file.parent,
        prefix=state_file.name,
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, state_file)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def should_suggest_compaction(
    state: dict[str, Any],
    threshold: int = DEFAULT_COMPACT_THRESHOLD,
    interval: int = DEFAULT_REMINDER_INTERVAL,
) -> tuple[bool, str]:
    """Determine if compaction should be suggested.

    Args:
        state: Current compaction state
        threshold: Tool calls before first suggestion
        interval: Interval between reminders

    Returns:
        Tuple of (should_suggest, reason)

    """
    count = state.get("tool_call_count", 0)

    # First threshold
    if count == threshold:
        return True, f"Reached {threshold} tool calls - good time to compact"

    # Periodic reminders after threshold
    if count > threshold and (count - threshold) % interval == 0:
        return True, f"At {count} tool calls - consider compacting"

    return False, ""


def get_compaction_recommendations(context: dict[str, Any]) -> list[str]:
    """Get recommendations for what to compact.

    Args:
        context: Current session context

    Returns:
        List of recommendations

    """
    recommendations = []

    # Check completed phases
    completed_phases = context.get("completed_phases", [])

    if completed_phases:
        recommendations.append(
            f"Completed phases ({', '.join(completed_phases)}) can be summarized",
        )

    # Check for exploration context
    if context.get("exploration_complete", False):
        recommendations.append("Exploration context can be compacted to findings only")

    # Check for research context
    if context.get("research_complete", False):
        recommendations.append("Research context can be compacted to conclusions")

    # General recommendations
    if not recommendations:
        recommendations = [
            "Summarize completed work before starting new tasks",
            "Keep implementation plan, compact exploration details",
            "Preserve critical decisions and constraints",
        ]

    return recommendations


def main(**context: Any) -> dict[str, Any]:
    """Suggest compact hook main function.

    Tracks tool usage and suggests compaction at strategic points.

    Args:
        **context: Hook context (tool name, current phase, etc.)

    Returns:
        Compaction suggestion result

    """
    threshold = int(os.environ.get("COMPACT_THRESHOLD", DEFAULT_COMPACT_THRESHOLD))
    interval = int(os.environ.get("COMPACT_INTERVAL", DEFAULT_REMINDER_INTERVAL))

    # Load and update state
    state = load_compaction_state()
    state["tool_call_count"] = state.get("tool_call_count", 0) + 1

    result = {
        "tool_call_count": state["tool_call_count"],
        "suggest_compaction": False,
        "reason": "",
        "recommendations": [],
        "messages": [],
    }

    # Check if we should suggest compaction
    should_suggest, reason = should_suggest_compaction(state, threshold, interval)

    if should_suggest:
        result["suggest_compaction"] = True
        result["reason"] = reason
        result["recommendations"] = get_compaction_recommendations(context)

        state["last_suggestion"] = datetime.now().isoformat()
        state["suggestion_count"] = state.get("suggestion_count", 0) + 1

        result["messages"].append(f"[SuggestCompact] {reason}")
        for rec in result["recommendations"]:
            result["messages"].append(f"[SuggestCompact] - {rec}")

    # Save updated state
    save_compaction_state(state)

    # Log messages
    for msg in result["messages"]:
        logger.info(msg)

    return result


def reset_on_compaction(**context: Any) -> dict[str, Any]:
    """Reset compaction state after a compaction event.

    Called by PreCompact hook.

    Args:
        **context: Hook context

    Returns:
        Reset confirmation

    """
    state = load_compaction_state()
    state["tool_call_count"] = 0
    state["last_compaction"] = datetime.now().isoformat()
    save_compaction_state(state)

    logger.info("[SuggestCompact] Reset after compaction")

    return {
        "reset": True,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    # Allow running as a script for testing

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Simulate tool calls
    for i in range(60):
        result = main(current_phase="implementation")
        if result["suggest_compaction"]:
            print(f"\nCall {i + 1}: SUGGEST COMPACTION")
            print(f"  Reason: {result['reason']}")
            for rec in result["recommendations"]:
                print(f"  - {rec}")
