"""Tests for workflow_commands.py using real data and file I/O.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from datetime import datetime

from attune import workflow_commands


class TestLoadPatterns:
    """Test _load_patterns with real file I/O."""

    def test_load_patterns_from_existing_directory(self, tmp_path):
        """Test loading patterns from directory with real JSON files."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create real pattern files
        debugging_patterns = {
            "patterns": [
                {"id": "pattern1", "description": "Debug pattern 1"},
                {"id": "pattern2", "description": "Debug pattern 2"},
            ]
        }

        security_patterns = {"patterns": [{"id": "sec1", "description": "Security pattern 1"}]}

        # Write real JSON files
        (patterns_dir / "debugging.json").write_text(json.dumps(debugging_patterns))
        (patterns_dir / "security.json").write_text(json.dumps(security_patterns))

        # Load patterns
        result = workflow_commands._load_patterns(str(patterns_dir))

        # Verify loaded correctly
        assert "debugging" in result
        assert len(result["debugging"]) == 2
        assert result["debugging"][0]["id"] == "pattern1"

        assert "security" in result
        assert len(result["security"]) == 1
        assert result["security"][0]["id"] == "sec1"

    def test_load_patterns_from_nonexistent_directory(self, tmp_path):
        """Test loading patterns when directory doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"

        result = workflow_commands._load_patterns(str(nonexistent_dir))

        # Should return empty pattern structure
        assert isinstance(result, dict)
        assert "debugging" in result
        assert result["debugging"] == []
        assert "security" in result
        assert result["security"] == []

    def test_load_patterns_with_items_key(self, tmp_path):
        """Test loading patterns when JSON uses 'items' key instead of 'patterns'."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create pattern file with 'items' key
        tech_debt_data = {
            "items": [
                {"id": "debt1", "description": "Technical debt item 1"},
                {"id": "debt2", "description": "Technical debt item 2"},
            ]
        }

        (patterns_dir / "tech_debt.json").write_text(json.dumps(tech_debt_data))

        result = workflow_commands._load_patterns(str(patterns_dir))

        # Should load from 'items' key
        assert "tech_debt" in result
        assert len(result["tech_debt"]) == 2
        assert result["tech_debt"][0]["id"] == "debt1"

    def test_load_patterns_handles_invalid_json(self, tmp_path):
        """Test loading patterns with corrupted JSON file."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create invalid JSON file
        (patterns_dir / "debugging.json").write_text("{ invalid json }")

        result = workflow_commands._load_patterns(str(patterns_dir))

        # Should handle gracefully
        assert isinstance(result, dict)
        assert "debugging" in result
        # Should be empty due to JSON error
        assert result["debugging"] == []

    def test_load_patterns_handles_missing_files(self, tmp_path):
        """Test loading patterns when some pattern files are missing."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Only create debugging patterns
        debugging_data = {"patterns": [{"id": "d1"}]}
        (patterns_dir / "debugging.json").write_text(json.dumps(debugging_data))

        result = workflow_commands._load_patterns(str(patterns_dir))

        # Should have debugging but empty others
        assert len(result["debugging"]) == 1
        assert result["security"] == []
        assert result["tech_debt"] == []


class TestLoadStats:
    """Test _load_stats with real file I/O."""

    def test_load_stats_from_existing_file(self, tmp_path):
        """Test loading stats from existing stats.json file."""
        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()

        # Create real stats file
        stats_data = {
            "commands": {"morning": 5, "ship": 3},
            "last_session": "2025-01-14T10:00:00",
            "patterns_learned": 12,
        }

        (empathy_dir / "stats.json").write_text(json.dumps(stats_data))

        result = workflow_commands._load_stats(str(empathy_dir))

        # Verify loaded correctly
        assert result["commands"]["morning"] == 5
        assert result["commands"]["ship"] == 3
        assert result["patterns_learned"] == 12
        assert result["last_session"] == "2025-01-14T10:00:00"

    def test_load_stats_from_nonexistent_file(self, tmp_path):
        """Test loading stats when file doesn't exist."""
        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()

        result = workflow_commands._load_stats(str(empathy_dir))

        # Should return default structure
        assert result["commands"] == {}
        assert result["last_session"] is None
        assert result["patterns_learned"] == 0

    def test_load_stats_handles_invalid_json(self, tmp_path):
        """Test loading stats with corrupted JSON."""
        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()

        (empathy_dir / "stats.json").write_text("{ corrupted }")

        result = workflow_commands._load_stats(str(empathy_dir))

        # Should return defaults on error
        assert result["commands"] == {}
        assert result["last_session"] is None


class TestSaveStats:
    """Test _save_stats with real file I/O."""

    def test_save_stats_creates_directory(self, tmp_path):
        """Test save_stats creates directory if it doesn't exist."""
        empathy_dir = tmp_path / ".empathy"

        stats_data = {
            "commands": {"morning": 1},
            "last_session": "2025-01-14",
            "patterns_learned": 5,
        }

        workflow_commands._save_stats(stats_data, str(empathy_dir))

        # Verify directory was created
        assert empathy_dir.exists()
        assert empathy_dir.is_dir()

        # Verify file was created
        stats_file = empathy_dir / "stats.json"
        assert stats_file.exists()

    def test_save_stats_writes_valid_json(self, tmp_path):
        """Test save_stats writes valid JSON that can be read back."""
        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()

        stats_data = {
            "commands": {"morning": 3, "ship": 2, "fix-all": 1},
            "last_session": "2025-01-14T12:00:00",
            "patterns_learned": 10,
        }

        workflow_commands._save_stats(stats_data, str(empathy_dir))

        # Read back and verify
        stats_file = empathy_dir / "stats.json"
        loaded_data = json.loads(stats_file.read_text())

        assert loaded_data["commands"]["morning"] == 3
        assert loaded_data["commands"]["ship"] == 2
        assert loaded_data["patterns_learned"] == 10

    def test_save_stats_overwrites_existing_file(self, tmp_path):
        """Test save_stats overwrites existing stats file."""
        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()

        # Save initial stats
        initial_stats = {"commands": {"morning": 1}, "patterns_learned": 5}
        workflow_commands._save_stats(initial_stats, str(empathy_dir))

        # Save updated stats
        updated_stats = {"commands": {"morning": 2}, "patterns_learned": 7}
        workflow_commands._save_stats(updated_stats, str(empathy_dir))

        # Verify updated stats were saved
        loaded = json.loads((empathy_dir / "stats.json").read_text())
        assert loaded["commands"]["morning"] == 2
        assert loaded["patterns_learned"] == 7

    def test_save_stats_handles_datetime_objects(self, tmp_path):
        """Test save_stats converts datetime objects to strings."""
        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()

        now = datetime.now()
        stats_data = {"commands": {}, "last_session": now, "patterns_learned": 0}

        # Should not raise error
        workflow_commands._save_stats(stats_data, str(empathy_dir))

        # Should be saved as string
        loaded = json.loads((empathy_dir / "stats.json").read_text())
        assert isinstance(loaded["last_session"], str)


