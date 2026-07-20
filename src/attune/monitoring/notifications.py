"""Alert notification delivery channels.

Handles sending alert notifications through various channels:
- Webhook (Slack, Discord, PagerDuty, etc.)
- Email (SMTP)
- Stdout/console output

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import smtplib
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.request import HTTPRedirectHandler, build_opener

from attune.monitoring.models import AlertChannel, AlertConfig, AlertEvent
from attune.monitoring.validators import _validate_webhook_url

logger = logging.getLogger(__name__)


def deliver_notification(alert: AlertConfig, event: AlertEvent) -> bool:
    """Deliver notification through configured channel.

    Args:
        alert: The alert configuration
        event: The alert event

    Returns:
        True if delivered successfully

    """
    try:
        if alert.channel == AlertChannel.WEBHOOK:
            return deliver_webhook(alert, event)
        if alert.channel == AlertChannel.EMAIL:
            return deliver_email(alert, event)
        if alert.channel in (AlertChannel.VSCODE_OUTPUT, AlertChannel.STDOUT):
            return deliver_stdout(event)
        logger.warning("unknown_alert_channel: channel=%s", alert.channel.value)
        return False
    except Exception as e:  # noqa: BLE001
        logger.error(
            "alert_delivery_failed: alert_id=%s channel=%s error=%s",
            alert.alert_id,
            alert.channel.value,
            str(e),
        )
        return False


def deliver_webhook(alert: AlertConfig, event: AlertEvent) -> bool:
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
            "invalid_webhook_url: url=%s error=%s",
            alert.webhook_url,
            str(e),
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
    req = urllib.request.Request(  # noqa: S310 — URL validated by _validate_webhook_url
        validated_url,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    # Block redirects — webhook endpoints must respond
    # directly. Redirect chains are an SSRF vector.
    class _NoRedirect(HTTPRedirectHandler):
        """Raise on any redirect attempt."""

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise urllib.error.HTTPError(
                newurl,
                code,
                f"Redirect blocked (SSRF protection): {code} -> {newurl}",
                headers,
                fp,
            )

    opener = build_opener(_NoRedirect)

    try:
        with opener.open(
            req, timeout=10
        ) as response:  # noqa: S310  # nosec B310 — URL validated by _validate_webhook_url
            if response.status == 200:
                logger.info("webhook_delivered: url=%s", validated_url)
                return True
            logger.warning(
                "webhook_unexpected_status: url=%s status=%s",
                validated_url,
                response.status,
            )
            return False
    except urllib.error.HTTPError as e:
        logger.warning(
            "webhook_http_error: url=%s status=%s error=%s",
            validated_url,
            e.code,
            e,
        )
        return False
    except urllib.error.URLError as e:
        logger.error("webhook_delivery_failed: url=%s error=%s", validated_url, e)
        return False


def deliver_email(alert: AlertConfig, event: AlertEvent) -> bool:
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
    from_email = os.environ.get("SMTP_FROM", "alerts@attune-ai.local")

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = alert.email
    msg["Subject"] = f"[{event.severity.value.upper()}] {event.alert_name}"

    body = f"""
Attune AI Alert

Alert: {event.alert_name}
Metric: {event.metric.value}
Current Value: {event.current_value:.2f}
Threshold: {event.threshold:.2f}
Severity: {event.severity.value}
Triggered: {event.triggered_at.isoformat()}

--
Attune AI Monitoring
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
        logger.error("email_delivery_failed: email=%s error=%s", alert.email, e)
        return False


def deliver_stdout(event: AlertEvent) -> bool:
    """Deliver alert to stdout/console."""
    print(f"\n{'=' * 60}")
    print(event.message)
    print(f"{'=' * 60}\n")
    return True
