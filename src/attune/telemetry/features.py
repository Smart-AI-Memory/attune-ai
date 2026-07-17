"""Telemetry feature availability checking.

Provides API for checking which telemetry features are available based on
installed dependencies (primarily Redis for real-time features).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass
from enum import Enum


class FeatureStatus(Enum):
    """Status of an optional feature."""

    AVAILABLE = "available"
    MISSING_DEPENDENCY = "missing_dependency"
    DISABLED = "disabled"


@dataclass
class FeatureInfo:
    """Information about a telemetry feature."""

    name: str
    status: FeatureStatus
    message: str
    install_command: str | None = None


class TelemetryFeatures:
    """Check availability of telemetry features.

    Provides methods to check which telemetry features are available based on
    installed dependencies (Redis for real-time features).

    Example:
        >>> # Check if event streaming is available
        >>> info = TelemetryFeatures.get_feature_status("event_streaming")
        >>> if info.status == FeatureStatus.AVAILABLE:
        ...     from attune.telemetry import EventStreamer
        ...     streamer = EventStreamer()

        >>> # Require Redis or raise error
        >>> TelemetryFeatures.require_redis("Event streaming")

    """

    @staticmethod
    def is_redis_available() -> bool:
        """Check if Redis package is installed.

        Returns:
            True if the redis package is importable, False otherwise.

        """
        from attune.memory import is_redis_available

        return is_redis_available()

    @staticmethod
    def get_feature_status(feature: str) -> FeatureInfo:
        """Get status of a specific feature.

        Args:
            feature: Feature name ("event_streaming", "agent_coordination", etc.)

        Returns:
            FeatureInfo with status and guidance for installation.

        Example:
            >>> info = TelemetryFeatures.get_feature_status("event_streaming")
            >>> print(f"{info.name}: {info.status.value}")

        """
        redis_features = {
            "event_streaming": "Real-time event streaming",
            "agent_heartbeats": "Agent heartbeat tracking",
            "agent_coordination": "Inter-agent coordination",
            "approval_gates": "Workflow approval gates",
        }

        core_features = {
            "usage_tracking": "Usage tracking (file-based)",
            "feedback_loop": "Quality feedback collection",
            "cli": "CLI commands",
        }

        if feature in redis_features:
            if not TelemetryFeatures.is_redis_available():
                return FeatureInfo(
                    name=redis_features[feature],
                    status=FeatureStatus.MISSING_DEPENDENCY,
                    message="Redis package not importable (it ships as a "
                    "core dependency, so this usually means a broken or "
                    "partial install)",
                    install_command="pip install --force-reinstall 'redis>=5.0.0,<9.0.0'",
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
    def require_redis(feature_name: str) -> None:
        """Raise exception if Redis is not available.

        Args:
            feature_name: Human-readable feature name for error message

        Raises:
            ImportError: If Redis is not available with installation instructions.

        Example:
            >>> def __init__(self):
            ...     TelemetryFeatures.require_redis("Event streaming")
            ...     # ... rest of init

        """
        if not TelemetryFeatures.is_redis_available():
            raise ImportError(
                f"{feature_name} requires the redis package, which ships "
                f"as a core attune-ai dependency — a failure here usually "
                f"means a broken or partial install.\n"
                f"Fix: pip install --force-reinstall 'redis>=5.0.0,<9.0.0'\n"
                f"Redis server setup: https://redis.io/docs/install/",
            )

    @staticmethod
    def list_all_features() -> dict[str, FeatureInfo]:
        """List status of all telemetry features.

        Returns:
            Dictionary mapping feature names to FeatureInfo.

        Example:
            >>> features = TelemetryFeatures.list_all_features()
            >>> for name, info in features.items():
            ...     print(f"{name}: {info.status.value}")

        """
        features = [
            # Redis-dependent features
            "event_streaming",
            "agent_heartbeats",
            "agent_coordination",
            "approval_gates",
            # Core features
            "usage_tracking",
            "feedback_loop",
            "cli",
        ]

        return {feature: TelemetryFeatures.get_feature_status(feature) for feature in features}
