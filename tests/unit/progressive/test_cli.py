"""Unit tests for progressive workflow CLI commands.

Tests cover:
- List command
- Show command (text and JSON output)
- Analytics command (text and JSON output)
- Cleanup command (normal and dry-run)
- Argument parsing
- Main entry point
"""

import argparse
import json
from datetime import datetime, timedelta
from unittest.mock import patch

from attune.workflows.progressive.cli import (
    cmd_analytics,
    cmd_cleanup,
    cmd_list_results,
    cmd_show_report,
    create_parser,
    main,
)


class TestCmdListResults:
    """Test list command."""

    def test_list_no_results(self, tmp_path, capsys):
        """Test list with no results."""
        storage_path = tmp_path / "progressive_runs"

        args = argparse.Namespace(storage_path=str(storage_path))
        exit_code = cmd_list_results(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "No results found" in captured.out

    def test_list_with_results(self, tmp_path, capsys):
        """Test list with multiple results."""
        storage_path = tmp_path / "progressive_runs"

        # Create sample results
        for i in range(3):
            task_dir = storage_path / f"task-{i}"
            task_dir.mkdir(parents=True)

            summary = {
                "task_id": f"task-{i}",
                "workflow": "test-gen",
                "timestamp": datetime.now().isoformat(),
                "total_cost": (i + 1) * 0.5,
                "cost_savings_percent": 30.0,
                "success": i < 2,  # First 2 succeed
            }

            (task_dir / "summary.json").write_text(json.dumps(summary))

        args = argparse.Namespace(storage_path=str(storage_path))
        exit_code = cmd_list_results(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Found 3 progressive workflow results" in captured.out
        assert "task-0" in captured.out
        assert "task-1" in captured.out
        assert "task-2" in captured.out
        assert "test-gen" in captured.out
        assert "✅" in captured.out  # Success icon
        assert "❌" in captured.out  # Failure icon

    def test_list_with_default_storage_path(self, capsys):
        """Test list uses default storage path when not specified."""
        args = argparse.Namespace(storage_path=None)
        exit_code = cmd_list_results(args)

        # Should use default path and handle gracefully
        assert exit_code == 0


class TestCmdShowReport:
    """Test show command."""

    def test_show_existing_task(self, tmp_path, capsys):
        """Test showing report for existing task."""
        storage_path = tmp_path / "progressive_runs"
        task_dir = storage_path / "test-task"
        task_dir.mkdir(parents=True)

        # Create sample result
        summary = {"task_id": "test-task", "workflow": "test-gen"}
        (task_dir / "summary.json").write_text(json.dumps(summary))

        tier_data = {"tier": "cheap", "model": "gpt-4o-mini"}
        (task_dir / "tier_0_cheap.json").write_text(json.dumps(tier_data))

        report_text = "Sample Progressive Report"
        (task_dir / "report.txt").write_text(report_text)

        args = argparse.Namespace(task_id="test-task", storage_path=str(storage_path), json=False)
        exit_code = cmd_show_report(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Sample Progressive Report" in captured.out

    def test_show_with_json_output(self, tmp_path, capsys):
        """Test showing report in JSON format."""
        storage_path = tmp_path / "progressive_runs"
        task_dir = storage_path / "test-task"
        task_dir.mkdir(parents=True)

        # Create sample result
        summary = {"task_id": "test-task", "workflow": "test-gen"}
        (task_dir / "summary.json").write_text(json.dumps(summary))
        (task_dir / "report.txt").write_text("report")

        args = argparse.Namespace(task_id="test-task", storage_path=str(storage_path), json=True)
        exit_code = cmd_show_report(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        # Should be valid JSON
        output_data = json.loads(captured.out)
        assert output_data["summary"]["task_id"] == "test-task"

    def test_show_nonexistent_task(self, tmp_path, capsys):
        """Test showing report for nonexistent task."""
        storage_path = tmp_path / "progressive_runs"
        storage_path.mkdir()

        args = argparse.Namespace(
            task_id="nonexistent-task",
            storage_path=str(storage_path),
            json=False,
        )
        exit_code = cmd_show_report(args)

        assert exit_code == 1  # Error exit code

        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_show_missing_report(self, tmp_path, capsys):
        """Test showing task with missing report.txt."""
        storage_path = tmp_path / "progressive_runs"
        task_dir = storage_path / "test-task"
        task_dir.mkdir(parents=True)

        # Create summary but no report.txt
        summary = {"task_id": "test-task", "workflow": "test-gen"}
        (task_dir / "summary.json").write_text(json.dumps(summary))

        args = argparse.Namespace(task_id="test-task", storage_path=str(storage_path), json=False)
        exit_code = cmd_show_report(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "No report found" in captured.out


class TestCmdAnalytics:
    """Test analytics command."""

    def test_analytics_no_results(self, tmp_path, capsys):
        """Test analytics with no results."""
        storage_path = tmp_path / "progressive_runs"

        args = argparse.Namespace(storage_path=str(storage_path), json=False)
        exit_code = cmd_analytics(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "No results found" in captured.out

    def test_analytics_with_results(self, tmp_path, capsys):
        """Test analytics with results."""
        storage_path = tmp_path / "progressive_runs"

        # Create sample results
        for i in range(2):
            task_dir = storage_path / f"task-{i}"
            task_dir.mkdir(parents=True)

            summary = {
                "task_id": f"task-{i}",
                "workflow": "test-gen",
                "timestamp": datetime.now().isoformat(),
                "total_cost": 1.0,
                "cost_savings": 0.5,
                "cost_savings_percent": 50.0,
                "success": True,
                "tier_count": 2,
                "final_cqs": 85.0,
            }

            (task_dir / "summary.json").write_text(json.dumps(summary))

        args = argparse.Namespace(storage_path=str(storage_path), json=False)
        exit_code = cmd_analytics(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "PROGRESSIVE ESCALATION ANALYTICS" in captured.out
        assert "Total Runs: 2" in captured.out

    def test_analytics_json_output(self, tmp_path, capsys):
        """Test analytics with JSON output."""
        storage_path = tmp_path / "progressive_runs"

        # Create sample result
        task_dir = storage_path / "task-1"
        task_dir.mkdir(parents=True)

        summary = {
            "task_id": "task-1",
            "workflow": "test-gen",
            "timestamp": datetime.now().isoformat(),
            "total_cost": 1.0,
            "cost_savings": 0.5,
            "success": True,
            "tier_count": 1,
            "final_cqs": 85.0,
        }

        (task_dir / "summary.json").write_text(json.dumps(summary))

        args = argparse.Namespace(storage_path=str(storage_path), json=True)
        exit_code = cmd_analytics(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        # Should be valid JSON
        output_data = json.loads(captured.out)
        assert output_data["total_runs"] == 1
        assert output_data["total_cost"] == 1.0


class TestCmdCleanup:
    """Test cleanup command."""

    def test_cleanup_removes_old_results(self, tmp_path, capsys):
        """Test cleanup removes old results."""
        storage_path = tmp_path / "progressive_runs"

        # Create old result
        old_dir = storage_path / "old-task"
        old_dir.mkdir(parents=True)
        old_timestamp = datetime.now() - timedelta(days=40)
        old_summary = {
            "task_id": "old-task",
            "timestamp": old_timestamp.isoformat(),
        }
        (old_dir / "summary.json").write_text(json.dumps(old_summary))

        # Create recent result
        recent_dir = storage_path / "recent-task"
        recent_dir.mkdir(parents=True)
        recent_timestamp = datetime.now() - timedelta(days=10)
        recent_summary = {
            "task_id": "recent-task",
            "timestamp": recent_timestamp.isoformat(),
        }
        (recent_dir / "summary.json").write_text(json.dumps(recent_summary))

        args = argparse.Namespace(storage_path=str(storage_path), retention_days=30, dry_run=False)
        exit_code = cmd_cleanup(args)

        assert exit_code == 0
        assert not old_dir.exists()
        assert recent_dir.exists()

        captured = capsys.readouterr()
        assert "Cleanup complete" in captured.out
        assert "Deleted: 1" in captured.out
        assert "Retained: 1" in captured.out

    def test_cleanup_dry_run(self, tmp_path, capsys):
        """Test cleanup with dry run mode."""
        storage_path = tmp_path / "progressive_runs"

        # Create old result
        old_dir = storage_path / "old-task"
        old_dir.mkdir(parents=True)
        old_timestamp = datetime.now() - timedelta(days=40)
        old_summary = {
            "task_id": "old-task",
            "timestamp": old_timestamp.isoformat(),
        }
        (old_dir / "summary.json").write_text(json.dumps(old_summary))

        args = argparse.Namespace(storage_path=str(storage_path), retention_days=30, dry_run=True)
        exit_code = cmd_cleanup(args)

        assert exit_code == 0
        assert old_dir.exists()  # Not deleted in dry run

        captured = capsys.readouterr()
        assert "Dry run mode" in captured.out
        assert "Would delete: 1" in captured.out


class TestCreateParser:
    """Test argument parser creation."""

    def test_parser_list_command(self):
        """Test parsing list command."""
        parser = create_parser()
        args = parser.parse_args(["list"])

        assert args.command == "list"
        assert hasattr(args, "func")

    def test_parser_show_command(self):
        """Test parsing show command."""
        parser = create_parser()
        args = parser.parse_args(["show", "test-task-id"])

        assert args.command == "show"
        assert args.task_id == "test-task-id"
        assert args.json is False

    def test_parser_show_with_json(self):
        """Test parsing show command with JSON flag."""
        parser = create_parser()
        args = parser.parse_args(["show", "test-task-id", "--json"])

        assert args.task_id == "test-task-id"
        assert args.json is True

    def test_parser_analytics_command(self):
        """Test parsing analytics command."""
        parser = create_parser()
        args = parser.parse_args(["analytics"])

        assert args.command == "analytics"
        assert args.json is False

    def test_parser_analytics_with_json(self):
        """Test parsing analytics command with JSON flag."""
        parser = create_parser()
        args = parser.parse_args(["analytics", "--json"])

        assert args.json is True

    def test_parser_cleanup_command(self):
        """Test parsing cleanup command."""
        parser = create_parser()
        args = parser.parse_args(["cleanup"])

        assert args.command == "cleanup"
        assert args.retention_days == 30  # Default
        assert args.dry_run is False

    def test_parser_cleanup_with_options(self):
        """Test parsing cleanup command with options."""
        parser = create_parser()
        args = parser.parse_args(["cleanup", "--retention-days", "60", "--dry-run"])

        assert args.retention_days == 60
        assert args.dry_run is True

    def test_parser_custom_storage_path(self):
        """Test parsing with custom storage path."""
        parser = create_parser()
        args = parser.parse_args(["--storage-path", "/custom/path", "list"])

        assert args.storage_path == "/custom/path"


class TestMain:
    """Test main entry point."""

    def test_main_list_command(self, tmp_path, capsys):
        """Test main with list command."""
        storage_path = tmp_path / "progressive_runs"

        exit_code = main(["--storage-path", str(storage_path), "list"])

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "No results found" in captured.out

    def test_main_no_command(self, capsys):
        """Test main with no command shows help."""
        exit_code = main([])

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "usage:" in captured.out or "Manage progressive tier escalation" in captured.out

    def test_main_with_default_argv(self, capsys):
        """Test main uses sys.argv when argv is None."""
        with patch("sys.argv", ["prog", "list"]):
            exit_code = main(None)

        assert exit_code == 0
