"""Alert System for LLM Telemetry Monitoring

Provides threshold-based alerting for LLM usage metrics.

This module re-exports all public APIs from the refactored submodules
for backward compatibility. All existing imports from
``attune.monitoring.alerts`` continue to work unchanged.

**Submodules:**
- ``models``: Enums and dataclasses (AlertChannel, AlertMetric, etc.)
- ``validators``: Webhook URL validation (SSRF prevention)
- ``notifications``: Notification delivery channels
- ``engine``: AlertEngine with SQLite storage and threshold monitoring

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.monitoring.engine import AlertEngine, get_alert_engine
from attune.monitoring.models import (
    AlertChannel,
    AlertConfig,
    AlertEvent,
    AlertMetric,
    AlertSeverity,
)
from attune.monitoring.validators import _validate_webhook_url

__all__ = [
    "AlertChannel",
    "AlertConfig",
    "AlertEngine",
    "AlertEvent",
    "AlertMetric",
    "AlertSeverity",
    "_validate_webhook_url",
    "get_alert_engine",
]
