"""Telemetry configuration section.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass


@dataclass
class TelemetryConfig:
    """Telemetry and usage tracking configuration.

    Controls cost tracking, usage analytics, and telemetry data
    retention settings.

    Attributes:
        enabled: Enable telemetry collection.
        cost_tracking: Track API costs and token usage.
        usage_analytics: Collect usage analytics (local only).
        export_path: Path for telemetry exports.
        retention_days: Days to retain telemetry data.
        detailed_logging: Enable detailed operation logging.

    """

    enabled: bool = True
    cost_tracking: bool = True
    usage_analytics: bool = False
    export_path: str = "~/.attune/telemetry"
    retention_days: int = 30
    detailed_logging: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "enabled": self.enabled,
            "cost_tracking": self.cost_tracking,
            "usage_analytics": self.usage_analytics,
            "export_path": self.export_path,
            "retention_days": self.retention_days,
            "detailed_logging": self.detailed_logging,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TelemetryConfig":
        """Create from dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            cost_tracking=data.get("cost_tracking", True),
            usage_analytics=data.get("usage_analytics", False),
            export_path=data.get("export_path", "~/.attune/telemetry"),
            retention_days=data.get("retention_days", 30),
            detailed_logging=data.get("detailed_logging", False),
        )