class TestRunCommand:
    """Test _run_command with real subprocess calls."""

    def test_run_command_successful_execution(self):
        """Test running a successful command."""
        # Use a simple, reliable command
        success, output = workflow_commands._run_command(["echo", "hello world"])

        assert success is True
        assert "hello world" in output

    def test_run_command_failed_execution(self):
        """Test running a command that fails."""
        # Use a command that will fail
        success, output = workflow_commands._run_command(["false"])

        assert success is False

    def test_run_command_nonexistent_command(self):
        """Test running a command that doesn't exist."""
        success, output = workflow_commands._run_command(["nonexistent_command_12345"])

        assert success is False
        assert "not found" in output.lower() or "Command not found" in output

    def test_run_command_with_arguments(self):
        """Test running command with multiple arguments."""
        success, output = workflow_commands._run_command(["echo", "arg1", "arg2"])

        assert success is True
        assert "arg1" in output
        assert "arg2" in output

    def test_run_command_captures_stderr(self):
        """Test that stderr is captured in output."""
        # Use sh -c to write to stderr
        success, output = workflow_commands._run_command(["sh", "-c", "echo 'error message' >&2"])

        assert "error message" in output


class TestGetTechDebtTrend:
    """Test _get_tech_debt_trend with real file I/O."""

    def test_tech_debt_increasing_trend(self, tmp_path):
        """Test detecting increasing tech debt."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create tech debt file with increasing trend
        tech_debt_data = {
            "snapshots": [
                {"timestamp": "2025-01-10", "total_items": 5},
                {"timestamp": "2025-01-14", "total_items": 8},
            ]
        }

        (patterns_dir / "tech_debt.json").write_text(json.dumps(tech_debt_data))

        result = workflow_commands._get_tech_debt_trend(str(patterns_dir))

        assert result == "increasing"

    def test_tech_debt_decreasing_trend(self, tmp_path):
        """Test detecting decreasing tech debt."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create tech debt file with decreasing trend
        tech_debt_data = {
            "snapshots": [
                {"timestamp": "2025-01-10", "total_items": 10},
                {"timestamp": "2025-01-14", "total_items": 6},
            ]
        }

        (patterns_dir / "tech_debt.json").write_text(json.dumps(tech_debt_data))

        result = workflow_commands._get_tech_debt_trend(str(patterns_dir))

        assert result == "decreasing"

    def test_tech_debt_stable_trend(self, tmp_path):
        """Test detecting stable tech debt."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create tech debt file with stable values
        tech_debt_data = {
            "snapshots": [
                {"timestamp": "2025-01-10", "total_items": 7},
                {"timestamp": "2025-01-14", "total_items": 7},
            ]
        }

        (patterns_dir / "tech_debt.json").write_text(json.dumps(tech_debt_data))

        result = workflow_commands._get_tech_debt_trend(str(patterns_dir))

        assert result == "stable"

    def test_tech_debt_insufficient_data(self, tmp_path):
        """Test with insufficient snapshot data."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create tech debt file with only one snapshot
        tech_debt_data = {"snapshots": [{"timestamp": "2025-01-14", "total_items": 5}]}

        (patterns_dir / "tech_debt.json").write_text(json.dumps(tech_debt_data))

        result = workflow_commands._get_tech_debt_trend(str(patterns_dir))

        assert result == "insufficient_data"

    def test_tech_debt_no_file(self, tmp_path):
        """Test when tech_debt.json doesn't exist."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        result = workflow_commands._get_tech_debt_trend(str(patterns_dir))

        assert result == "unknown"

    def test_tech_debt_multiple_snapshots(self, tmp_path):
        """Test with multiple snapshots (uses last two)."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create tech debt file with many snapshots
        tech_debt_data = {
            "snapshots": [
                {"timestamp": "2025-01-01", "total_items": 10},
                {"timestamp": "2025-01-07", "total_items": 8},
                {"timestamp": "2025-01-10", "total_items": 12},
                {"timestamp": "2025-01-14", "total_items": 15},
            ]
        }

        (patterns_dir / "tech_debt.json").write_text(json.dumps(tech_debt_data))

        result = workflow_commands._get_tech_debt_trend(str(patterns_dir))

        # Should compare last two: 12 -> 15
        assert result == "increasing"


class TestStatsLoadSaveRoundTrip:
    """Integration tests for stats load/save workflow."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test saving stats and loading them back."""
        empathy_dir = tmp_path / ".empathy"

        original_stats = {
            "commands": {"morning": 10, "ship": 5, "fix-all": 3, "learn": 2},
            "last_session": "2025-01-14T15:30:00",
            "patterns_learned": 25,
        }

        # Save
        workflow_commands._save_stats(original_stats, str(empathy_dir))

        # Load
        loaded_stats = workflow_commands._load_stats(str(empathy_dir))

        # Verify roundtrip
        assert loaded_stats["commands"]["morning"] == 10
        assert loaded_stats["commands"]["ship"] == 5
        assert loaded_stats["patterns_learned"] == 25


