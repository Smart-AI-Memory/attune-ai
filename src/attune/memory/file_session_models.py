"""Data models for file-based session memory.

Contains configuration, working memory entries, staged patterns,
and session state dataclasses used by the file session subsystem.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# =============================================================================
# Configuration
# =============================================================================


@dataclass
class FileSessionConfig:
    """Configuration for file-based session memory."""

    # Storage locations
    base_dir: str = ".attune"
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
        """Path to sessions directory."""
        return Path(self.base_dir) / self.sessions_subdir

    @property
    def patterns_dir(self) -> Path:
        """Path to patterns directory."""
        return Path(self.base_dir) / self.patterns_subdir

    @property
    def archive_dir(self) -> Path:
        """Path to archive directory."""
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
        """Check if this entry has expired.

        Returns:
            True if the entry is past its expiration time.

        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this entry.

        """
        return {
            "key": self.key,
            "value": self.value,
            "agent_id": self.agent_id,
            "stashed_at": self.stashed_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorkingEntry:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with entry fields.

        Returns:
            Reconstructed WorkingEntry instance.

        """
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
        """Check if this pattern has expired.

        Returns:
            True if the pattern is past its expiration time.

        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this pattern.

        """
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
        """Deserialize from dictionary.

        Args:
            data: Dictionary with pattern fields.

        Returns:
            Reconstructed StagedPatternFile instance.

        """
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
        """Serialize to dictionary.

        Returns:
            Dictionary representation of this session state.

        """
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
        """Deserialize from dictionary.

        Args:
            data: Dictionary with session state fields.

        Returns:
            Reconstructed SessionState instance.

        """
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
        """Create a new session state.

        Args:
            user_id: User/agent identifier.

        Returns:
            Fresh SessionState with generated session ID.

        """
        now = time.time()
        return cls(
            session_id=f"session_{int(now)}_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            started_at=now,
            last_updated=now,
        )
