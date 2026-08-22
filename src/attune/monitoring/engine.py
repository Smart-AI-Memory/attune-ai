"""Alert engine with SQLite storage and threshold monitoring.

Core AlertEngine class: monitors telemetry metrics and triggers
notifications when configurable thresholds are exceeded.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.monitoring.metrics import collect_metrics
from attune.monitoring.models import (
    AlertChannel,
    AlertConfig,
    AlertEvent,
    AlertMetric,
    AlertSeverity,
)
from attune.monitoring.notifications import deliver_notification

logger = logging.getLogger(__name__)


class AlertEngine:
    """Alert engine with SQLite storage and notification delivery.

    Monitors telemetry metrics and sends alerts when thresholds are exceeded.

    Example:
        >>> engine = AlertEngine()
        >>> engine.add_alert(
        ...     alert_id="cost_alert",
        ...     name="Daily Cost Alert",
        ...     metric=AlertMetric.DAILY_COST,
        ...     threshold=10.0,
        ...     channel=AlertChannel.WEBHOOK,
        ...     webhook_url="https://hooks.slack.com/..."
        ... )
        >>> events = engine.check_and_trigger()
        >>> for event in events:
        ...     print(f"Alert: {event.message}")

    """

    def __init__(
        self,
        db_path: str | Path = ".attune/alerts.db",
        telemetry_dir: str | Path | None = None,
    ):
        """Initialize AlertEngine.

        Args:
            db_path: Path to SQLite database for alert storage
            telemetry_dir: Path to telemetry directory (default: ~/.attune/telemetry)

        """
        # Resolved to an ABSOLUTE path so a later ``chdir`` cannot move the
        # target. The default is CWD-relative (".attune/alerts.db"), and
        # ``alerts watch --daemon`` calls ``os.chdir("/")`` while
        # daemonizing — every query after that point would otherwise look
        # for "/.attune/alerts.db" and fail with "unable to open database
        # file". Same anchoring rule as
        # ``attune.memory.storage_backend.default_storage_dir``, which
        # likewise anchors via ``Path.cwd()`` rather than ``resolve()``:
        # making the path absolute is what the fix needs, and resolving
        # symlinks on top would silently rewrite a caller's own absolute
        # path (a caller passing /var/... on macOS would read back
        # /private/var/...).
        self.db_path = Path(db_path).expanduser().absolute()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.telemetry_dir = (
            Path(telemetry_dir) if telemetry_dir else Path.home() / ".attune" / "telemetry"
        )

        self._cooldown_cache: dict[str, float] = {}  # alert_id -> last_triggered_time
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with alerts and history tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Alerts configuration table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                metric TEXT NOT NULL,
                threshold REAL NOT NULL,
                channel TEXT NOT NULL,
                webhook_url TEXT,
                email TEXT,
                enabled INTEGER DEFAULT 1,
                cooldown INTEGER DEFAULT 3600,
                severity TEXT DEFAULT 'warning',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Alert history table for audit trail
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT NOT NULL,
                metric TEXT NOT NULL,
                current_value REAL NOT NULL,
                threshold REAL NOT NULL,
                severity TEXT NOT NULL,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered INTEGER DEFAULT 0,
                delivery_error TEXT,
                FOREIGN KEY (alert_id) REFERENCES alerts(id)
            )
        """,
        )

        conn.commit()
        conn.close()

    def add_alert(
        self,
        alert_id: str,
        name: str,
        metric: AlertMetric | str,
        threshold: float,
        channel: AlertChannel | str,
        webhook_url: str | None = None,
        email: str | None = None,
        cooldown_seconds: int = 3600,
        severity: AlertSeverity | str = AlertSeverity.WARNING,
    ) -> AlertConfig:
        """Add a new alert configuration.

        Args:
            alert_id: Unique identifier for the alert
            name: Human-readable name
            metric: Metric to monitor
            threshold: Threshold value that triggers the alert
            channel: Notification channel
            webhook_url: Webhook URL (required for webhook channel)
            email: Email address (required for email channel)
            cooldown_seconds: Minimum seconds between alerts
            severity: Alert severity level

        Returns:
            AlertConfig for the created alert

        Raises:
            ValueError: If webhook_url missing for webhook channel or email missing for email channel

        """
        # Normalize enum values
        if isinstance(metric, str):
            metric = AlertMetric(metric)
        if isinstance(channel, str):
            channel = AlertChannel(channel)
        if isinstance(severity, str):
            severity = AlertSeverity(severity)

        # Validate channel requirements
        if channel == AlertChannel.WEBHOOK and not webhook_url:
            raise ValueError("webhook_url required for webhook channel")
        if channel == AlertChannel.EMAIL and not email:
            raise ValueError("email required for email channel")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO alerts
            (id, name, metric, threshold, channel, webhook_url, email, cooldown, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                alert_id,
                name,
                metric.value,
                threshold,
                channel.value,
                webhook_url,
                email,
                cooldown_seconds,
                severity.value,
            ),
        )

        conn.commit()
        conn.close()

        logger.info(
            "alert_created: alert_id=%s metric=%s threshold=%s channel=%s",
            alert_id,
            metric.value,
            threshold,
            channel.value,
        )

        return AlertConfig(
            alert_id=alert_id,
            name=name,
            metric=metric,
            threshold=threshold,
            channel=channel,
            webhook_url=webhook_url,
            email=email,
            cooldown_seconds=cooldown_seconds,
            severity=severity,
            created_at=datetime.now(),
        )

    @staticmethod
    def _row_to_alert_config(row: tuple) -> AlertConfig:
        """Convert a database row to an AlertConfig instance."""
        return AlertConfig(
            alert_id=row[0],
            name=row[1],
            metric=AlertMetric(row[2]),
            threshold=row[3],
            channel=AlertChannel(row[4]),
            webhook_url=row[5],
            email=row[6],
            enabled=bool(row[7]),
            cooldown_seconds=row[8],
            severity=AlertSeverity(row[9]) if row[9] else AlertSeverity.WARNING,
            created_at=datetime.fromisoformat(row[10]) if row[10] else None,
        )

    def list_alerts(self) -> list[AlertConfig]:
        """List all configured alerts.

        Returns:
            List of AlertConfig objects

        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, metric, threshold, channel, webhook_url, email, "
            "enabled, cooldown, severity, created_at FROM alerts",
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_alert_config(row) for row in rows]

    def get_alert(self, alert_id: str) -> AlertConfig | None:
        """Get a specific alert by ID.

        Args:
            alert_id: The alert ID

        Returns:
            AlertConfig or None if not found

        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, metric, threshold, channel, webhook_url, email, "
            "enabled, cooldown, severity, created_at FROM alerts WHERE id = ?",
            (alert_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_alert_config(row)

    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert by ID.

        Args:
            alert_id: The alert ID to delete

        Returns:
            True if deleted, False if not found

        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        if deleted:
            logger.info("alert_deleted: alert_id=%s", alert_id)

        return deleted

    def enable_alert(self, alert_id: str) -> bool:
        """Enable an alert."""
        return self._set_alert_enabled(alert_id, True)

    def disable_alert(self, alert_id: str) -> bool:
        """Disable an alert."""
        return self._set_alert_enabled(alert_id, False)

    def _set_alert_enabled(self, alert_id: str, enabled: bool) -> bool:
        """Set alert enabled status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("UPDATE alerts SET enabled = ? WHERE id = ?", (int(enabled), alert_id))
        updated = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return updated

    def get_metrics(self) -> dict[str, float]:
        """Get current telemetry metrics.

        Delegates to ``collect_metrics()`` in the metrics module.

        Returns:
            Dictionary of metric name to current value

        """
        return collect_metrics(self.telemetry_dir)

    def check_and_trigger(self) -> list[AlertEvent]:
        """Check all alerts and trigger notifications if thresholds exceeded.

        Returns:
            List of AlertEvent objects for triggered alerts

        """
        alerts = self.list_alerts()
        metrics = self.get_metrics()
        triggered_events = []

        for alert in alerts:
            if not alert.enabled:
                continue

            # Check cooldown
            last_triggered = self._cooldown_cache.get(alert.alert_id, 0)
            if time.time() - last_triggered < alert.cooldown_seconds:
                logger.debug(
                    "alert_in_cooldown: alert_id=%s remaining=%s",
                    alert.alert_id,
                    alert.cooldown_seconds - (time.time() - last_triggered),
                )
                continue

            # Get current metric value
            current_value = metrics.get(alert.metric.value, 0.0)

            # Check threshold
            if current_value >= alert.threshold:
                event = AlertEvent(
                    alert_id=alert.alert_id,
                    alert_name=alert.name,
                    metric=alert.metric,
                    current_value=current_value,
                    threshold=alert.threshold,
                    severity=alert.severity,
                    triggered_at=datetime.now(),
                    message=self._format_alert_message(alert, current_value),
                )

                # Deliver notification
                success = self._deliver_notification(alert, event)

                # Record in history
                self._record_alert_history(event, success)

                # Update cooldown
                self._cooldown_cache[alert.alert_id] = time.time()

                triggered_events.append(event)

                logger.info(
                    "alert_triggered: alert_id=%s metric=%s current_value=%s threshold=%s delivered=%s",
                    alert.alert_id,
                    alert.metric.value,
                    current_value,
                    alert.threshold,
                    success,
                )

        return triggered_events

    def _format_alert_message(self, alert: AlertConfig, current_value: float) -> str:
        """Format human-readable alert message."""
        metric_units = {
            AlertMetric.DAILY_COST: "USD",
            AlertMetric.ERROR_RATE: "%",
            AlertMetric.AVG_LATENCY: "ms",
            AlertMetric.TOKEN_USAGE: "tokens",
        }
        unit = metric_units.get(alert.metric, "")

        return (
            f"[{alert.severity.value.upper()}] {alert.name}\n"
            f"Metric: {alert.metric.value}\n"
            f"Current: {current_value:.2f} {unit}\n"
            f"Threshold: {alert.threshold:.2f} {unit}\n"
            f"Triggered at: {datetime.now().isoformat()}"
        )

    def _deliver_notification(self, alert: AlertConfig, event: AlertEvent) -> bool:
        """Deliver notification through configured channel."""
        return deliver_notification(alert, event)

    # Backward-compatible wrappers for direct method calls in tests
    def _deliver_webhook(self, alert: AlertConfig, event: AlertEvent) -> bool:
        """Deliver alert via webhook. Delegates to notifications module."""
        from attune.monitoring.notifications import deliver_webhook

        return deliver_webhook(alert, event)

    def _deliver_email(self, alert: AlertConfig, event: AlertEvent) -> bool:
        """Deliver alert via email. Delegates to notifications module."""
        from attune.monitoring.notifications import deliver_email

        return deliver_email(alert, event)

    def _deliver_stdout(self, event: AlertEvent) -> bool:
        """Deliver alert to stdout. Delegates to notifications module."""
        from attune.monitoring.notifications import deliver_stdout

        return deliver_stdout(event)

    def _record_alert_history(self, event: AlertEvent, delivered: bool) -> None:
        """Record alert event in history table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO alert_history
            (alert_id, metric, current_value, threshold, severity, delivered)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                event.alert_id,
                event.metric.value,
                event.current_value,
                event.threshold,
                event.severity.value,
                int(delivered),
            ),
        )

        conn.commit()
        conn.close()

    def get_alert_history(
        self,
        alert_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get alert history.

        Args:
            alert_id: Filter by alert ID (optional)
            limit: Maximum number of records to return

        Returns:
            List of alert history records

        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        base_sql = (
            "SELECT alert_id, metric, current_value, threshold, severity,"
            " triggered_at, delivered, delivery_error FROM alert_history"
        )
        if alert_id:
            cursor.execute(
                base_sql + " WHERE alert_id = ? ORDER BY triggered_at DESC LIMIT ?",
                (alert_id, limit),
            )
        else:
            cursor.execute(
                base_sql + " ORDER BY triggered_at DESC LIMIT ?",
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "alert_id": r[0],
                "metric": r[1],
                "current_value": r[2],
                "threshold": r[3],
                "severity": r[4],
                "triggered_at": r[5],
                "delivered": bool(r[6]),
                "delivery_error": r[7],
            }
            for r in rows
        ]


def get_alert_engine(
    db_path: str | Path = ".attune/alerts.db",
) -> AlertEngine:
    """Get an AlertEngine instance.

    Args:
        db_path: Path to SQLite database

    Returns:
        Configured AlertEngine instance

    """
    return AlertEngine(db_path=db_path)