class TestPatternsLoadingIntegration:
    """Integration tests for full pattern loading workflow."""

    def test_load_all_pattern_types(self, tmp_path):
        """Test loading all four pattern types."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create all pattern type files
        pattern_types = {
            "debugging": [{"id": "d1"}],
            "security": [{"id": "s1"}, {"id": "s2"}],
            "tech_debt": [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}],
            "inspection": [{"id": "i1"}],
        }

        for pattern_type, patterns in pattern_types.items():
            data = {"patterns": patterns}
            (patterns_dir / f"{pattern_type}.json").write_text(json.dumps(data))

        # Load all
        result = workflow_commands._load_patterns(str(patterns_dir))

        # Verify all loaded
        assert len(result["debugging"]) == 1
        assert len(result["security"]) == 2
        assert len(result["tech_debt"]) == 3
        assert len(result["inspection"]) == 1


class TestMorningWorkflow:
    """Test morning_workflow with mocked commands and real file I/O."""

    def test_morning_workflow_basic_execution(self, tmp_path, monkeypatch, capsys):
        """Test morning workflow runs and displays output."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()

        # Create pattern files
        debugging_patterns = {
            "patterns": [
                {"id": "p1", "bug_type": "null_reference", "status": "resolved"},
                {"id": "p2", "bug_type": "type_mismatch", "status": "investigating"},
            ]
        }
        (patterns_dir / "debugging.json").write_text(json.dumps(debugging_patterns))

        # Mock _run_command to avoid real git/ruff calls
        def mock_run_command(cmd, capture=True):
            if cmd[0] == "ruff":
                return True, ""
            if cmd[0] == "git":
                return True, ""
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        # Run workflow
        result = workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path), verbose=False
        )

        assert result == 0

        # Check output contains expected sections
        captured = capsys.readouterr()
        assert "MORNING BRIEFING" in captured.out
        assert "PATTERNS LEARNED" in captured.out
        assert "TECH DEBT TRAJECTORY" in captured.out
        assert "QUICK HEALTH CHECK" in captured.out
        assert "SUGGESTED FOCUS TODAY" in captured.out

    def test_morning_workflow_shows_recent_patterns(self, tmp_path, monkeypatch, capsys):
        """Test morning workflow shows recent patterns from last 7 days."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create patterns with recent timestamps
        from datetime import datetime, timedelta

        recent_date = (datetime.now() - timedelta(days=2)).isoformat()
        old_date = (datetime.now() - timedelta(days=30)).isoformat()

        debugging_patterns = {
            "patterns": [
                {
                    "id": "recent1",
                    "bug_type": "null_reference",
                    "status": "resolved",
                    "timestamp": recent_date,
                    "root_cause": "Recent bug fix",
                },
                {
                    "id": "old1",
                    "bug_type": "type_mismatch",
                    "status": "resolved",
                    "timestamp": old_date,
                    "root_cause": "Old bug fix",
                },
            ]
        }
        (patterns_dir / "debugging.json").write_text(json.dumps(debugging_patterns))

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path)
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "New this week: 1 patterns" in captured.out

    def test_morning_workflow_suggests_resolving_investigating_bugs(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test morning workflow suggests resolving investigating bugs."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        debugging_patterns = {
            "patterns": [
                {"id": "p1", "status": "investigating"},
                {"id": "p2", "status": "investigating"},
                {"id": "p3", "status": "resolved"},
            ]
        }
        (patterns_dir / "debugging.json").write_text(json.dumps(debugging_patterns))

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path)
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Resolve 2 investigating bug(s)" in captured.out

    def test_morning_workflow_shows_tech_debt_hotspots(self, tmp_path, monkeypatch, capsys):
        """Test morning workflow shows tech debt hotspots."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        tech_debt_data = {
            "snapshots": [
                {
                    "timestamp": "2025-01-10",
                    "total_items": 5,
                    "hotspots": ["file1.py", "file2.py", "file3.py"],
                },
                {
                    "timestamp": "2025-01-14",
                    "total_items": 8,
                    "hotspots": ["file1.py", "file2.py", "file4.py"],
                },
            ]
        }
        (patterns_dir / "tech_debt.json").write_text(json.dumps(tech_debt_data))

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path)
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Top hotspots:" in captured.out
        assert "file1.py" in captured.out

    def test_morning_workflow_updates_stats(self, tmp_path, monkeypatch):
        """Test morning workflow updates usage statistics."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
        tmp_path / ".empathy"

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path)
        )

        assert result == 0


class TestShipWorkflow:
    """Test ship_workflow with mocked commands."""

    def test_ship_workflow_tests_only_mode(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow with --tests-only flag."""

        def mock_run_command(cmd, capture=True):
            if "pytest" in cmd:
                return True, "All tests passed"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.ship_workflow(project_root=str(tmp_path), tests_only=True)

        assert result == 0
        captured = capsys.readouterr()
        assert "TEST RESULTS" in captured.out

    def test_ship_workflow_security_only_mode(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow with --security-only flag."""

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.ship_workflow(project_root=str(tmp_path), security_only=True)

        assert result == 0
        captured = capsys.readouterr()
        assert "SECURITY SCAN" in captured.out

    def test_ship_workflow_full_validation(self, tmp_path, monkeypatch, capsys):
        """Test full ship workflow with all checks."""

        def mock_run_command(cmd, capture=True):
            # All checks pass
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=True)

        assert result == 0
        captured = capsys.readouterr()
        assert "READY TO SHIP" in captured.out

    def test_ship_workflow_with_lint_failures(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow detects lint failures."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "ruff" and "check" in cmd:
                return False, "error: E501 line too long\nerror: F401 unused import"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=True)

        assert result == 1
        captured = capsys.readouterr()
        assert "NOT READY TO SHIP" in captured.out
        assert "BLOCKERS" in captured.out

    def test_ship_workflow_with_format_warnings(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow detects formatting warnings."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "ruff" and "format" in cmd:
                return False, "file1.py would be reformatted\nfile2.py would be reformatted"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=True)

        assert result == 0
        captured = capsys.readouterr()
        assert "WARNINGS" in captured.out

    def test_ship_workflow_syncs_to_claude(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow syncs patterns to Claude."""

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=False)

        assert result == 0
        captured = capsys.readouterr()
        assert "Patterns synced" in captured.out


