"""Storage protocol for session state.

Defines the SessionStorage interface and a default local
file implementation. Apps can swap in Redis, a database,
or any backend that implements get/set.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

_SESSION_TTL_SECONDS = 4 * 3600  # 4 hours


class SessionStorage(Protocol):
    """Protocol for session state backends.

    Implement get_session() and set_session() to use a
    custom backend (Redis, database, etc.).
    """

    def get_session(self, user_id: str) -> dict[str, Any]:
        """Load session state for a user.

        Args:
            user_id: User identifier.

        Returns:
            Dict with last_topic and depth_level.
        """
        ...

    def set_session(self, user_id: str, state: dict[str, Any]) -> None:
        """Persist session state for a user.

        Args:
            user_id: User identifier.
            state: Session state dict to persist.
        """
        ...


def _defaults() -> dict[str, Any]:
    """Fresh session defaults."""
    return {"last_topic": None, "depth_level": 0}


class LocalFileStorage:
    """File-based session storage (default implementation).

    Stores session state as JSON files in a configurable
    directory. Each user gets their own file. Supports
    4-hour TTL for session expiry.

    Args:
        storage_dir: Directory for session files.
            Defaults to ~/.attune-help/sessions/.
        ttl_seconds: Session time-to-live in seconds.
            Defaults to 4 hours.
    """

    def __init__(
        self,
        storage_dir: str | Path | None = None,
        ttl_seconds: int = _SESSION_TTL_SECONDS,
    ) -> None:
        if storage_dir is None:
            self._dir = Path("~/.attune-help/sessions").expanduser()
        else:
            self._dir = Path(storage_dir)
        self._ttl = ttl_seconds

    @staticmethod
    def _safe_filename(user_id: str) -> str:
        """Sanitize user_id into a safe filename.

        Allows only alphanumerics, hyphens, underscores,
        and dots. Prevents path traversal (CWE-22).

        Args:
            user_id: Raw user identifier.

        Returns:
            Sanitized filename string.

        Raises:
            ValueError: If user_id is empty or invalid.
        """
        import re

        sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", user_id)
        if not sanitized or sanitized in (".", ".."):
            raise ValueError(f"Invalid user_id: {user_id!r}")
        return sanitized

    def _resolve_path(self, user_id: str) -> Path:
        """Resolve and validate the session file path.

        Args:
            user_id: User identifier.

        Returns:
            Safe, resolved Path within the storage dir.
        """
        safe_name = self._safe_filename(user_id)
        path = self._dir / f"{safe_name}.json"
        # Containment check
        try:
            path.resolve().relative_to(self._dir.resolve())
        except ValueError as e:
            raise ValueError(f"Path traversal blocked: {user_id!r}") from e
        return path

    def get_session(self, user_id: str) -> dict[str, Any]:
        """Load session state from a JSON file.

        Args:
            user_id: User identifier (used as filename).

        Returns:
            Session state dict, or fresh defaults if
            file is missing, corrupt, or expired.
        """
        defaults = _defaults()
        try:
            path = self._resolve_path(user_id)
        except ValueError:
            logger.warning("Invalid user_id: %s", user_id)
            return defaults
        try:
            if not path.exists():
                return defaults
            data = json.loads(path.read_text(encoding="utf-8"))
            ts = data.get("timestamp", 0)
            if time.time() - ts > self._ttl:
                return defaults
            return {
                "last_topic": data.get("last_topic"),
                "depth_level": data.get("depth_level", 0),
            }
        except (json.JSONDecodeError, OSError, KeyError):
            return defaults

    def set_session(self, user_id: str, state: dict[str, Any]) -> None:
        """Write session state atomically.

        Args:
            user_id: User identifier.
            state: Session state dict to persist.
        """
        try:
            path = self._resolve_path(user_id)
        except ValueError:
            logger.warning("Invalid user_id: %s", user_id)
            return
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
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
            tmp.replace(path)  # replace() is cross-platform
        except OSError as e:
            logger.warning("Session write failed: %s", e)
