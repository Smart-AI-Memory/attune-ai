"""Pattern staging mixin for file-based session memory.

Handles staging, retrieval, promotion, and cleanup of patterns
that are awaiting validation before permanent storage.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import time

import structlog

from .file_session_models import (
    FileSessionConfig,
    SessionState,
    StagedPatternFile,
)

logger = structlog.get_logger(__name__)


class PatternStagingMixin:
    """Mixin providing pattern staging operations.

    Expects the host class to have:
        - self.config: FileSessionConfig
        - self.user_id: str
        - self._state: SessionState
        - self._dirty: bool
        - self._atomic_write(path, data): method
    """

    config: FileSessionConfig
    user_id: str
    _state: SessionState
    _dirty: bool

    def _atomic_write(self, path: object, data: dict) -> None:
        """Write JSON atomically (provided by PersistenceMixin)."""
        ...  # pragma: no cover

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
            pattern_id: Unique pattern identifier.
            pattern_type: Type (security, performance, etc.).
            name: Human-readable name.
            description: Pattern description.
            code: Optional code example.
            confidence: Confidence score (0.0 - 1.0).
            metadata: Additional metadata.

        Returns:
            True if staged successfully.
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
            expires_at=(time.time() + self.config.pattern_ttl_seconds),
            metadata=metadata or {},
        )

        self._state.staged_patterns[pattern_id] = pattern
        self._dirty = True

        # Also write to patterns/staged/ for persistence
        pattern_file = self.config.patterns_dir / "staged" / f"{pattern_id}.json"
        self._atomic_write(pattern_file, pattern.to_dict())

        logger.info(
            "pattern_staged",
            pattern_id=pattern_id,
            confidence=confidence,
        )
        return True

    def get_staged_patterns(self, pattern_type: str | None = None) -> list[StagedPatternFile]:
        """Get all staged patterns, optionally filtered by type.

        Args:
            pattern_type: Optional type filter.

        Returns:
            List of staged patterns sorted by confidence
            (descending).
        """
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
            pattern_id: Pattern to promote.
            min_confidence: Minimum confidence threshold.

        Returns:
            Tuple of (success, pattern, message).
        """
        pattern = self._state.staged_patterns.get(pattern_id)
        if pattern is None:
            return False, None, "Pattern not found"

        if pattern.is_expired():
            del self._state.staged_patterns[pattern_id]
            self._dirty = True
            return False, None, "Pattern expired"

        if pattern.confidence < min_confidence:
            return (
                False,
                None,
                f"Confidence {pattern.confidence} " f"below threshold {min_confidence}",
            )

        # Move to promoted directory
        promoted_file = self.config.patterns_dir / "promoted" / f"{pattern_id}.json"
        self._atomic_write(promoted_file, pattern.to_dict())

        # Remove from staged
        staged_file = self.config.patterns_dir / "staged" / f"{pattern_id}.json"
        if staged_file.exists():
            staged_file.unlink()
        del self._state.staged_patterns[pattern_id]
        self._dirty = True

        logger.info(
            "pattern_promoted",
            pattern_id=pattern_id,
            confidence=pattern.confidence,
        )
        return True, pattern, "Pattern promoted successfully"

    def _cleanup_expired_patterns(self) -> None:
        """Remove expired patterns from state and disk."""
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
