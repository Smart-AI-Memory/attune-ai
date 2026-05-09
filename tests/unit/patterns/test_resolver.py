"""Unit tests for attune.patterns.resolver module.

Tests PatternResolver: find_bug, list_investigating, resolve_bug,
regenerate_summary, and cmd_patterns_resolve CLI handler.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from attune.patterns.resolver import PatternResolver, cmd_patterns_resolve


def _write_bug(dir_path: Path, filename: str, data: dict) -> Path:
    """Helper: write a bug JSON file into dir_path."""
    dir_path.mkdir(parents=True, exist_ok=True)
    bug_file = dir_path / filename
    bug_file.write_text(json.dumps(data), encoding="utf-8")
    return bug_file


class TestPatternResolverInit:
    """Tests for PatternResolver initialization."""

    def test_init_stores_patterns_dir(self, tmp_path):
        """__init__ stores patterns_dir as Path."""
        resolver = PatternResolver(str(tmp_path))
        assert resolver.patterns_dir == tmp_path

    def test_init_has_debugging_dirs(self, tmp_path):
        """__init__ sets expected debugging directory names."""
        resolver = PatternResolver(str(tmp_path))
        assert "debugging" in resolver._debugging_dirs
        assert "debugging_demo" in resolver._debugging_dirs
        assert "repo_test/debugging" in resolver._debugging_dirs


class TestPatternResolverFindBug:
    """Tests for PatternResolver.find_bug."""

    def test_find_bug_returns_none_when_not_found(self, tmp_path):
        """find_bug returns (None, None) when bug does not exist."""
        resolver = PatternResolver(str(tmp_path))
        file_path, data = resolver.find_bug("bug_nonexistent_001")
        assert file_path is None
        assert data is None

    def test_find_bug_finds_by_exact_filename(self, tmp_path):
        """find_bug matches by filename first."""
        bug_data = {"bug_id": "bug_filename_001", "status": "investigating"}
        _write_bug(tmp_path / "debugging", "bug_filename_001.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        file_path, data = resolver.find_bug("bug_filename_001")

        assert file_path is not None
        assert data is not None
        assert data["bug_id"] == "bug_filename_001"

    def test_find_bug_finds_by_bug_id_field(self, tmp_path):
        """find_bug falls back to searching bug_id field in JSON."""
        # File is named differently, but bug_id field matches
        bug_data = {"bug_id": "bug_search_001", "status": "investigating"}
        _write_bug(tmp_path / "debugging", "bug_other_name.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        file_path, data = resolver.find_bug("bug_search_001")

        assert file_path is not None
        assert data["bug_id"] == "bug_search_001"

    def test_find_bug_searches_debugging_demo_dir(self, tmp_path):
        """find_bug searches in debugging_demo directory."""
        bug_data = {"bug_id": "bug_demo_001", "status": "resolved"}
        _write_bug(tmp_path / "debugging_demo", "bug_demo_001.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        file_path, data = resolver.find_bug("bug_demo_001")

        assert file_path is not None
        assert data["bug_id"] == "bug_demo_001"

    def test_find_bug_searches_repo_test_debugging_dir(self, tmp_path):
        """find_bug searches in repo_test/debugging directory."""
        bug_data = {"bug_id": "bug_repo_001", "status": "resolved"}
        _write_bug(tmp_path / "repo_test" / "debugging", "bug_repo_001.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        file_path, data = resolver.find_bug("bug_repo_001")

        assert file_path is not None
        assert data["bug_id"] == "bug_repo_001"

    def test_find_bug_returns_file_path_as_path_object(self, tmp_path):
        """find_bug returns a Path object for the file path."""
        bug_data = {"bug_id": "bug_path_001"}
        _write_bug(tmp_path / "debugging", "bug_path_001.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        file_path, _ = resolver.find_bug("bug_path_001")

        assert isinstance(file_path, Path)

    def test_find_bug_skips_invalid_json_during_search(self, tmp_path):
        """find_bug skips files with invalid JSON when searching by bug_id field."""
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        (debug_dir / "bug_bad.json").write_text("not valid json", encoding="utf-8")

        resolver = PatternResolver(str(tmp_path))
        file_path, data = resolver.find_bug("bug_missing")
        assert file_path is None


class TestPatternResolverListInvestigating:
    """Tests for PatternResolver.list_investigating."""

    def test_list_investigating_returns_empty_when_no_bugs(self, tmp_path):
        """list_investigating returns empty list with no files."""
        resolver = PatternResolver(str(tmp_path))
        result = resolver.list_investigating()
        assert result == []

    def test_list_investigating_returns_investigating_bugs(self, tmp_path):
        """list_investigating returns bugs with status 'investigating'."""
        bug1 = {"bug_id": "bug_001", "status": "investigating", "error_type": "null_reference"}
        bug2 = {"bug_id": "bug_002", "status": "resolved", "error_type": "type_mismatch"}
        _write_bug(tmp_path / "debugging", "bug_001.json", bug1)
        _write_bug(tmp_path / "debugging", "bug_002.json", bug2)

        resolver = PatternResolver(str(tmp_path))
        result = resolver.list_investigating()

        assert len(result) == 1
        assert result[0]["bug_id"] == "bug_001"

    def test_list_investigating_returns_two_investigating_bugs(self, tmp_path):
        """list_investigating returns all investigating bugs from all dirs."""
        bug1 = {"bug_id": "bug_inv_001", "status": "investigating"}
        bug2 = {"bug_id": "bug_inv_002", "status": "investigating"}
        _write_bug(tmp_path / "debugging", "bug_inv_001.json", bug1)
        _write_bug(tmp_path / "debugging_demo", "bug_inv_002.json", bug2)

        resolver = PatternResolver(str(tmp_path))
        result = resolver.list_investigating()

        assert len(result) == 2

    def test_list_investigating_adds_file_path_field(self, tmp_path):
        """list_investigating adds _file_path to each returned dict."""
        bug = {"bug_id": "bug_fp_001", "status": "investigating"}
        _write_bug(tmp_path / "debugging", "bug_fp_001.json", bug)

        resolver = PatternResolver(str(tmp_path))
        result = resolver.list_investigating()

        assert "_file_path" in result[0]
        assert "bug_fp_001.json" in result[0]["_file_path"]

    def test_list_investigating_skips_invalid_json(self, tmp_path):
        """list_investigating skips files with invalid JSON."""
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        (debug_dir / "bug_bad.json").write_text("not valid json", encoding="utf-8")

        resolver = PatternResolver(str(tmp_path))
        result = resolver.list_investigating()
        assert result == []


class TestPatternResolverResolveBug:
    """Tests for PatternResolver.resolve_bug."""

    def test_resolve_bug_returns_false_when_not_found(self, tmp_path):
        """resolve_bug returns False when bug_id does not exist."""
        resolver = PatternResolver(str(tmp_path))
        result = resolver.resolve_bug(
            bug_id="bug_nonexistent",
            root_cause="Unknown",
            fix_applied="Nothing",
        )
        assert result is False

    def test_resolve_bug_returns_true_on_success(self, tmp_path):
        """resolve_bug returns True when bug is found and updated."""
        bug_data = {"bug_id": "bug_resolve_001", "status": "investigating"}
        _write_bug(tmp_path / "debugging", "bug_resolve_001.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        result = resolver.resolve_bug(
            bug_id="bug_resolve_001",
            root_cause="Missing null check",
            fix_applied="Added guard clause",
        )
        assert result is True

    def test_resolve_bug_updates_status_to_resolved(self, tmp_path):
        """resolve_bug updates status field to 'resolved'."""
        bug_data = {"bug_id": "bug_status_001", "status": "investigating"}
        bug_file = _write_bug(tmp_path / "debugging", "bug_status_001.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        resolver.resolve_bug(
            bug_id="bug_status_001",
            root_cause="Found it",
            fix_applied="Fixed it",
        )

        updated = json.loads(bug_file.read_text(encoding="utf-8"))
        assert updated["status"] == "resolved"

    def test_resolve_bug_writes_root_cause_and_fix(self, tmp_path):
        """resolve_bug writes root_cause and fix_applied to the file."""
        bug_data = {"bug_id": "bug_update_001", "status": "investigating"}
        bug_file = _write_bug(tmp_path / "debugging", "bug_update_001.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        resolver.resolve_bug(
            bug_id="bug_update_001",
            root_cause="The actual root cause",
            fix_applied="The actual fix",
            resolution_time_minutes=30,
            resolved_by="@testdev",
        )

        updated = json.loads(bug_file.read_text(encoding="utf-8"))
        assert updated["root_cause"] == "The actual root cause"
        assert updated["fix_applied"] == "The actual fix"
        assert updated["resolution_time_minutes"] == 30
        assert updated["resolved_by"] == "@testdev"

    def test_resolve_bug_writes_fix_code_when_provided(self, tmp_path):
        """resolve_bug writes fix_code field when provided."""
        bug_data = {"bug_id": "bug_code_001", "status": "investigating"}
        bug_file = _write_bug(tmp_path / "debugging", "bug_code_001.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        resolver.resolve_bug(
            bug_id="bug_code_001",
            root_cause="Root cause",
            fix_applied="Fix description",
            fix_code="data?.items ?? []",
        )

        updated = json.loads(bug_file.read_text(encoding="utf-8"))
        assert updated["fix_code"] == "data?.items ?? []"

    def test_resolve_bug_sets_resolved_at_timestamp(self, tmp_path):
        """resolve_bug sets resolved_at timestamp."""
        bug_data = {"bug_id": "bug_ts_001", "status": "investigating"}
        bug_file = _write_bug(tmp_path / "debugging", "bug_ts_001.json", bug_data)

        resolver = PatternResolver(str(tmp_path))
        resolver.resolve_bug(
            bug_id="bug_ts_001",
            root_cause="Root cause",
            fix_applied="Fix",
        )

        updated = json.loads(bug_file.read_text(encoding="utf-8"))
        assert "resolved_at" in updated
        assert updated["resolved_at"] is not None


class TestPatternResolverRegenerateSummary:
    """Tests for PatternResolver.regenerate_summary."""

    def test_regenerate_summary_returns_true_on_success(self, tmp_path):
        """regenerate_summary returns True when PatternSummaryGenerator succeeds."""
        resolver = PatternResolver(str(tmp_path))

        mock_generator = MagicMock()
        mock_cls = MagicMock(return_value=mock_generator)
        # PatternSummaryGenerator is imported inside regenerate_summary's function
        # body, so we patch the class in the summary module (Python caches imports
        # from sys.modules, so patching the class attribute works at call time).
        import attune.patterns.summary as summary_mod

        with patch.object(summary_mod, "PatternSummaryGenerator", mock_cls):
            result = resolver.regenerate_summary()

        assert result is True
        mock_generator.load_all_patterns.assert_called_once()
        mock_generator.write_to_file.assert_called_once()

    def test_regenerate_summary_returns_false_on_exception(self, tmp_path):
        """regenerate_summary returns False when generator raises."""
        resolver = PatternResolver(str(tmp_path))

        import attune.patterns.summary as summary_mod

        with patch.object(
            summary_mod,
            "PatternSummaryGenerator",
            side_effect=RuntimeError("boom"),
        ):
            result = resolver.regenerate_summary()

        assert result is False


class TestCmdPatternsResolve:
    """Tests for cmd_patterns_resolve CLI handler."""

    def _make_args(self, **kwargs):
        """Create a mock args namespace."""
        defaults = {
            "patterns_dir": "/tmp/patterns",
            "bug_id": None,
            "root_cause": None,
            "fix": None,
            "fix_code": None,
            "time": None,
            "resolved_by": "@developer",
            "no_regenerate": True,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_cmd_patterns_resolve_lists_investigating_when_no_bug_id(self, tmp_path, capsys):
        """cmd_patterns_resolve lists investigating bugs when no bug_id given."""
        bug = {
            "bug_id": "bug_list_001",
            "status": "investigating",
            "error_type": "null_reference",
            "file_path": "test.py",
            "error_message": "Cannot read property",
        }
        _write_bug(tmp_path / "debugging", "bug_list_001.json", bug)

        args = self._make_args(patterns_dir=str(tmp_path))
        cmd_patterns_resolve(args)

        captured = capsys.readouterr()
        assert "bug_list_001" in captured.out

    def test_cmd_patterns_resolve_prints_no_bugs_when_none(self, tmp_path, capsys):
        """cmd_patterns_resolve prints 'No bugs' when no investigating bugs."""
        args = self._make_args(patterns_dir=str(tmp_path))
        cmd_patterns_resolve(args)

        captured = capsys.readouterr()
        assert "No bugs" in captured.out

    def test_cmd_patterns_resolve_resolves_bug_and_prints_success(self, tmp_path, capsys):
        """cmd_patterns_resolve resolves a bug and prints confirmation."""
        bug_data = {"bug_id": "bug_cli_001", "status": "investigating"}
        _write_bug(tmp_path / "debugging", "bug_cli_001.json", bug_data)

        args = self._make_args(
            patterns_dir=str(tmp_path),
            bug_id="bug_cli_001",
            root_cause="The root cause",
            fix="The fix applied",
            no_regenerate=True,
        )
        cmd_patterns_resolve(args)

        captured = capsys.readouterr()
        assert "bug_cli_001" in captured.out

    def test_cmd_patterns_resolve_prints_failure_when_not_found(self, tmp_path, capsys):
        """cmd_patterns_resolve prints failure message when bug not found."""
        args = self._make_args(
            patterns_dir=str(tmp_path),
            bug_id="bug_missing_001",
            root_cause="Cause",
            fix="Fix",
            no_regenerate=True,
        )
        cmd_patterns_resolve(args)

        captured = capsys.readouterr()
        assert "bug_missing_001" in captured.out

    def test_cmd_patterns_resolve_calls_regenerate_when_not_suppressed(self, tmp_path, capsys):
        """cmd_patterns_resolve calls regenerate_summary when no_regenerate=False."""
        bug_data = {"bug_id": "bug_regen_001", "status": "investigating"}
        _write_bug(tmp_path / "debugging", "bug_regen_001.json", bug_data)

        args = self._make_args(
            patterns_dir=str(tmp_path),
            bug_id="bug_regen_001",
            root_cause="Cause",
            fix="Fix",
            no_regenerate=False,
        )

        with patch.object(PatternResolver, "regenerate_summary", return_value=True) as mock_regen:
            cmd_patterns_resolve(args)

        mock_regen.assert_called_once()


# ===========================================================================
# Coverage gap tests
# ===========================================================================


class TestResolverCoverageGaps:
    """Cover lines 80-81, 88->84, 169-171, 231, 239-276."""

    def test_find_bug_malformed_json_logged(self, tmp_path, caplog):
        """Lines 80-81: malformed JSON in <bug_id>.json → warning logged."""
        import logging

        from attune.patterns.resolver import PatternResolver

        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        # Direct file <bug_id>.json with bad JSON
        (debug_dir / "bug_x.json").write_text("not-json{")

        resolver = PatternResolver(str(tmp_path))
        with caplog.at_level(logging.WARNING):
            file_path, data = resolver.find_bug("bug_x")
        assert file_path is None
        assert any("Failed to load" in r.message for r in caplog.records)

    def test_find_bug_glob_skips_unmatched(self, tmp_path):
        """Branch 88->84: bug_id field doesn't match → continue glob."""
        import json as _json

        from attune.patterns.resolver import PatternResolver

        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        # File exists but bug_id field doesn't match
        (debug_dir / "bug_other.json").write_text(_json.dumps({"bug_id": "different-id"}))

        resolver = PatternResolver(str(tmp_path))
        file_path, data = resolver.find_bug("target-id")
        assert file_path is None

    def test_resolve_bug_oserror_logged(self, tmp_path, caplog):
        """Lines 169-171: OSError on write → log + return False."""
        import json as _json
        import logging
        from unittest.mock import patch as _patch

        from attune.patterns.resolver import PatternResolver

        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        # Create the file so find_bug succeeds
        (debug_dir / "bug_x.json").write_text(
            _json.dumps({"bug_id": "bug_x", "status": "investigating"})
        )

        resolver = PatternResolver(str(tmp_path))

        # Patch open() (write mode) to raise OSError
        original_open = open

        def fake_open(path, mode="r", *args, **kwargs):
            if "w" in mode:
                raise OSError("disk full")
            return original_open(path, mode, *args, **kwargs)

        with caplog.at_level(logging.ERROR), _patch("builtins.open", side_effect=fake_open):
            result = resolver.resolve_bug(bug_id="bug_x", root_cause="cause", fix_applied="fix")
        assert result is False
        assert any("Failed to write" in r.message for r in caplog.records)


