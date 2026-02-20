"""Alert data models and enumerations.

Defines the core types used throughout the alert system:
- AlertChannel: Notification delivery channels
- AlertMetric: Monitorable telemetry metrics
- AlertSeverity: Alert severity levels
- AlertConfig: Configuration for a single alert rule
- AlertEvent: A triggered alert instance

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class AlertChannel(Enum):
    """Notification channels for alerts."""

    WEBHOOK = "webhook"
    EMAIL = "email"
    VSCODE_OUTPUT = "vscode_output"
    STDOUT = "stdout"


class AlertMetric(Enum):
    """Metrics that can be monitored."""

    DAILY_COST = "daily_cost"
    ERROR_RATE = "error_rate"
    AVG_LATENCY = "avg_latency"
    TOKEN_USAGE = "token_usage"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertConfig:
    """Configuration for a single alert."""

    alert_id: str
    name: str
    metric: AlertMetric
    threshold: float
    channel: AlertChannel
    webhook_url: str | None = None
    email: str | None = None
    enabled: bool = True
    cooldown_seconds: int = 3600  # 1 hour default
    severity: AlertSeverity = AlertSeverity.WARNING
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "metric": self.metric.value,
            "threshold": self.threshold,
            "channel": self.channel.value,
            "webhook_url": self.webhook_url,
            "email": self.email,
            "enabled": self.enabled,
            "cooldown_seconds": self.cooldown_seconds,
            "severity": self.severity.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlertConfig:
        """Create from dictionary."""
        return cls(
            alert_id=data["alert_id"],
            name=data["name"],
            metric=AlertMetric(data["metric"]),
            threshold=data["threshold"],
            channel=AlertChannel(data["channel"]),
            webhook_url=data.get("webhook_url"),
            email=data.get("email"),
            enabled=data.get("enabled", True),
            cooldown_seconds=data.get("cooldown_seconds", 3600),
            severity=AlertSeverity(data.get("severity", "warning")),
            created_at=(
                datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
            ),
        )


@dataclass
class AlertEvent:
    """An alert event that was triggered."""

    alert_id: str
    alert_name: str
    metric: AlertMetric
    current_value: float
    threshold: float
    severity: AlertSeverity
    triggered_at: datetime
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "alert_name": self.alert_name,
            "metric": self.metric.value,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "triggered_at": self.triggered_at.isoformat(),
            "message": self.message,
        }
