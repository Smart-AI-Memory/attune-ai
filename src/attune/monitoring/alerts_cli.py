"""Alert CLI Workflow

Interactive workflow for setting up LLM telemetry alerts.

**Usage:**
    attune alerts init      # Interactive setup workflow
    attune alerts list      # List configured alerts
    attune alerts delete    # Delete an alert
    attune alerts watch     # Start monitoring
    attune alerts history   # View alert history
    attune alerts metrics   # View current metrics

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import signal
import sys
import time

import click

from .alerts import (
    get_alert_engine,
)


@click.group()
def alerts():
    """Alert management commands for LLM telemetry monitoring."""


@alerts.command()
@click.option("--non-interactive", is_flag=True, help="Skip interactive prompts")
@click.option(
    "--metric",
    type=click.Choice(["daily_cost", "error_rate", "avg_latency", "token_usage"]),
)
@click.option("--threshold", type=float)
@click.option("--channel", type=click.Choice(["webhook", "email", "stdout"]))
@click.option("--webhook-url", help="Webhook URL (for webhook channel)")
@click.option("--email", help="Email address (for email channel)")
def init(
    non_interactive: bool,
    metric: str | None,
    threshold: float | None,
    channel: str | None,
    webhook_url: str | None,
    email: str | None,
):
    """Initialize an alert with interactive workflow or CLI flags."""
    if non_interactive:
        # Non-interactive mode - require all parameters
        if not all([metric, threshold, channel]):
            click.echo(
                "Error: --metric, --threshold, and --channel required in non-interactive mode",
            )
            sys.exit(1)

        if channel == "webhook" and not webhook_url:
            click.echo("Error: --webhook-url required for webhook channel")
            sys.exit(1)

        if channel == "email" and not email:
            click.echo("Error: --email required for email channel")
            sys.exit(1)

        _create_alert(metric, threshold, channel, webhook_url, email)
        return

    # Interactive workflow
    click.echo("🔔 Alert Setup Workflow\n")

    # Question 1: What metric?
    click.echo("1. What metric do you want to monitor?")
    click.echo("   a) Daily cost (total USD spent)")
    click.echo("   b) Error rate (% of failed calls)")
    click.echo("   c) Latency (avg response time)")
    click.echo("   d) Token usage (total tokens)")

    metric_choice = click.prompt("Choose (a/b/c/d)", type=click.Choice(["a", "b", "c", "d"]))

    metric_map = {
        "a": ("daily_cost", "Daily Cost", "USD"),
        "b": ("error_rate", "Error Rate", "%"),
        "c": ("avg_latency", "Average Latency", "ms"),
        "d": ("token_usage", "Token Usage", "tokens"),
    }

    metric, metric_name, unit = metric_map[metric_choice]

    # Question 2: What threshold?
    click.echo(f"\n2. What threshold for {metric_name}?")
    defaults = {
        "daily_cost": 10.0,
        "error_rate": 10.0,
        "avg_latency": 3000,
        "token_usage": 100000,
    }
    threshold = click.prompt(f"Threshold ({unit})", type=float, default=defaults[metric])

    # Question 3: Where to send?
    click.echo("\n3. Where should alerts be sent?")
    click.echo("   a) Webhook (Slack, Discord, Teams)")
    click.echo("   b) Email")
    click.echo("   c) Console output")

    channel_choice = click.prompt("Choose (a/b/c)", type=click.Choice(["a", "b", "c"]))

    channel_map = {
        "a": "webhook",
        "b": "email",
        "c": "stdout",
    }

    channel = channel_map[channel_choice]
    webhook_url = None
    email_addr = None

    if channel == "webhook":
        webhook_url = click.prompt("Webhook URL")
    elif channel == "email":
        email_addr = click.prompt("Email address")

    _create_alert(metric, threshold, channel, webhook_url, email_addr)


def _create_alert(
    metric: str,
    threshold: float,
    channel: str,
    webhook_url: str | None,
    email: str | None,
) -> None:
    """Create an alert with the given configuration."""
    engine = get_alert_engine()
    alert_id = f"alert_{metric}_{int(time.time())}"

    metric_names = {
        "daily_cost": "Daily Cost",
        "error_rate": "Error Rate",
        "avg_latency": "Average Latency",
        "token_usage": "Token Usage",
    }

    try:
        engine.add_alert(
            alert_id=alert_id,
            name=f"{metric_names.get(metric, metric)} Alert",
            metric=metric,
            threshold=threshold,
            channel=channel,
            webhook_url=webhook_url,
            email=email,
        )

        click.echo("\n✅ Alert created successfully!")
        click.echo(f"   ID: {alert_id}")
        click.echo(f"   Metric: {metric_names.get(metric, metric)}")
        click.echo(f"   Threshold: {threshold}")
        click.echo(f"   Channel: {channel}")

        click.echo("\n💡 Tip: Run 'attune alerts watch' to start monitoring")

    except ValueError as e:
        click.echo(f"\n❌ Error: {e}")
        sys.exit(1)


@alerts.command(name="list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def list_cmd(as_json: bool):
    """List all configured alerts."""
    engine = get_alert_engine()
    alerts_list = engine.list_alerts()

    if not alerts_list:
        if as_json:
            click.echo("[]")
        else:
            click.echo("No alerts configured. Run 'attune alerts init' to create one.")
        return

    if as_json:
        import json

        click.echo(json.dumps([a.to_dict() for a in alerts_list], indent=2))
        return

    click.echo("📋 Configured Alerts:\n")

    for alert in alerts_list:
        status = "✓ Enabled" if alert.enabled else "✗ Disabled"
        click.echo(f"  [{status}] {alert.name}")
        click.echo(f"    ID: {alert.alert_id}")
        click.echo(f"    Metric: {alert.metric.value} >= {alert.threshold}")
        click.echo(f"    Channel: {alert.channel.value}")
        click.echo(f"    Severity: {alert.severity.value}")
        click.echo(f"    Cooldown: {alert.cooldown_seconds}s")
        click.echo()


@alerts.command()
@click.argument("alert_id")
def delete(alert_id: str):
    """Delete an alert by ID."""
    engine = get_alert_engine()
    deleted = engine.delete_alert(alert_id)

    if deleted:
        click.echo(f"✅ Alert '{alert_id}' deleted successfully")
    else:
        click.echo(f"❌ Alert '{alert_id}' not found")
        sys.exit(1)


@alerts.command()
@click.argument("alert_id")
def enable(alert_id: str):
    """Enable an alert by ID."""
    engine = get_alert_engine()
    if engine.enable_alert(alert_id):
        click.echo(f"✅ Alert '{alert_id}' enabled")
    else:
        click.echo(f"❌ Alert '{alert_id}' not found")
        sys.exit(1)


@alerts.command()
@click.argument("alert_id")
def disable(alert_id: str):
    """Disable an alert by ID."""
    engine = get_alert_engine()
    if engine.disable_alert(alert_id):
        click.echo(f"✅ Alert '{alert_id}' disabled")
    else:
        click.echo(f"❌ Alert '{alert_id}' not found")
        sys.exit(1)


@alerts.command()
@click.option("--interval", default=60, help="Check interval in seconds (default: 60)")
@click.option("--daemon", is_flag=True, help="Run as background daemon")
@click.option("--once", is_flag=True, help="Check once and exit")
def watch(interval: int, daemon: bool, once: bool):
    """Watch telemetry and trigger alerts when thresholds are exceeded."""
    engine = get_alert_engine()

    alerts_list = engine.list_alerts()
    if not alerts_list:
        click.echo("No alerts configured. Run 'attune alerts init' first.")
        sys.exit(1)

    enabled_count = sum(1 for a in alerts_list if a.enabled)
    click.echo(f"🔔 Monitoring {enabled_count} enabled alert(s)")

    if once:
        # Single check mode
        events = engine.check_and_trigger()
        if events:
            click.echo(f"\n⚠️  {len(events)} alert(s) triggered!")
            for event in events:
                click.echo(
                    f"   - {event.alert_name}: {event.current_value:.2f} >= {event.threshold:.2f}",
                )
        else:
            click.echo("✅ All metrics within thresholds")
        return

    if daemon:
        click.echo("🔄 Starting alert watcher as daemon...")
        click.echo(
            "⚠️  Daemon mode runs in background. Use 'ps aux | grep empathy' to check status.",
        )
        # Daemonize
        _daemonize()

    click.echo(f"🔄 Starting alert watcher (checking every {interval}s)...")
    click.echo("   Press Ctrl+C to stop\n")

    # Set up signal handler for graceful shutdown
    running = True

    def signal_handler(sig, frame):
        """Handle shutdown signals for graceful exit."""
        nonlocal running
        running = False
        click.echo("\n✓ Alert watcher stopped")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    check_count = 0
    triggered_count = 0

    try:
        while running:
            check_count += 1
            events = engine.check_and_trigger()

            if events:
                triggered_count += len(events)
                for event in events:
                    click.echo(f"⚠️  ALERT: {event.alert_name}")
                    click.echo(
                        f"   {event.metric.value}: {event.current_value:.2f} >= {event.threshold:.2f}",
                    )

            # Status update every 5 checks
            if check_count % 5 == 0:
                click.echo(
                    f"   [Check #{check_count}] Monitoring... ({triggered_count} alerts triggered)",
                )

            time.sleep(interval)
    except KeyboardInterrupt:
        pass

    click.echo(f"\n📊 Summary: {check_count} checks, {triggered_count} alerts triggered")


def _daemonize():
    """Daemonize the current process (Unix only)."""
    import os

    # Double fork to detach from terminal
    try:
        pid = os.fork()
        if pid > 0:
            # Parent exits
            sys.exit(0)
    except OSError as e:
        click.echo(f"Fork #1 failed: {e}")
        sys.exit(1)

    # Decouple from parent environment
    os.chdir("/")
    os.setsid()
    # 0o077, NOT 0o000. The conventional daemon umask(0) means "inherit
    # nothing, let each caller pick its own mode" — but nothing downstream
    # here passes an explicit mode, so creations land wide open. Measured:
    # under umask(0) a created directory is 0o777 (world-WRITABLE) and the
    # SQLite database 0o644 (world-readable); under 0o077 they are 0o700
    # and 0o600. The alert database and its journal/WAL siblings are
    # created without an explicit mode, so this keeps them owner-only.
    os.umask(0o077)

    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            click.echo(f"Daemon started with PID: {pid}")
            sys.exit(0)
    except OSError as e:
        click.echo(f"Fork #2 failed: {e}")
        sys.exit(1)

    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()

    # Close file descriptors
    with open("/dev/null", "rb", 0) as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open("/dev/null", "ab", 0) as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
    with open("/dev/null", "ab", 0) as f:
        os.dup2(f.fileno(), sys.stderr.fileno())


@alerts.command()
@click.option("--alert-id", help="Filter by alert ID")
@click.option("--limit", default=20, help="Maximum records to show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def history(alert_id: str | None, limit: int, as_json: bool):
    """View alert trigger history."""
    engine = get_alert_engine()
    records = engine.get_alert_history(alert_id=alert_id, limit=limit)

    if not records:
        if as_json:
            click.echo("[]")
        else:
            click.echo("No alert history found.")
        return

    if as_json:
        import json

        click.echo(json.dumps(records, indent=2))
        return

    click.echo("📜 Alert History:\n")

    for record in records:
        delivered = "✓" if record["delivered"] else "✗"
        click.echo(f"  [{delivered}] {record['alert_id']}")
        click.echo(
            f"    Metric: {record['metric']} = {record['current_value']:.2f} (threshold: {record['threshold']:.2f})",
        )
        click.echo(f"    Severity: {record['severity']}")
        click.echo(f"    Triggered: {record['triggered_at']}")
        if record.get("delivery_error"):
            click.echo(f"    Error: {record['delivery_error']}")
        click.echo()


@alerts.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def metrics(as_json: bool):
    """View current telemetry metrics."""
    engine = get_alert_engine()
    current_metrics = engine.get_metrics()

    if as_json:
        import json

        click.echo(json.dumps(current_metrics, indent=2))
        return

    click.echo("📊 Current Metrics (last 24 hours):\n")

    metric_info = {
        "daily_cost": ("Daily Cost", "USD"),
        "error_rate": ("Error Rate", "%"),
        "avg_latency": ("Avg Latency", "ms"),
        "token_usage": ("Token Usage", "tokens"),
    }

    for key, value in current_metrics.items():
        name, unit = metric_info.get(key, (key, ""))
        click.echo(f"  {name}: {value:.2f} {unit}")

    click.echo()

    # Show alerts that would trigger
    alerts_list = engine.list_alerts()
    triggered = []
    for alert in alerts_list:
        if alert.enabled:
            current = current_metrics.get(alert.metric.value, 0)
            if current >= alert.threshold:
                triggered.append((alert.name, current, alert.threshold))

    if triggered:
        click.echo("⚠️  Alerts that would trigger:")
        for name, current, threshold in triggered:
            click.echo(f"    {name}: {current:.2f} >= {threshold:.2f}")
    else:
        click.echo("✅ All metrics within thresholds")


if __name__ == "__main__":
    alerts()
