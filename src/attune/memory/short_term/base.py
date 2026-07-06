"""Core CRUD operations and connection management for short-term memory.

This module provides the foundational Redis operations:
- Connection management with retry logic
- Basic get/set/delete/keys operations
- Health check (ping) and statistics
- Cleanup and lifecycle management

The BaseOperations class is designed to be composed into the main
RedisShortTermMemory facade, providing backward compatibility while
enabling modular testing and maintenance.

Target Methods (extracted from original RedisShortTermMemory):
    - __init__ (initialization logic)
    - client property
    - _create_client_with_retry
    - _execute_with_retry
    - _get
    - _set
    - _delete
    - _keys
    - ping
    - get_stats
    - close

Dependencies:
    - RedisConfig for configuration
    - RedisMetrics for operation tracking
    - structlog for logging

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog

from attune.memory.types import RedisConfig, RedisMetrics

logger = structlog.get_logger(__name__)

# Redis availability check
try:
    import redis
    from redis.exceptions import ConnectionError as RedisConnectionError
    from redis.exceptions import TimeoutError as RedisTimeoutError

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore
    RedisConnectionError = Exception  # type: ignore
    RedisTimeoutError = Exception  # type: ignore


class BaseOperations:
    """Core CRUD operations and connection management.

    This class provides the foundational Redis operations that other
    modules build upon. It handles:

    - Connection creation with exponential backoff retry
    - Basic get/set/delete/keys operations
    - Health checks and statistics
    - Resource cleanup

    Example:
        >>> from attune.memory.short_term.base import BaseOperations
        >>> from attune.memory.types import RedisConfig
        >>> config = RedisConfig(use_mock=True)
        >>> base = BaseOperations(config=config)
        >>> base._set("key", "value")
        True
        >>> base._get("key")
        'value'

    Attributes:
        use_mock: Whether using mock storage instead of Redis
        _config: Redis configuration
        _metrics: Operation metrics tracker
        _client: Redis client instance (None if mock)
        _mock_storage: In-memory storage for mock mode

    """

    # Key prefixes for namespacing (shared across all operations)
    PREFIX_WORKING = "empathy:working:"
    PREFIX_STAGED = "empathy:staged:"
    PREFIX_CONFLICT = "empathy:conflict:"
    PREFIX_SESSION = "empathy:session:"
    PREFIX_PUBSUB = "empathy:pubsub:"
    PREFIX_STREAM = "empathy:stream:"
    PREFIX_TIMELINE = "empathy:timeline:"
    PREFIX_QUEUE = "empathy:queue:"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        use_mock: bool = False,
        config: RedisConfig | None = None,
    ) -> None:
        """Initialize Redis connection and core components.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            use_mock: Use in-memory mock for testing
            config: Full RedisConfig for advanced settings (overrides other args)

        """
        # Use config if provided, otherwise build from individual args
        if config is not None:
            self._config = config
        else:
            # Check for explicit REDIS_ENABLED env var (backward compatible)
            redis_explicit = os.getenv("REDIS_ENABLED")
            if redis_explicit is not None:
                # User explicitly set REDIS_ENABLED — respect it
                redis_enabled = redis_explicit.lower() in ("true", "1", "yes")
                if not redis_enabled and not use_mock:
                    use_mock = True
                    logger.info(
                        "redis_disabled_via_env",
                        message="Redis explicitly disabled via REDIS_ENABLED env var",
                    )
            elif not use_mock:
                # Auto-detect Redis availability
                from attune.memory.redis_auto_detect import RedisAutoDetector

                detector = RedisAutoDetector()
                result = detector.detect()
                if not result.available:
                    use_mock = True
                    logger.info(
                        "redis_auto_detect_unavailable",
                        message=f"Redis not available: {result.reason}",
                    )

            if use_mock:
                self._config = RedisConfig(use_mock=True)
            else:
                # Check if caller provided non-default args (backward compatibility)
                caller_overrode = (
                    host != "127.0.0.1" or port != 6379 or db != 0 or password is not None
                )
                if caller_overrode:
                    self._config = RedisConfig(
                        host=host,
                        port=port,
                        db=db,
                        password=password,
                        use_mock=False,
                    )
                else:
                    # Delegate to centralized config (respects REDIS_MODE)
                    from attune.redis_config import get_redis_config

                    self._config = get_redis_config()

        self.use_mock = self._config.use_mock or not REDIS_AVAILABLE

        # Initialize metrics
        self._metrics = RedisMetrics()

        # Mock storage for testing
        self._mock_storage: dict[str, tuple[Any, float | None]] = {}
        self._mock_lists: dict[str, list[str]] = {}
        self._mock_sorted_sets: dict[str, list[tuple[float, str]]] = {}
        self._mock_streams: dict[str, list[tuple[str, dict]]] = {}

        # Create client
        if self.use_mock:
            self._client = None
        else:
            self._client = self._create_client_with_retry()

    @property
    def client(self) -> Any:
        """Get the Redis client instance.

        Returns:
            Redis client instance or None if using mock mode

        Example:
            >>> memory = BaseOperations(use_mock=True)
            >>> memory.client is None
            True

        """
        return self._client

    @property
    def metrics(self) -> RedisMetrics:
        """Get Redis metrics instance.

        Returns:
            RedisMetrics instance with connection and operation statistics

        Example:
            >>> base = BaseOperations(use_mock=True)
            >>> base.metrics.retries_total
            0

        """
        return self._metrics

    def _create_client_with_retry(self) -> Any:
        """Create Redis client with exponential backoff retry.

        Returns:
            Connected Redis client

        Raises:
            ConnectionError: If all retry attempts fail

        """
        max_attempts = self._config.retry_max_attempts
        base_delay = self._config.retry_base_delay
        max_delay = self._config.retry_max_delay

        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                client = redis.Redis(**self._config.to_redis_kwargs())
                # Test connection
                client.ping()
                logger.info(
                    "redis_connected",
                    host=self._config.host,
                    port=self._config.port,
                    attempt=attempt + 1,
                )
                return client
            except (RedisConnectionError, RedisTimeoutError) as e:
                last_error = e
                self._metrics.retries_total += 1

                if attempt < max_attempts - 1:
                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.warning(
                        "redis_connection_retry",
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e),
                    )
                    time.sleep(delay)

        # All retries failed
        logger.error(
            "redis_connection_failed",
            max_attempts=max_attempts,
            error=str(last_error),
        )
        raise last_error or ConnectionError("Failed to connect to Redis")

    def _execute_with_retry(self, operation: Callable[[], Any], op_name: str = "operation") -> Any:
        """Execute a Redis operation with retry logic.

        Args:
            operation: Callable that performs the Redis operation
            op_name: Name of operation for logging/metrics

        Returns:
            Result of the operation

        Raises:
            ConnectionError: If all retry attempts fail

        """
        start_time = time.perf_counter()
        max_attempts = self._config.retry_max_attempts
        base_delay = self._config.retry_base_delay
        max_delay = self._config.retry_max_delay

        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                result = operation()
                latency_ms = (time.perf_counter() - start_time) * 1000
                self._metrics.record_operation(op_name, latency_ms, success=True)
                return result
            except (RedisConnectionError, RedisTimeoutError) as e:
                last_error = e
                self._metrics.retries_total += 1

                if attempt < max_attempts - 1:
                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.warning(
                        "redis_operation_retry",
                        operation=op_name,
                        attempt=attempt + 1,
                        delay=delay,
                    )
                    time.sleep(delay)

        latency_ms = (time.perf_counter() - start_time) * 1000
        self._metrics.record_operation(op_name, latency_ms, success=False)
        raise last_error or ConnectionError("Redis operation failed")

    def _get(self, key: str) -> str | None:
        """Get value from Redis or mock storage.

        Args:
            key: Key to retrieve

        Returns:
            Value as string, or None if not found

        """
        # Mock mode path
        if self.use_mock:
            if key in self._mock_storage:
                value, expires = self._mock_storage[key]
                if expires is None or datetime.now().timestamp() < expires:
                    return str(value) if value is not None else None
                del self._mock_storage[key]
            return None

        # Real Redis path
        if self._client is None:
            return None

        result = self._client.get(key)
        return str(result) if result else None

    # Default TTL for keys without an explicit TTL (24 hours).
    # Prevents unbounded key growth in Redis when callers omit TTL.
    DEFAULT_TTL: int = 86400

    def _set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """Set value in Redis or mock storage.

        Args:
            key: Key to set
            value: Value to store
            ttl: Time-to-live in seconds. Defaults to DEFAULT_TTL (24h)
                if not specified, to prevent unbounded key growth.

        Returns:
            True if successful

        """
        effective_ttl = ttl if ttl is not None else self.DEFAULT_TTL

        # Mock mode path
        if self.use_mock:
            expires = datetime.now().timestamp() + effective_ttl
            self._mock_storage[key] = (value, expires)
            return True

        # Real Redis path
        if self._client is None:
            return False

        # Always set with TTL to prevent unbounded key growth
        self._client.setex(key, effective_ttl, value)
        return True

    def _delete(self, key: str) -> bool:
        """Delete key from Redis or mock storage.

        Args:
            key: Key to delete

        Returns:
            True if key was deleted

        """
        # Mock mode path
        if self.use_mock:
            if key in self._mock_storage:
                del self._mock_storage[key]
                return True
            return False

        # Real Redis path
        if self._client is None:
            return False

        return bool(self._client.delete(key) > 0)

    def _keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern.

        Args:
            pattern: Glob-style pattern to match

        Returns:
            List of matching keys

        """
        if self.use_mock:
            import fnmatch

            # Use list comp for small result sets (typical <1000 keys)
            return [k for k in self._mock_storage.keys() if fnmatch.fnmatch(k, pattern)]

        if self._client is None:
            return []

        # Use scan_iter instead of keys() to avoid blocking Redis with O(n) scan
        keys = list(self._client.scan_iter(match=pattern, count=100))
        # Convert bytes to strings - needed for API return type
        return [k.decode() if isinstance(k, bytes) else str(k) for k in keys]

    def ping(self) -> bool:
        """Check Redis connection health.

        Returns:
            True if connected and responsive

        """
        if self.use_mock:
            return True
        if self._client is None:
            return False
        try:
            return bool(self._client.ping())
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Health check should not raise, just return False
            return False

    def get_stats(self) -> dict:
        """Get memory statistics.

        Returns:
            Dict with memory stats including mode, key counts by prefix

        """
        if self.use_mock:
            # Use generator expressions for memory-efficient counting
            return {
                "mode": "mock",
                "total_keys": len(self._mock_storage),
                "working_keys": sum(
                    1 for k in self._mock_storage if k.startswith(self.PREFIX_WORKING)
                ),
                "staged_keys": sum(
                    1 for k in self._mock_storage if k.startswith(self.PREFIX_STAGED)
                ),
                "conflict_keys": sum(
                    1 for k in self._mock_storage if k.startswith(self.PREFIX_CONFLICT)
                ),
            }

        if self._client is None:
            return {"mode": "disconnected", "error": "No Redis client"}

        info = self._client.info("memory")
        return {
            "mode": "redis",
            "used_memory": info.get("used_memory_human"),
            "peak_memory": info.get("used_memory_peak_human"),
            "total_keys": self._client.dbsize(),
            "working_keys": len(self._keys(f"{self.PREFIX_WORKING}*")),
            "staged_keys": len(self._keys(f"{self.PREFIX_STAGED}*")),
            "conflict_keys": len(self._keys(f"{self.PREFIX_CONFLICT}*")),
        }

    def get_metrics(self) -> dict:
        """Get operation metrics for observability.

        Returns:
            Dict with operation counts, latencies, and success rates

        """
        return self._metrics.to_dict()

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._metrics = RedisMetrics()

    def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self._client:
            self._client.close()
            self._client = None
        logger.info("redis_connection_closed")
