"""Tests for CLI cost commands.

Tests for `attune costs`, `attune costs today`, `attune costs export`,
and `attune costs reset` commands.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.cli_commands.cost_commands import cmd_costs
from attune.cli_minimal import create_parser, main

_CLI = "attune.cli_minimal"
_COST_CMDS = "attune.cli_commands.cost_commands"
_COST_TRACKER = "attune.cost_tracker.CostTracker"


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestCostsParser:
    """Tests that the costs command group parses correctly."""

    @pytest.fixture
    def parser(self):
        return create_parser()

    def test_costs_defaults(self, parser) -> None:
        """Attune costs parses with default values."""
        args = parser.parse_args(["costs"])
        assert args.command == "costs"
        assert args.days == 7
        assert args.json is False
        assert args.workflow is None

    def test_costs_days_flag(self, parser) -> None:
        """Attune costs --days 30 parses days."""
        args = parser.parse_args(["costs", "--days", "30"])
        assert args.days == 30

    def test_costs_json_flag(self, parser) -> None:
        """Attune costs --json parses json flag."""
        args = parser.parse_args(["costs", "--json"])
        assert args.json is True

    def test_costs_workflow_flag(self, parser) -> None:
        """Attune costs --workflow code-review parses workflow."""
        args = parser.parse_args(["costs", "--workflow", "code-review"])
        assert args.workflow == "code-review"

    def test_costs_short_flags(self, parser) -> None:
        """Attune costs -d 14 -w test parses short flags."""
        args = parser.parse_args(["costs", "-d", "14", "-w", "test"])
        assert args.days == 14
        assert args.workflow == "test"

    def test_costs_today(self, parser) -> None:
        """Attune costs today parses subcommand."""
        args = parser.parse_args(["costs", "today"])
        assert args.costs_command == "today"

    def test_costs_export(self, parser) -> None:
        """Attune costs export parses with required output."""
        args = parser.parse_args(["costs", "export", "-o", "out.json"])
        assert args.costs_command == "export"
        assert args.output == "out.json"

    def test_costs_export_csv(self, parser) -> None:
        """Attune costs export -f csv parses format."""
        args = parser.parse_args(["costs", "export", "-o", "out.csv", "-f", "csv", "-d", "60"])
        assert args.format == "csv"
        assert args.days == 60

    def test_costs_reset_confirm(self, parser) -> None:
        """Attune costs reset --confirm parses flag."""
        args = parser.parse_args(["costs", "reset", "--confirm"])
        assert args.costs_command == "reset"
        assert args.confirm is True

    def test_costs_reset_no_confirm(self, parser) -> None:
        """Attune costs reset without --confirm defaults to False."""
        args = parser.parse_args(["costs", "reset"])
        assert args.confirm is False


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------


class TestMainCostsRouting:
    """Tests that main() routes costs subcommands correctly."""

    @patch(f"{_CLI}.cmd_costs", return_value=0)
    def test_costs_default(self, mock_fn: MagicMock) -> None:
        """Attune costs dispatches to cmd_costs."""
        assert main(["costs"]) == 0
        mock_fn.assert_called_once()

    @patch("attune.cost_tracker.CostTracker")
    def test_costs_today(self, mock_tracker_cls: MagicMock) -> None:
        """Attune costs today dispatches to cmd_costs_today."""
        tracker = MagicMock()
        tracker.get_today.return_value = {
            "requests": 5,
            "actual_cost": 0.0044,
            "baseline_cost": 0.2625,
            "savings": 0.2581,
        }
        mock_tracker_cls.return_value = tracker
        assert main(["costs", "today"]) == 0
        tracker.get_today.assert_called_once()

    @patch("attune.cost_tracker.CostTracker")
    def test_costs_export(self, mock_tracker_cls: MagicMock, tmp_path) -> None:
        """Attune costs export dispatches to cmd_costs_export."""
        tracker = MagicMock()
        tracker.get_summary.return_value = {"total_cost": 0.0, "requests": 0}
        mock_tracker_cls.return_value = tracker
        out = tmp_path / "costs.json"
        assert main(["costs", "export", "-o", str(out)]) == 0

    def test_costs_reset(self) -> None:
        """Attune costs reset dispatches to cmd_costs_reset."""
        # cmd_costs_reset directly deletes files, no CostTracker needed
        assert main(["costs", "reset", "--confirm"]) == 0


# ---------------------------------------------------------------------------
# Handler tests - cmd_costs
# ---------------------------------------------------------------------------


_SAMPLE_SUMMARY = {
    "days": 7,
    "requests": 42,
    "input_tokens": 50000,
    "output_tokens": 25000,
    "actual_cost": 0.1234,
    "baseline_cost": 0.9876,
    "savings": 0.8642,
    "savings_percent": 87.5,
    "by_tier": {"cheap": 30, "capable": 10, "premium": 2},
    "by_task": {"workflow:code-review:analyze": 20, "workflow:test-gen:generate": 22},
}


class TestCmdCosts:
    """Tests for cmd_costs() handler."""

    @patch(_COST_TRACKER)
    def test_prints_report(self, MockTracker, capsys) -> None:
        """cmd_costs prints text report."""
        mock_tracker = MockTracker.return_value
        mock_tracker.get_report.return_value = "COST REPORT\nTotal: $0.12"

        args = Namespace(days=7, json=False, workflow=None)
        result = cmd_costs(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "COST REPORT" in captured.out
        mock_tracker.get_report.assert_called_once_with(7)

    @patch(_COST_TRACKER)
    def test_json_output(self, MockTracker, capsys) -> None:
        """cmd_costs --json prints valid JSON."""
        mock_tracker = MockTracker.return_value
        mock_tracker.get_summary.return_value = _SAMPLE_SUMMARY

        args = Namespace(days=7, json=True, workflow=None)
        result = cmd_costs(args)

        assert result == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["requests"] == 42
        assert parsed["savings_percent"] == 87.5

    @patch(_COST_TRACKER)
    def test_custom_days(self, MockTracker, capsys) -> None:
        """cmd_costs --days 30 passes days to get_report."""
        mock_tracker = MockTracker.return_value
        mock_tracker.get_report.return_value = "Report"

        args = Namespace(days=30, json=False, workflow=None)
        cmd_costs(args)

        mock_tracker.get_report.assert_called_once_with(30)

    @patch(_COST_TRACKER)
    def test_workflow_filter(self, MockTracker, capsys) -> None:
        """cmd_costs --workflow filters by task_type."""
        mock_tracker = MockTracker.return_value
        mock_tracker._load_requests = MagicMock()
        mock_tracker._buffer = []
        mock_tracker.data = {
            "requests": [
                {
                    "timestamp": "2099-01-01T00:00:00",
                    "task_type": "workflow:code-review:analyze",
                    "actual_cost": 0.05,
                    "baseline_cost": 0.50,
                    "savings": 0.45,
                },
                {
                    "timestamp": "2099-01-01T00:00:00",
                    "task_type": "workflow:test-gen:generate",
                    "actual_cost": 0.03,
                    "baseline_cost": 0.30,
                    "savings": 0.27,
                },
            ],
        }

        args = Namespace(days=365, json=False, workflow="code-review")
        result = cmd_costs(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "code-review" in captured.out
        assert "$0.0500" in captured.out

    @patch(_COST_TRACKER)
    def test_workflow_filter_json(self, MockTracker, capsys) -> None:
        """cmd_costs --workflow --json outputs filtered JSON."""
        mock_tracker = MockTracker.return_value
        mock_tracker._load_requests = MagicMock()
        mock_tracker._buffer = []
        mock_tracker.data = {
            "requests": [
                {
                    "timestamp": "2099-01-01T00:00:00",
                    "task_type": "workflow:code-review:analyze",
                    "actual_cost": 0.05,
                    "baseline_cost": 0.50,
                    "savings": 0.45,
                },
            ],
        }

        args = Namespace(days=365, json=True, workflow="code-review")
        result = cmd_costs(args)

        assert result == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["workflow"] == "code-review"
        assert parsed["requests"] == 1

    @patch(_COST_TRACKER)
    def test_oserror_returns_1(self, MockTracker, capsys) -> None:
        """cmd_costs returns 1 and prints an error when CostTracker raises OSError."""
        MockTracker.side_effect = OSError("disk read error")

        args = Namespace(days=7, json=False, workflow=None)
        result = cmd_costs(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error reading cost data" in captured.out
        assert "disk read error" in captured.out

    @patch(_COST_TRACKER)
    def test_non_oserror_returns_1(self, MockTracker, capsys) -> None:
        """Regression (library-review R5): corrupt tracker data returns 1.

        The docstring promises exit 1 on failure, but the handler used to
        catch OSError only — a record missing "timestamp" raised KeyError
        straight through to a traceback.
        """
        mock_tracker = MockTracker.return_value
        mock_tracker._load_requests = MagicMock()
        mock_tracker._buffer = []
        mock_tracker.data = {"requests": [{"task_type": "code-review"}]}

        args = Namespace(days=365, json=False, workflow="code-review")
        result = cmd_costs(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error generating cost report" in captured.out

    @patch(_COST_TRACKER)
    def test_json_dump_typeerror_returns_1(self, MockTracker, capsys) -> None:
        """Regression (library-review R5): unserializable summary returns 1."""
        mock_tracker = MockTracker.return_value
        mock_tracker.get_summary.return_value = {"bad": object()}

        args = Namespace(days=7, json=True, workflow=None)
        result = cmd_costs(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error generating cost report" in captured.out


# ---------------------------------------------------------------------------
# Handler tests - cmd_costs_today
# ---------------------------------------------------------------------------


class TestCmdCostsToday:
    """Tests for cmd_costs_today() handler."""

    @patch(_COST_TRACKER)
    def test_prints_today(self, MockTracker, capsys) -> None:
        """cmd_costs_today prints today's summary."""
        mock_tracker = MockTracker.return_value
        mock_tracker.get_today.return_value = {
            "requests": 5,
            "actual_cost": 0.0234,
            "baseline_cost": 0.1580,
            "savings": 0.1346,
        }

        from attune.cli_commands.cost_commands import cmd_costs_today

        args = Namespace()
        result = cmd_costs_today(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "5 requests" in captured.out
        assert "$0.0234" in captured.out
        assert "saved" in captured.out

    @patch(_COST_TRACKER)
    def test_zero_requests(self, MockTracker, capsys) -> None:
        """cmd_costs_today handles zero requests gracefully."""
        mock_tracker = MockTracker.return_value
        mock_tracker.get_today.return_value = {
            "requests": 0,
            "actual_cost": 0,
            "baseline_cost": 0,
            "savings": 0,
        }

        from attune.cli_commands.cost_commands import cmd_costs_today

        args = Namespace()
        result = cmd_costs_today(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "0 requests" in captured.out
        assert "0.0%" in captured.out

    @patch(_COST_TRACKER)
    def test_oserror_returns_1(self, MockTracker, capsys) -> None:
        """cmd_costs_today returns 1 and prints an error when CostTracker raises OSError."""
        MockTracker.side_effect = OSError("cannot read costs.json")

        from attune.cli_commands.cost_commands import cmd_costs_today

        args = Namespace()
        result = cmd_costs_today(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error reading cost data" in captured.out
        assert "cannot read costs.json" in captured.out

    @patch(_COST_TRACKER)
    def test_non_oserror_returns_1(self, MockTracker, capsys) -> None:
        """Regression (library-review R5): corrupt today-record returns 1.

        Non-numeric cost fields raise ValueError/TypeError in the format
        expression — previously an unhandled traceback.
        """
        mock_tracker = MockTracker.return_value
        mock_tracker.get_today.return_value = {
            "requests": 5,
            "actual_cost": "corrupt",
            "baseline_cost": 0.1,
            "savings": 0.05,
        }

        from attune.cli_commands.cost_commands import cmd_costs_today

        args = Namespace()
        result = cmd_costs_today(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error reading cost data" in captured.out


# ---------------------------------------------------------------------------
# Handler tests - cmd_costs_export
# ---------------------------------------------------------------------------


class TestCmdCostsExport:
    """Tests for cmd_costs_export() handler."""

    @patch(_COST_TRACKER)
    def test_export_json(self, MockTracker, tmp_path, capsys) -> None:
        """cmd_costs_export writes JSON file."""
        mock_tracker = MockTracker.return_value
        mock_tracker.get_summary.return_value = _SAMPLE_SUMMARY

        from attune.cli_commands.cost_commands import cmd_costs_export

        out_file = tmp_path / "costs.json"
        args = Namespace(output=str(out_file), format="json", days=30)
        result = cmd_costs_export(args)

        assert result == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["requests"] == 42
        captured = capsys.readouterr()
        assert "Exported to" in captured.out

    @patch(_COST_TRACKER)
    def test_export_csv(self, MockTracker, tmp_path, capsys) -> None:
        """cmd_costs_export writes CSV file."""
        mock_tracker = MockTracker.return_value
        mock_tracker.data = {
            "daily_totals": {
                "2099-01-01": {
                    "requests": 10,
                    "input_tokens": 5000,
                    "output_tokens": 2500,
                    "actual_cost": 0.05,
                    "baseline_cost": 0.50,
                    "savings": 0.45,
                },
                "2099-01-02": {
                    "requests": 8,
                    "input_tokens": 4000,
                    "output_tokens": 2000,
                    "actual_cost": 0.04,
                    "baseline_cost": 0.40,
                    "savings": 0.36,
                },
            },
        }

        from attune.cli_commands.cost_commands import cmd_costs_export

        out_file = tmp_path / "costs.csv"
        args = Namespace(output=str(out_file), format="csv", days=365)
        result = cmd_costs_export(args)

        assert result == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "date,requests,input_tokens" in content
        assert "2099-01-01" in content
        assert "2099-01-02" in content

    def test_export_rejects_system_path(self, capsys) -> None:
        """cmd_costs_export rejects system directory paths."""
        from attune.cli_commands.cost_commands import cmd_costs_export

        args = Namespace(output="/etc/costs.json", format="json", days=30)
        result = cmd_costs_export(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out

    def test_export_rejects_null_bytes(self, capsys) -> None:
        """cmd_costs_export rejects null bytes in path."""
        from attune.cli_commands.cost_commands import cmd_costs_export

        args = Namespace(output="costs\x00.json", format="json", days=30)
        result = cmd_costs_export(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.out

    @patch(_COST_TRACKER)
    def test_export_permission_error(self, MockTracker, tmp_path, capsys) -> None:
        """cmd_costs_export returns 1 and reports permission errors distinctly."""
        MockTracker.side_effect = PermissionError("Operation not permitted")

        from attune.cli_commands.cost_commands import cmd_costs_export

        out_file = tmp_path / "costs.json"
        args = Namespace(output=str(out_file), format="json", days=30)
        result = cmd_costs_export(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Permission denied" in captured.out
        assert "Operation not permitted" in captured.out
        assert not out_file.exists()

    @patch(_COST_TRACKER)
    def test_export_oserror(self, MockTracker, tmp_path, capsys) -> None:
        """cmd_costs_export returns 1 and reports generic OSErrors during export."""
        MockTracker.side_effect = OSError("disk full")

        from attune.cli_commands.cost_commands import cmd_costs_export

        out_file = tmp_path / "costs.json"
        args = Namespace(output=str(out_file), format="json", days=30)
        result = cmd_costs_export(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error exporting cost data" in captured.out
        assert "disk full" in captured.out

    @patch(_COST_TRACKER)
    def test_export_non_oserror_returns_1(self, MockTracker, tmp_path, capsys) -> None:
        """Regression (library-review R5): unserializable summary returns 1.

        json.dump of corrupt tracker data raises TypeError, not OSError —
        previously an unhandled traceback.
        """
        mock_tracker = MockTracker.return_value
        mock_tracker.get_summary.return_value = {"bad": object()}

        from attune.cli_commands.cost_commands import cmd_costs_export

        out_file = tmp_path / "costs.json"
        args = Namespace(output=str(out_file), format="json", days=30)
        result = cmd_costs_export(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error exporting cost data" in captured.out
        # Codex cross-review finding: serialization failure must not
        # leave a truncated/partial export file behind.
        assert not out_file.exists()


# ---------------------------------------------------------------------------
# Handler tests - cmd_costs_reset
# ---------------------------------------------------------------------------


class TestCmdCostsReset:
    """Tests for cmd_costs_reset() handler."""

    def test_reset_without_confirm(self, capsys) -> None:
        """cmd_costs_reset without --confirm prints warning."""
        from attune.cli_commands.cost_commands import cmd_costs_reset

        args = Namespace(confirm=False)
        result = cmd_costs_reset(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "delete all cost tracking data" in captured.out
        assert "--confirm" in captured.out

    def test_reset_with_confirm(self, tmp_path, capsys, monkeypatch) -> None:
        """cmd_costs_reset --confirm deletes cost files."""
        # Create fake cost files in tmp_path acting as .attune
        (tmp_path / "costs.json").write_text("{}")
        (tmp_path / "costs.jsonl").write_text("")
        (tmp_path / "costs_summary.json").write_text("{}")

        from attune.cli_commands import cost_commands

        # Patch Path inside the lazy import so it returns tmp_path
        original_path = Path

        def patched_path(p: str) -> Path:
            if p == ".attune":
                return tmp_path
            return original_path(p)

        monkeypatch.setattr(cost_commands, "Path", patched_path, raising=False)

        args = Namespace(confirm=True)
        result = cost_commands.cmd_costs_reset(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "cleared" in captured.out
        assert not (tmp_path / "costs.json").exists()
        assert not (tmp_path / "costs.jsonl").exists()
        assert not (tmp_path / "costs_summary.json").exists()

    def test_reset_no_files(self, tmp_path, capsys, monkeypatch) -> None:
        """cmd_costs_reset --confirm works when no cost files exist."""
        from attune.cli_commands import cost_commands

        original_path = Path

        def patched_path(p: str) -> Path:
            if p == ".attune":
                return tmp_path
            return original_path(p)

        monkeypatch.setattr(cost_commands, "Path", patched_path, raising=False)

        args = Namespace(confirm=True)
        result = cost_commands.cmd_costs_reset(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "0 file(s)" in captured.out

    def test_reset_delete_oserror(self, tmp_path, capsys, monkeypatch) -> None:
        """cmd_costs_reset returns 1 and reports the error when unlink() fails.

        Uses a real filesystem round trip rather than mocking unlink: making
        "costs.json" a directory means Path.exists() is True but
        Path.unlink() raises IsADirectoryError (a real OSError subclass),
        exercising the except OSError branch without any mocking.
        """
        (tmp_path / "costs.json").mkdir()

        from attune.cli_commands import cost_commands

        original_path = Path

        def patched_path(p: str) -> Path:
            if p == ".attune":
                return tmp_path
            return original_path(p)

        monkeypatch.setattr(cost_commands, "Path", patched_path, raising=False)

        args = Namespace(confirm=True)
        result = cost_commands.cmd_costs_reset(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error deleting" in captured.out
        assert str(tmp_path / "costs.json") in captured.out
