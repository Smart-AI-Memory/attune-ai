"""Compaction State Management

Handles state serialization and persistence for context compaction events.
Preserves critical collaboration state through context window resets.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.config import _validate_file_path

logger = logging.getLogger(__name__)


@dataclass
class PatternSummary:
    """Compact representation of a detected pattern.

    Preserves essential pattern information without full metadata.
    """

    pattern_type: str
    trigger: str
    action: str
    confidence: float
    occurrences: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PatternSummary:
        """Create from dictionary."""
        return cls(
            pattern_type=data.get("pattern_type", "preference"),
            trigger=data.get("trigger", ""),
            action=data.get("action", ""),
            confidence=data.get("confidence", 0.0),
            occurrences=data.get("occurrences", 0),
        )


@dataclass
class SBARHandoff:
    """SBAR-format handoff for continuity across compaction.

    Situation-Background-Assessment-Recommendation format
    for clear communication of pending work.
    """

    situation: str  # What's happening now
    background: str  # Relevant context
    assessment: str  # Current understanding
    recommendation: str  # Suggested next action
    priority: str = "normal"  # low, normal, high, critical
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SBARHandoff:
        """Create from dictionary."""
        return cls(
            situation=data.get("situation", ""),
            background=data.get("background", ""),
            assessment=data.get("assessment", ""),
            recommendation=data.get("recommendation", ""),
            priority=data.get("priority", "normal"),
            metadata=data.get("metadata", {}),
        )

    def format_summary(self) -> str:
        """Format as readable summary for restoration."""
        lines = [
            f"**Situation**: {self.situation}",
            f"**Background**: {self.background}",
            f"**Assessment**: {self.assessment}",
            f"**Recommendation**: {self.recommendation}",
        ]
        if self.priority != "normal":
            lines.insert(0, f"**Priority**: {self.priority.upper()}")
        return "\n".join(lines)


@dataclass
class CompactState:
    """Essential state preserved through context compaction.

    This dataclass captures the minimum information needed to restore
    meaningful collaboration state after a context window reset.
    """

    # User identity
    user_id: str

    # Trust and relationship
    trust_level: float
    empathy_level: int

    # Pattern knowledge (summarized)
    detected_patterns: list[PatternSummary] = field(default_factory=list)

    # Session continuity
    session_id: str = ""
    current_phase: str = ""
    completed_phases: list[str] = field(default_factory=list)

    # Pending work
    pending_handoff: SBARHandoff | None = None

    # Metrics
    interaction_count: int = 0
    successful_actions: int = 0
    failed_actions: int = 0

    # User preferences (key settings only)
    preferences: dict[str, Any] = field(default_factory=dict)

    # Metadata
    saved_at: str = ""
    version: str = "1.0"

    def __post_init__(self):
        """Set saved_at if not provided."""
        if not self.saved_at:
            self.saved_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "trust_level": self.trust_level,
            "empathy_level": self.empathy_level,
            "detected_patterns": [p.to_dict() for p in self.detected_patterns],
            "session_id": self.session_id,
            "current_phase": self.current_phase,
            "completed_phases": self.completed_phases,
            "pending_handoff": self.pending_handoff.to_dict() if self.pending_handoff else None,
            "interaction_count": self.interaction_count,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "preferences": self.preferences,
            "saved_at": self.saved_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompactState:
        """Create from dictionary."""
        patterns = [PatternSummary.from_dict(p) for p in data.get("detected_patterns", [])]

        handoff_data = data.get("pending_handoff")
        handoff = SBARHandoff.from_dict(handoff_data) if handoff_data else None

        return cls(
            user_id=data.get("user_id", ""),
            trust_level=data.get("trust_level", 0.5),
            empathy_level=data.get("empathy_level", 1),
            detected_patterns=patterns,
            session_id=data.get("session_id", ""),
            current_phase=data.get("current_phase", ""),
            completed_phases=data.get("completed_phases", []),
            pending_handoff=handoff,
            interaction_count=data.get("interaction_count", 0),
            successful_actions=data.get("successful_actions", 0),
            failed_actions=data.get("failed_actions", 0),
            preferences=data.get("preferences", {}),
            saved_at=data.get("saved_at", ""),
            version=data.get("version", "1.0"),
        )

    def format_restoration_prompt(self) -> str:
        """Generate a restoration prompt for context resumption.

        Returns formatted text that can be injected at session start
        to restore collaboration state.
        """
        lines = [
            "## Session Restoration",
            "",
            f"**User**: {self.user_id}",
            f"**Trust Level**: {self.trust_level:.2f}",
            f"**Empathy Level**: {self.empathy_level}",
            f"**Session**: {self.session_id or 'New'}",
            f"**Interactions**: {self.interaction_count}",
            "",
        ]

        if self.detected_patterns:
            lines.append("### Known Patterns")
            for pattern in self.detected_patterns[:5]:  # Top 5
                lines.append(
                    f"- **{pattern.trigger}** → {pattern.action} "
                    f"(confidence: {pattern.confidence:.0%})"
                )
            lines.append("")

        if self.current_phase:
            lines.append("### Current Work")
            lines.append(f"**Phase**: {self.current_phase}")
            if self.completed_phases:
                lines.append(f"**Completed**: {', '.join(self.completed_phases)}")
            lines.append("")

        if self.pending_handoff:
            lines.append("### Pending Handoff")
            lines.append(self.pending_handoff.format_summary())
            lines.append("")

        if self.preferences:
            lines.append("### User Preferences")
            for key, value in list(self.preferences.items())[:5]:
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        return "\n".join(lines)


class CompactionStateManager:
    """Manages CompactState persistence and retrieval.

    Handles saving and loading state files for context compaction,
    with support for versioning and cleanup of old states.
    """

    def __init__(
        self,
        storage_dir: str | Path = ".attune/compact_states",
        max_states_per_user: int = 5,
    ):
        """Initialize the manager.

        Args:
            storage_dir: Directory for state files
            max_states_per_user: Maximum states to keep per user
        """
        self.storage_dir = Path(storage_dir)
        self.max_states_per_user = max_states_per_user

    def _ensure_storage(self) -> None:
        """Ensure storage directory exists."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, user_id: str) -> Path:
        """Get storage directory for a user."""
        # Sanitize user_id for filesystem
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return self.storage_dir / safe_id

    def save_state(self, state: CompactState) -> Path:
        """Save compaction state to storage.

        Args:
            state: The CompactState to save

        Returns:
            Path to the saved state file
        """
        self._ensure_storage()

        user_dir = self._get_user_dir(state.user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp + uuid suffix for guaranteed uniqueness
        # (datetime.now() may have low resolution on some Windows systems)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        unique_suffix = uuid.uuid4().hex[:8]
        filename = f"compact_{timestamp}_{unique_suffix}.json"
        filepath = user_dir / filename

        # Save state
        validated_path = _validate_file_path(str(filepath))
        with open(validated_path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, default=str)

        logger.info(f"Saved compact state to {filepath}")

        # Cleanup old states
        self._cleanup_old_states(state.user_id)

        return filepath

    def load_latest_state(self, user_id: str) -> CompactState | None:
        """Load the most recent state for a user.

        Args:
            user_id: User identifier

        Returns:
            Most recent CompactState or None if not found
        """
        user_dir = self._get_user_dir(user_id)

        if not user_dir.exists():
            logger.debug(f"No state directory for user {user_id}")
            return None

        # Find most recent state file
        state_files = sorted(
            user_dir.glob("compact_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not state_files:
            logger.debug(f"No state files for user {user_id}")
            return None

        latest = state_files[0]

        try:
            with open(latest, encoding="utf-8") as f:
                data = json.load(f)

            state = CompactState.from_dict(data)
            logger.info(f"Loaded compact state from {latest}")
            return state

        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load state from {latest}: {e}")
            return None

    def load_state_by_session(self, session_id: str) -> CompactState | None:
        """Load state for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            CompactState for session or None if not found
        """
        self._ensure_storage()

        # Search all user directories
        for user_dir in self.storage_dir.iterdir():
            if not user_dir.is_dir():
                continue

            for state_file in user_dir.glob("compact_*.json"):
                try:
                    with open(state_file, encoding="utf-8") as f:
                        data = json.load(f)

                    if data.get("session_id") == session_id:
                        return CompactState.from_dict(data)

                except (json.JSONDecodeError, OSError):
                    continue

        return None

    def _cleanup_old_states(self, user_id: str) -> int:
        """Remove old state files beyond the limit.

        Args:
            user_id: User identifier

        Returns:
            Number of files removed
        """
        user_dir = self._get_user_dir(user_id)

        if not user_dir.exists():
            return 0

        # Get all state files sorted by age
        state_files = sorted(
            user_dir.glob("compact_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # Remove files beyond limit
        removed = 0
        for old_file in state_files[self.max_states_per_user :]:
            try:
                old_file.unlink()
                removed += 1
                logger.debug(f"Cleaned up old state: {old_file}")
            except OSError as e:
                logger.warning(f"Failed to cleanup {old_file}: {e}")

        return removed

    def get_all_states(self, user_id: str) -> list[CompactState]:
        """Get all saved states for a user.

        Args:
            user_id: User identifier

        Returns:
            List of CompactStates, newest first
        """
        user_dir = self._get_user_dir(user_id)

        if not user_dir.exists():
            return []

        states = []

        # Load all state files
        for state_file in sorted(
            user_dir.glob("compact_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                with open(state_file, encoding="utf-8") as f:
                    data = json.load(f)
                states.append(CompactState.from_dict(data))
            except (json.JSONDecodeError, OSError):
                continue

        return states

    def clear_user_states(self, user_id: str) -> int:
        """Remove all states for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of files removed
        """
        user_dir = self._get_user_dir(user_id)

        if not user_dir.exists():
            return 0

        removed = 0
        for state_file in user_dir.glob("compact_*.json"):
            try:
                state_file.unlink()
                removed += 1
            except OSError:
                continue

        # Remove user directory if empty
        try:
            user_dir.rmdir()
        except OSError:
            pass

        return removed
