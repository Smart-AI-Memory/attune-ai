"""Tests for the meta-workflow analytics Typer CLI (analytics_commands).

Drives the analytics / list-runs / show / cleanup commands via typer's
CliRunner with PatternLearner and the execution-result loaders mocked.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from attune.meta_workflows.cli_commands import meta_workflow_app

MOD = "attune.meta_workflows.cli_commands.analytics_commands"


@pytest.fixture
def runner():
    return CliRunner()


def _full_report() -> dict:
    return {
        "summary": {
            "total_runs": 10,
            "successful_runs": 8,
            "success_rate": 0.8,
            "total_cost": 1.5,
            "avg_cost_per_run": 0.15,
            "total_agents_created": 20,
            "avg_agents_per_run": 2.0,
        },
        "recommendations": ["Switch small modules to CHEAP tier"],
        "insights": {
            "tier_performance": [
                {"description": "CHEAP is fastest", "confidence": 0.9, "sample_size": 5},
            ],
            "cost_analysis": [
                {
                    "description": "Cost concentrated in PREMIUM",
                    "data": {
                        "tier_breakdown": {
                            "CHEAP": {"avg": 0.1, "total": 1.0, "count": 10},
                        },
                    },
                },
            ],
            "failure_analysis": [{"description": "Timeouts on large modules"}],
        },
    }


def _agent_result(success=True, error=None):
    ar = MagicMock()
    ar.success = success
    ar.role = "researcher"
    ar.tier_used = "CHEAP"
    ar.cost = 0.5
    ar.duration = 1.0
    ar.error = error
    return ar


def _result(
    success=True, error=None, template_id="tpl", timestamp="2026-01-01T12:00:00", agents=None
):
    r = MagicMock()
    r.template_id = template_id
    r.success = success
    r.total_cost = 1.5
    r.total_duration = 2.0
    r.timestamp = timestamp
    r.error = error
    r.agents_created = ["a", "b"]
    r.agent_results = agents if agents is not None else [_agent_result()]
    r.form_responses.responses = {"goal": "ship it"}
    r.to_json.return_value = '{"run_id": "run_1"}'
    return r


class TestAnalytics:
    def test_full_report_renders(self, runner):
        learner = MagicMock()
        learner.generate_analytics_report.return_value = _full_report()
        with patch(f"{MOD}.PatternLearner", return_value=learner):
            result = runner.invoke(meta_workflow_app, ["analytics", "my-template"])
        assert result.exit_code == 0
        assert "Meta-Workflow Analytics Report" in result.output
        assert "Recommendations" in result.output
        assert "Tier Performance" in result.output
        assert "Cost Analysis" in result.output
        assert "Failure Analysis" in result.output

    def test_use_memory_initializes_memory_learner(self, runner):
        learner = MagicMock()
        learner.generate_analytics_report.return_value = _full_report()
        with (
            patch(f"{MOD}.PatternLearner", return_value=learner),
            patch("attune.memory.unified.UnifiedMemory") as mock_mem,
        ):
            result = runner.invoke(meta_workflow_app, ["analytics", "--use-memory"])
        assert result.exit_code == 0
        assert "memory-enhanced analytics" in result.output
        mock_mem.assert_called_once()

    def test_error_exits_one(self, runner):
        learner = MagicMock()
        learner.generate_analytics_report.side_effect = RuntimeError("boom")
        with patch(f"{MOD}.PatternLearner", return_value=learner):
            result = runner.invoke(meta_workflow_app, ["analytics"])
        assert result.exit_code == 1
        assert "Error:" in result.output


class TestListRuns:
    def test_empty(self, runner):
        with patch(f"{MOD}.list_execution_results", return_value=[]):
            result = runner.invoke(meta_workflow_app, ["list-runs"])
        assert "No execution results found" in result.output

    def test_renders_rows_with_status_and_bad_timestamp(self, runner):
        good = _result(success=True)
        bad_ts = _result(success=False, timestamp="not-a-date")
        with (
            patch(f"{MOD}.list_execution_results", return_value=["r1", "r2"]),
            patch(f"{MOD}.load_execution_result", side_effect=[good, bad_ts]),
        ):
            result = runner.invoke(meta_workflow_app, ["list-runs"])
        assert result.exit_code == 0
        assert "Recent Executions" in result.output

    def test_load_failure_warns_and_continues(self, runner):
        with (
            patch(f"{MOD}.list_execution_results", return_value=["r1"]),
            patch(f"{MOD}.load_execution_result", side_effect=RuntimeError("corrupt")),
        ):
            result = runner.invoke(meta_workflow_app, ["list-runs"])
        # All loads failed -> count == 0 -> "no valid" message.
        assert "No valid execution results" in result.output

    def test_template_filter_no_match(self, runner):
        r = _result(template_id="other")
        with (
            patch(f"{MOD}.list_execution_results", return_value=["r1"]),
            patch(f"{MOD}.load_execution_result", return_value=r),
        ):
            result = runner.invoke(meta_workflow_app, ["list-runs", "--template", "wanted"])
        assert "No executions found for template: wanted" in result.output

    def test_list_execution_error_exits_one(self, runner):
        with patch(f"{MOD}.list_execution_results", side_effect=RuntimeError("io")):
            result = runner.invoke(meta_workflow_app, ["list-runs"])
        assert result.exit_code == 1
        assert "Error:" in result.output


class TestShow:
    def test_json_format(self, runner):
        with patch(f"{MOD}.load_execution_result", return_value=_result()):
            result = runner.invoke(meta_workflow_app, ["show", "run_1", "--format", "json"])
        assert result.exit_code == 0
        assert '"run_id": "run_1"' in result.output

    def test_text_format_with_errors(self, runner):
        r = _result(success=False, error="workflow failed", agents=[_agent_result(False, "boom")])
        with patch(f"{MOD}.load_execution_result", return_value=r):
            result = runner.invoke(meta_workflow_app, ["show", "run_1"])
        assert result.exit_code == 0
        assert "Execution Report: run_1" in result.output
        assert "Failed" in result.output
        assert "workflow failed" in result.output
        assert "Cost Breakdown by Tier" in result.output

    def test_not_found_exits_one(self, runner):
        with patch(f"{MOD}.load_execution_result", side_effect=FileNotFoundError()):
            result = runner.invoke(meta_workflow_app, ["show", "ghost"])
        assert result.exit_code == 1
        assert "Execution not found" in result.output

    def test_generic_error_exits_one(self, runner):
        with patch(f"{MOD}.load_execution_result", side_effect=RuntimeError("io")):
            result = runner.invoke(meta_workflow_app, ["show", "run_1"])
        assert result.exit_code == 1
        assert "Error:" in result.output


class TestCleanup:
    def test_empty(self, runner):
        with patch(f"{MOD}.list_execution_results", return_value=[]):
            result = runner.invoke(meta_workflow_app, ["cleanup"])
        assert "No execution results found" in result.output

    def test_nothing_old_enough(self, runner):
        recent = _result(timestamp="2099-01-01T00:00:00")
        with (
            patch(f"{MOD}.list_execution_results", return_value=["r1"]),
            patch(f"{MOD}.load_execution_result", return_value=recent),
        ):
            result = runner.invoke(meta_workflow_app, ["cleanup"])
        assert "No executions older than" in result.output

    def test_dry_run_lists_without_deleting(self, runner):
        old = _result(timestamp="2020-01-01T00:00:00")
        with (
            patch(f"{MOD}.list_execution_results", return_value=["r1"]),
            patch(f"{MOD}.load_execution_result", return_value=old),
        ):
            result = runner.invoke(meta_workflow_app, ["cleanup", "--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_confirm_no_cancels(self, runner):
        old = _result(timestamp="2020-01-01T00:00:00")
        with (
            patch(f"{MOD}.list_execution_results", return_value=["r1"]),
            patch(f"{MOD}.load_execution_result", return_value=old),
        ):
            result = runner.invoke(meta_workflow_app, ["cleanup"], input="n\n")
        assert "Cancelled" in result.output

    def test_confirm_yes_deletes(self, runner, tmp_path, monkeypatch):
        old = _result(timestamp="2020-01-01T00:00:00")
        monkeypatch.setattr(f"{MOD}.Path.home", lambda: tmp_path)
        run_dir = tmp_path / ".attune" / "meta_workflows" / "executions" / "r1"
        run_dir.mkdir(parents=True)
        with (
            patch(f"{MOD}.list_execution_results", return_value=["r1"]),
            patch(f"{MOD}.load_execution_result", return_value=old),
        ):
            result = runner.invoke(meta_workflow_app, ["cleanup"], input="y\n")
        assert result.exit_code == 0
        assert "Deleted 1 execution" in result.output
        assert not run_dir.exists()

    def test_load_failure_warns(self, runner):
        with (
            patch(f"{MOD}.list_execution_results", return_value=["r1"]),
            patch(f"{MOD}.load_execution_result", side_effect=RuntimeError("corrupt")),
        ):
            result = runner.invoke(meta_workflow_app, ["cleanup"])
        # Load failed -> nothing collected -> nothing-old message.
        assert "No executions older than" in result.output

    def test_error_exits_one(self, runner):
        with patch(f"{MOD}.list_execution_results", side_effect=RuntimeError("io")):
            result = runner.invoke(meta_workflow_app, ["cleanup"])
        assert result.exit_code == 1
        assert "Error:" in result.output
