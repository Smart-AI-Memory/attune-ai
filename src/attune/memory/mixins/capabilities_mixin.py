"""Capabilities and health check mixin for UnifiedMemory.

Provides backend availability checks, health monitoring, and feature detection.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..file_session import FileSessionMemory
    from ..long_term import LongTermMemory
    from ..redis_bootstrap import RedisStatus


class CapabilitiesMixin:
    """Mixin providing capability detection and health checks for UnifiedMemory."""

    # Type hints for attributes that will be provided by UnifiedMemory
    _file_session: "FileSessionMemory | None"
    _short_term: Any  # MemoryBackend | None
    _long_term: Any  # SecureMemDocsIntegration
    _simple_long_term: "LongTermMemory | None"
    _redis_status: "RedisStatus | None"
    config: Any  # MemoryConfig

    # =========================================================================
    # BACKEND AVAILABILITY CHECKS
    # =========================================================================

    @property
    def has_short_term(self) -> bool:
        """Check if short-term memory is available."""
        return self._short_term is not None

    @property
    def has_long_term(self) -> bool:
        """Check if long-term memory is available."""
        return self._long_term is not None

    @property
    def redis_status(self) -> "RedisStatus | None":
        """Get Redis connection status."""
        return self._redis_status

    @property
    def using_real_redis(self) -> bool:
        """Check if using real Redis (not mock)."""
        from ..redis_bootstrap import RedisStartMethod

        return (
            self._redis_status is not None
            and self._redis_status.available
            and self._redis_status.method != RedisStartMethod.MOCK
        )

    @property
    def short_term(self) -> Any:
        """Get short-term memory backend for direct access (testing).

        Returns:
            RedisShortTermMemory instance

        Raises:
            RuntimeError: If short-term memory is not initialized

        """
        if self._short_term is None:
            raise RuntimeError(
                "Short-term memory not initialized. "
                "Ensure Redis is running and UnifiedMemory was initialized with Redis enabled.",
            )
        return self._short_term

    @property
    def long_term(self) -> "LongTermMemory":
        """Get simple long-term memory backend for direct access (testing).

        Returns:
            LongTermMemory instance

        Raises:
            RuntimeError: If long-term memory is not initialized

        Note:
            For production use with security features (PII scrubbing, encryption),
            use persist_pattern() and recall_pattern() methods instead.

        """
        if self._simple_long_term is None:
            raise RuntimeError(
                "Long-term memory not initialized. "
                "Ensure UnifiedMemory was initialized with long_term_enabled=True.",
            )
        return self._simple_long_term

    # =========================================================================
    # HEALTH CHECKS
    # =========================================================================

    def health_check(self) -> dict[str, Any]:
        """Check health of memory backends.

        Returns:
            Status of each memory backend

        """
        redis_info: dict[str, Any] = {
            "available": self.has_short_term,
            "mock_mode": not self.using_real_redis,
        }
        if self._redis_status:
            redis_info["method"] = self._redis_status.method.value
            redis_info["host"] = self._redis_status.host
            redis_info["port"] = self._redis_status.port

        return {
            "file_session": {
                "available": self._file_session is not None,
                "session_id": self._file_session._state.session_id if self._file_session else None,
                "base_dir": self.config.file_session_dir,
            },
            "short_term": redis_info,
            "long_term": {
                "available": self.has_long_term,
                "storage_dir": self.config.storage_dir,
                "encryption": self.config.encryption_enabled,
            },
            "environment": self.config.environment.value,
        }

    # =========================================================================
    # CAPABILITY DETECTION (File-First Architecture)
    # =========================================================================

    @property
    def has_file_session(self) -> bool:
        """Check if file-based session memory is available (always True if enabled)."""
        return self._file_session is not None

    @property
    def file_session(self) -> "FileSessionMemory":
        """Get file session memory backend for direct access.

        Returns:
            FileSessionMemory instance

        Raises:
            RuntimeError: If file session memory is not initialized

        """
        if self._file_session is None:
            raise RuntimeError(
                "File session memory not initialized. "
                "File session tracking is automatically enabled when UnifiedMemory is initialized.",
            )
        return self._file_session

    def supports_realtime(self) -> bool:
        """Check if real-time features are available (requires Redis).

        Real-time features include:
        - Pub/Sub messaging between agents
        - Cross-session coordination
        - Distributed task queues

        Returns:
            True if Redis is available and connected

        """
        return self.using_real_redis

    def supports_distributed(self) -> bool:
        """Check if distributed features are available (requires Redis).

        Distributed features include:
        - Multi-process coordination
        - Cross-session state sharing
        - Agent discovery

        Returns:
            True if Redis is available and connected

        """
        return self.using_real_redis

    def supports_persistence(self) -> bool:
        """Check if persistence is available (always True with file-first).

        Returns:
            True if file session or long-term memory is available

        """
        return self._file_session is not None or self._long_term is not None

    def get_capabilities(self) -> dict[str, bool]:
        """Get a summary of available memory capabilities.

        Returns:
            Dictionary mapping capability names to availability

        """
        return {
            "file_session": self.has_file_session,
            "redis": self.using_real_redis,
            "long_term": self.has_long_term,
            "persistence": self.supports_persistence(),
            "realtime": self.supports_realtime(),
            "distributed": self.supports_distributed(),
            "encryption": self.config.encryption_enabled and self.has_long_term,
        }
