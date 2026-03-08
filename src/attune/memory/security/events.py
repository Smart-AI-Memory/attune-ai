"""Audit Event Data Models

Dataclass definitions for audit events and security violations
used throughout the audit logging framework.

Reference:
- SECURE_MEMORY_ARCHITECTURE.md: Audit Trail Implementation
- SOC2 CC7.2: System Monitoring
- HIPAA 164.312(b): Audit Controls
- GDPR Article 30: Records of Processing

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditEvent:
    """Represents a single audit event.

    All audit events share these core fields for compliance
    tracking.
    """

    # Core identification
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0"

    # Event classification
    event_type: str = ""
    user_id: str = ""
    session_id: str = ""

    # Status tracking
    status: str = "success"  # success, failed, blocked
    error: str = ""

    # Custom fields (populated by specific event types)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Flatten data dict into top level for easier querying
        data = result.pop("data", {})
        result.update(data)
        return result


@dataclass
class SecurityViolation:
    """Represents a security policy violation.

    Used for tracking and alerting on security issues.
    """

    violation_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    details: dict[str, Any] = field(default_factory=dict)
    user_notified: bool = False
    manager_notified: bool = False
    security_team_notified: bool = False
