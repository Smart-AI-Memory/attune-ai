"""Session state for progressive help depth.

Tracks which topic the user is viewing and at what
depth level. Persists to ~/.attune/help_session.json
with a 4-hour TTL. Thread-safe for concurrent sessions.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SESSION_FILE = Path("~/.attune/help_session.json").expanduser()
_SESSION_TTL_SECONDS = 4 * 3600  # 4 hours
_SESSION_LOCK = threading.RLock()


def _defaults() -> dict[str, Any]:
    """Fresh session defaults."""
    return {"last_topic": None, "depth_level": 0}


def _load_session() -> dict[str, Any]:
    """Load session state from disk.

    Returns fresh defaults if the file is missing, corrupt,
    or older than _SESSION_TTL_SECONDS. Thread-safe.

    Returns:
        Session state dict with last_topic and depth_level.
    """
    with _SESSION_LOCK:
        defaults = _defaults()
        try:
            if not _SESSION_FILE.exists():
                return defaults
            data = json.loads(
                _SESSION_FILE.read_text(encoding="utf-8"),
            )
            # A valid-JSON non-dict (externally corrupted cache) would
            # crash the .get chain below — and _load_session() runs at
            # module import, so that crash hits every importer
            # (library-review F3). The docstring promises defaults.
            if not isinstance(data, dict):
                return defaults
            ts = data.get("timestamp", 0)
            if time.time() - ts > _SESSION_TTL_SECONDS:
                return defaults
            return {
                "last_topic": data.get("last_topic"),
                "depth_level": data.get("depth_level", 0),
            }
        except (json.JSONDecodeError, OSError, KeyError):
            return defaults


def _persist_session(state: dict[str, Any]) -> None:
    """Write session state to disk atomically.

    Creates ~/.attune/ if needed. Thread-safe. Failures
    are silently ignored — persistence is best-effort.

    Args:
        state: Session state dict to persist.
    """
    with _SESSION_LOCK:
        try:
            _SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = _SESSION_FILE.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(
                    {
                        "last_topic": state["last_topic"],
                        "depth_level": state["depth_level"],
                        "timestamp": time.time(),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            tmp.replace(_SESSION_FILE)
        except OSError:
            pass  # Best-effort


# Module-level state (loaded once at import time).
_session_state: dict[str, Any] = _load_session()


def get_state() -> dict[str, Any]:
    """Get the current session state (thread-safe read).

    Returns:
        Dict with last_topic and depth_level.
    """
    with _SESSION_LOCK:
        return dict(_session_state)


def update_state(
    topic: str,
    starting_level: int | None = None,
) -> int:
    """Update session state for a topic access.

    If the topic matches the last one, depth increments.
    Otherwise resets to starting_level (default 0).

    Args:
        topic: Topic being accessed.
        starting_level: Override starting depth (0-2).

    Returns:
        The new depth level.
    """
    with _SESSION_LOCK:
        if topic == _session_state["last_topic"]:
            _session_state["depth_level"] = min(
                _session_state["depth_level"] + 1,
                2,
            )
        else:
            _session_state["last_topic"] = topic
            _session_state["depth_level"] = starting_level if starting_level is not None else 0
        depth = _session_state["depth_level"]
        _persist_session(_session_state)
        return depth


def reset_session() -> None:
    """Reset progressive depth to defaults."""
    with _SESSION_LOCK:
        _session_state["last_topic"] = None
        _session_state["depth_level"] = 0
        _persist_session(_session_state)