class TestCmdPatternsResolveRegenerateFailure:
    """Cover line 231: regenerate_summary returns False → 'Failed to regenerate'."""

    def test_regenerate_failure_prints_warning(self, tmp_path, capsys):
        from types import SimpleNamespace
        from unittest.mock import patch as _patch

        from attune.patterns.resolver import PatternResolver, cmd_patterns_resolve

        # Set up bug to resolve
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        import json as _json

        (debug_dir / "bug_x.json").write_text(
            _json.dumps({"bug_id": "bug_x", "status": "investigating"})
        )

        args = SimpleNamespace(
            patterns_dir=str(tmp_path),
            bug_id="bug_x",
            root_cause="cause",
            fix="fix",
            fix_code=None,
            time=None,
            resolved_by="@dev",
            no_regenerate=False,
        )

        with _patch.object(PatternResolver, "regenerate_summary", return_value=False):
            cmd_patterns_resolve(args)

        out = capsys.readouterr().out
        assert "Failed to regenerate" in out


class TestMainEntryPoint:
    """Cover lines 239-276: main() CLI entry point."""

    def test_main_no_bug_id_lists_investigating(self, tmp_path, capsys, monkeypatch):
        """Line 198-211: no bug_id → list investigating."""
        import json as _json
        from unittest.mock import patch as _patch

        from attune.patterns import resolver as mod

        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        (debug_dir / "bug_x.json").write_text(
            _json.dumps(
                {
                    "bug_id": "bug_x",
                    "status": "investigating",
                    "error_type": "null_ref",
                    "file_path": "src/x.py",
                    "error_message": "boom",
                }
            )
        )

        argv = ["prog", "--patterns-dir", str(tmp_path)]
        with _patch("sys.argv", argv):
            mod.main()
        out = capsys.readouterr().out
        assert "bug_x" in out

    def test_main_resolve_with_required_args(self, tmp_path, capsys):
        """Line 273: bug_id present requires --root-cause and --fix."""
        import json as _json
        from unittest.mock import patch as _patch

        from attune.patterns import resolver as mod

        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        (debug_dir / "bug_x.json").write_text(
            _json.dumps({"bug_id": "bug_x", "status": "investigating"})
        )

        argv = [
            "prog",
            "bug_x",
            "--root-cause",
            "cause",
            "--fix",
            "fix",
            "--patterns-dir",
            str(tmp_path),
            "--no-regenerate",
        ]
        with _patch("sys.argv", argv):
            mod.main()
        out = capsys.readouterr().out
        assert "Resolved" in out

    def test_main_resolve_missing_required_args_errors(self, tmp_path, capsys):
        """Line 273-274: missing root-cause or fix → parser.error."""
        from unittest.mock import patch as _patch

        import pytest

        from attune.patterns import resolver as mod

        argv = ["prog", "bug_x", "--patterns-dir", str(tmp_path)]
        with _patch("sys.argv", argv), pytest.raises(SystemExit):
            mod.main()