class TestRunTestsOnly:
    """Test _run_tests_only function."""

    def test_run_tests_only_success(self, tmp_path, monkeypatch, capsys):
        """Test running tests successfully."""

        def mock_run_command(cmd, capture=True):
            if "pytest" in cmd:
                return True, "test_example.py::test_foo PASSED"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands._run_tests_only(str(tmp_path))

        assert result == 0
        captured = capsys.readouterr()
        assert "All tests passed!" in captured.out

    def test_run_tests_only_failure(self, tmp_path, monkeypatch, capsys):
        """Test running tests with failures."""

        def mock_run_command(cmd, capture=True):
            if "pytest" in cmd:
                return False, "test_example.py::test_foo FAILED"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands._run_tests_only(str(tmp_path))

        assert result == 1
        captured = capsys.readouterr()
        assert "Test Results:" in captured.out


class TestRunSecurityOnly:
    """Test _run_security_only function."""

    def test_run_security_only_no_issues(self, tmp_path, monkeypatch, capsys):
        """Test security scan with no issues."""

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands._run_security_only(str(tmp_path))

        assert result == 0
        captured = capsys.readouterr()
        assert "No security issues found!" in captured.out

    def test_run_security_only_with_bandit_issues(self, tmp_path, monkeypatch, capsys):
        """Test security scan detects Bandit issues."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "bandit":
                return (
                    False,
                    ">> Issue: [B105:hardcoded_password_string]\n>> Issue: [B602:shell_injection]",
                )
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands._run_security_only(str(tmp_path))

        assert result == 1
        captured = capsys.readouterr()
        assert "SECURITY ISSUES FOUND" in captured.out
        assert "Bandit: 2 security issues" in captured.out

    def test_run_security_only_detects_hardcoded_secrets(self, tmp_path, monkeypatch, capsys):
        """Test security scan detects hardcoded secrets."""

        def mock_run_command(cmd, capture=True):
            if "grep" in cmd and "password" in str(cmd):
                return True, "file1.py:10:password='secret123'\nfile2.py:20:password = 'test'"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands._run_security_only(str(tmp_path))

        assert result == 1
        captured = capsys.readouterr()
        assert "Secrets: 2 potential hardcoded secrets" in captured.out

    def test_run_security_only_detects_sensitive_files(self, tmp_path, monkeypatch, capsys):
        """Test security scan detects sensitive files in git."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "ls-files" in cmd:
                return True, ".env\napi_key.pem\nprivate.key"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands._run_security_only(str(tmp_path))

        assert result == 1
        captured = capsys.readouterr()
        assert "Files: 3 sensitive files in git" in captured.out


class TestFixAllWorkflow:
    """Test fix_all_workflow with mocked commands."""

    def test_fix_all_workflow_basic_execution(self, tmp_path, monkeypatch, capsys):
        """Test fix-all workflow runs all fixes."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "ruff" and "--fix" in cmd:
                return True, "Fixed 5 issues"
            if cmd[0] == "ruff" and "format" in cmd:
                return True, "Formatted 3 files"
            if cmd[0] == "isort":
                return True, "Fixing 2 files"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.fix_all_workflow(str(tmp_path))

        assert result == 0
        captured = capsys.readouterr()
        assert "AUTO-FIX ALL" in captured.out

    def test_fix_all_workflow_dry_run(self, tmp_path, monkeypatch, capsys):
        """Test fix-all workflow in dry-run mode."""

        def mock_run_command(cmd, capture=True):
            if "--diff" in cmd:
                return True, "@@ diff output"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.fix_all_workflow(str(tmp_path), dry_run=True)

        assert result == 0
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "no files were modified" in captured.out

    def test_fix_all_workflow_with_unfixable_issues(self, tmp_path, monkeypatch, capsys):
        """Test fix-all workflow with issues that can't be auto-fixed."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "ruff" and "--fix" in cmd:
                return False, "error: syntax error in file1.py\nerror: undefined name in file2.py"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.fix_all_workflow(str(tmp_path))

        assert result == 0
        captured = capsys.readouterr()
        assert "require manual fix" in captured.out


