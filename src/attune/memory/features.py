"""Memory feature availability checking.

Provides API for checking which memory features are available based on
installed dependencies and runtime environment.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import importlib
import logging
import os
import re
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

#: States that warn loudly, once per session (R3: never self-healing).
_LOUD_STATES = frozenset({"degraded_auth"})

#: State values already warned about this process (loud-once scope).
_warned_states: set[str] = set()
_warned_lock = threading.Lock()

#: Credential section of any URL embedded in free text (defensive
#: scrub — R3: secrets stay redacted in every message).
_CRED_RE = re.compile(r"://([^/@:\s]*):[^@\s]*@")


def _scrub_secrets(text: str) -> str:
    """Mask the password of any credentialed URL embedded in text."""
    return _CRED_RE.sub(r"://\1:***@", text)


def _warn_once(report: "RedisHealthReport") -> None:
    """Emit ONE structured warning per session for loud states (R3)."""
    state = report.state.value
    if state not in _LOUD_STATES:
        return
    with _warned_lock:
        if state in _warned_states:
            return
        _warned_states.add(state)
    logger.warning(
        "Redis memory degraded (%s): %s — memory features fall back "
        "silently until this is fixed. Effective target: %s%s",
        state,
        report.detail,
        report.redacted_url or "(unresolved)",
        ("; overrides: " + "; ".join(report.overrides)) if report.overrides else "",
    )


def reset_redis_health_warnings() -> None:
    """Reset loud-once state (session boundaries and tests)."""
    _warned_states.clear()


class FeatureStatus(Enum):
    """Status of an optional feature."""

    AVAILABLE = "available"
    MISSING_DEPENDENCY = "missing_dependency"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"


class RedisHealthState(Enum):
    """Classified Redis health at the resolver-consumer seam (R3).

    - ``HEALTHY``: resolved connection answers PING.
    - ``DEGRADED_AUTH``: auth rejected or config malformed — will
      never self-heal, so it warns loudly ONCE per session.
    - ``DEGRADED_CONNECTIVITY``: server absent or transient failure —
      stays silent (may self-heal; matches today's quiet fallback).
    - ``DISABLED``: mock mode requested intentionally
      (``ATTUNE_REDIS_MOCK=true``) — distinguished from broken.
    """

    HEALTHY = "healthy"
    DEGRADED_AUTH = "degraded_auth"
    DEGRADED_CONNECTIVITY = "degraded_connectivity"
    DISABLED = "disabled"


@dataclass(frozen=True)
class RedisHealthReport:
    """Result of :meth:`MemoryFeatures.classify_redis_health`.

    ``detail`` and ``redacted_url`` are safe for logs and notices —
    passwords never appear (redis-config-truth R3: secrets stay
    redacted in every message).
    """

    state: RedisHealthState
    detail: str
    redacted_url: str | None = None
    overrides: tuple[str, ...] = ()


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

            client = redis.Redis(
                host=host,
                port=port,
                socket_connect_timeout=1,
                # R3: authenticate so `requirepass` isn't misread as "Redis down".
                password=os.environ.get("REDIS_PASSWORD") or None,
            )
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
                    message="Redis package not importable (it ships as a "
                    "core dependency, so this usually means a broken or "
                    "partial install)",
                    install_command="pip install --force-reinstall 'redis>=5.0.0,<9.0.0'",
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
    def classify_redis_health(env: Mapping[str, str] | None = None) -> RedisHealthReport:
        """Classify Redis health at the resolver-consumer seam (R3).

        Never raises and never blocks (ratified P15): every failure
        collapses to a classified, fail-open report. Auth failures and
        malformed config are distinguished from an absent server so the
        loud-once path can warn about the classes that never self-heal.

        Args:
            env: Environment mapping (defaults to ``os.environ``;
                injectable for tests).

        Returns:
            A :class:`RedisHealthReport` with the classified state.

        """
        if env is None:
            from attune.config.env_compat import get_attune_env

            mock_flag = get_attune_env("REDIS_MOCK", "") or ""
        else:
            mock_flag = env.get("ATTUNE_REDIS_MOCK") or ""
        if mock_flag.lower() == "true":
            return RedisHealthReport(
                RedisHealthState.DISABLED,
                "mock mode requested (ATTUNE_REDIS_MOCK=true)",
            )

        if not MemoryFeatures.is_redis_available():
            return RedisHealthReport(
                RedisHealthState.DEGRADED_CONNECTIVITY,
                "redis package not importable",
            )

        from attune.memory.config import resolve_redis_connection

        try:
            resolved = resolve_redis_connection(env)
        except ValueError as exc:
            # Malformed config never self-heals — same loud class as auth.
            return RedisHealthReport(RedisHealthState.DEGRADED_AUTH, _scrub_secrets(str(exc)))

        import redis

        try:
            client = redis.Redis.from_url(resolved.url, socket_connect_timeout=1)
            client.ping()
        except (redis.exceptions.AuthenticationError, redis.exceptions.NoPermissionError) as exc:
            return RedisHealthReport(
                RedisHealthState.DEGRADED_AUTH,
                _scrub_secrets(f"authentication rejected: {exc}"),
                redacted_url=resolved.redacted_url,
                overrides=resolved.overrides,
            )
        except Exception:  # noqa: BLE001
            # INTENTIONAL broad catch (P15 never-block): ANY unexpected probe
            # failure must degrade silently, never propagate into a workflow.
            logger.debug("Redis ping failed", exc_info=True)
            return RedisHealthReport(
                RedisHealthState.DEGRADED_CONNECTIVITY,
                "server unreachable",
                redacted_url=resolved.redacted_url,
                overrides=resolved.overrides,
            )

        return RedisHealthReport(
            RedisHealthState.HEALTHY,
            "resolved connection answers PING",
            redacted_url=resolved.redacted_url,
            overrides=resolved.overrides,
        )

    @staticmethod
    def check_redis() -> bool:
        """Check if Redis is usable without raising (fail-open gate).

        Classifies the failure (R3) and routes the never-self-healing
        classes (auth rejection, malformed config) through the
        loud-once notice; server-absent stays silent as before.

        Returns:
            True if the resolved Redis connection is healthy.

        """
        report = MemoryFeatures.classify_redis_health()
        _warn_once(report)
        return report.state is RedisHealthState.HEALTHY

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
                    message="Redis package not importable (it ships as a "
                    "core dependency, so this usually means a broken or "
                    "partial install)",
                    install_command="pip install --force-reinstall 'redis>=5.0.0,<9.0.0'",
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
