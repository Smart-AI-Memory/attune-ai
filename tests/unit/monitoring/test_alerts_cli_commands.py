"""Tests for the `attune alerts` Click CLI (alerts_cli).

The existing test_alerts_cli.py actually covers the AlertEngine
(attune.monitoring.alerts); this drives the CLI itself via click's
CliRunner with the engine mocked, covering init (interactive +
non-interactive + validation), list/delete/enable/disable, watch
(once + loop + daemon), history, and metrics.

The os.fork-based _daemonize() plumbing and the __main__ block are left
uncovered intentionally (unsafe / not meaningful to unit-test).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from attune.monitoring.alerts_cli import alerts

ENGINE_PATH = "attune.monitoring.alerts_cli.get_alert_engine"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def engine():
    return MagicMock()


def _fake_alert(enabled: bool = True) -> MagicMock:
    a = MagicMock()
    a.enabled = enabled
    a.name = "Cost Alert"
    a.alert_id = "alert_1"
    a.metric.value = "daily_cost"
    a.threshold = 10.0
    a.channel.value = "stdout"
    a.severity.value = "warning"
    a.cooldown_seconds = 300
    a.to_dict.return_value = {"alert_id": "alert_1"}
    return a


class TestInitNonInteractive:
    def test_missing_required_params_errors(self, runner, engine):
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["init", "--non-interactive", "--metric", "daily_cost"])
        assert result.exit_code == 1
        assert "required in non-interactive mode" in result.output

    def test_webhook_without_url_errors(self, runner, engine):
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(
                alerts,
                [
                    "init",
                    "--non-interactive",
                    "--metric",
                    "daily_cost",
                    "--threshold",
                    "10",
                    "--channel",
                    "webhook",
                ],
            )
        assert result.exit_code == 1
        assert "--webhook-url required" in result.output

    def test_email_without_address_errors(self, runner, engine):
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(
                alerts,
                [
                    "init",
                    "--non-interactive",
                    "--metric",
                    "error_rate",
                    "--threshold",
                    "5",
                    "--channel",
                    "email",
                ],
            )
        assert result.exit_code == 1
        assert "--email required" in result.output

    def test_valid_creates_alert(self, runner, engine):
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(
                alerts,
                [
                    "init",
                    "--non-interactive",
                    "--metric",
                    "daily_cost",
                    "--threshold",
                    "10",
                    "--channel",
                    "stdout",
                ],
            )
        assert result.exit_code == 0
        assert "Alert created successfully" in result.output
        engine.add_alert.assert_called_once()

    def test_add_alert_value_error_exits(self, runner, engine):
        engine.add_alert.side_effect = ValueError("duplicate id")
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(
                alerts,
                [
                    "init",
                    "--non-interactive",
                    "--metric",
                    "daily_cost",
                    "--threshold",
                    "10",
                    "--channel",
                    "stdout",
                ],
            )
        assert result.exit_code == 1
        assert "duplicate id" in result.output


class TestInitInteractive:
    def test_interactive_webhook_flow(self, runner, engine):
        # metric=a(daily_cost), threshold=10, channel=a(webhook), url
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["init"], input="a\n10\na\nhttps://hook\n")
        assert result.exit_code == 0
        engine.add_alert.assert_called_once()
        _, kwargs = engine.add_alert.call_args
        assert kwargs["channel"] == "webhook"
        assert kwargs["webhook_url"] == "https://hook"

    def test_interactive_email_flow(self, runner, engine):
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["init"], input="b\n5\nb\nuser@example.com\n")
        assert result.exit_code == 0
        _, kwargs = engine.add_alert.call_args
        assert kwargs["channel"] == "email"
        assert kwargs["email"] == "user@example.com"

    def test_interactive_stdout_flow(self, runner, engine):
        # channel=c(stdout) needs no follow-up prompt
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["init"], input="c\n2000\nc\n")
        assert result.exit_code == 0
        _, kwargs = engine.add_alert.call_args
        assert kwargs["channel"] == "stdout"
        assert kwargs["metric"] == "avg_latency"


class TestListCommand:
    def test_empty_plain(self, runner, engine):
        engine.list_alerts.return_value = []
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["list"])
        assert "No alerts configured" in result.output

    def test_empty_json(self, runner, engine):
        engine.list_alerts.return_value = []
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["list", "--json"])
        assert result.output.strip() == "[]"

    def test_populated_plain(self, runner, engine):
        engine.list_alerts.return_value = [_fake_alert(enabled=True), _fake_alert(enabled=False)]
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["list"])
        assert "Configured Alerts" in result.output
        assert "✓ Enabled" in result.output
        assert "✗ Disabled" in result.output

    def test_populated_json(self, runner, engine):
        engine.list_alerts.return_value = [_fake_alert()]
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["list", "--json"])
        assert '"alert_id": "alert_1"' in result.output


class TestDeleteEnableDisable:
    def test_delete_success(self, runner, engine):
        engine.delete_alert.return_value = True
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["delete", "alert_1"])
        assert result.exit_code == 0
        assert "deleted successfully" in result.output

    def test_delete_not_found(self, runner, engine):
        engine.delete_alert.return_value = False
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["delete", "ghost"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_enable_success_and_not_found(self, runner, engine):
        engine.enable_alert.side_effect = [True, False]
        with patch(ENGINE_PATH, return_value=engine):
            ok = runner.invoke(alerts, ["enable", "a1"])
            missing = runner.invoke(alerts, ["enable", "ghost"])
        assert ok.exit_code == 0 and "enabled" in ok.output
        assert missing.exit_code == 1 and "not found" in missing.output

    def test_disable_success_and_not_found(self, runner, engine):
        engine.disable_alert.side_effect = [True, False]
        with patch(ENGINE_PATH, return_value=engine):
            ok = runner.invoke(alerts, ["disable", "a1"])
            missing = runner.invoke(alerts, ["disable", "ghost"])
        assert ok.exit_code == 0 and "disabled" in ok.output
        assert missing.exit_code == 1 and "not found" in missing.output


def _event() -> MagicMock:
    ev = MagicMock()
    ev.alert_name = "Cost Alert"
    ev.metric.value = "daily_cost"
    ev.current_value = 15.0
    ev.threshold = 10.0
    return ev


class TestWatch:
    def test_no_alerts_exits(self, runner, engine):
        engine.list_alerts.return_value = []
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["watch"])
        assert result.exit_code == 1
        assert "No alerts configured" in result.output

    def test_once_with_triggers(self, runner, engine):
        engine.list_alerts.return_value = [_fake_alert()]
        engine.check_and_trigger.return_value = [_event()]
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["watch", "--once"])
        assert result.exit_code == 0
        assert "alert(s) triggered" in result.output

    def test_once_all_within_thresholds(self, runner, engine):
        engine.list_alerts.return_value = [_fake_alert()]
        engine.check_and_trigger.return_value = []
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["watch", "--once"])
        assert "within thresholds" in result.output

    def test_loop_runs_until_interrupt_with_status_line(self, runner, engine):
        engine.list_alerts.return_value = [_fake_alert()]
        engine.check_and_trigger.return_value = [_event()]
        # 5 iterations then KeyboardInterrupt on the 5th sleep -> covers the
        # per-event loop output, the every-5-checks status line, and summary.
        with (
            patch(ENGINE_PATH, return_value=engine),
            patch(
                "attune.monitoring.alerts_cli.time.sleep",
                side_effect=[None, None, None, None, KeyboardInterrupt],
            ),
        ):
            result = runner.invoke(alerts, ["watch", "--interval", "1"])
        assert "Monitoring" in result.output
        assert "Summary" in result.output

    def test_daemon_mode_invokes_daemonize(self, runner, engine):
        engine.list_alerts.return_value = [_fake_alert()]
        engine.check_and_trigger.return_value = []
        with (
            patch(ENGINE_PATH, return_value=engine),
            patch("attune.monitoring.alerts_cli._daemonize") as mock_daemon,
            patch("attune.monitoring.alerts_cli.time.sleep", side_effect=KeyboardInterrupt),
        ):
            result = runner.invoke(alerts, ["watch", "--daemon"])
        mock_daemon.assert_called_once()
        assert "daemon" in result.output.lower()


class TestHistory:
    def _record(self, delivered=True, error=None):
        r = {
            "delivered": delivered,
            "alert_id": "alert_1",
            "metric": "daily_cost",
            "current_value": 15.0,
            "threshold": 10.0,
            "severity": "warning",
            "triggered_at": "2026-01-01T00:00:00",
        }
        if error:
            r["delivery_error"] = error
        return r

    def test_empty_plain(self, runner, engine):
        engine.get_alert_history.return_value = []
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["history"])
        assert "No alert history" in result.output

    def test_empty_json(self, runner, engine):
        engine.get_alert_history.return_value = []
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["history", "--json"])
        assert result.output.strip() == "[]"

    def test_records_plain_with_delivery_error(self, runner, engine):
        engine.get_alert_history.return_value = [self._record(delivered=False, error="timeout")]
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["history"])
        assert "Alert History" in result.output
        assert "Error: timeout" in result.output

    def test_records_json(self, runner, engine):
        engine.get_alert_history.return_value = [self._record()]
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["history", "--json"])
        assert '"alert_id": "alert_1"' in result.output


class TestMetrics:
    def test_json(self, runner, engine):
        engine.get_metrics.return_value = {"daily_cost": 5.0}
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["metrics", "--json"])
        assert '"daily_cost": 5.0' in result.output

    def test_plain_no_triggers(self, runner, engine):
        engine.get_metrics.return_value = {"daily_cost": 5.0, "error_rate": 1.0}
        engine.list_alerts.return_value = [_fake_alert()]  # threshold 10 > 5 -> no trigger
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["metrics"])
        assert "Current Metrics" in result.output
        assert "within thresholds" in result.output

    def test_plain_with_triggers(self, runner, engine):
        engine.get_metrics.return_value = {"daily_cost": 50.0}
        alert = _fake_alert()  # threshold 10 <= 50 -> triggers
        engine.list_alerts.return_value = [alert]
        with patch(ENGINE_PATH, return_value=engine):
            result = runner.invoke(alerts, ["metrics"])
        assert "would trigger" in result.output