class TestLearnWorkflow:
    """Test learn_workflow with mocked git commands."""

    def test_learn_workflow_analyzes_commits(self, tmp_path, monkeypatch, capsys):
        """Test learn workflow analyzes git commits."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "log" in cmd:
                return True, (
                    "abc123|fix: null reference bug in parser|John Doe|2025-01-14 10:00:00\n"
                    "def456|feat: add new feature|Jane Smith|2025-01-13 15:30:00\n"
                    "ghi789|fix: type error in converter|Bob Johnson|2025-01-12 09:00:00"
                )
            if cmd[0] == "git" and "show" in cmd:
                return True, "file1.py | 10 ++++\nfile2.py | 5 +++--"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(
            workflow_commands, "_load_stats", lambda: {"commands": {}, "patterns_learned": 0}
        )

        result = workflow_commands.learn_workflow(
            patterns_dir=str(patterns_dir), analyze_commits=10
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "PATTERN LEARNING" in captured.out
        assert "Bug fixes found: 2" in captured.out

        # Check pattern file was created
        debugging_file = patterns_dir / "debugging.json"
        assert debugging_file.exists()
        data = json.loads(debugging_file.read_text())
        assert len(data["patterns"]) == 2

    def test_learn_workflow_classifies_bug_types(self, tmp_path, monkeypatch):
        """Test learn workflow classifies bug types correctly."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "log" in cmd:
                return True, (
                    "a1|fix: null pointer exception|Dev|2025-01-14\n"
                    "a2|fix: async timeout issue|Dev|2025-01-14\n"
                    "a3|fix: type conversion error|Dev|2025-01-14\n"
                    "a4|fix: import missing module|Dev|2025-01-14"
                )
            if cmd[0] == "git" and "show" in cmd:
                return True, "file.py | 5 ++"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(
            workflow_commands, "_load_stats", lambda: {"commands": {}, "patterns_learned": 0}
        )

        result = workflow_commands.learn_workflow(
            patterns_dir=str(patterns_dir), analyze_commits=10
        )

        assert result == 0

        # Check bug types
        debugging_file = patterns_dir / "debugging.json"
        data = json.loads(debugging_file.read_text())
        bug_types = [p["bug_type"] for p in data["patterns"]]
        assert "null_reference" in bug_types
        assert "async_timing" in bug_types
        assert "type_mismatch" in bug_types
        assert "import_error" in bug_types

    def test_learn_workflow_avoids_duplicate_patterns(self, tmp_path, monkeypatch):
        """Test learn workflow doesn't add duplicate patterns."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        # Create existing pattern
        existing_pattern = {
            "patterns": [{"pattern_id": "bug_20250114_abc123", "bug_type": "null_reference"}]
        }
        (patterns_dir / "debugging.json").write_text(json.dumps(existing_pattern))

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "log" in cmd:
                return True, "abc123|fix: duplicate bug|Dev|2025-01-14 10:00:00"
            if cmd[0] == "git" and "show" in cmd:
                return True, "file.py | 5 ++"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(
            workflow_commands, "_load_stats", lambda: {"commands": {}, "patterns_learned": 0}
        )

        result = workflow_commands.learn_workflow(patterns_dir=str(patterns_dir), analyze_commits=5)

        assert result == 0

        # Should not add duplicate
        debugging_file = patterns_dir / "debugging.json"
        data = json.loads(debugging_file.read_text())
        assert len(data["patterns"]) == 1

    def test_learn_workflow_watch_mode_not_implemented(self, tmp_path, monkeypatch, capsys):
        """Test learn workflow watch mode returns error."""
        result = workflow_commands.learn_workflow(patterns_dir=str(tmp_path), watch=True)

        assert result == 1
        captured = capsys.readouterr()
        assert "Watch mode not yet implemented" in captured.out

    def test_learn_workflow_handles_git_errors(self, tmp_path, monkeypatch, capsys):
        """Test learn workflow handles git command failures."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git":
                return False, "fatal: not a git repository"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.learn_workflow(patterns_dir=str(tmp_path), analyze_commits=5)

        assert result == 1
        captured = capsys.readouterr()
        assert "Are you in a git repository?" in captured.out


class TestCLICommandHandlers:
    """Test CLI command handler functions."""

    def test_cmd_morning_handler(self, tmp_path, monkeypatch):
        """Test cmd_morning delegates to morning_workflow."""
        called_with = {}

        def mock_morning_workflow(patterns_dir, project_root, verbose):
            called_with["patterns_dir"] = patterns_dir
            called_with["project_root"] = project_root
            called_with["verbose"] = verbose
            return 0

        monkeypatch.setattr(workflow_commands, "morning_workflow", mock_morning_workflow)

        # Create args object
        class Args:
            patterns_dir = "./patterns"
            project_root = "."
            verbose = False

        result = workflow_commands.cmd_morning(Args())

        assert result == 0
        assert called_with["patterns_dir"] == "./patterns"
        assert called_with["project_root"] == "."
        assert called_with["verbose"] is False

    def test_cmd_ship_handler(self, tmp_path, monkeypatch):
        """Test cmd_ship delegates to ship_workflow."""
        called_with = {}

        def mock_ship_workflow(
            patterns_dir, project_root, skip_sync, tests_only, security_only, verbose
        ):
            called_with["skip_sync"] = skip_sync
            called_with["tests_only"] = tests_only
            called_with["security_only"] = security_only
            return 0

        monkeypatch.setattr(workflow_commands, "ship_workflow", mock_ship_workflow)

        class Args:
            patterns_dir = "./patterns"
            project_root = "."
            skip_sync = True
            tests_only = False
            security_only = False
            verbose = False

        result = workflow_commands.cmd_ship(Args())

        assert result == 0
        assert called_with["skip_sync"] is True
        assert called_with["tests_only"] is False

    def test_cmd_fix_all_handler(self, tmp_path, monkeypatch):
        """Test cmd_fix_all delegates to fix_all_workflow."""
        called_with = {}

        def mock_fix_all_workflow(project_root, dry_run, verbose):
            called_with["dry_run"] = dry_run
            called_with["verbose"] = verbose
            return 0

        monkeypatch.setattr(workflow_commands, "fix_all_workflow", mock_fix_all_workflow)

        class Args:
            project_root = "."
            dry_run = True
            verbose = False

        result = workflow_commands.cmd_fix_all(Args())

        assert result == 0
        assert called_with["dry_run"] is True

    def test_cmd_learn_handler(self, tmp_path, monkeypatch):
        """Test cmd_learn delegates to learn_workflow."""
        called_with = {}

        def mock_learn_workflow(patterns_dir, analyze_commits, watch, verbose):
            called_with["analyze_commits"] = analyze_commits
            called_with["watch"] = watch
            return 0

        monkeypatch.setattr(workflow_commands, "learn_workflow", mock_learn_workflow)

        class Args:
            patterns_dir = "./patterns"
            analyze = 20
            watch = False
            verbose = False

        result = workflow_commands.cmd_learn(Args())

        assert result == 0
        assert called_with["analyze_commits"] == 20
        assert called_with["watch"] is False


