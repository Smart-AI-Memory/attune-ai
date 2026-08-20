"""Persistence mixin for file-based session memory.

Handles directory creation, session loading/saving, atomic writes,
and session archiving with optional gzip compression.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import gzip
import json
import time
from pathlib import Path

import structlog

from attune.security.path_validation import _validate_file_path

from .file_session_models import FileSessionConfig, SessionState

logger = structlog.get_logger(__name__)


class PersistenceMixin:
    """Mixin providing session persistence operations.

    Expects the host class to have:
        - self.config: FileSessionConfig
        - self.user_id: str
        - self._state: SessionState
        - self._dirty: bool
    """

    config: FileSessionConfig
    user_id: str
    _state: SessionState
    _dirty: bool

    # =========================================================================
    # Directory Management
    # =========================================================================

    def _ensure_directories(self) -> None:
        """Create required directories for session storage."""
        dirs = [
            self.config.sessions_dir,
            self.config.patterns_dir,
            self.config.patterns_dir / "staged",
            self.config.patterns_dir / "promoted",
            self.config.archive_dir,
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # Session Lifecycle
    # =========================================================================

    def _load_current_or_create(self) -> SessionState:
        """Load current session or create a new one.

        Returns:
            Active or newly created SessionState.

        """
        current_file = self.config.sessions_dir / "current.json"

        if current_file.exists():
            try:
                data = json.loads(current_file.read_text(encoding="utf-8"))
                # A valid-JSON non-dict would reach from_dict and raise
                # AttributeError/TypeError past the handler below,
                # crashing session load instead of starting a fresh
                # session (library-review E1 widening).
                if not isinstance(data, dict):
                    raise ValueError("session file is not a JSON object")
                state = SessionState.from_dict(data)

                # Check if session is stale
                age_hours = (time.time() - state.last_updated) / 3600
                if age_hours < self.config.session_ttl_hours:
                    logger.info(
                        "session_resumed",
                        session_id=state.session_id,
                        age_hours=age_hours,
                    )
                    return state

                # Archive stale session
                logger.info(
                    "session_stale",
                    session_id=state.session_id,
                    age_hours=age_hours,
                )
                self._archive_session(state)

            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                logger.warning("session_load_failed", error=str(e))

        # Create new session
        state = SessionState.new(self.user_id)
        self._save_current(state)
        logger.info("session_created", session_id=state.session_id)
        return state

    def _load_session(self, session_id: str) -> SessionState:
        """Load a specific session by ID.

        Args:
            session_id: The session identifier to load.

        Returns:
            The loaded SessionState.

        Raises:
            ValueError: If session is not found.

        """
        # Try current
        current_file = self.config.sessions_dir / "current.json"
        if current_file.exists():
            data = json.loads(current_file.read_text(encoding="utf-8"))
            if data.get("session_id") == session_id:
                return SessionState.from_dict(data)

        # Try archive
        archive_file = self.config.archive_dir / f"{session_id}.json.gz"
        if archive_file.exists():
            with gzip.open(archive_file, "rt", encoding="utf-8") as f:
                data = json.load(f)
                return SessionState.from_dict(data)

        raise ValueError(f"Session not found: {session_id}")

    def _save_current(self, state: SessionState | None = None) -> None:
        """Save current session state with atomic write.

        Args:
            state: State to save; defaults to self._state.

        """
        state = state or self._state
        state.last_updated = time.time()

        current_file = self.config.sessions_dir / "current.json"
        self._atomic_write(current_file, state.to_dict())
        self._dirty = False

    def _atomic_write(self, path: Path, data: dict) -> None:
        """Write JSON with atomic rename to prevent corruption.

        Args:
            path: Target file path.
            data: Dictionary to serialize as JSON.

        """
        # Validate path
        validated_path = _validate_file_path(str(path))

        # Write to temp file first
        tmp_path = validated_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )

        # Atomic rename (use replace() for cross-platform
        # support - rename() fails on Windows when target exists)
        tmp_path.replace(validated_path)

    def _archive_session(self, state: SessionState) -> Path:
        """Archive a session to compressed storage.

        Args:
            state: Session state to archive.

        Returns:
            Path to the archived file.

        """
        archive_file = self.config.archive_dir / f"{state.session_id}.json.gz"

        if self.config.archive_compression:
            with gzip.open(archive_file, "wt", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2, default=str)
        else:
            archive_file = archive_file.with_suffix("")
            archive_file.write_text(
                json.dumps(state.to_dict(), indent=2, default=str),
                encoding="utf-8",
            )

        logger.info(
            "session_archived",
            session_id=state.session_id,
            path=str(archive_file),
        )
        return archive_file
