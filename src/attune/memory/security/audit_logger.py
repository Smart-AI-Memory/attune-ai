"""Audit Logging Framework for Attune AI

Comprehensive audit logging for SOC2, HIPAA, and GDPR compliance.
Implements tamper-evident, append-only logging with structured
JSON format.

Key Features:
- JSON Lines format (one event per line)
- ISO-8601 timestamps (UTC)
- Unique event IDs (UUID)
- Tamper-evident (append-only)
- Query/search capability
- Log rotation support

Reference:
- SECURE_MEMORY_ARCHITECTURE.md: Audit Trail Implementation
- SOC2 CC7.2: System Monitoring
- HIPAA 164.312(b): Audit Controls
- GDPR Article 30: Records of Processing

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .events import AuditEvent, SecurityViolation
from .log_methods import AuditLogMethodsMixin
from .query import AuditQueryMixin
from .reports import AuditReportMixin

# Re-export for backward compatibility so that:
#   from attune.memory.security.audit_logger import AuditEvent
# continues to work.
__all__ = ["AuditEvent", "AuditLogger", "SecurityViolation"]

logger = logging.getLogger(__name__)


class AuditLogger(
    AuditLogMethodsMixin,
    AuditQueryMixin,
    AuditReportMixin,
):
    """Comprehensive audit logging for Attune AI.

    Implements SOC2, HIPAA, and GDPR compliant audit trails
    with:
    - Tamper-evident append-only logging
    - Structured JSON Lines format
    - Comprehensive event tracking
    - Query and search capabilities
    - Log rotation support

    Example:
        >>> logger = AuditLogger()
        >>> logger.log_llm_request(
        ...     user_id="user@company.com",
        ...     empathy_level=3,
        ...     provider="anthropic",
        ...     model="claude-sonnet-4",
        ...     memory_sources=[
        ...         "enterprise", "user", "project",
        ...     ],
        ...     pii_count=0,
        ...     secrets_count=0,
        ... )

    Log Format:
        Each line is a complete JSON object representing one
        event. Format: JSON Lines (.jsonl) - one event per
        line, append-only.

    Compliance:
        - SOC2 CC7.2: System Monitoring and Logging
        - HIPAA 164.312(b): Audit Controls
        - GDPR Article 30: Records of Processing Activities

    """

    def __init__(
        self,
        log_dir: str | None = None,
        log_filename: str = "audit.jsonl",
        max_file_size_mb: int = 100,
        retention_days: int = 365,
        enable_rotation: bool = True,
        enable_console_logging: bool = False,
    ):
        """Initialize the audit logger.

        Args:
            log_dir: Directory for audit logs
            log_filename: Name of the audit log file
            max_file_size_mb: Maximum file size before
                rotation (if enabled)
            retention_days: Number of days to retain audit
                logs
            enable_rotation: Whether to enable automatic
                log rotation
            enable_console_logging: Whether to also log to
                console (for development)

        """
        # Use platform-appropriate default if not specified
        if log_dir is None:
            from attune.platform_utils import (
                get_default_log_dir,
            )

            self.log_dir = get_default_log_dir()
        else:
            self.log_dir = Path(log_dir)
        self.log_filename = log_filename
        self.log_path = self.log_dir / log_filename
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.retention_days = retention_days
        self.enable_rotation = enable_rotation
        self.enable_console_logging = enable_console_logging

        # Track security violations for alerting
        self._violation_counts: dict[str, int] = {}

        # Initialize log directory
        self._initialize_log_directory()

    def _initialize_log_directory(self) -> None:
        """Create log directory if it doesn't exist."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            # Set restrictive permissions (owner read/write)
            os.chmod(self.log_dir, 0o700)
            logger.info(f"Audit log directory initialized: {self.log_dir}")
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Fallback on any init error (permissions,
            # disk, etc.). Fixed home-relative location — a cwd-relative
            # ./logs lands wherever the process happened to start — and
            # the same 0o700 as the primary dir (#2242).
            logger.error(f"Failed to initialize audit log directory: {e}")
            self.log_dir = Path.home() / ".attune" / "logs" / "audit"
            self.log_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(self.log_dir, 0o700)
            except OSError as chmod_err:
                # Best-effort on the fallback: a chmod refusal must not
                # take audit logging down entirely.
                logger.warning(f"Could not restrict fallback log dir perms: {chmod_err}")
            self.log_path = self.log_dir / self.log_filename
            logger.warning(f"Using fallback log directory: {self.log_dir}")

    def _write_event(self, event: AuditEvent) -> None:
        """Write an audit event to the log file.

        Uses append-only mode for tamper-evidence.

        Args:
            event: The audit event to write

        """
        try:
            # Check if rotation is needed
            if self.enable_rotation and self.log_path.exists():
                if self.log_path.stat().st_size > self.max_file_size_bytes:
                    self._rotate_log()

            # Write event as single line JSON
            with open(self.log_path, "a", encoding="utf-8") as f:
                json.dump(event.to_dict(), f, ensure_ascii=False)
                f.write("\n")

            # Optional console logging for development
            if self.enable_console_logging:
                logger.debug(f"Audit event: {event.event_type} - {event.status}")

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Audit logging failure should not
            # crash the application
            logger.error(f"Failed to write audit event: {e}")
            if self.enable_console_logging:
                print(f"AUDIT LOG FAILURE: {e}", flush=True)

    def _rotate_log(self) -> None:
        """Rotate the audit log file.

        Renames current log with timestamp and creates new
        file.
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            rotated_name = f"{self.log_filename}.{timestamp}"
            rotated_path = self.log_dir / rotated_name

            self.log_path.replace(rotated_path)
            logger.info(f"Audit log rotated: {rotated_path}")

            # Clean up old logs beyond retention period
            self._cleanup_old_logs()

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Rotation failure is non-fatal
            logger.error(f"Failed to rotate audit log: {e}")

    def _cleanup_old_logs(self) -> None:
        """Remove audit logs older than retention period."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

            for log_file in self.log_dir.glob(f"{self.log_filename}.*"):
                try:
                    # Extract timestamp from filename
                    timestamp_str = log_file.suffix[1:]
                    file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").replace(
                        tzinfo=timezone.utc
                    )

                    if file_date < cutoff_date:
                        log_file.unlink()
                        logger.info(f"Removed old audit log: {log_file}")
                except (ValueError, IndexError):
                    # Skip files that don't match format
                    continue

        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Cleanup failure is non-fatal
            logger.error(f"Failed to cleanup old audit logs: {e}")

    def _handle_security_violation(
        self,
        user_id: str,
        violation_type: str,
        severity: str,
        details: dict[str, Any],
    ) -> None:
        """Internal handler for security violations.

        Tracks violation counts and triggers alerts.

        Args:
            user_id: User who triggered the violation
            violation_type: Type of violation
            severity: Violation severity level
            details: Additional violation details

        """
        # Track violations per user
        key = f"{user_id}:{violation_type}"
        self._violation_counts[key] = self._violation_counts.get(key, 0) + 1

        # Log the violation
        self.log_security_violation(
            user_id=user_id,
            violation_type=violation_type,
            severity=severity,
            details=details,
        )

        # Alert logic
        count = self._violation_counts[key]
        if severity == "CRITICAL" or count >= 3:
            logger.warning(
                f"Security violation threshold reached: "
                f"{user_id} - {violation_type} "
                f"(count: {count}, severity: {severity})",
            )