class TestCommandTimeouts:
    """Test command timeout handling."""

    def test_run_command_respects_timeout(self, monkeypatch):
        """Test _run_command handles timeout correctly."""
        import subprocess

        def mock_subprocess_run(cmd, check, capture_output, text, timeout):
            raise subprocess.TimeoutExpired(cmd, timeout)

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        success, output = workflow_commands._run_command(["long_running_command"])

        assert success is False
        assert "timed out" in output.lower()

    def test_run_command_handles_exceptions(self, monkeypatch):
        """Test _run_command handles generic exceptions."""
        import subprocess

        def mock_subprocess_run(cmd, check, capture_output, text, timeout):
            raise Exception("Unexpected error")

        monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

        success, output = workflow_commands._run_command(["failing_command"])

        assert success is False
        assert "Unexpected error" in output


class TestTechDebtTrendEdgeCases:
    """Test edge cases for tech debt trend analysis."""

    def test_tech_debt_handles_malformed_json(self, tmp_path):
        """Test tech debt trend with malformed JSON."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        (patterns_dir / "tech_debt.json").write_text("{ malformed json")

        result = workflow_commands._get_tech_debt_trend(str(patterns_dir))

        assert result == "unknown"

    def test_tech_debt_handles_missing_snapshots_key(self, tmp_path):
        """Test tech debt trend with missing snapshots key."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        tech_debt_data = {"last_updated": "2025-01-14"}
        (patterns_dir / "tech_debt.json").write_text(json.dumps(tech_debt_data))

        result = workflow_commands._get_tech_debt_trend(str(patterns_dir))

        assert result == "insufficient_data"

    def test_tech_debt_handles_missing_total_items_key(self, tmp_path):
        """Test tech debt trend with missing total_items key."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        tech_debt_data = {"snapshots": [{"timestamp": "2025-01-10"}, {"timestamp": "2025-01-14"}]}
        (patterns_dir / "tech_debt.json").write_text(json.dumps(tech_debt_data))

        result = workflow_commands._get_tech_debt_trend(str(patterns_dir))

        # Missing total_items defaults to 0, so 0 == 0 = "stable"
        assert result == "stable"


class TestVerboseOutputMode:
    """Test verbose mode output."""

    def test_ship_workflow_verbose_mode(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow shows detailed output in verbose mode."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "ruff" and "check" in cmd:
                return False, "file1.py:10: E501 line too long\nfile2.py:5: F401 unused import"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.ship_workflow(
            project_root=str(tmp_path), skip_sync=True, verbose=True
        )

        assert result == 1
        captured = capsys.readouterr()
        # In verbose mode, should show detailed error output
        assert "E501" in captured.out or "line too long" in captured.out

    def test_learn_workflow_verbose_mode(self, tmp_path, monkeypatch, capsys):
        """Test learn workflow shows detailed output in verbose mode."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "log" in cmd:
                return True, "abc123|fix: bug in parser|Dev|2025-01-14"
            if cmd[0] == "git" and "show" in cmd:
                return True, "file.py | 5 ++"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(
            workflow_commands, "_load_stats", lambda: {"commands": {}, "patterns_learned": 0}
        )

        result = workflow_commands.learn_workflow(
            patterns_dir=str(patterns_dir), analyze_commits=5, verbose=True
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Found:" in captured.out


class TestGitStatusParsing:
    """Test git status output parsing."""

    def test_ship_workflow_detects_staged_files(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow detects staged files correctly."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "status" in cmd:
                return True, "A  new_file.py\nM  modified_file.py\n M unstaged_file.py"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=True)

        captured = capsys.readouterr()
        assert "staged" in captured.out

    def test_ship_workflow_warns_unstaged_files(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow warns about unstaged files."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "status" in cmd:
                return True, " M unstaged1.py\n M unstaged2.py\n?? untracked.py"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=True)

        captured = capsys.readouterr()
        assert "unstaged" in captured.out


class TestMorningWorkflowEdgeCases:
    """Additional tests for morning workflow edge cases."""

    def test_morning_workflow_handles_missing_timestamp_formats(
        self, tmp_path, monkeypatch, capsys
    ):
        """Test morning workflow handles various timestamp formats."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        debugging_patterns = {
            "patterns": [
                {"id": "p1", "timestamp": "invalid-timestamp"},
                {"id": "p2", "resolved_at": "2025-01-14T10:00:00Z"},
                {"id": "p3"},  # No timestamp
            ]
        }
        (patterns_dir / "debugging.json").write_text(json.dumps(debugging_patterns))

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path)
        )

        assert result == 0

    def test_morning_workflow_handles_ruff_failures(self, tmp_path, monkeypatch, capsys):
        """Test morning workflow handles ruff command failures."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "ruff":
                return False, "error: E501 line too long\nerror: F401 unused"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path)
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "issues" in captured.out

    def test_morning_workflow_handles_git_failures(self, tmp_path, monkeypatch, capsys):
        """Test morning workflow handles git command failures."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git":
                return False, "fatal: not a git repository"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path)
        )

        assert result == 0

    def test_morning_workflow_no_patterns_suggests_learning(self, tmp_path, monkeypatch, capsys):
        """Test morning workflow suggests learning when no patterns exist."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path)
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "Start learning patterns" in captured.out


