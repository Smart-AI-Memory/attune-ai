"""Short-term memory operations mixin for UnifiedMemory.

Provides working memory operations (stash/retrieve) and pattern staging.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ..file_session import FileSessionMemory
    from ..redis_bootstrap import RedisStatus
    from ..types import AccessTier, AgentCredentials

logger = structlog.get_logger(__name__)


class ShortTermOperationsMixin:
    """Mixin providing short-term memory operations for UnifiedMemory."""

    # Type hints for attributes that will be provided by UnifiedMemory
    user_id: str
    access_tier: "AccessTier"
    _file_session: "FileSessionMemory | None"
    _short_term: Any  # MemoryBackend | None
    _redis_status: "RedisStatus | None"
    config: Any  # MemoryConfig

    @property
    def credentials(self) -> "AgentCredentials":
        """Get agent credentials for short-term memory operations."""
        from ..types import AgentCredentials

        return AgentCredentials(agent_id=self.user_id, tier=self.access_tier)

    # =========================================================================
    # SHORT-TERM MEMORY OPERATIONS (Working Memory)
    # =========================================================================

    def stash(self, key: str, value: Any, ttl_seconds: int | None = None) -> bool:
        """Store data in working memory with TTL.

        Uses file-based session as primary storage, with optional Redis for
        real-time features. Data is persisted to disk automatically.

        Args:
            key: Storage key
            value: Data to store (must be JSON-serializable)
            ttl_seconds: Time-to-live in seconds (default from config)

        Returns:
            True if stored successfully

        """
        from ..types import TTLStrategy

        ttl = ttl_seconds or self.config.default_ttl_seconds

        # Primary: File session memory (always available)
        if self._file_session:
            self._file_session.stash(key, value, ttl=ttl)

        # Optional: Redis for real-time sync
        if self._short_term and self._redis_status and self._redis_status.available:
            # Map ttl_seconds to TTLStrategy
            ttl_strategy = TTLStrategy.WORKING_RESULTS
            if ttl_seconds is not None:
                # COORDINATION removed in v5.0 - use SESSION for short-lived data
                if ttl_seconds <= TTLStrategy.SESSION.value:
                    ttl_strategy = TTLStrategy.SESSION
                elif ttl_seconds <= TTLStrategy.WORKING_RESULTS.value:
                    ttl_strategy = TTLStrategy.WORKING_RESULTS
                elif ttl_seconds <= TTLStrategy.STAGED_PATTERNS.value:
                    ttl_strategy = TTLStrategy.STAGED_PATTERNS
                else:
                    ttl_strategy = TTLStrategy.CONFLICT_CONTEXT

            try:
                self._short_term.stash(key, value, self.credentials, ttl_strategy)
            except Exception as e:
                logger.debug("redis_stash_failed", key=key, error=str(e))

        # Return True if at least one backend succeeded
        return self._file_session is not None

    def retrieve(self, key: str) -> Any | None:
        """Retrieve data from working memory.

        Checks Redis first (if available) for faster access, then falls back
        to file-based session storage.

        Args:
            key: Storage key

        Returns:
            Stored data or None if not found

        """
        # Try Redis first (faster, if available)
        if self._short_term and self._redis_status and self._redis_status.available:
            try:
                result = self._short_term.retrieve(key, self.credentials)
                if result is not None:
                    return result
            except Exception as e:
                logger.debug("redis_retrieve_failed", key=key, error=str(e))

        # Fall back to file session (primary storage)
        if self._file_session:
            return self._file_session.retrieve(key)

        return None

    # =========================================================================
    # PATTERN STAGING
    # =========================================================================

    def stage_pattern(
        self,
        pattern_data: dict[str, Any],
        pattern_type: str = "general",
        ttl_hours: int = 24,
    ) -> str | None:
        """Stage a pattern for validation before long-term storage.

        Args:
            pattern_data: Pattern content and metadata
            pattern_type: Type of pattern (algorithm, protocol, etc.)
            ttl_hours: Hours before staged pattern expires (not used in current impl)

        Returns:
            Staged pattern ID or None if failed

        """
        from ..types import StagedPattern

        if not self._short_term:
            logger.warning("short_term_memory_unavailable")
            return None

        # Create a StagedPattern object from the pattern_data dict
        pattern_id = f"staged_{uuid.uuid4().hex[:12]}"
        staged_pattern = StagedPattern(
            pattern_id=pattern_id,
            agent_id=self.user_id,
            pattern_type=pattern_type,
            name=pattern_data.get("name", f"Pattern {pattern_id[:8]}"),
            description=pattern_data.get("description", ""),
            code=pattern_data.get("code"),
            context=pattern_data.get("context", {}),
            confidence=pattern_data.get("confidence", 0.5),
            staged_at=datetime.now(),
            interests=pattern_data.get("interests", []),
        )
        # Store content in context if provided
        if "content" in pattern_data:
            staged_pattern.context["content"] = pattern_data["content"]

        success = self._short_term.stage_pattern(staged_pattern, self.credentials)
        return pattern_id if success else None

    def get_staged_patterns(self) -> list[dict]:
        """Get all staged patterns awaiting validation.

        Returns:
            List of staged patterns with metadata

        """
        if not self._short_term:
            return []

        staged_list = self._short_term.list_staged_patterns(self.credentials)
        return [p.to_dict() for p in staged_list]
