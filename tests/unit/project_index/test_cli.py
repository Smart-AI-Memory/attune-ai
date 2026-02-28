"""Tests for Project Index CLI

Tests comprehensive CLI functionality including:
- Main entry point with all subcommands
- refresh, summary, report, query, file commands
- JSON and text output formats
- Error handling for missing index

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.project_index.cli import (
    cmd_file,
    cmd_query,
    cmd_refresh,
    cmd_report,
    cmd_summary,
    main,
)
from attune.project_index.models import (
    FileCategory,
    FileRecord,
    ProjectSummary,
    TestRequirement,
)

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def sample_summary():
    """Create a sample project summary."""
    return ProjectSummary(
        total_files=100,
        source_files=60,
        test_files=35,
        config_files=3,
        doc_files=2,
        files_requiring_tests=50,
        files_with_tests=40,
        files_without_tests=10,
        test_coverage_avg=78.5,
        total_test_count=250,
        stale_file_count=5,
        avg_staleness_days=3.2,
        most_stale_files=["src/old_module.py", "src/legacy.py"],
        total_lines_of_code=5000,
        total_lines_of_test=3500,
        test_to_code_ratio=0.7,
        avg_complexity=2.5,
        files_with_docstrings_pct=85.0,
        files_with_type_hints_pct=90.0,
        total_lint_issues=12,
        high_impact_files=["src/core.py", "src/api.py"],
        critical_untested_files=["src/critical.py"],
        files_needing_attention=8,
        top_attention_files=["src/needs_work.py"],
    )


@pytest.fixture
def sample_file_record():
    """Create a sample file record."""
    return FileRecord(
        path="src/module.py",
        name="module.py",
        category=FileCategory.SOURCE,
        language="python",
        test_requirement=TestRequirement.REQUIRED,
        test_file_path="tests/test_module.py",
        tests_exist=True,
        test_count=5,
        coverage_percent=85.5,
        lines_of_code=150,
        complexity_score=3.5,
        has_docstrings=True,
        has_type_hints=True,
        import_count=10,
        imported_by_count=3,
        impact_score=6.5,
        needs_attention=False,
        attention_reasons=[],
    )


@pytest.fixture
def sample_file_record_stale():
    """Create a stale file record."""
    return FileRecord(
        path="src/stale_module.py",
        name="stale_module.py",
        category=FileCategory.SOURCE,
        language="python",
        tests_exist=True,
        is_stale=True,
        staleness_days=15,
        coverage_percent=60.0,
        impact_score=4.0,
        needs_attention=True,
        attention_reasons=["Stale tests", "Low coverage"],
    )


@pytest.fixture
def sample_file_record_no_tests():
    """Create a file record with no tests."""
    return FileRecord(
        path="src/untested.py",
        name="untested.py",
        category=FileCategory.SOURCE,
        language="python",
        tests_exist=False,
        coverage_percent=0.0,
        impact_score=8.0,
        needs_attention=True,
        attention_reasons=["No tests"],
    )


@pytest.fixture
def mock_index(
    sample_summary,
    sample_file_record,
    sample_file_record_stale,
    sample_file_record_no_tests,
):
    """Create a mock ProjectIndex."""
    index = MagicMock()
    index.project_root = Path("/test/project")
    index._index_path = Path("/test/project/.attune/project_index.json")
    index.load.return_value = True
    index.get_summary.return_value = sample_summary
    index.get_all_files.return_value = [
        sample_file_record,
        sample_file_record_stale,
        sample_file_record_no_tests,
    ]
    index.get_files_needing_tests.return_value = [sample_file_record_no_tests]
    index.get_stale_files.return_value = [sample_file_record_stale]
    index.get_high_impact_files.return_value = [sample_file_record]
    index.get_files_needing_attention.return_value = [
        sample_file_record_stale,
        sample_file_record_no_tests,
    ]
    index.get_file.return_value = sample_file_record
    return index


# =========================================================================
# Test main() entry point
# =========================================================================


class TestMain:
    """Tests for main CLI entry point."""

    def test_main_no_command_prints_help(self, capsys, monkeypatch):
        """Test that main prints help when no command given."""
        monkeypatch.setattr("sys.argv", ["project_index_cli"])

        result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "Project Index" in captured.out

    def test_main_refresh_command(self, monkeypatch, tmp_path):
        """Test main with refresh command."""
        monkeypatch.setattr(
            "sys.argv",
            ["project_index_cli", "--project", str(tmp_path), "refresh"],
        )

        with patch("attune.project_index.cli.ProjectIndex") as mock_cls:
            mock_index = MagicMock()
            mock_index.project_root = tmp_path
            mock_index._index_path = tmp_path / ".empathy" / "project_index.json"
            mock_index.get_summary.return_value = ProjectSummary(
                total_files=10,
                source_files=5,
                test_files=3,
            )
            mock_cls.return_value = mock_index

            result = main()

            assert result == 0
            mock_index.refresh.assert_called_once()

    def test_main_summary_command(self, monkeypatch, tmp_path, sample_summary):
        """Test main with summary command."""
        monkeypatch.setattr(
            "sys.argv",
            ["project_index_cli", "--project", str(tmp_path), "summary"],
        )

        with patch("attune.project_index.cli.ProjectIndex") as mock_cls:
            mock_index = MagicMock()
            mock_index.load.return_value = True
            mock_index.get_summary.return_value = sample_summary
            mock_cls.return_value = mock_index

            result = main()

            assert result == 0

    def test_main_report_command(self, monkeypatch, tmp_path, sample_summary, sample_file_record):
        """Test main with report command."""
        monkeypatch.setattr(
            "sys.argv",
            ["project_index_cli", "--project", str(tmp_path), "report", "health"],
        )

        with (
            patch("attune.project_index.cli.ProjectIndex") as mock_cls,
            patch("attune.project_index.cli.ReportGenerator") as mock_gen_cls,
        ):
            mock_index = MagicMock()
            mock_index.load.return_value = True
            mock_index.get_summary.return_value = sample_summary
            mock_index.get_all_files.return_value = [sample_file_record]
            mock_cls.return_value = mock_index

            mock_gen = MagicMock()
            mock_gen.to_markdown.return_value = "# Health Report\n"
            mock_gen_cls.return_value = mock_gen

            result = main()

            assert result == 0

    def test_main_query_command(self, monkeypatch, tmp_path, mock_index):
        """Test main with query command."""
        monkeypatch.setattr(
            "sys.argv",
            ["project_index_cli", "--project", str(tmp_path), "query", "needing_tests"],
        )

        with patch("attune.project_index.cli.ProjectIndex") as mock_cls:
            mock_cls.return_value = mock_index

            result = main()

            assert result == 0

    def test_main_file_command(self, monkeypatch, tmp_path, mock_index):
        """Test main with file command."""
        monkeypatch.setattr(
            "sys.argv",
            ["project_index_cli", "--project", str(tmp_path), "file", "src/module.py"],
        )

        with patch("attune.project_index.cli.ProjectIndex") as mock_cls:
            mock_cls.return_value = mock_index

            result = main()

            assert result == 0

    def test_main_json_flag(self, monkeypatch, tmp_path, mock_index, capsys):
        """Test main with --json flag."""
        monkeypatch.setattr(
            "sys.argv",
            ["project_index_cli", "--project", str(tmp_path), "--json", "summary"],
        )

        with patch("attune.project_index.cli.ProjectIndex") as mock_cls:
            mock_cls.return_value = mock_index

            result = main()

            assert result == 0
            captured = capsys.readouterr()
            # Should output valid JSON
            data = json.loads(captured.out)
            assert "total_files" in data


# =========================================================================
# Test cmd_refresh
# =========================================================================


class TestCmdRefresh:
    """Tests for refresh command."""

    def test_refresh_success(self, capsys):
        """Test successful refresh."""
        mock_index = MagicMock()
        mock_index.project_root = Path("/test/project")
        mock_index._index_path = Path("/test/project/.attune/project_index.json")
        mock_index.get_summary.return_value = ProjectSummary(
            total_files=50,
            source_files=30,
            test_files=15,
            files_without_tests=5,
            files_needing_attention=3,
        )

        args = argparse.Namespace(force=False)

        result = cmd_refresh(mock_index, args)

        assert result == 0
        mock_index.refresh.assert_called_once()

        captured = capsys.readouterr()
        assert "Refreshing index" in captured.out
        assert "Index refreshed successfully" in captured.out
        assert "Files indexed: 50" in captured.out
        assert "Source files: 30" in captured.out
        assert "Test files: 15" in captured.out


# =========================================================================
# Test cmd_summary
# =========================================================================


class TestCmdSummary:
    """Tests for summary command."""

    def test_summary_no_index(self, capsys):
        """Test summary when no index exists."""
        mock_index = MagicMock()
        mock_index.load.return_value = False

        args = argparse.Namespace(json=False)

        result = cmd_summary(mock_index, args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No index found" in captured.out

    def test_summary_text_output(self, capsys, sample_summary):
        """Test summary with text output."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = sample_summary

        args = argparse.Namespace(json=False)

        result = cmd_summary(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "PROJECT INDEX SUMMARY" in captured.out
        assert "Total files:     100" in captured.out
        assert "Source files:    60" in captured.out
        assert "Test files:      35" in captured.out
        assert "TEST HEALTH" in captured.out
        assert "ATTENTION NEEDED" in captured.out
        assert "CRITICAL UNTESTED FILES" in captured.out

    def test_summary_json_output(self, capsys, sample_summary):
        """Test summary with JSON output."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = sample_summary

        args = argparse.Namespace(json=True)

        result = cmd_summary(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total_files"] == 100
        assert data["source_files"] == 60
        assert data["test_coverage_avg"] == 78.5

    def test_summary_no_critical_files(self, capsys):
        """Test summary when no critical untested files."""
        summary = ProjectSummary(
            total_files=10,
            source_files=5,
            test_files=5,
            critical_untested_files=[],  # Empty
        )

        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = summary

        args = argparse.Namespace(json=False)

        result = cmd_summary(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        # Should NOT show critical untested section when empty
        assert "CRITICAL UNTESTED FILES" not in captured.out


# =========================================================================
# Test cmd_report
# =========================================================================


class TestCmdReport:
    """Tests for report command."""

    def test_report_no_index(self, capsys):
        """Test report when no index exists."""
        mock_index = MagicMock()
        mock_index.load.return_value = False

        args = argparse.Namespace(report_type="health", markdown=False, json=False)

        result = cmd_report(mock_index, args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No index found" in captured.out

    def test_report_health_markdown(self, capsys, sample_summary, sample_file_record):
        """Test health report in markdown format."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = sample_summary
        mock_index.get_all_files.return_value = [sample_file_record]

        args = argparse.Namespace(report_type="health", markdown=True, json=False)

        with patch("attune.project_index.cli.ReportGenerator") as mock_gen_cls:
            mock_gen = MagicMock()
            mock_gen.to_markdown.return_value = "# Health Report\n\nScore: A"
            mock_gen_cls.return_value = mock_gen

            result = cmd_report(mock_index, args)

            assert result == 0
            mock_gen.to_markdown.assert_called_once_with("health")
            captured = capsys.readouterr()
            assert "# Health Report" in captured.out

    def test_report_health_json(self, capsys, sample_summary, sample_file_record):
        """Test health report in JSON format."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = sample_summary
        mock_index.get_all_files.return_value = [sample_file_record]

        args = argparse.Namespace(report_type="health", markdown=False, json=True)

        with patch("attune.project_index.cli.ReportGenerator") as mock_gen_cls:
            mock_gen = MagicMock()
            mock_gen.health_report.return_value = {"score": "A", "health": 95}
            mock_gen_cls.return_value = mock_gen

            result = cmd_report(mock_index, args)

            assert result == 0
            mock_gen.health_report.assert_called_once()
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["score"] == "A"

    def test_report_test_gap_json(self, capsys, sample_summary, sample_file_record):
        """Test test_gap report in JSON format."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = sample_summary
        mock_index.get_all_files.return_value = [sample_file_record]

        args = argparse.Namespace(report_type="test_gap", markdown=False, json=True)

        with patch("attune.project_index.cli.ReportGenerator") as mock_gen_cls:
            mock_gen = MagicMock()
            mock_gen.test_gap_report.return_value = {"files_without_tests": 5}
            mock_gen_cls.return_value = mock_gen

            result = cmd_report(mock_index, args)

            assert result == 0
            mock_gen.test_gap_report.assert_called_once()

    def test_report_staleness_json(self, capsys, sample_summary, sample_file_record):
        """Test staleness report in JSON format."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = sample_summary
        mock_index.get_all_files.return_value = [sample_file_record]

        args = argparse.Namespace(report_type="staleness", markdown=False, json=True)

        with patch("attune.project_index.cli.ReportGenerator") as mock_gen_cls:
            mock_gen = MagicMock()
            mock_gen.staleness_report.return_value = {"stale_files": 3}
            mock_gen_cls.return_value = mock_gen

            result = cmd_report(mock_index, args)

            assert result == 0
            mock_gen.staleness_report.assert_called_once()

    def test_report_coverage_json(self, capsys, sample_summary, sample_file_record):
        """Test coverage report in JSON format."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = sample_summary
        mock_index.get_all_files.return_value = [sample_file_record]

        args = argparse.Namespace(report_type="coverage", markdown=False, json=True)

        with patch("attune.project_index.cli.ReportGenerator") as mock_gen_cls:
            mock_gen = MagicMock()
            mock_gen.coverage_report.return_value = {"avg_coverage": 78.5}
            mock_gen_cls.return_value = mock_gen

            result = cmd_report(mock_index, args)

            assert result == 0
            mock_gen.coverage_report.assert_called_once()

    def test_report_sprint_json(self, capsys, sample_summary, sample_file_record):
        """Test sprint planning report in JSON format."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = sample_summary
        mock_index.get_all_files.return_value = [sample_file_record]

        args = argparse.Namespace(report_type="sprint", markdown=False, json=True)

        with patch("attune.project_index.cli.ReportGenerator") as mock_gen_cls:
            mock_gen = MagicMock()
            mock_gen.sprint_planning_report.return_value = {"priority_files": []}
            mock_gen_cls.return_value = mock_gen

            result = cmd_report(mock_index, args)

            assert result == 0
            mock_gen.sprint_planning_report.assert_called_once()

    def test_report_default_markdown(self, capsys, sample_summary, sample_file_record):
        """Test report defaults to markdown output."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_summary.return_value = sample_summary
        mock_index.get_all_files.return_value = [sample_file_record]

        # Neither markdown nor json specified
        args = argparse.Namespace(report_type="health", markdown=False, json=False)

        with patch("attune.project_index.cli.ReportGenerator") as mock_gen_cls:
            mock_gen = MagicMock()
            mock_gen.to_markdown.return_value = "# Report"
            mock_gen_cls.return_value = mock_gen

            result = cmd_report(mock_index, args)

            assert result == 0
            mock_gen.to_markdown.assert_called_once_with("health")


# =========================================================================
# Test cmd_query
# =========================================================================


class TestCmdQuery:
    """Tests for query command."""

    def test_query_no_index(self, capsys):
        """Test query when no index exists."""
        mock_index = MagicMock()
        mock_index.load.return_value = False

        args = argparse.Namespace(query_type="needing_tests", limit=20, json=False)

        result = cmd_query(mock_index, args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No index found" in captured.out

    def test_query_needing_tests(self, capsys, sample_file_record_no_tests):
        """Test query for files needing tests."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_files_needing_tests.return_value = [sample_file_record_no_tests]

        args = argparse.Namespace(query_type="needing_tests", limit=20, json=False)

        result = cmd_query(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "FILES NEEDING TESTS" in captured.out
        assert "src/untested.py" in captured.out
        assert "Has Tests: False" in captured.out

    def test_query_stale(self, capsys, sample_file_record_stale):
        """Test query for stale files."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_stale_files.return_value = [sample_file_record_stale]

        args = argparse.Namespace(query_type="stale", limit=20, json=False)

        result = cmd_query(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "STALE TEST FILES" in captured.out
        assert "src/stale_module.py" in captured.out
        assert "STALE: 15 days" in captured.out

    def test_query_high_impact(self, capsys, sample_file_record):
        """Test query for high impact files."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_high_impact_files.return_value = [sample_file_record]

        args = argparse.Namespace(query_type="high_impact", limit=20, json=False)

        result = cmd_query(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "HIGH IMPACT FILES" in captured.out
        assert "src/module.py" in captured.out
        assert "Impact Score: 6.5" in captured.out

    def test_query_attention(self, capsys, sample_file_record_stale, sample_file_record_no_tests):
        """Test query for files needing attention."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_files_needing_attention.return_value = [
            sample_file_record_stale,
            sample_file_record_no_tests,
        ]

        args = argparse.Namespace(query_type="attention", limit=20, json=False)

        result = cmd_query(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "FILES NEEDING ATTENTION" in captured.out
        assert "Attention:" in captured.out

    def test_query_all(self, capsys, sample_file_record, sample_file_record_stale):
        """Test query for all files."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_all_files.return_value = [sample_file_record, sample_file_record_stale]

        args = argparse.Namespace(query_type="all", limit=20, json=False)

        result = cmd_query(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "ALL FILES" in captured.out
        assert "2 results" in captured.out

    def test_query_limit(self, capsys, sample_file_record):
        """Test query respects limit parameter."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        # Return 10 files
        files = [sample_file_record] * 10
        mock_index.get_all_files.return_value = files

        args = argparse.Namespace(query_type="all", limit=3, json=False)

        result = cmd_query(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        # Should show only 3 results due to limit
        assert "3 results" in captured.out

    def test_query_json_output(self, capsys, sample_file_record):
        """Test query with JSON output."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_high_impact_files.return_value = [sample_file_record]

        args = argparse.Namespace(query_type="high_impact", limit=20, json=True)

        result = cmd_query(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["path"] == "src/module.py"

    def test_query_unknown_type(self, capsys):
        """Test query with unknown query type returns empty results."""
        mock_index = MagicMock()
        mock_index.load.return_value = True

        # Simulate an unknown query type that would fall to else branch
        args = argparse.Namespace(query_type="unknown", limit=20, json=False)

        result = cmd_query(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "RESULTS (0 results)" in captured.out


# =========================================================================
# Test cmd_file
# =========================================================================


class TestCmdFile:
    """Tests for file command."""

    def test_file_no_index(self, capsys):
        """Test file command when no index exists."""
        mock_index = MagicMock()
        mock_index.load.return_value = False

        args = argparse.Namespace(path="src/module.py", json=False)

        result = cmd_file(mock_index, args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No index found" in captured.out

    def test_file_not_found(self, capsys):
        """Test file command when file not in index."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_file.return_value = None

        args = argparse.Namespace(path="src/nonexistent.py", json=False)

        result = cmd_file(mock_index, args)

        assert result == 1
        captured = capsys.readouterr()
        assert "File not found in index" in captured.out

    def test_file_text_output(self, capsys, sample_file_record):
        """Test file command with text output."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_file.return_value = sample_file_record

        args = argparse.Namespace(path="src/module.py", json=False)

        result = cmd_file(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "FILE: src/module.py" in captured.out
        assert "Name:         module.py" in captured.out
        assert "Category:     source" in captured.out
        assert "Language:     python" in captured.out
        assert "TESTING" in captured.out
        assert "Requires Tests: required" in captured.out
        assert "Has Tests:      True" in captured.out
        assert "Coverage:       85.5%" in captured.out
        assert "METRICS" in captured.out
        assert "Lines of Code:  150" in captured.out
        assert "DEPENDENCIES" in captured.out
        assert "Imports:        10 modules" in captured.out

    def test_file_json_output(self, capsys, sample_file_record):
        """Test file command with JSON output."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_file.return_value = sample_file_record

        args = argparse.Namespace(path="src/module.py", json=True)

        result = cmd_file(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["path"] == "src/module.py"
        assert data["name"] == "module.py"
        assert data["category"] == "source"
        assert data["coverage_percent"] == 85.5

    def test_file_stale(self, capsys, sample_file_record_stale):
        """Test file command shows staleness."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_file.return_value = sample_file_record_stale

        args = argparse.Namespace(path="src/stale_module.py", json=False)

        result = cmd_file(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "STALE:           15 days" in captured.out
        assert "Reasons:" in captured.out

    def test_file_needs_attention(self, capsys, sample_file_record_no_tests):
        """Test file command shows attention reasons."""
        mock_index = MagicMock()
        mock_index.load.return_value = True
        mock_index.get_file.return_value = sample_file_record_no_tests

        args = argparse.Namespace(path="src/untested.py", json=False)

        result = cmd_file(mock_index, args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Needs Attention: True" in captured.out
        assert "Reasons:" in captured.out
        assert "No tests" in captured.out


# =========================================================================
# Integration tests
# =========================================================================


class TestCLIIntegration:
    """Integration tests for CLI."""

    def test_end_to_end_workflow(self, tmp_path, monkeypatch, capsys):
        """Test complete workflow: refresh -> summary -> query."""
        # Create mock project structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module.py").write_text("def foo(): pass")

        with patch("attune.project_index.cli.ProjectIndex") as mock_cls:
            mock_index = MagicMock()
            mock_index.project_root = tmp_path
            mock_index._index_path = tmp_path / ".empathy" / "project_index.json"
            mock_index.load.return_value = True
            mock_index.get_summary.return_value = ProjectSummary(
                total_files=10,
                source_files=5,
                test_files=3,
            )
            mock_index.get_all_files.return_value = []
            mock_cls.return_value = mock_index

            # Step 1: Refresh
            monkeypatch.setattr("sys.argv", ["cli", "--project", str(tmp_path), "refresh"])
            result = main()
            assert result == 0

            # Step 2: Summary
            monkeypatch.setattr("sys.argv", ["cli", "--project", str(tmp_path), "summary"])
            result = main()
            assert result == 0

            # Step 3: Query
            monkeypatch.setattr("sys.argv", ["cli", "--project", str(tmp_path), "query", "all"])
            result = main()
            assert result == 0

    def test_all_report_types(self, tmp_path, monkeypatch, sample_summary, sample_file_record):
        """Test all report types can be generated."""
        report_types = ["health", "test_gap", "staleness", "coverage", "sprint"]

        for report_type in report_types:
            with (
                patch("attune.project_index.cli.ProjectIndex") as mock_cls,
                patch("attune.project_index.cli.ReportGenerator") as mock_gen_cls,
            ):
                mock_index = MagicMock()
                mock_index.load.return_value = True
                mock_index.get_summary.return_value = sample_summary
                mock_index.get_all_files.return_value = [sample_file_record]
                mock_cls.return_value = mock_index

                mock_gen = MagicMock()
                mock_gen.to_markdown.return_value = f"# {report_type} Report"
                mock_gen.health_report.return_value = {}
                mock_gen.test_gap_report.return_value = {}
                mock_gen.staleness_report.return_value = {}
                mock_gen.coverage_report.return_value = {}
                mock_gen.sprint_planning_report.return_value = {}
                mock_gen_cls.return_value = mock_gen

                monkeypatch.setattr(
                    "sys.argv",
                    ["cli", "--project", str(tmp_path), "report", report_type],
                )
                result = main()
                assert result == 0, f"Report type {report_type} failed"

    def test_all_query_types(self, tmp_path, monkeypatch, mock_index):
        """Test all query types can be executed."""
        query_types = ["needing_tests", "stale", "high_impact", "attention", "all"]

        for query_type in query_types:
            with patch("attune.project_index.cli.ProjectIndex") as mock_cls:
                mock_cls.return_value = mock_index

                monkeypatch.setattr(
                    "sys.argv",
                    ["cli", "--project", str(tmp_path), "query", query_type],
                )
                result = main()
                assert result == 0, f"Query type {query_type} failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