class TestShipWorkflowEdgeCases:
    """Additional tests for ship workflow edge cases."""

    def test_ship_workflow_handles_mypy_not_installed(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow handles mypy not being installed."""

        def mock_run_command(cmd, capture=True):
            if "mypy" in cmd:
                return False, "No module named 'mypy'"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=True)

        assert result == 0

    def test_ship_workflow_detects_type_errors(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow detects type errors."""

        def mock_run_command(cmd, capture=True):
            if "mypy" in cmd:
                return False, "file.py:10: error: incompatible types\nfile.py:20: error: undefined"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=True)

        captured = capsys.readouterr()
        assert "type issues" in captured.out

    def test_ship_workflow_sync_claude_import_error(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow handles sync_claude import errors gracefully."""

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        # Don't mock the import - let it fail naturally
        workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=False)

        captured = capsys.readouterr()
        assert "SKIP" in captured.out or "sync" in captured.out.lower()

    def test_ship_workflow_handles_empty_git_status(self, tmp_path, monkeypatch, capsys):
        """Test ship workflow handles clean git status."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "status" in cmd:
                return True, ""  # Empty = clean
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=True)

        captured = capsys.readouterr()
        assert "clean" in captured.out.lower()


class TestSecurityOnlyEdgeCases:
    """Additional tests for security-only mode edge cases."""

    def test_security_only_bandit_not_installed(self, tmp_path, monkeypatch, capsys):
        """Test security scan handles bandit not installed."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "bandit":
                return False, "bandit: command not found"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        workflow_commands._run_security_only(str(tmp_path))

        captured = capsys.readouterr()
        assert "SKIP" in captured.out
        assert "not installed" in captured.out

    def test_security_only_multiple_issues(self, tmp_path, monkeypatch, capsys):
        """Test security scan detects multiple issue types."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "bandit":
                return False, ">> Issue: [B105]\n>> Issue: [B602]"
            if "grep" in cmd and "password" in str(cmd):
                return True, "file.py:10:password='secret'"
            if cmd[0] == "git" and "ls-files" in cmd:
                return True, ".env\napi.key"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        result = workflow_commands._run_security_only(str(tmp_path))

        assert result == 1
        captured = capsys.readouterr()
        assert "Bandit: 2 security issues" in captured.out
        assert "Secrets: 1 potential hardcoded secrets" in captured.out
        assert "Files: 2 sensitive files in git" in captured.out


