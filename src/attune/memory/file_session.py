"""File-Based Session Memory for Attune AI.

Provides persistent session storage without requiring Redis.
Uses JSON files with atomic writes for data safety.

This is the primary storage layer for users without Redis.
Redis becomes an optional enhancement for real-time features.

Features:
- Atomic writes (write to temp, then rename)
- TTL support with lazy expiration
- Session history for context continuity
- Auto-compaction of old sessions
- Cross-session pattern promotion

Architecture:
    .attune/
    |-- sessions/
    |   |-- current.json       <- Active session state
    |   |-- archive/           <- Compressed old sessions
    |   +-- index.json         <- Session metadata index
    |-- patterns/
    |   |-- staged/            <- Patterns awaiting validation
    |   +-- promoted/          <- Validated patterns
    +-- config.json            <- User preferences

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import gzip
import json
import time
from typing import Any

import structlog

# Re-export all public data models so existing imports
# from attune.memory.file_session still work.
from .file_session_models import (  # noqa: F401
    FileSessionConfig,
    SessionState,
    StagedPatternFile,
    WorkingEntry,
)
from .file_session_patterns import PatternStagingMixin
from .file_session_persistence import PersistenceMixin

logger = structlog.get_logger(__name__)


# =============================================================================
# File Session Memory (Facade)
# =============================================================================


class FileSessionMemory(PersistenceMixin, PatternStagingMixin):
    """File-based session memory with persistence.

    This class provides the same interface as RedisShortTermMemory
    but uses local JSON files instead of Redis.

    Usage:
        memory = FileSessionMemory(user_id="developer")

        # Store working data
        memory.stash("analysis_results", {"issues": 3})

        # Retrieve data
        results = memory.retrieve("analysis_results")

        # Stage a pattern
        memory.stage_pattern(
            pattern_id="sec_001",
            pattern_type="security",
            name="SQL Injection Prevention",
            description="Always use parameterized queries",
            confidence=0.9
        )

        # Persist on close
        memory.close()
    """

    def __init__(
        self,
        user_id: str,
        config: FileSessionConfig | None = None,
        session_id: str | None = None,
    ):
        """Initialize file-based session memory.

        Args:
            user_id: User/agent identifier.
            config: Configuration (uses defaults if None).
            session_id: Resume specific session (creates new
                if None).
        """
        self.user_id = user_id
        self.config = config or FileSessionConfig()
        self._dirty = False  # Track unsaved changes

        # Create directories
        self._ensure_directories()

        # Load or create session
        if session_id:
            self._state = self._load_session(session_id)
        else:
            self._state = self._load_current_or_create()

        logger.info(
            "file_session_memory_initialized",
            user_id=user_id,
            session_id=self._state.session_id,
            base_dir=str(self.config.base_dir),
        )

    # =========================================================================
    # Working Memory (Redis-compatible interface)
    # =========================================================================

    def stash(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        agent_id: str | None = None,
    ) -> bool:
        """Store data in working memory.

        Args:
            key: Storage key.
            value: Data to store (must be JSON-serializable).
            ttl: Time-to-live in seconds (default from config).
            agent_id: Agent identifier (defaults to user_id).

        Returns:
            True if stored successfully.
        """
        ttl = ttl or self.config.working_ttl_seconds
        agent_id = agent_id or self.user_id

        entry = WorkingEntry(
            key=key,
            value=value,
            agent_id=agent_id,
            stashed_at=time.time(),
            expires_at=(time.time() + ttl if ttl else None),
        )

        self._state.working_memory[key] = entry
        self._dirty = True

        logger.debug("working_stashed", key=key, ttl=ttl)
        return True

    def retrieve(
        self,
        key: str,
        agent_id: str | None = None,
    ) -> Any | None:
        """Retrieve data from working memory.

        Args:
            key: Storage key.
            agent_id: Agent identifier (for cross-agent
                retrieval).

        Returns:
            Stored value or None if not found/expired.
        """
        # Clean up expired entries
        self._cleanup_expired()

        entry = self._state.working_memory.get(key)
        if entry is None:
            return None

        if entry.is_expired():
            del self._state.working_memory[key]
            self._dirty = True
            return None

        return entry.value

    def delete(self, key: str) -> bool:
        """Delete a key from working memory.

        Args:
            key: Key to delete.

        Returns:
            True if deleted, False if key not found.
        """
        if key in self._state.working_memory:
            del self._state.working_memory[key]
            self._dirty = True
            return True
        return False

    def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern (supports * wildcard).

        Args:
            pattern: Glob-style pattern for key matching.

        Returns:
            List of matching key names.
        """
        import fnmatch

        self._cleanup_expired()
        return [k for k in self._state.working_memory.keys() if fnmatch.fnmatch(k, pattern)]

    def _cleanup_expired(self) -> None:
        """Remove expired entries from working memory."""
        expired = [k for k, v in self._state.working_memory.items() if v.is_expired()]
        for key in expired:
            del self._state.working_memory[key]
        if expired:
            self._dirty = True
            logger.debug("expired_entries_cleaned", count=len(expired))

    # =========================================================================
    # Context Management
    # =========================================================================

    def set_context(self, key: str, value: Any) -> None:
        """Store context data (no TTL, persists for session).

        Args:
            key: Context key.
            value: Context value.
        """
        self._state.context[key] = value
        self._dirty = True

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve context data.

        Args:
            key: Context key.
            default: Default if key not found.

        Returns:
            Stored context value or default.
        """
        return self._state.context.get(key, default)

    def get_all_context(self) -> dict[str, Any]:
        """Get all context data.

        Returns:
            Copy of the full context dictionary.
        """
        return self._state.context.copy()

    # =========================================================================
    # Session History
    # =========================================================================

    def get_recent_sessions(self, limit: int = 5) -> list[dict]:
        """Load recent archived sessions for context continuity.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of session summaries (most recent first).
        """
        archive_dir = self.config.archive_dir
        sessions: list[dict] = []

        # Find archived sessions
        archive_files = sorted(
            archive_dir.glob("session_*.json*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for archive_file in archive_files[:limit]:
            try:
                if archive_file.suffix == ".gz":
                    with gzip.open(archive_file, "rt", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = json.loads(archive_file.read_text(encoding="utf-8"))

                sessions.append(
                    {
                        "session_id": data.get("session_id"),
                        "user_id": data.get("user_id"),
                        "started_at": data.get("started_at"),
                        "last_updated": data.get("last_updated"),
                        "context_keys": list(data.get("context", {}).keys()),
                        "pattern_count": len(data.get("staged_patterns", {})),
                    }
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "session_load_error",
                    file=str(archive_file),
                    error=str(e),
                )

        return sessions

    # =========================================================================
    # Statistics and Diagnostics
    # =========================================================================

    def get_stats(self) -> dict:
        """Get memory statistics.

        Returns:
            Dictionary of current memory statistics.
        """
        self._cleanup_expired()

        return {
            "mode": "file",
            "session_id": self._state.session_id,
            "user_id": self.user_id,
            "working_keys": len(self._state.working_memory),
            "staged_patterns": len(self._state.staged_patterns),
            "context_keys": len(self._state.context),
            "session_age_hours": ((time.time() - self._state.started_at) / 3600),
            "dirty": self._dirty,
            "base_dir": str(self.config.base_dir),
        }

    def is_connected(self) -> bool:
        """Check if storage is available.

        Returns:
            Always True for file-based storage.
        """
        return True

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def save(self) -> None:
        """Explicitly save session state."""
        if self._dirty:
            self._save_current()
            logger.debug(
                "session_saved",
                session_id=self._state.session_id,
            )

    def close(self) -> None:
        """Close session and save state."""
        if self.config.auto_compact_on_close:
            self._cleanup_expired()
            self._cleanup_expired_patterns()

        self.save()
        logger.info(
            "session_closed",
            session_id=self._state.session_id,
        )

    def __enter__(self) -> FileSessionMemory:
        """Enter context manager.

        Returns:
            Self for use in with-statement.
        """
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager, closing session."""
        self.close()

    # =========================================================================
    # Redis Compatibility (No-op for features requiring Redis)
    # =========================================================================

    @property
    def use_mock(self) -> bool:
        """File-based memory is not mock mode."""
        return False

    def publish(self, channel: str, message: dict) -> int:
        """Publish is not supported in file mode.

        Args:
            channel: Channel name (unused).
            message: Message payload (unused).

        Returns:
            Always 0 (no subscribers).
        """
        logger.warning("publish_not_supported", channel=channel)
        return 0

    def subscribe(self, channel: str, handler: Any) -> bool:
        """Subscribe is not supported in file mode.

        Args:
            channel: Channel name (unused).
            handler: Message handler (unused).

        Returns:
            Always False.
        """
        logger.warning("subscribe_not_supported", channel=channel)
        return False

    def supports_realtime(self) -> bool:
        """Check if real-time features are available.

        Returns:
            Always False for file-based storage.
        """
        return False

    def supports_distributed(self) -> bool:
        """Check if distributed features are available.

        Returns:
            Always False for file-based storage.
        """
        return False


# =============================================================================
# Factory Function
# =============================================================================


def get_file_session_memory(
    user_id: str,
    base_dir: str = ".attune",
    **kwargs: Any,
) -> FileSessionMemory:
    """Create a file-based session memory instance.

    Args:
        user_id: User/agent identifier.
        base_dir: Base directory for storage.
        **kwargs: Additional config options passed to
            FileSessionConfig.

    Returns:
        Configured FileSessionMemory instance.
    """
    config = FileSessionConfig(base_dir=base_dir, **kwargs)
    return FileSessionMemory(user_id=user_id, config=config)
