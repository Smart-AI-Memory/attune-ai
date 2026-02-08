"""File-Based Session Memory for Empathy Framework.

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
    ├── sessions/
    │   ├── current.json       <- Active session state
    │   ├── archive/           <- Compressed old sessions
    │   └── index.json         <- Session metadata index
    ├── patterns/
    │   ├── staged/            <- Patterns awaiting validation
    │   └── promoted/          <- Validated patterns
    └── config.json            <- User preferences

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

from __future__ import annotations

import gzip
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from attune.config import _validate_file_path

logger = structlog.get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class FileSessionConfig:
    """Configuration for file-based session memory."""

    # Storage locations
    base_dir: str = ".empathy"
    sessions_subdir: str = "sessions"
    patterns_subdir: str = "patterns"
    archive_subdir: str = "archive"

    # Session settings
    session_ttl_hours: int = 24
    working_ttl_seconds: int = 3600  # 1 hour default for working memory
    pattern_ttl_seconds: int = 86400  # 24 hours for staged patterns

    # Archive settings
    max_sessions_before_archive: int = 10
    archive_compression: bool = True
    archive_retention_days: int = 30

    # Auto-save settings
    auto_save_interval_seconds: int = 60
    auto_compact_on_close: bool = True

    @property
    def sessions_dir(self) -> Path:
        return Path(self.base_dir) / self.sessions_subdir

    @property
    def patterns_dir(self) -> Path:
        return Path(self.base_dir) / self.patterns_subdir

    @property
    def archive_dir(self) -> Path:
        return self.sessions_dir / self.archive_subdir


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class WorkingEntry:
    """Entry in working memory."""

    key: str
    value: Any
    agent_id: str
    stashed_at: float
    expires_at: float | None = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "agent_id": self.agent_id,
            "stashed_at": self.stashed_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorkingEntry:
        return cls(
            key=data["key"],
            value=data["value"],
            agent_id=data["agent_id"],
            stashed_at=data["stashed_at"],
            expires_at=data.get("expires_at"),
        )


@dataclass
class StagedPatternFile:
    """Pattern staged for validation (file-based version)."""

    pattern_id: str
    agent_id: str
    pattern_type: str
    name: str
    description: str
    code: str | None = None
    confidence: float = 0.5
    staged_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    metadata: dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "agent_id": self.agent_id,
            "pattern_type": self.pattern_type,
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "confidence": self.confidence,
            "staged_at": self.staged_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StagedPatternFile:
        return cls(
            pattern_id=data["pattern_id"],
            agent_id=data["agent_id"],
            pattern_type=data["pattern_type"],
            name=data["name"],
            description=data["description"],
            code=data.get("code"),
            confidence=data.get("confidence", 0.5),
            staged_at=data.get("staged_at", time.time()),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SessionState:
    """Complete state of a session."""

    session_id: str
    user_id: str
    started_at: float
    last_updated: float
    working_memory: dict[str, WorkingEntry] = field(default_factory=dict)
    staged_patterns: dict[str, StagedPatternFile] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "started_at": self.started_at,
            "last_updated": self.last_updated,
            "working_memory": {k: v.to_dict() for k, v in self.working_memory.items()},
            "staged_patterns": {k: v.to_dict() for k, v in self.staged_patterns.items()},
            "context": self.context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SessionState:
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            started_at=data["started_at"],
            last_updated=data["last_updated"],
            working_memory={
                k: WorkingEntry.from_dict(v) for k, v in data.get("working_memory", {}).items()
            },
            staged_patterns={
                k: StagedPatternFile.from_dict(v)
                for k, v in data.get("staged_patterns", {}).items()
            },
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def new(cls, user_id: str) -> SessionState:
        """Create a new session state."""
        now = time.time()
        return cls(
            session_id=f"session_{int(now)}_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            started_at=now,
            last_updated=now,
        )


# =============================================================================
# File Session Memory
# =============================================================================


class FileSessionMemory:
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
            user_id: User/agent identifier
            config: Configuration (uses defaults if None)
            session_id: Resume specific session (creates new if None)
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
    # Directory Management
    # =========================================================================

    def _ensure_directories(self) -> None:
        """Create required directories."""
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
        """Load current session or create a new one."""
        current_file = self.config.sessions_dir / "current.json"

        if current_file.exists():
            try:
                data = json.loads(current_file.read_text(encoding="utf-8"))
                state = SessionState.from_dict(data)

                # Check if session is stale
                age_hours = (time.time() - state.last_updated) / 3600
                if age_hours < self.config.session_ttl_hours:
                    logger.info("session_resumed", session_id=state.session_id, age_hours=age_hours)
                    return state

                # Archive stale session
                logger.info("session_stale", session_id=state.session_id, age_hours=age_hours)
                self._archive_session(state)

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("session_load_failed", error=str(e))

        # Create new session
        state = SessionState.new(self.user_id)
        self._save_current(state)
        logger.info("session_created", session_id=state.session_id)
        return state

    def _load_session(self, session_id: str) -> SessionState:
        """Load a specific session by ID."""
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
        """Save current session state with atomic write."""
        state = state or self._state
        state.last_updated = time.time()

        current_file = self.config.sessions_dir / "current.json"
        self._atomic_write(current_file, state.to_dict())
        self._dirty = False

    def _atomic_write(self, path: Path, data: dict) -> None:
        """Write JSON with atomic rename to prevent corruption."""
        # Validate path
        validated_path = _validate_file_path(str(path))

        # Write to temp file first
        tmp_path = validated_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

        # Atomic rename (use replace() for cross-platform support -
        # rename() fails on Windows when target exists)
        tmp_path.replace(validated_path)

    def _archive_session(self, state: SessionState) -> Path:
        """Archive a session to compressed storage."""
        archive_file = self.config.archive_dir / f"{state.session_id}.json.gz"

        if self.config.archive_compression:
            with gzip.open(archive_file, "wt", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2, default=str)
        else:
            archive_file = archive_file.with_suffix("")  # Remove .gz
            archive_file.write_text(
                json.dumps(state.to_dict(), indent=2, default=str), encoding="utf-8"
            )

        logger.info("session_archived", session_id=state.session_id, path=str(archive_file))
        return archive_file

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
            key: Storage key
            value: Data to store (must be JSON-serializable)
            ttl: Time-to-live in seconds (default from config)
            agent_id: Agent identifier (defaults to user_id)

        Returns:
            True if stored successfully
        """
        ttl = ttl or self.config.working_ttl_seconds
        agent_id = agent_id or self.user_id

        entry = WorkingEntry(
            key=key,
            value=value,
            agent_id=agent_id,
            stashed_at=time.time(),
            expires_at=time.time() + ttl if ttl else None,
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
            key: Storage key
            agent_id: Agent identifier (for cross-agent retrieval)

        Returns:
            Stored value or None if not found/expired
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
        """Delete a key from working memory."""
        if key in self._state.working_memory:
            del self._state.working_memory[key]
            self._dirty = True
            return True
        return False

    def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern (supports * wildcard)."""
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
    # Pattern Staging (Redis-compatible interface)
    # =========================================================================

    def stage_pattern(
        self,
        pattern_id: str,
        pattern_type: str,
        name: str,
        description: str,
        code: str | None = None,
        confidence: float = 0.5,
        metadata: dict | None = None,
    ) -> bool:
        """Stage a pattern for validation.

        Args:
            pattern_id: Unique pattern identifier
            pattern_type: Type of pattern (security, performance, etc.)
            name: Human-readable name
            description: Pattern description
            code: Optional code example
            confidence: Confidence score (0.0 - 1.0)
            metadata: Additional metadata

        Returns:
            True if staged successfully
        """
        pattern = StagedPatternFile(
            pattern_id=pattern_id,
            agent_id=self.user_id,
            pattern_type=pattern_type,
            name=name,
            description=description,
            code=code,
            confidence=confidence,
            staged_at=time.time(),
            expires_at=time.time() + self.config.pattern_ttl_seconds,
            metadata=metadata or {},
        )

        self._state.staged_patterns[pattern_id] = pattern
        self._dirty = True

        # Also write to patterns/staged/ for persistence
        pattern_file = self.config.patterns_dir / "staged" / f"{pattern_id}.json"
        self._atomic_write(pattern_file, pattern.to_dict())

        logger.info("pattern_staged", pattern_id=pattern_id, confidence=confidence)
        return True

    def get_staged_patterns(self, pattern_type: str | None = None) -> list[StagedPatternFile]:
        """Get all staged patterns, optionally filtered by type."""
        self._cleanup_expired_patterns()

        patterns = list(self._state.staged_patterns.values())
        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]

        return sorted(patterns, key=lambda p: p.confidence, reverse=True)

    def promote_pattern(
        self,
        pattern_id: str,
        min_confidence: float = 0.7,
    ) -> tuple[bool, StagedPatternFile | None, str]:
        """Promote a staged pattern to permanent storage.

        Args:
            pattern_id: Pattern to promote
            min_confidence: Minimum confidence threshold

        Returns:
            Tuple of (success, pattern, message)
        """
        pattern = self._state.staged_patterns.get(pattern_id)
        if pattern is None:
            return False, None, "Pattern not found"

        if pattern.is_expired():
            del self._state.staged_patterns[pattern_id]
            self._dirty = True
            return False, None, "Pattern expired"

        if pattern.confidence < min_confidence:
            return False, None, f"Confidence {pattern.confidence} below threshold {min_confidence}"

        # Move to promoted directory
        promoted_file = self.config.patterns_dir / "promoted" / f"{pattern_id}.json"
        self._atomic_write(promoted_file, pattern.to_dict())

        # Remove from staged
        staged_file = self.config.patterns_dir / "staged" / f"{pattern_id}.json"
        if staged_file.exists():
            staged_file.unlink()
        del self._state.staged_patterns[pattern_id]
        self._dirty = True

        logger.info("pattern_promoted", pattern_id=pattern_id, confidence=pattern.confidence)
        return True, pattern, "Pattern promoted successfully"

    def _cleanup_expired_patterns(self) -> None:
        """Remove expired patterns."""
        expired = [k for k, v in self._state.staged_patterns.items() if v.is_expired()]
        for pattern_id in expired:
            del self._state.staged_patterns[pattern_id]
            # Also remove file
            staged_file = self.config.patterns_dir / "staged" / f"{pattern_id}.json"
            if staged_file.exists():
                staged_file.unlink()
        if expired:
            self._dirty = True
            logger.debug("expired_patterns_cleaned", count=len(expired))

    # =========================================================================
    # Context Management
    # =========================================================================

    def set_context(self, key: str, value: Any) -> None:
        """Store context data (no TTL, persists for session)."""
        self._state.context[key] = value
        self._dirty = True

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve context data."""
        return self._state.context.get(key, default)

    def get_all_context(self) -> dict[str, Any]:
        """Get all context data."""
        return self._state.context.copy()

    # =========================================================================
    # Session History
    # =========================================================================

    def get_recent_sessions(self, limit: int = 5) -> list[dict]:
        """Load recent archived sessions for context continuity.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries (most recent first)
        """
        archive_dir = self.config.archive_dir
        sessions = []

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
                logger.warning("session_load_error", file=str(archive_file), error=str(e))

        return sessions

    # =========================================================================
    # Statistics and Diagnostics
    # =========================================================================

    def get_stats(self) -> dict:
        """Get memory statistics."""
        self._cleanup_expired()

        return {
            "mode": "file",
            "session_id": self._state.session_id,
            "user_id": self.user_id,
            "working_keys": len(self._state.working_memory),
            "staged_patterns": len(self._state.staged_patterns),
            "context_keys": len(self._state.context),
            "session_age_hours": (time.time() - self._state.started_at) / 3600,
            "dirty": self._dirty,
            "base_dir": str(self.config.base_dir),
        }

    def is_connected(self) -> bool:
        """Check if storage is available (always True for file-based)."""
        return True

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def save(self) -> None:
        """Explicitly save session state."""
        if self._dirty:
            self._save_current()
            logger.debug("session_saved", session_id=self._state.session_id)

    def close(self) -> None:
        """Close session and save state."""
        if self.config.auto_compact_on_close:
            self._cleanup_expired()
            self._cleanup_expired_patterns()

        self.save()
        logger.info("session_closed", session_id=self._state.session_id)

    def __enter__(self) -> FileSessionMemory:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # =========================================================================
    # Redis Compatibility (No-op for features requiring Redis)
    # =========================================================================

    @property
    def use_mock(self) -> bool:
        """File-based memory is not mock mode."""
        return False

    def publish(self, channel: str, message: dict) -> int:
        """Publish is not supported in file mode."""
        logger.warning("publish_not_supported", channel=channel)
        return 0

    def subscribe(self, channel: str, handler: Any) -> bool:
        """Subscribe is not supported in file mode."""
        logger.warning("subscribe_not_supported", channel=channel)
        return False

    def supports_realtime(self) -> bool:
        """Check if real-time features are available."""
        return False

    def supports_distributed(self) -> bool:
        """Check if distributed features are available."""
        return False


# =============================================================================
# Factory Function
# =============================================================================


def get_file_session_memory(
    user_id: str,
    base_dir: str = ".empathy",
    **kwargs,
) -> FileSessionMemory:
    """Create a file-based session memory instance.

    Args:
        user_id: User/agent identifier
        base_dir: Base directory for storage
        **kwargs: Additional config options

    Returns:
        Configured FileSessionMemory instance
    """
    config = FileSessionConfig(base_dir=base_dir, **kwargs)
    return FileSessionMemory(user_id=user_id, config=config)