class TestFixAllWorkflowEdgeCases:
    """Additional tests for fix-all workflow edge cases."""

    def test_fix_all_counts_fixes_correctly(self, tmp_path, monkeypatch, capsys):
        """Test fix-all workflow counts fixes correctly."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "ruff" and "--fix" in cmd:
                return True, "Fixed 10 issues\nFixed 5 more\nFixed 3 additional"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.fix_all_workflow(str(tmp_path))

        assert result == 0
        captured = capsys.readouterr()
        assert "Fixed" in captured.out

    def test_fix_all_isort_output_handling(self, tmp_path, monkeypatch, capsys):
        """Test fix-all workflow handles isort output correctly."""

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "isort":
                return True, "Skipped 5 files\nFixing file1.py\nFixing file2.py"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.fix_all_workflow(str(tmp_path))

        assert result == 0

    def test_fix_all_dry_run_counts_diffs(self, tmp_path, monkeypatch, capsys):
        """Test fix-all dry-run counts diff blocks correctly."""

        def mock_run_command(cmd, capture=True):
            if "--diff" in cmd:
                return True, "@@ -1,5 +1,5 @@\n@@ -10,3 +10,3 @@"
            return True, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(workflow_commands, "_load_stats", lambda: {"commands": {}})

        result = workflow_commands.fix_all_workflow(str(tmp_path), dry_run=True)

        assert result == 0
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out


class TestLearnWorkflowEdgeCases:
    """Additional tests for learn workflow edge cases."""

    def test_learn_workflow_handles_empty_commits(self, tmp_path, monkeypatch):
        """Test learn workflow handles empty commit list."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "log" in cmd:
                return True, ""
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(
            workflow_commands, "_load_stats", lambda: {"commands": {}, "patterns_learned": 0}
        )

        result = workflow_commands.learn_workflow(
            patterns_dir=str(patterns_dir), analyze_commits=10
        )

        assert result == 0

    def test_learn_workflow_handles_malformed_commit_lines(self, tmp_path, monkeypatch):
        """Test learn workflow handles malformed commit lines."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "log" in cmd:
                return True, "invalid line\n|missing parts|\nabc123|fix: bug|Dev|2025-01-14"
            if cmd[0] == "git" and "show" in cmd:
                return True, "file.py | 5 ++"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(
            workflow_commands, "_load_stats", lambda: {"commands": {}, "patterns_learned": 0}
        )

        result = workflow_commands.learn_workflow(
            patterns_dir=str(patterns_dir), analyze_commits=10
        )

        assert result == 0

    def test_learn_workflow_filters_non_bug_commits(self, tmp_path, monkeypatch):
        """Test learn workflow only processes bug fix commits."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "log" in cmd:
                return True, (
                    "a1|feat: new feature|Dev|2025-01-14\n"
                    "a2|docs: update readme|Dev|2025-01-14\n"
                    "a3|fix: actual bug|Dev|2025-01-14\n"
                    "a4|chore: update deps|Dev|2025-01-14"
                )
            if cmd[0] == "git" and "show" in cmd:
                return True, "file.py | 5 ++"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(
            workflow_commands, "_load_stats", lambda: {"commands": {}, "patterns_learned": 0}
        )

        result = workflow_commands.learn_workflow(
            patterns_dir=str(patterns_dir), analyze_commits=10
        )

        assert result == 0

        debugging_file = patterns_dir / "debugging.json"
        data = json.loads(debugging_file.read_text())
        # Only 1 bug fix commit should be learned
        assert len(data["patterns"]) == 1

    def test_learn_workflow_extracts_files_from_diff(self, tmp_path, monkeypatch):
        """Test learn workflow extracts file names from git diff."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "log" in cmd:
                return True, "abc123|fix: bug|Dev|2025-01-14"
            if cmd[0] == "git" and "show" in cmd:
                return True, (
                    "file1.py | 10 ++++------\n"
                    "file2.py | 5 +++++\n"
                    "file3.py | 2 --\n"
                    "Total: 3 files changed"
                )
            return False, ""

        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)
        monkeypatch.setattr(workflow_commands, "_save_stats", lambda stats: None)
        monkeypatch.setattr(
            workflow_commands, "_load_stats", lambda: {"commands": {}, "patterns_learned": 0}
        )

        result = workflow_commands.learn_workflow(
            patterns_dir=str(patterns_dir), analyze_commits=10
        )

        assert result == 0

        debugging_file = patterns_dir / "debugging.json"
        data = json.loads(debugging_file.read_text())
        pattern = data["patterns"][0]
        # Should extract first 3 files
        assert len(pattern["files_affected"]) == 3
        assert "file1.py" in pattern["files_affected"]


class TestCLIHandlerDefaults:
    """Test CLI handlers handle missing attributes with defaults."""

    def test_cmd_morning_uses_defaults(self, monkeypatch):
        """Test cmd_morning uses defaults when attributes missing."""
        called = False

        def mock_morning_workflow(patterns_dir, project_root, verbose):
            nonlocal called
            called = True
            assert patterns_dir == "./patterns"
            assert project_root == "."
            assert verbose is False
            return 0

        monkeypatch.setattr(workflow_commands, "morning_workflow", mock_morning_workflow)

        class Args:
            pass  # No attributes

        result = workflow_commands.cmd_morning(Args())
        assert result == 0
        assert called

    def test_cmd_ship_uses_defaults(self, monkeypatch):
        """Test cmd_ship uses defaults when attributes missing."""
        called = False

        def mock_ship_workflow(
            patterns_dir, project_root, skip_sync, tests_only, security_only, verbose
        ):
            nonlocal called
            called = True
            assert skip_sync is False
            assert tests_only is False
            assert security_only is False
            return 0

        monkeypatch.setattr(workflow_commands, "ship_workflow", mock_ship_workflow)

        class Args:
            pass

        result = workflow_commands.cmd_ship(Args())
        assert result == 0
        assert called

    def test_cmd_fix_all_uses_defaults(self, monkeypatch):
        """Test cmd_fix_all uses defaults when attributes missing."""
        called = False

        def mock_fix_all_workflow(project_root, dry_run, verbose):
            nonlocal called
            called = True
            assert dry_run is False
            assert verbose is False
            return 0

        monkeypatch.setattr(workflow_commands, "fix_all_workflow", mock_fix_all_workflow)

        class Args:
            pass

        result = workflow_commands.cmd_fix_all(Args())
        assert result == 0
        assert called

    def test_cmd_learn_uses_defaults(self, monkeypatch):
        """Test cmd_learn uses defaults when attributes missing."""
        called = False

        def mock_learn_workflow(patterns_dir, analyze_commits, watch, verbose):
            nonlocal called
            called = True
            assert analyze_commits is None
            assert watch is False
            return 0

        monkeypatch.setattr(workflow_commands, "learn_workflow", mock_learn_workflow)

        class Args:
            pass

        result = workflow_commands.cmd_learn(Args())
        assert result == 0
        assert called


class TestStatsIntegration:
    """Test stats tracking across workflows."""

    def test_morning_workflow_increments_stats(self, tmp_path, monkeypatch):
        """Test morning workflow increments morning command counter."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
        tmp_path / ".empathy"

        initial_stats = {"commands": {"morning": 5}, "patterns_learned": 0}
        saved_stats = {}

        def mock_load_stats():
            return initial_stats.copy()

        def mock_save_stats(stats):
            saved_stats.update(stats)

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_load_stats", mock_load_stats)
        monkeypatch.setattr(workflow_commands, "_save_stats", mock_save_stats)
        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        workflow_commands.morning_workflow(
            patterns_dir=str(patterns_dir), project_root=str(tmp_path)
        )

        assert saved_stats["commands"]["morning"] == 6

    def test_ship_workflow_increments_stats(self, tmp_path, monkeypatch):
        """Test ship workflow increments ship command counter."""
        initial_stats = {"commands": {"ship": 2}}
        saved_stats = {}

        def mock_load_stats():
            return initial_stats.copy()

        def mock_save_stats(stats):
            saved_stats.update(stats)

        def mock_run_command(cmd, capture=True):
            return True, ""

        monkeypatch.setattr(workflow_commands, "_load_stats", mock_load_stats)
        monkeypatch.setattr(workflow_commands, "_save_stats", mock_save_stats)
        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        workflow_commands.ship_workflow(project_root=str(tmp_path), skip_sync=True)

        assert saved_stats["commands"]["ship"] == 3

    def test_learn_workflow_tracks_patterns_learned(self, tmp_path, monkeypatch):
        """Test learn workflow tracks total patterns learned."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()

        initial_stats = {"commands": {}, "patterns_learned": 10}
        saved_stats = {}

        def mock_load_stats():
            return initial_stats.copy()

        def mock_save_stats(stats):
            saved_stats.update(stats)

        def mock_run_command(cmd, capture=True):
            if cmd[0] == "git" and "log" in cmd:
                return True, ("a1|fix: bug1|Dev|2025-01-14\na2|fix: bug2|Dev|2025-01-14")
            if cmd[0] == "git" and "show" in cmd:
                return True, "file.py | 5 ++"
            return False, ""

        monkeypatch.setattr(workflow_commands, "_load_stats", mock_load_stats)
        monkeypatch.setattr(workflow_commands, "_save_stats", mock_save_stats)
        monkeypatch.setattr(workflow_commands, "_run_command", mock_run_command)

        workflow_commands.learn_workflow(patterns_dir=str(patterns_dir), analyze_commits=10)

        # Should increment by 2 new patterns
        assert saved_stats["patterns_learned"] == 12
