"""Alert System for LLM Telemetry Monitoring

Provides threshold-based alerting for LLM usage metrics.

**Features:**
- Interactive CLI workflow (`empathy alerts init`)
- Multiple notification channels (webhook, email, stdout)
- Threshold triggers (daily cost, error rate, etc.)
- Cooldown mechanism (prevent spam)
- Enterprise background daemon (`empathy alerts watch --daemon`)

**Supported Metrics:**
- daily_cost: Total USD spent in the last 24 hours
- error_rate: Percentage of failed LLM calls
- avg_latency: Average response time in milliseconds
- token_usage: Total tokens used in the last 24 hours

Copyright 2025-2026 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from __future__ import annotations

import ipaddress
import json
import logging
import smtplib
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _validate_webhook_url(url: str) -> str:
    """Validate webhook URL to prevent SSRF attacks.

    Args:
        url: Webhook URL to validate

    Returns:
        Validated URL (unchanged if valid)

    Raises:
        ValueError: If URL is invalid or targets unsafe destinations

    Security:
        Prevents Server-Side Request Forgery (SSRF) by blocking:
        - Non-HTTP(S) schemes (file://, gopher://, ftp://)
        - Localhost and loopback addresses (127.0.0.1, ::1)
        - Cloud metadata services (169.254.169.254)
        - Private IP ranges (10.x, 172.16-31.x, 192.168.x)
        - Common internal service ports (Redis, PostgreSQL, etc.)
    """
    if not url or not isinstance(url, str):
        raise ValueError("webhook_url must be a non-empty string")

    # Parse URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")

    # Only allow http and https schemes
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid scheme '{parsed.scheme}'. Only http and https allowed for webhooks."
        )

    # Check hostname exists
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Webhook URL must contain a valid hostname")

    # Blocked hostnames (localhost, metadata services)
    blocked_hosts = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",  # nosec B104 - blocklist, not a bind
        "::1",
        "[::1]",
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
        "instance-data",  # Azure metadata pattern
    }

    hostname_lower = hostname.lower()
    if hostname_lower in blocked_hosts:
        raise ValueError(f"Webhook URL cannot target local or metadata address: {hostname}")

    # Check for private/internal IPs
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private:
            raise ValueError(f"Webhook URL cannot target private IP: {hostname}")
        if ip.is_loopback:
            raise ValueError(f"Webhook URL cannot target loopback address: {hostname}")
        if ip.is_link_local:
            raise ValueError(f"Webhook URL cannot target link-local address: {hostname}")
        if ip.is_reserved:
            raise ValueError(f"Webhook URL cannot target reserved IP: {hostname}")
    except ValueError as e:
        # Check if this is our own validation error
        if "cannot target" in str(e):
            raise
        # Not an IP address (it's a hostname) - that's fine, continue

    # Block common internal service ports
    if parsed.port is not None:
        blocked_ports = {
            22,  # SSH
            23,  # Telnet
            3306,  # MySQL
            5432,  # PostgreSQL
            6379,  # Redis
            27017,  # MongoDB
            9200,  # Elasticsearch
            2379,  # etcd
            8500,  # Consul
        }
        if parsed.port in blocked_ports:
            raise ValueError(
                f"Webhook URL cannot target internal service port {parsed.port}. "
                "Use standard HTTP (80) or HTTPS (443) ports."
            )

    return url


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
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.telemetry_dir = (
            Path(telemetry_dir) if telemetry_dir else Path.home() / ".empathy" / "telemetry"
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
        """
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
        """
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
            "alert_created",
            alert_id=alert_id,
            metric=metric.value,
            threshold=threshold,
            channel=channel.value,
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

    def list_alerts(self) -> list[AlertConfig]:
        """List all configured alerts.

        Returns:
            List of AlertConfig objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, metric, threshold, channel, webhook_url, email, "
            "enabled, cooldown, severity, created_at FROM alerts"
        )
        rows = cursor.fetchall()
        conn.close()

        alerts = []
        for row in rows:
            alerts.append(
                AlertConfig(
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
            )

        return alerts

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
            logger.info("alert_deleted", alert_id=alert_id)

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

        Reads from telemetry files and calculates:
        - daily_cost: Total cost in last 24 hours
        - error_rate: Percentage of errors
        - avg_latency: Average latency in ms
        - token_usage: Total tokens in last 24 hours

        Returns:
            Dictionary of metric name to current value
        """
        usage_file = self.telemetry_dir / "usage.jsonl"

        if not usage_file.exists():
            logger.debug("telemetry_file_not_found", path=str(usage_file))
            return {
                "daily_cost": 0.0,
                "error_rate": 0.0,
                "avg_latency": 0.0,
                "token_usage": 0,
            }

        # Read last 24 hours of data
        cutoff = datetime.now() - timedelta(hours=24)
        total_cost = 0.0
        total_tokens = 0
        total_latency = 0.0
        total_calls = 0
        error_calls = 0

        try:
            with open(usage_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        timestamp = datetime.fromisoformat(entry.get("timestamp", "2000-01-01"))
                        if timestamp < cutoff:
                            continue

                        total_calls += 1
                        total_cost += entry.get("cost", 0.0)
                        total_tokens += entry.get("tokens", {}).get("total", 0)
                        total_latency += entry.get("duration_ms", 0)

                        if entry.get("error"):
                            error_calls += 1
                    except (json.JSONDecodeError, KeyError):
                        continue
        except (OSError, PermissionError) as e:
            logger.warning("telemetry_read_error", error=str(e))
            return {
                "daily_cost": 0.0,
                "error_rate": 0.0,
                "avg_latency": 0.0,
                "token_usage": 0,
            }

        return {
            "daily_cost": total_cost,
            "error_rate": (error_calls / total_calls * 100) if total_calls > 0 else 0.0,
            "avg_latency": (total_latency / total_calls) if total_calls > 0 else 0.0,
            "token_usage": total_tokens,
        }

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
                    "alert_in_cooldown",
                    alert_id=alert.alert_id,
                    remaining=alert.cooldown_seconds - (time.time() - last_triggered),
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
                    "alert_triggered",
                    alert_id=alert.alert_id,
                    metric=alert.metric.value,
                    current_value=current_value,
                    threshold=alert.threshold,
                    delivered=success,
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
        """Deliver notification through configured channel.

        Args:
            alert: The alert configuration
            event: The alert event

        Returns:
            True if delivered successfully
        """
        try:
            if alert.channel == AlertChannel.WEBHOOK:
                return self._deliver_webhook(alert, event)
            elif alert.channel == AlertChannel.EMAIL:
                return self._deliver_email(alert, event)
            elif alert.channel in (AlertChannel.VSCODE_OUTPUT, AlertChannel.STDOUT):
                return self._deliver_stdout(event)
            else:
                logger.warning("unknown_alert_channel", channel=alert.channel.value)
                return False
        except Exception as e:
            logger.error(
                "alert_delivery_failed",
                alert_id=alert.alert_id,
                channel=alert.channel.value,
                error=str(e),
            )
            return False

    def _deliver_webhook(self, alert: AlertConfig, event: AlertEvent) -> bool:
        """Deliver alert via webhook (Slack, Discord, etc.).

        Security:
            Validates webhook URL to prevent SSRF attacks before making request.
            See _validate_webhook_url() for details on blocked targets.
        """
        if not alert.webhook_url:
            return False

        # Validate webhook URL to prevent SSRF (CWE-918)
        try:
            validated_url = _validate_webhook_url(alert.webhook_url)
        except ValueError as e:
            logger.warning(
                "invalid_webhook_url",
                url=alert.webhook_url,
                error=str(e),
            )
            return False

        payload = {
            "text": event.message,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 {event.alert_name}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Metric:*\n{event.metric.value}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{event.severity.value}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Current Value:*\n{event.current_value:.2f}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Threshold:*\n{event.threshold:.2f}",
                        },
                    ],
                },
            ],
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            validated_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                if response.status == 200:
                    logger.info("webhook_delivered", url=validated_url)
                    return True
                else:
                    logger.warning(
                        "webhook_unexpected_status",
                        url=validated_url,
                        status=response.status,
                    )
                    return False
        except urllib.error.HTTPError as e:
            logger.warning(
                "webhook_http_error",
                url=validated_url,
                status=e.code,
                error=str(e),
            )
            return False
        except urllib.error.URLError as e:
            logger.error("webhook_delivery_failed", url=validated_url, error=str(e))
            return False

    def _deliver_email(self, alert: AlertConfig, event: AlertEvent) -> bool:
        """Deliver alert via email.

        Requires SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD environment variables.
        """
        if not alert.email:
            return False

        import os

        smtp_host = os.environ.get("SMTP_HOST", "localhost")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_password = os.environ.get("SMTP_PASSWORD", "")
        from_email = os.environ.get("SMTP_FROM", "alerts@empathy-framework.local")

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = alert.email
        msg["Subject"] = f"[{event.severity.value.upper()}] {event.alert_name}"

        body = f"""
Empathy Framework Alert

Alert: {event.alert_name}
Metric: {event.metric.value}
Current Value: {event.current_value:.2f}
Threshold: {event.threshold:.2f}
Severity: {event.severity.value}
Triggered: {event.triggered_at.isoformat()}

--
Empathy Framework Monitoring
"""
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_user and smtp_password:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                server.sendmail(from_email, alert.email, msg.as_string())
            return True
        except (smtplib.SMTPException, OSError) as e:
            logger.error("email_delivery_failed", email=alert.email, error=str(e))
            return False

    def _deliver_stdout(self, event: AlertEvent) -> bool:
        """Deliver alert to stdout/console."""
        print(f"\n{'='*60}")
        print(event.message)
        print(f"{'='*60}\n")
        return True

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
        self, alert_id: str | None = None, limit: int = 100
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

        if alert_id:
            cursor.execute(
                """
                SELECT alert_id, metric, current_value, threshold, severity,
                       triggered_at, delivered, delivery_error
                FROM alert_history
                WHERE alert_id = ?
                ORDER BY triggered_at DESC
                LIMIT ?
            """,
                (alert_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT alert_id, metric, current_value, threshold, severity,
                       triggered_at, delivered, delivery_error
                FROM alert_history
                ORDER BY triggered_at DESC
                LIMIT ?
            """,
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "alert_id": row[0],
                "metric": row[1],
                "current_value": row[2],
                "threshold": row[3],
                "severity": row[4],
                "triggered_at": row[5],
                "delivered": bool(row[6]),
                "delivery_error": row[7],
            }
            for row in rows
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
