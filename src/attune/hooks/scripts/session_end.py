"""Session End Hook

Persists session state and triggers pattern evaluation.
Ported from everything-claude-code/scripts/hooks/session-end.js

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_sessions_dir() -> Path:
    """Get the sessions directory path."""
    return Path.home() / ".attune" / "sessions"


def save_session_state(
    session_id: str,
    state: dict[str, Any],
) -> Path:
    """Save session state to a file.

    Args:
        session_id: Unique session identifier
        state: Session state to save

    Returns:
        Path to saved file

    """
    sessions_dir = get_sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_{session_id}_{timestamp}.json"
    file_path = sessions_dir / filename

    # Add metadata
    state_with_meta = {
        **state,
        "saved_at": datetime.now().isoformat(),
        "session_id": session_id,
    }

    with open(file_path, "w") as f:
        json.dump(state_with_meta, f, indent=2, default=str)

    logger.info("Saved session state to %s", file_path)
    return file_path


def cleanup_old_sessions(max_sessions: int = 50) -> int:
    """Remove old session files beyond max_sessions.

    Args:
        max_sessions: Maximum number of session files to keep

    Returns:
        Number of files removed

    """
    sessions_dir = get_sessions_dir()

    if not sessions_dir.exists():
        return 0

    session_files = sorted(
        sessions_dir.glob("session_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    removed = 0
    for old_file in session_files[max_sessions:]:
        try:
            old_file.unlink()
            removed += 1
            logger.debug("Removed old session file: %s", old_file)
        except OSError as e:
            logger.warning("Failed to remove %s: %s", old_file, e)

    return removed


def main(**context: Any) -> dict[str, Any]:
    """Session end hook main function.

    Persists:
    - Trust level and collaboration state
    - Detected patterns and preferences
    - Interaction statistics

    Args:
        **context: Hook context with session state

    Returns:
        Session end summary

    """
    session_id = context.get("session_id", datetime.now().strftime("%Y%m%d%H%M%S"))

    # Extract state to persist
    state_to_save = {
        "trust_level": context.get("trust_level", 0.5),
        "empathy_level": context.get("empathy_level", 4),
        "interaction_count": context.get("interaction_count", 0),
        "detected_patterns": context.get("detected_patterns", []),
        "user_preferences": context.get("user_preferences", {}),
        "completed_phases": context.get("completed_phases", []),
        "pending_handoff": context.get("pending_handoff"),
        "metrics": {
            "success_rate": context.get("success_rate", 0),
            "total_tokens": context.get("total_tokens", 0),
            "total_cost": context.get("total_cost", 0),
        },
    }

    result = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "state_saved": False,
        "file_path": None,
        "old_sessions_removed": 0,
        "evaluate_for_learning": False,
        "messages": [],
    }

    try:
        # Save session state
        file_path = save_session_state(session_id, state_to_save)
        result["state_saved"] = True
        result["file_path"] = str(file_path)
        result["messages"].append(f"[SessionEnd] State saved to {file_path.name}")

        # Cleanup old sessions
        removed = cleanup_old_sessions()
        result["old_sessions_removed"] = removed
        if removed > 0:
            result["messages"].append(f"[SessionEnd] Removed {removed} old session file(s)")

        # Check if session should be evaluated for learning
        min_interactions = context.get("min_learning_interactions", 10)
        if state_to_save["interaction_count"] >= min_interactions:
            result["evaluate_for_learning"] = True
            result["messages"].append(
                f"[SessionEnd] Session has {state_to_save['interaction_count']} "
                f"interactions - evaluate for pattern extraction"
            )

        # Chain evaluation into Stop hook for automatic learning
        _try_evaluate_session(context, result)

    except OSError as e:
        logger.error("Failed to save session state: %s", e)
        result["messages"].append(f"[SessionEnd] Error: {e}")

    # Log messages
    for msg in result["messages"]:
        logger.info(msg)

    return result


def _try_evaluate_session(context: dict[str, Any], result: dict[str, Any]) -> None:
    """Attempt to evaluate session for learning patterns.

    Chains evaluate_session into the Stop hook for automatic learning.
    Fails gracefully if the learning module is not available.

    Args:
        context: Hook context from Claude Code.
        result: Mutable result dict to update with evaluation data.

    """
    try:
        from attune.hooks.scripts.evaluate_session import run_evaluate_session

        eval_result = run_evaluate_session(context)
        result["evaluation"] = eval_result
        patterns_extracted = eval_result.get("patterns_extracted", 0)
        if patterns_extracted > 0:
            result["messages"].append(f"[Learning] Extracted {patterns_extracted} pattern(s)")
    except ImportError:
        logger.debug("evaluate_session or learning module not available — skipping")
    except (TypeError, KeyError, ValueError) as e:
        logger.warning("Session evaluation failed: %s", e)


def _read_stdin_context() -> dict[str, Any]:
    """Read hook context from stdin (Claude Code protocol).

    Claude Code passes JSON on stdin with session_id, cwd, transcript_path, etc.
    Handles empty stdin, malformed JSON, and missing fields gracefully.

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
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    context = _read_stdin_context()
    result = main(**context)
    print(json.dumps(result, indent=2))
