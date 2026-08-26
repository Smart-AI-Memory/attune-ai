# Licensed under the Apache License, Version 2.0
# Copyright 2025 Smart AI Memory, LLC
"""Tests for pattern reporting, report generator, monitoring
validators, and template engine -- Batch 14.

Covers: meta_workflows/pattern_reporting, meta_workflows/report_generator,
monitoring/validators, template_engine.

(Formerly also covered workflow_fixall -- removed with the
legacy one-command family; see
docs/reports/d-block-triage-2026-07-14.md.)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# === Module: meta_workflows/pattern_reporting.py ===


class TestPatternReporting:
    def _make_report(self, **overrides):
        report = {
            "summary": {
                "total_runs": 10,
                "successful_runs": 8,
                "success_rate": 0.8,
                "total_cost": 1.50,
                "avg_cost_per_run": 0.15,
                "total_agents_created": 20,
                "avg_agents_per_run": 2.0,
            },
            "recommendations": ["Use haiku for cheap tasks"],
            "insights": {},
        }
        report.update(overrides)
        return report

    def test_prints_summary_fields(self, capsys):
        from attune.meta_workflows.pattern_reporting import print_analytics_report

        print_analytics_report(self._make_report())
        out = capsys.readouterr().out
        assert "10" in out
        assert "8" in out
        assert "1.50" in out

    def test_prints_recommendations(self, capsys):
        from attune.meta_workflows.pattern_reporting import print_analytics_report

        print_analytics_report(self._make_report())
        out = capsys.readouterr().out
        assert "Use haiku for cheap tasks" in out

    def test_prints_tier_performance(self, capsys):
        from attune.meta_workflows.pattern_reporting import print_analytics_report

        report = self._make_report(
            insights={
                "tier_performance": [
                    {
                        "description": "Haiku is cheapest",
                        "confidence": 0.9,
                        "sample_size": 5,
                    }
                ]
            }
        )
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "Haiku is cheapest" in out
        assert "90%" in out

    def test_prints_cost_analysis(self, capsys):
        from attune.meta_workflows.pattern_reporting import print_analytics_report

        report = self._make_report(
            insights={
                "cost_analysis": [{"description": "Total: $1.50"}],
            }
        )
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "Total: $1.50" in out

    def test_prints_failure_analysis(self, capsys):
        from attune.meta_workflows.pattern_reporting import print_analytics_report

        report = self._make_report(
            insights={
                "failure_analysis": [{"description": "Timeout was common"}],
            }
        )
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "Timeout was common" in out

    def test_no_recommendations_section_hidden(self, capsys):
        from attune.meta_workflows.pattern_reporting import print_analytics_report

        report = self._make_report()
        report["recommendations"] = []
        print_analytics_report(report)
        out = capsys.readouterr().out
        # Should not crash; Recommendations header may still appear or not
        assert "10" in out

    def test_empty_insights_no_crash(self, capsys):
        from attune.meta_workflows.pattern_reporting import print_analytics_report

        report = self._make_report(insights={})
        print_analytics_report(report)
        capsys.readouterr()  # Should not raise


# === Module: meta_workflows/report_generator.py ===


class TestReportGenerator:
    def _make_result_and_template(self):
        mock_result = MagicMock()
        mock_result.run_id = "run-001"
        mock_result.timestamp = "2026-01-01T00:00:00"
        mock_result.success = True
        mock_result.error = None
        mock_result.total_cost = 0.25
        mock_result.total_duration = 12.5
        mock_result.agents_created = []
        mock_result.agent_results = []
        mock_result.form_responses.responses = {"goal": "test coverage"}
        mock_result.template_id = "health-check"

        mock_template = MagicMock()
        mock_template.name = "Health Check"

        return mock_result, mock_template

    def test_generate_report_returns_string(self):
        from attune.meta_workflows.report_generator import generate_report

        result, template = self._make_result_and_template()
        report = generate_report(result, template)
        assert isinstance(report, str)

    def test_generate_report_contains_run_id(self):
        from attune.meta_workflows.report_generator import generate_report

        result, template = self._make_result_and_template()
        report = generate_report(result, template)
        assert "run-001" in report

    def test_generate_report_contains_template_name(self):
        from attune.meta_workflows.report_generator import generate_report

        result, template = self._make_result_and_template()
        report = generate_report(result, template)
        assert "Health Check" in report

    def test_generate_report_success_yes(self):
        from attune.meta_workflows.report_generator import generate_report

        result, template = self._make_result_and_template()
        result.success = True
        report = generate_report(result, template)
        assert "Yes" in report

    def test_generate_report_failure_no(self):
        from attune.meta_workflows.report_generator import generate_report

        result, template = self._make_result_and_template()
        result.success = False
        report = generate_report(result, template)
        assert "No" in report

    def test_generate_report_includes_cost(self):
        from attune.meta_workflows.report_generator import generate_report

        result, template = self._make_result_and_template()
        report = generate_report(result, template)
        assert "0.25" in report

    def test_generate_report_with_error(self):
        from attune.meta_workflows.report_generator import generate_report

        result, template = self._make_result_and_template()
        result.error = "Something went wrong"
        report = generate_report(result, template)
        assert "Something went wrong" in report

    def test_generate_report_includes_form_responses(self):
        from attune.meta_workflows.report_generator import generate_report

        result, template = self._make_result_and_template()
        report = generate_report(result, template)
        assert "test coverage" in report

    def test_generate_report_with_agents(self):
        from attune.meta_workflows.report_generator import generate_report

        result, template = self._make_result_and_template()

        mock_agent = MagicMock()
        mock_agent.role = "security_auditor"
        mock_agent.agent_id = "agent-1"
        mock_agent.base_template = "security"
        mock_agent.tier_strategy.value = "haiku"
        mock_agent.tools = ["Bash", "Read"]
        mock_agent.config = {}
        mock_agent.success_criteria = ["No critical issues"]
        result.agents_created = [mock_agent]

        mock_ar = MagicMock()
        mock_ar.role = "security_auditor"
        mock_ar.success = True
        mock_ar.tier_used = "haiku"
        mock_ar.cost = 0.01
        mock_ar.duration = 3.0
        mock_ar.error = None
        result.agent_results = [mock_ar]

        report = generate_report(result, template)
        assert "security_auditor" in report
        assert "haiku" in report


# === Module: monitoring/validators.py ===


class TestMonitoringValidators:
    def test_validate_webhook_url_valid(self):
        import socket

        from attune.monitoring.validators import _validate_webhook_url

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, None, None, None, ("8.8.8.8", 0))]
            result = _validate_webhook_url("https://example.com/hook")
        assert result == "https://example.com/hook"

    def test_validate_webhook_url_empty_raises(self):
        from attune.monitoring.validators import _validate_webhook_url

        with pytest.raises(ValueError, match="non-empty"):
            _validate_webhook_url("")

    def test_validate_webhook_url_non_http_raises(self):
        from attune.monitoring.validators import _validate_webhook_url

        with pytest.raises(ValueError, match="scheme"):
            _validate_webhook_url("ftp://example.com/hook")

    def test_validate_webhook_url_file_scheme_raises(self):
        from attune.monitoring.validators import _validate_webhook_url

        with pytest.raises(ValueError, match="scheme"):
            _validate_webhook_url("file:///etc/passwd")

    def test_validate_webhook_url_localhost_raises(self):
        from attune.monitoring.validators import _validate_webhook_url

        with pytest.raises(ValueError, match="local or metadata"):
            _validate_webhook_url("https://localhost/hook")

    def test_validate_webhook_url_loopback_ip_raises(self):
        from attune.monitoring.validators import _validate_webhook_url

        with pytest.raises(ValueError, match="local or metadata|loopback"):
            _validate_webhook_url("https://127.0.0.1/hook")

    def test_validate_webhook_url_metadata_service_raises(self):
        from attune.monitoring.validators import _validate_webhook_url

        with pytest.raises(ValueError, match="local or metadata"):
            _validate_webhook_url("http://169.254.169.254/latest/meta-data")

    def test_validate_webhook_url_private_ip_raises(self):
        from attune.monitoring.validators import _validate_webhook_url

        with pytest.raises(ValueError, match="private"):
            _validate_webhook_url("https://192.168.1.100/hook")

    def test_validate_webhook_url_blocked_port_raises(self):
        import socket

        from attune.monitoring.validators import _validate_webhook_url

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, None, None, None, ("8.8.8.8", 0))]
            with pytest.raises(ValueError, match="internal service port"):
                _validate_webhook_url("https://example.com:6379/hook")

    def test_validate_webhook_url_redis_port_blocked(self):
        from attune.monitoring.validators import _validate_webhook_url

        # 8.8.8.8 passes IP checks; port 6379 is blocked before DNS resolve
        with pytest.raises(ValueError, match="6379"):
            _validate_webhook_url("https://8.8.8.8:6379/hook")

    def test_resolve_and_check_ip_private_raises(self):
        import socket

        from attune.monitoring.validators import _resolve_and_check_ip

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(socket.AF_INET, None, None, None, ("10.0.0.1", 0))]
            with pytest.raises(ValueError, match="unsafe IP"):
                _resolve_and_check_ip("internal.corp.example.com")

    def test_resolve_and_check_ip_dns_error_raises(self):
        import socket

        from attune.monitoring.validators import _resolve_and_check_ip

        with patch("socket.getaddrinfo", side_effect=socket.gaierror("NXDOMAIN")):
            with pytest.raises(ValueError, match="Cannot resolve"):
                _resolve_and_check_ip("nonexistent.invalid")
