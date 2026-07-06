"""Memory feature availability checking.

Provides API for checking which memory features are available based on
installed dependencies and runtime environment.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import importlib
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FeatureStatus(Enum):
    """Status of an optional feature."""

    AVAILABLE = "available"
    MISSING_DEPENDENCY = "missing_dependency"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"


@dataclass
class FeatureInfo:
    """Information about a memory feature."""

    name: str
    status: FeatureStatus
    message: str
    install_command: str | None = None


class MemoryFeatures:
    """Check availability of memory subsystem features.

    Provides methods to check which memory features are available based on
    installed dependencies (Redis) and runtime configuration.

    Example:
        >>> # Check if Redis is available
        >>> if MemoryFeatures.is_redis_available():
        ...     from attune.memory import RedisShortTermMemory
        ...     memory = RedisShortTermMemory()
        ... else:
        ...     from attune.memory import FileSessionMemory
        ...     memory = FileSessionMemory()

        >>> # Get feature status with install instructions
        >>> info = MemoryFeatures.get_feature_status("short_term")
        >>> print(f"{info.name}: {info.status.value}")
        >>> if info.install_command:
        ...     print(f"Install: {info.install_command}")

        >>> # Require Redis or raise helpful error
        >>> MemoryFeatures.require_redis("Short-term memory")

    """

    @staticmethod
    def is_redis_available() -> bool:
        """Check if Redis package is installed.

        Returns:
            True if the redis package is importable, False otherwise.

        """
        try:
            importlib.import_module("redis")
            return True
        except ImportError:
            return False

    @staticmethod
    def is_redis_running(host: str = "127.0.0.1", port: int = 6379) -> bool:
        """Check if Redis server is running and accessible.

        Args:
            host: Redis host (default: 127.0.0.1 — literal loopback, not
                "localhost": getaddrinfo runs before socket timeouts
                apply and has wedged Windows CI workers for 20 minutes;
                see docs/specs/windows-exit139-segfault/)
            port: Redis port (default: 6379)

        Returns:
            True if Redis server responds to ping, False otherwise.

        """
        if not MemoryFeatures.is_redis_available():
            return False

        try:
            import redis

            client = redis.Redis(host=host, port=port, socket_connect_timeout=1)
            return bool(client.ping())
        except ImportError:
            logger.debug("redis module not installed")
            return False
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Redis availability is optional; any failure means unavailable
            logger.debug("Redis ping failed", exc_info=True)
            return False

    @staticmethod
    def get_feature_status(feature: str) -> FeatureInfo:
        """Get status of a specific feature.

        Args:
            feature: Feature name ("short_term", "cross_session", "event_streaming", etc.)

        Returns:
            FeatureInfo with status and guidance for installation/configuration.

        Example:
            >>> info = MemoryFeatures.get_feature_status("short_term")
            >>> if info.status == FeatureStatus.MISSING_DEPENDENCY:
            ...     print(f"Install: {info.install_command}")

        """
        redis_features = {
            "short_term": "Short-term memory (Redis-based)",
            "cross_session": "Cross-session coordination",
            "event_streaming": "Real-time event streaming",
            "agent_heartbeats": "Agent liveness tracking",
            "control_panel": "Memory control panel",
        }

        # Core features are always available
        core_features = {
            "long_term": "Long-term memory (file-based)",
            "file_session": "File session storage",
            "security": "PII scrubbing and secrets detection",
            "graph": "Pattern graph structures",
            "encryption": "AES-256-GCM encryption",
        }

        if feature in redis_features:
            if not MemoryFeatures.is_redis_available():
                return FeatureInfo(
                    name=redis_features[feature],
                    status=FeatureStatus.MISSING_DEPENDENCY,
                    message="Redis package not installed",
                    install_command="pip install 'attune-ai[redis]'",
                )

            if not MemoryFeatures.is_redis_running():
                return FeatureInfo(
                    name=redis_features[feature],
                    status=FeatureStatus.NOT_CONFIGURED,
                    message="Redis server not running",
                    install_command="Install Redis: https://redis.io/docs/install/",
                )

            return FeatureInfo(
                name=redis_features[feature],
                status=FeatureStatus.AVAILABLE,
                message=f"{redis_features[feature]} is available",
            )

        if feature in core_features:
            return FeatureInfo(
                name=core_features[feature],
                status=FeatureStatus.AVAILABLE,
                message="Core feature (always available)",
            )

        # Unknown feature
        return FeatureInfo(
            name=feature,
            status=FeatureStatus.DISABLED,
            message=f"Unknown feature: {feature}",
        )

    @staticmethod
    def check_redis() -> bool:
        """Check if Redis is available without raising.

        Returns:
            True if Redis is available, False otherwise.

        """
        info = MemoryFeatures.get_feature_status("short_term")
        return info.status == FeatureStatus.AVAILABLE

    @staticmethod
    def require_redis(feature_name: str) -> None:
        """Raise exception if Redis is not available.

        Args:
            feature_name: Human-readable feature name for error message

        Raises:
            ImportError: If Redis is not available with installation instructions.

        Example:
            >>> def __init__(self):
            ...     MemoryFeatures.require_redis("Short-term memory")
            ...     # ... rest of init

        """
        info = MemoryFeatures.get_feature_status("short_term")
        if info.status != FeatureStatus.AVAILABLE:
            raise ImportError(
                f"{feature_name} requires Redis.\n"
                f"Status: {info.message}\n"
                f"Install: {info.install_command}",
            )

    @staticmethod
    def list_all_features() -> dict[str, FeatureInfo]:
        """List status of all memory features.

        Returns:
            Dictionary mapping feature names to FeatureInfo.

        Example:
            >>> features = MemoryFeatures.list_all_features()
            >>> for name, info in features.items():
            ...     print(f"{name}: {info.status.value}")

        """
        redis_features = {
            "short_term": "Short-term memory (Redis-based)",
            "cross_session": "Cross-session coordination",
            "event_streaming": "Real-time event streaming",
            "agent_heartbeats": "Agent liveness tracking",
            "control_panel": "Memory control panel",
        }
        core_features = [
            "long_term",
            "file_session",
            "security",
            "graph",
            "encryption",
        ]

        # Probe Redis ONCE up front. is_redis_running() does a real
        # network ping at localhost:6379 with a 1s connect timeout —
        # calling it per-feature meant 5 probes per list_all_features()
        # call. Under xdist on Windows with 12 workers hitting the
        # closed port simultaneously, that contention crashed workers
        # (see docs/specs/windows-memory-detection/decisions.md).
        redis_pkg_available = MemoryFeatures.is_redis_available()
        redis_server_running = redis_pkg_available and MemoryFeatures.is_redis_running()

        def _redis_feature_info(name: str, display: str) -> FeatureInfo:
            if not redis_pkg_available:
                return FeatureInfo(
                    name=display,
                    status=FeatureStatus.MISSING_DEPENDENCY,
                    message="Redis package not installed",
                    install_command="pip install 'attune-ai[redis]'",
                )
            if not redis_server_running:
                return FeatureInfo(
                    name=display,
                    status=FeatureStatus.NOT_CONFIGURED,
                    message="Redis server not running",
                    install_command="Install Redis: https://redis.io/docs/install/",
                )
            return FeatureInfo(
                name=display,
                status=FeatureStatus.AVAILABLE,
                message=f"{display} is available",
            )

        result: dict[str, FeatureInfo] = {
            name: _redis_feature_info(name, display) for name, display in redis_features.items()
        }
        for name in core_features:
            result[name] = MemoryFeatures.get_feature_status(name)
        return result
