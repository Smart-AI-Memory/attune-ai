"""Backend initialization mixin for UnifiedMemory.

Handles initialization of file session, Redis, and long-term memory backends.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ..file_session import FileSessionMemory
    from ..long_term import LongTermMemory, SecureMemDocsIntegration
    from ..redis_bootstrap import RedisStatus

logger = structlog.get_logger(__name__)


class BackendInitMixin:
    """Mixin providing backend initialization for UnifiedMemory."""

    # Type hints for attributes that will be provided by UnifiedMemory
    user_id: str
    config: Any  # MemoryConfig
    _file_session: "FileSessionMemory | None"
    _short_term: Any  # MemoryBackend | None
    _long_term: "SecureMemDocsIntegration | None"
    _simple_long_term: "LongTermMemory | None"
    _redis_status: "RedisStatus | None"
    _initialized: bool

    # =========================================================================
    # BACKEND INITIALIZATION
    # =========================================================================

    def _initialize_backends(self):
        """Initialize short-term and long-term memory backends.

        File-First Architecture:
        1. FileSessionMemory is always initialized (primary storage)
        2. Redis is optional (for real-time features like pub/sub)
        3. Falls back gracefully when Redis is unavailable
        """
        from ..claude_memory import ClaudeMemoryConfig
        from ..file_session import FileSessionConfig, FileSessionMemory
        from ..long_term import LongTermMemory, SecureMemDocsIntegration

        # Redis backend is optional -- guard all Redis imports
        try:
            from ..config import get_redis_memory
            from ..redis_bootstrap import RedisStartMethod, RedisStatus, ensure_redis
            from ..short_term import RedisShortTermMemory

            _HAS_REDIS_BACKEND = True
        except ImportError:
            _HAS_REDIS_BACKEND = False

        if self._initialized:
            return

        # Initialize file-based session memory (PRIMARY - always available)
        if self.config.file_session_enabled:
            try:
                file_config = FileSessionConfig(base_dir=self.config.file_session_dir)
                self._file_session = FileSessionMemory(
                    user_id=self.user_id,
                    config=file_config,
                )
                logger.info(
                    "file_session_memory_initialized",
                    base_dir=self.config.file_session_dir,
                    session_id=self._file_session._state.session_id,
                )
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: File session is optional — degrade gracefully
                logger.error("file_session_memory_failed", error=str(e))
                self._file_session = None

        # Initialize Redis short-term memory (OPTIONAL - for real-time features)
        if not _HAS_REDIS_BACKEND:
            self._short_term = None
            self._redis_status = None
            logger.info(
                "redis_backend_not_installed",
                message="Redis backend not available, using file-based storage only",
            )
        else:
            try:
                if self.config.redis_mock:
                    self._short_term = RedisShortTermMemory(use_mock=True)
                    self._redis_status = RedisStatus(
                        available=False,
                        method=RedisStartMethod.MOCK,
                        message="Mock mode explicitly enabled",
                    )
                elif self.config.redis_url:
                    self._short_term = get_redis_memory(url=self.config.redis_url)
                    self._redis_status = RedisStatus(
                        available=True,
                        method=RedisStartMethod.ALREADY_RUNNING,
                        message="Connected via REDIS_URL",
                    )
                # Use auto-start if enabled
                elif self.config.redis_auto_start:
                    self._redis_status = ensure_redis(
                        host=self.config.redis_host,
                        port=self.config.redis_port,
                        auto_start=True,
                        verbose=True,
                    )
                    if self._redis_status.available:
                        self._short_term = RedisShortTermMemory(
                            host=self.config.redis_host,
                            port=self.config.redis_port,
                            use_mock=False,
                        )
                    else:
                        self._short_term = None
                        self._redis_status = RedisStatus(
                            available=False,
                            method=RedisStartMethod.MOCK,
                            message="Redis unavailable, using file-based storage",
                        )
                else:
                    # Try to connect to existing Redis
                    try:
                        self._short_term = get_redis_memory()
                        if self._short_term.is_connected():
                            self._redis_status = RedisStatus(
                                available=True,
                                method=RedisStartMethod.ALREADY_RUNNING,
                                message="Connected to existing Redis",
                            )
                        else:
                            self._short_term = None
                            self._redis_status = RedisStatus(
                                available=False,
                                method=RedisStartMethod.MOCK,
                                message="Redis not available, using file-based storage",
                            )
                    except Exception:  # noqa: BLE001
                        # INTENTIONAL: Redis is optional — fall back to file storage
                        self._short_term = None
                        self._redis_status = RedisStatus(
                            available=False,
                            method=RedisStartMethod.MOCK,
                            message="Redis not available, using file-based storage",
                        )

                logger.info(
                    "short_term_memory_initialized",
                    redis_available=self._redis_status.available if self._redis_status else False,
                    file_session_available=self._file_session is not None,
                    redis_method=self._redis_status.method.value if self._redis_status else "none",
                    environment=self.config.environment.value,
                )

                # Fail if Redis is required but not available
                if self.config.redis_required and not (
                    self._redis_status and self._redis_status.available
                ):
                    attempted = self.config.redis_url or "default localhost"
                    raise RuntimeError(
                        "Redis is required but not available "
                        f"(attempted: {attempted}). "
                        f"Config requires Redis (redis_required=True, environment={self.config.environment.value}). "
                        "Either: (1) Start Redis server, (2) Set REDIS_URL environment variable, "
                        "or (3) Set redis_required=False in MemoryConfig. "
                        "Note: this is the unified-memory store, not the AMS server — "
                        "redis_memory_* tools may still work if AMS is reachable.",
                    )

            except RuntimeError:
                raise  # Re-raise required Redis error
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Redis init is optional — degrade to file storage
                logger.warning("redis_initialization_failed", error=str(e))
                self._short_term = None
                self._redis_status = None

        # Initialize long-term memory (SecureMemDocs)
        try:
            claude_config = ClaudeMemoryConfig(
                enabled=self.config.claude_memory_enabled,
                load_enterprise=self.config.load_enterprise_memory,
                load_project=self.config.load_project_memory,
                load_user=self.config.load_user_memory,
            )
            self._long_term = SecureMemDocsIntegration(
                claude_memory_config=claude_config,
                storage_dir=self.config.storage_dir,
                enable_encryption=self.config.encryption_enabled,
            )

            logger.info(
                "long_term_memory_initialized",
                storage_dir=self.config.storage_dir,
                encryption=self.config.encryption_enabled,
            )
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Long-term memory is optional — degrade gracefully
            logger.error("long_term_memory_failed", error=str(e))
            self._long_term = None

        # Initialize simple long-term memory (for testing and simple use cases)
        try:
            self._simple_long_term = LongTermMemory(storage_path=self.config.storage_dir)
            logger.debug("simple_long_term_memory_initialized")
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Simple long-term memory is optional
            logger.error("simple_long_term_memory_failed", error=str(e))
            self._simple_long_term = None

        self._initialized = True

    def get_backend_status(self) -> dict[str, Any]:
        """Get the current status of all memory backends.

        Returns a structured dict suitable for health checks and debugging.
        Can be serialized to JSON.

        Returns:
            dict with keys:
                - environment: Current environment (development/staging/production)
                - short_term: Status of Redis-based short-term memory
                - long_term: Status of persistent long-term memory
                - initialized: Whether backends have been initialized

        Example:
            >>> memory = UnifiedMemory(user_id="agent")
            >>> status = memory.get_backend_status()
            >>> print(status["short_term"]["available"])
            True

        """
        short_term_status: dict[str, Any] = {
            "available": False,
            "mock": True,
            "method": "unknown",
            "message": "Not initialized",
        }

        if self._redis_status:
            try:
                from ..redis_bootstrap import RedisStartMethod

                is_mock = (
                    not self._redis_status.available
                    or self._redis_status.method == RedisStartMethod.MOCK
                )
            except ImportError:
                is_mock = True
            short_term_status = {
                "available": self._redis_status.available,
                "mock": is_mock,
                "method": self._redis_status.method.value,
                "message": self._redis_status.message,
            }

        long_term_status: dict[str, Any] = {
            "available": self._long_term is not None,
            "storage_dir": self.config.storage_dir,
            "encryption_enabled": self.config.encryption_enabled,
        }

        return {
            "environment": self.config.environment.value,
            "initialized": self._initialized,
            "short_term": short_term_status,
            "long_term": long_term_status,
        }
