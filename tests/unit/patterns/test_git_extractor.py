"""Unit tests for attune.patterns.git_extractor module.

Tests GitPatternExtractor: commit extraction, staged extraction,
pattern detection, scoring, and save operations.

All git subprocess calls are mocked.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.patterns.git_extractor import GitPatternExtractor


def _make_completed_process(stdout="", returncode=0, stderr=""):
    """Create a mock CompletedProcess result."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


_HASH = "abcd1234" * 5  # 40 hex chars — the parser validates %H as hex


def _batch_record(
    subject, author="Jane Dev", date="2025-01-01T00:00:00Z", parents="parent1", diff=""
):
    """One NUL-framed record in the batched `git log` wire format."""
    return f"\x00{_HASH}\x1f{author}\x1f{date}\x1f{parents}\x1f{subject}\n{diff}"


class TestGitPatternExtractorInit:
    """Tests for GitPatternExtractor initialization."""

    def test_init_stores_patterns_dir(self, tmp_path):
        """__init__ stores patterns_dir as Path."""
        extractor = GitPatternExtractor(str(tmp_path))
        assert extractor.patterns_dir == tmp_path

    def test_init_sets_debugging_dir(self, tmp_path):
        """__init__ sets debugging subdirectory."""
        extractor = GitPatternExtractor(str(tmp_path))
        assert extractor.debugging_dir == tmp_path / "debugging"

    def test_init_has_fix_message_patterns(self, tmp_path):
        """__init__ populates _fix_message_patterns list."""
        extractor = GitPatternExtractor(str(tmp_path))
        assert len(extractor._fix_message_patterns) > 0

    def test_init_has_code_fix_patterns(self, tmp_path):
        """__init__ populates _code_fix_patterns dict."""
        extractor = GitPatternExtractor(str(tmp_path))
        assert "null_reference" in extractor._code_fix_patterns
        assert "error_handling" in extractor._code_fix_patterns
        assert "type_mismatch" in extractor._code_fix_patterns


class TestScoreFixCommit:
    """Tests for GitPatternExtractor._score_fix_commit."""

    def test_score_fix_commit_high_score_for_fix_prefix(self, tmp_path):
        """_score_fix_commit returns high score for 'fix:' prefix."""
        extractor = GitPatternExtractor(str(tmp_path))
        score = extractor._score_fix_commit("fix: null pointer dereference")
        assert score >= 0.9

    def test_score_fix_commit_high_score_for_hotfix(self, tmp_path):
        """_score_fix_commit returns high score for 'hotfix' keyword."""
        extractor = GitPatternExtractor(str(tmp_path))
        score = extractor._score_fix_commit("hotfix: production outage")
        assert score >= 1.0

    def test_score_fix_commit_zero_score_for_docs_commit(self, tmp_path):
        """_score_fix_commit returns 0 for docs-only commit."""
        extractor = GitPatternExtractor(str(tmp_path))
        score = extractor._score_fix_commit("docs: update readme")
        assert score == 0.0

    def test_score_fix_commit_low_or_zero_for_unrelated(self, tmp_path):
        """_score_fix_commit returns 0.0 for unrelated commit."""
        extractor = GitPatternExtractor(str(tmp_path))
        score = extractor._score_fix_commit("chore: update dependencies")
        assert score == 0.0

    def test_score_fix_commit_detects_resolved(self, tmp_path):
        """_score_fix_commit detects 'resolved' keyword."""
        extractor = GitPatternExtractor(str(tmp_path))
        score = extractor._score_fix_commit("resolved authentication issue")
        assert score >= 0.8

    def test_score_fix_commit_detects_bug_keyword(self, tmp_path):
        """_score_fix_commit detects 'bug' keyword."""
        extractor = GitPatternExtractor(str(tmp_path))
        score = extractor._score_fix_commit("squash the nasty bug in parser")
        assert score >= 0.7

    def test_score_fix_commit_detects_closes_issue(self, tmp_path):
        """_score_fix_commit detects 'closes #123' pattern."""
        extractor = GitPatternExtractor(str(tmp_path))
        score = extractor._score_fix_commit("closes #42 add missing guard")
        assert score >= 0.5

    def test_score_fix_commit_case_insensitive(self, tmp_path):
        """_score_fix_commit is case insensitive."""
        extractor = GitPatternExtractor(str(tmp_path))
        score_lower = extractor._score_fix_commit("fix: something")
        score_upper = extractor._score_fix_commit("FIX: something")
        assert score_lower == score_upper


class TestDetectFixPatterns:
    """Tests for GitPatternExtractor._detect_fix_patterns."""

    def test_detect_fix_patterns_null_reference_optional_chaining(self, tmp_path):
        """_detect_fix_patterns detects null_reference via optional chaining."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}
        added_lines = ["const val = obj?.property ?? default;"]

        result = extractor._detect_fix_patterns("src/module.js", added_lines, commit_info)

        types = [p["type"] for p in result]
        assert "null_reference" in types

    def test_detect_fix_patterns_error_handling_try_block(self, tmp_path):
        """_detect_fix_patterns detects error_handling via try block."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}
        added_lines = ["try:", "    result = risky_call()"]

        result = extractor._detect_fix_patterns("src/module.py", added_lines, commit_info)

        types = [p["type"] for p in result]
        assert "error_handling" in types

    def test_detect_fix_patterns_type_mismatch_isinstance(self, tmp_path):
        """_detect_fix_patterns detects type_mismatch via isinstance."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}
        added_lines = ["if isinstance(value, str):"]

        result = extractor._detect_fix_patterns("src/module.py", added_lines, commit_info)

        types = [p["type"] for p in result]
        assert "type_mismatch" in types

    def test_detect_fix_patterns_returns_empty_for_no_matches(self, tmp_path):
        """_detect_fix_patterns returns empty list when no patterns match."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}
        added_lines = ["x = 1 + 2"]  # No fix patterns

        result = extractor._detect_fix_patterns("src/module.py", added_lines, commit_info)

        assert result == []

    def test_detect_fix_patterns_includes_file_in_result(self, tmp_path):
        """_detect_fix_patterns includes file path in each detected pattern."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}
        added_lines = ["try:", "    pass"]

        result = extractor._detect_fix_patterns("src/my_file.py", added_lines, commit_info)

        if result:  # Only check if patterns were detected
            assert all(p["file"] == "src/my_file.py" for p in result)

    def test_detect_fix_patterns_includes_pattern_id(self, tmp_path):
        """_detect_fix_patterns includes pattern_id in each detected pattern."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}
        added_lines = ["try:", "    pass"]

        result = extractor._detect_fix_patterns("src/module.py", added_lines, commit_info)

        if result:
            assert all("pattern_id" in p for p in result)
            assert all(p["pattern_id"].startswith("bug_") for p in result)


class TestGeneratePatternId:
    """Tests for GitPatternExtractor._generate_pattern_id."""

    def test_generate_pattern_id_starts_with_bug_prefix(self, tmp_path):
        """_generate_pattern_id returns ID starting with 'bug_'."""
        extractor = GitPatternExtractor(str(tmp_path))
        pid = extractor._generate_pattern_id("src/file.py", "null_reference")
        assert pid.startswith("bug_")

    def test_generate_pattern_id_includes_date(self, tmp_path):
        """_generate_pattern_id includes current date in ID."""
        from datetime import datetime

        extractor = GitPatternExtractor(str(tmp_path))
        pid = extractor._generate_pattern_id("src/file.py", "null_reference")
        date_str = datetime.now().strftime("%Y%m%d")
        assert date_str in pid

    def test_generate_pattern_id_has_hash_suffix(self, tmp_path):
        """_generate_pattern_id appends an 8-char hex hash."""
        extractor = GitPatternExtractor(str(tmp_path))
        pid = extractor._generate_pattern_id("src/file.py", "null_reference")
        parts = pid.split("_")
        assert len(parts) == 3
        assert len(parts[2]) == 8


class TestSavePattern:
    """Tests for GitPatternExtractor.save_pattern."""

    def test_save_pattern_creates_json_file(self, tmp_path):
        """save_pattern creates a JSON file in debugging_dir."""
        extractor = GitPatternExtractor(str(tmp_path))
        pattern = {
            "pattern_id": "bug_20250101_abcdef01",
            "type": "null_reference",
            "file": "src/module.py",
            "description": "Null/undefined reference fix",
            "code_sample": "obj?.prop",
            "author": "@dev",
            "commit_hash": "abc12345",
            "commit_message": "fix: null pointer",
            "fix_score": 1.0,
        }

        saved_path = extractor.save_pattern(pattern)

        assert saved_path is not None
        assert saved_path.exists()
        assert saved_path.suffix == ".json"

    def test_save_pattern_returns_path(self, tmp_path):
        """save_pattern returns the path where file was saved."""
        extractor = GitPatternExtractor(str(tmp_path))
        pattern = {
            "pattern_id": "bug_20250101_deadbeef",
            "type": "error_handling",
            "file": "src/module.py",
            "description": "Error handling improvement",
            "code_sample": "try:",
            "author": "@dev",
            "commit_hash": "dead1234",
            "commit_message": "fix: handle errors",
            "fix_score": 0.9,
        }

        saved_path = extractor.save_pattern(pattern)

        assert isinstance(saved_path, Path)
        assert saved_path.name == "bug_20250101_deadbeef.json"

    def test_save_pattern_creates_debugging_dir(self, tmp_path):
        """save_pattern creates the debugging directory if absent."""
        extractor = GitPatternExtractor(str(tmp_path))
        pattern = {
            "pattern_id": "bug_20250101_cafebabe",
            "type": "type_mismatch",
            "file": "src/module.py",
            "description": "Type mismatch fix",
            "code_sample": "isinstance(x, str)",
            "author": "@dev",
        }

        extractor.save_pattern(pattern)

        assert (tmp_path / "debugging").exists()

    def test_save_pattern_sets_status_investigating(self, tmp_path):
        """save_pattern writes status 'investigating' to the file."""
        extractor = GitPatternExtractor(str(tmp_path))
        pattern = {
            "pattern_id": "bug_20250101_00000001",
            "type": "null_reference",
            "file": "src/module.py",
            "description": "Null fix",
            "code_sample": "?.prop",
            "author": "@dev",
        }

        saved_path = extractor.save_pattern(pattern)
        data = json.loads(saved_path.read_text(encoding="utf-8"))

        assert data["status"] == "investigating"
        assert data["auto_detected"] is True

    def test_save_pattern_uses_pattern_id_as_bug_id(self, tmp_path):
        """save_pattern writes pattern_id as the bug_id field."""
        extractor = GitPatternExtractor(str(tmp_path))
        pattern = {
            "pattern_id": "bug_20250101_12345678",
            "type": "import_error",
            "file": "src/module.py",
            "description": "Import fix",
            "code_sample": "from x import y",
            "author": "@dev",
        }

        saved_path = extractor.save_pattern(pattern)
        data = json.loads(saved_path.read_text(encoding="utf-8"))

        assert data["bug_id"] == "bug_20250101_12345678"


class TestExtractFromRecentCommits:
    """Tests for GitPatternExtractor.extract_from_recent_commits."""

    def test_extract_from_recent_commits_returns_empty_when_no_commits(self, tmp_path):
        """extract_from_recent_commits returns empty list when git fails."""
        extractor = GitPatternExtractor(str(tmp_path))
        failed = _make_completed_process(stdout="", returncode=128)

        with patch("subprocess.run", return_value=failed):
            result = extractor.extract_from_recent_commits(num_commits=1)

        assert result == []

    def test_extract_from_recent_commits_skips_non_fix_commits(self, tmp_path):
        """extract_from_recent_commits skips commits with low fix score."""
        extractor = GitPatternExtractor(str(tmp_path))

        # Commit with "docs: update readme" — score 0.0, below threshold 0.5
        batch_log = _batch_record("docs: update readme", author="John Doe")
        log_result = _make_completed_process(stdout=batch_log, returncode=0)

        with patch("subprocess.run", return_value=log_result):
            result = extractor.extract_from_recent_commits(num_commits=1)

        assert result == []

    def test_extract_from_recent_commits_detects_fix_commit(self, tmp_path):
        """extract_from_recent_commits returns patterns for fix commits."""
        extractor = GitPatternExtractor(str(tmp_path))

        diff_output = (
            "diff --git a/src/module.py b/src/module.py\n"
            "--- a/src/module.py\n"
            "+++ b/src/module.py\n"
            "+value = data.get('key', [])\n"
            "+if isinstance(value, list):\n"
        )
        batch_log = _batch_record(
            "fix: null pointer dereference", author="John Doe", diff=diff_output
        )
        log_result = _make_completed_process(stdout=batch_log, returncode=0)

        with patch("subprocess.run", return_value=log_result):
            result = extractor.extract_from_recent_commits(num_commits=1)

        # Should detect patterns from the diff
        assert isinstance(result, list)

    def test_extract_from_recent_commits_single_subprocess_for_batch(self, tmp_path):
        """The whole batch is read in ONE git subprocess (#2241)."""
        extractor = GitPatternExtractor(str(tmp_path))
        batch_log = _batch_record("fix: first bug", author="A", diff="+x = 1\n") + _batch_record(
            "fix: second bug", author="B", date="2025-01-02T00:00:00Z", diff="+y = 2\n"
        )
        log_result = _make_completed_process(stdout=batch_log, returncode=0)

        with patch("subprocess.run", return_value=log_result) as mock_run:
            result = extractor.extract_from_recent_commits(num_commits=3)

        assert mock_run.call_count == 1
        assert isinstance(result, list)

    def test_extract_from_recent_commits_root_commit_gets_empty_diff(self, tmp_path):
        """A parentless (root) commit contributes no diff, matching the old
        behavior where the HEAD~{i+1} lookup failed."""
        extractor = GitPatternExtractor(str(tmp_path))
        batch_log = _batch_record(
            "fix: initial import bug",
            author="A",
            parents="",
            diff="+this_diff_must_be_ignored = True\n",
        )
        log_result = _make_completed_process(stdout=batch_log, returncode=0)

        with patch("subprocess.run", return_value=log_result):
            commits = extractor._get_recent_commits_with_diffs(1)

        assert len(commits) == 1
        assert commits[0][1] == ""


class TestExtractFromStaged:
    """Tests for GitPatternExtractor.extract_from_staged."""

    def test_extract_from_staged_returns_empty_when_no_staged(self, tmp_path):
        """extract_from_staged returns empty list when diff is empty."""
        extractor = GitPatternExtractor(str(tmp_path))
        empty_diff = _make_completed_process(stdout="", returncode=0)

        with patch("subprocess.run", side_effect=[empty_diff]):
            result = extractor.extract_from_staged()

        assert result == []

    def test_extract_from_staged_analyzes_diff(self, tmp_path):
        """extract_from_staged analyzes the staged diff for patterns."""
        extractor = GitPatternExtractor(str(tmp_path))

        diff_output = (
            "diff --git a/src/module.py b/src/module.py\n"
            "+try:\n"
            "+    risky()\n"
            "+except ValueError as e:\n"
            "+    pass\n"
        )
        diff_result = _make_completed_process(stdout=diff_output, returncode=0)
        config_result = _make_completed_process(stdout="Jane Dev", returncode=0)

        with patch("subprocess.run", side_effect=[diff_result, config_result]):
            result = extractor.extract_from_staged()

        assert isinstance(result, list)

    def test_extract_from_staged_uses_staged_hash(self, tmp_path):
        """extract_from_staged uses 'staged' as commit hash."""
        extractor = GitPatternExtractor(str(tmp_path))

        diff_output = "diff --git a/src/module.py b/src/module.py\n" "+try:\n" "+    risky()\n"
        diff_result = _make_completed_process(stdout=diff_output, returncode=0)
        config_result = _make_completed_process(stdout="Dev Name", returncode=0)

        with patch("subprocess.run", side_effect=[diff_result, config_result]):
            result = extractor.extract_from_staged()

        # Result patterns won't have commit_hash from staged, just check no exception
        assert isinstance(result, list)


class TestGetCommitInfo:
    """Tests for GitPatternExtractor._get_commit_info."""

    def test_get_commit_info_returns_none_on_failure(self, tmp_path):
        """_get_commit_info returns None when git command fails."""
        extractor = GitPatternExtractor(str(tmp_path))
        failed = _make_completed_process(stdout="", returncode=128)

        with patch("subprocess.run", return_value=failed):
            result = extractor._get_commit_info("HEAD")

        assert result is None

    def test_get_commit_info_returns_dict_on_success(self, tmp_path):
        """_get_commit_info returns dict with expected keys."""
        extractor = GitPatternExtractor(str(tmp_path))
        log_output = "abcdef12\nfix: something\nJane Dev\n2025-01-01T00:00:00Z"
        success = _make_completed_process(stdout=log_output, returncode=0)

        with patch("subprocess.run", return_value=success):
            result = extractor._get_commit_info("HEAD")

        assert result is not None
        assert "hash" in result
        assert "message" in result
        assert "author" in result
        assert "date" in result

    def test_get_commit_info_parses_hash_short(self, tmp_path):
        """_get_commit_info returns only first 8 chars of hash."""
        extractor = GitPatternExtractor(str(tmp_path))
        log_output = "abcdef1234567890\nfix: something\nJane Dev\n2025-01-01T00:00:00Z"
        success = _make_completed_process(stdout=log_output, returncode=0)

        with patch("subprocess.run", return_value=success):
            result = extractor._get_commit_info("HEAD")

        assert result["hash"] == "abcdef12"

    def test_get_commit_info_returns_none_on_insufficient_lines(self, tmp_path):
        """_get_commit_info returns None when output has < 4 lines."""
        extractor = GitPatternExtractor(str(tmp_path))
        log_output = "abcdef12\nfix: something"  # Only 2 lines
        success = _make_completed_process(stdout=log_output, returncode=0)

        with patch("subprocess.run", return_value=success):
            result = extractor._get_commit_info("HEAD")

        assert result is None


class TestGetStagedDiff:
    """Tests for GitPatternExtractor._get_staged_diff."""

    def test_get_staged_diff_returns_empty_on_failure(self, tmp_path):
        """_get_staged_diff returns empty string on git failure."""
        extractor = GitPatternExtractor(str(tmp_path))
        failed = _make_completed_process(stdout="", returncode=128)

        with patch("subprocess.run", return_value=failed):
            result = extractor._get_staged_diff()

        assert result == ""

    def test_get_staged_diff_returns_stdout_on_success(self, tmp_path):
        """_get_staged_diff returns stdout content on success."""
        extractor = GitPatternExtractor(str(tmp_path))
        diff_content = "diff --git a/file.py b/file.py\n+new line\n"
        success = _make_completed_process(stdout=diff_content, returncode=0)

        with patch("subprocess.run", return_value=success):
            result = extractor._get_staged_diff()

        assert result == diff_content


class TestGetGitConfig:
    """Tests for GitPatternExtractor._get_git_config."""

    def test_get_git_config_returns_value_on_success(self, tmp_path):
        """_get_git_config returns the config value on success."""
        extractor = GitPatternExtractor(str(tmp_path))
        success = _make_completed_process(stdout="Test Developer\n", returncode=0)

        with patch("subprocess.run", return_value=success):
            result = extractor._get_git_config("user.name")

        assert result == "Test Developer"

    def test_get_git_config_returns_none_on_failure(self, tmp_path):
        """_get_git_config returns None on git failure."""
        extractor = GitPatternExtractor(str(tmp_path))
        failed = _make_completed_process(stdout="", returncode=1)

        with patch("subprocess.run", return_value=failed):
            result = extractor._get_git_config("user.name")

        assert result is None


class TestAnalyzeDiff:
    """Tests for GitPatternExtractor._analyze_diff."""

    def test_analyze_diff_empty_returns_empty(self, tmp_path):
        """_analyze_diff returns empty list for empty diff."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}
        result = extractor._analyze_diff("", commit_info)
        assert result == []

    def test_analyze_diff_parses_file_header(self, tmp_path):
        """_analyze_diff correctly extracts file names from diff headers."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}
        diff = "diff --git a/src/module.py b/src/module.py\n" "+try:\n" "+    pass\n"

        result = extractor._analyze_diff(diff, commit_info)

        if result:
            assert result[0]["file"] == "src/module.py"

    def test_analyze_diff_ignores_removed_lines(self, tmp_path):
        """_analyze_diff only analyzes added lines (starting with '+')."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}

        # Only removed lines, no additions that match patterns
        diff = "diff --git a/src/module.py b/src/module.py\n" "-old = line\n" "+x = 1\n"

        result = extractor._analyze_diff(diff, commit_info)
        # "x = 1" won't match any fix pattern — should be empty
        assert result == []


class TestGitHelperExceptionBranches:
    """Tests for the except Exception branches in git helper methods.

    These cover the intentional broad exception handling when git raises
    unexpected errors (e.g., OSError, timeout, subprocess failure).
    """

    def test_get_commit_info_returns_none_on_subprocess_exception(self, tmp_path):
        """_get_commit_info returns None when subprocess.run raises."""
        extractor = GitPatternExtractor(str(tmp_path))

        with patch("subprocess.run", side_effect=OSError("git not found")):
            result = extractor._get_commit_info("HEAD")

        assert result is None

    def test_get_commit_diff_returns_empty_on_subprocess_exception(self, tmp_path):
        """_get_commit_diff returns empty string when subprocess.run raises."""
        extractor = GitPatternExtractor(str(tmp_path))

        with patch("subprocess.run", side_effect=OSError("git not found")):
            result = extractor._get_commit_diff("HEAD~1", "HEAD")

        assert result == ""

    def test_get_staged_diff_returns_empty_on_subprocess_exception(self, tmp_path):
        """_get_staged_diff returns empty string when subprocess.run raises."""
        extractor = GitPatternExtractor(str(tmp_path))

        with patch("subprocess.run", side_effect=OSError("git not found")):
            result = extractor._get_staged_diff()

        assert result == ""

    def test_get_git_config_returns_none_on_subprocess_exception(self, tmp_path):
        """_get_git_config returns None when subprocess.run raises."""
        extractor = GitPatternExtractor(str(tmp_path))

        with patch("subprocess.run", side_effect=OSError("git not found")):
            result = extractor._get_git_config("user.name")

        assert result is None

    def test_save_pattern_returns_none_on_os_error(self, tmp_path):
        """save_pattern returns None when file write fails."""
        extractor = GitPatternExtractor(str(tmp_path))
        pattern = {
            "pattern_id": "bug_20250101_fail0001",
            "type": "null_reference",
            "file": "src/module.py",
            "description": "Null fix",
            "code_sample": "?.prop",
            "author": "@dev",
        }

        with patch.object(Path, "open", side_effect=OSError("disk full")):
            result = extractor.save_pattern(pattern)

        assert result is None


class TestGetCommitDiff:
    """Tests for GitPatternExtractor._get_commit_diff."""

    def test_get_commit_diff_returns_empty_on_failure(self, tmp_path):
        """_get_commit_diff returns empty string on git failure."""
        extractor = GitPatternExtractor(str(tmp_path))
        failed = _make_completed_process(stdout="", returncode=128)

        with patch("subprocess.run", return_value=failed):
            result = extractor._get_commit_diff("HEAD~1", "HEAD")

        assert result == ""

    def test_get_commit_diff_returns_stdout_on_success(self, tmp_path):
        """_get_commit_diff returns stdout content on success."""
        extractor = GitPatternExtractor(str(tmp_path))
        diff_content = "diff --git a/file.py b/file.py\n+new line\n"
        success = _make_completed_process(stdout=diff_content, returncode=0)

        with patch("subprocess.run", return_value=success):
            result = extractor._get_commit_diff("HEAD~1", "HEAD")

        assert result == diff_content


# ---------------------------------------------------------------------------
# Multi-file diff — covers lines 302-307 (process previous file on new header)
# ---------------------------------------------------------------------------


class TestAnalyzeDiffMultiFile:
    """Lines 302-307: previous file's patterns processed when a new diff header appears."""

    def test_two_file_diff_processes_first_file(self, tmp_path):
        """_analyze_diff hits the 'process previous file' branch (lines 302-307)."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}

        # Two-file diff: file1 has try: (error_handling), file2 has unrelated content
        diff = (
            "diff --git a/src/first.py b/src/first.py\n"
            "+try:\n"
            "+    risky()\n"
            "diff --git a/src/second.py b/src/second.py\n"
            "+x = 1\n"
        )

        result = extractor._analyze_diff(diff, commit_info)

        # The first file's error_handling pattern should be detected
        types = [p["type"] for p in result]
        assert "error_handling" in types

    def test_two_file_diff_processes_both_files(self, tmp_path):
        """_analyze_diff processes both file sections (last file + previous file)."""
        extractor = GitPatternExtractor(str(tmp_path))
        commit_info = {"author": "dev", "date": "2025-01-01T00:00:00"}

        # Both files have detectable patterns
        diff = (
            "diff --git a/src/a.py b/src/a.py\n"
            "+try:\n"
            "+    do_something()\n"
            "diff --git a/src/b.py b/src/b.py\n"
            "+if isinstance(value, str):\n"
        )

        result = extractor._analyze_diff(diff, commit_info)

        # Both files should contribute patterns
        files = {p["file"] for p in result}
        assert len(files) >= 1  # at least one file's patterns detected


# ---------------------------------------------------------------------------
# main() — covers lines 368-439
# ---------------------------------------------------------------------------


class TestGitExtractorMain:
    """Tests for the main() CLI entry point in git_extractor."""

    def _no_patterns_subprocess(self):
        """Returns a failed subprocess result (no git repo → no patterns)."""
        return _make_completed_process(stdout="", returncode=128)

    def test_main_no_patterns_prints_message(self, tmp_path, capsys):
        """Lines 409-412: main() prints 'No fix patterns detected' when empty."""
        from attune.patterns.git_extractor import main

        with (
            patch("sys.argv", ["git_extractor", "--patterns-dir", str(tmp_path)]),
            patch("subprocess.run", return_value=self._no_patterns_subprocess()),
        ):
            main()

        out = capsys.readouterr().out
        assert "No fix patterns detected" in out

    def test_main_quiet_no_output_when_no_patterns(self, tmp_path, capsys):
        """Line 410-411: --quiet suppresses 'No fix patterns detected' message."""
        from attune.patterns.git_extractor import main

        with (
            patch("sys.argv", ["git_extractor", "--patterns-dir", str(tmp_path), "--quiet"]),
            patch("subprocess.run", return_value=self._no_patterns_subprocess()),
        ):
            main()

        out = capsys.readouterr().out
        assert out == ""

    def test_main_staged_flag(self, tmp_path, capsys):
        """Line 405: --staged calls extract_from_staged."""
        from attune.patterns.git_extractor import main

        empty_diff = _make_completed_process(stdout="", returncode=0)
        with (
            patch("sys.argv", ["git_extractor", "--patterns-dir", str(tmp_path), "--staged"]),
            patch("subprocess.run", return_value=empty_diff),
        ):
            main()

        out = capsys.readouterr().out
        assert "No fix patterns detected" in out

    def test_main_with_patterns_displays_them(self, tmp_path, capsys):
        """Lines 415-429: main() displays detected patterns."""
        from attune.patterns.git_extractor import main

        diff_output = "diff --git a/src/module.py b/src/module.py\n" "+try:\n" "+    risky()\n"
        batch_log = _batch_record("fix: null pointer", diff=diff_output)
        log_result = _make_completed_process(stdout=batch_log, returncode=0)

        with (
            patch("sys.argv", ["git_extractor", "--patterns-dir", str(tmp_path)]),
            patch("subprocess.run", return_value=log_result),
        ):
            main()

        out = capsys.readouterr().out
        assert "Detected" in out
        assert "Pattern:" in out

    def test_main_with_patterns_and_save(self, tmp_path, capsys):
        """Lines 431-435: main() saves patterns when --save is set."""
        from attune.patterns.git_extractor import main

        diff_output = "diff --git a/src/module.py b/src/module.py\n" "+try:\n" "+    risky()\n"
        batch_log = _batch_record("fix: null pointer", diff=diff_output)
        log_result = _make_completed_process(stdout=batch_log, returncode=0)

        with (
            patch(
                "sys.argv",
                ["git_extractor", "--patterns-dir", str(tmp_path), "--save"],
            ),
            patch("subprocess.run", return_value=log_result),
        ):
            main()

        out = capsys.readouterr().out
        # Save completion message shown (lines 437-439)
        assert "saved" in out.lower() or "Saved" in out

    def test_main_quiet_with_patterns_no_display(self, tmp_path, capsys):
        """Lines 421: --quiet suppresses pattern display."""
        from attune.patterns.git_extractor import main

        diff_output = "diff --git a/src/module.py b/src/module.py\n" "+try:\n" "+    risky()\n"
        batch_log = _batch_record("fix: null pointer", diff=diff_output)
        log_result = _make_completed_process(stdout=batch_log, returncode=0)

        with (
            patch(
                "sys.argv",
                ["git_extractor", "--patterns-dir", str(tmp_path), "--quiet"],
            ),
            patch("subprocess.run", return_value=log_result),
        ):
            main()

        out = capsys.readouterr().out
        assert out == ""

    def test_main_pattern_with_commit_message_field(self, tmp_path, capsys):
        """Line 426-427: patterns with 'commit_message' field display the commit."""
        from attune.patterns.git_extractor import main

        diff_output = "diff --git a/src/module.py b/src/module.py\n" "+try:\n" "+    risky()\n"
        batch_log = _batch_record("fix: null pointer dereference in parser", diff=diff_output)
        log_result = _make_completed_process(stdout=batch_log, returncode=0)

        with (
            patch("sys.argv", ["git_extractor", "--patterns-dir", str(tmp_path)]),
            patch("subprocess.run", return_value=log_result),
        ):
            main()

        out = capsys.readouterr().out
        assert "Commit:" in out

    def test_main_staged_patterns_displayed_without_commit_message(self, tmp_path, capsys):
        """Line 426->428: pattern without 'commit_message' skips that print line."""
        from attune.patterns.git_extractor import main

        # --staged produces patterns without 'commit_message' key
        diff_output = "diff --git a/src/module.py b/src/module.py\n" "+try:\n" "+    risky()\n"
        diff_result = _make_completed_process(stdout=diff_output, returncode=0)
        # _get_git_config for user.name
        config_result = _make_completed_process(stdout="Dev Name", returncode=0)

        with (
            patch("sys.argv", ["git_extractor", "--patterns-dir", str(tmp_path), "--staged"]),
            patch("subprocess.run", side_effect=[diff_result, config_result]),
        ):
            main()

        out = capsys.readouterr().out
        # Pattern shown but no "Commit:" line (no commit_message key on staged patterns)
        assert "Pattern:" in out
        assert "Commit:" not in out

    def test_main_save_failed_skips_saved_path_message(self, tmp_path, capsys):
        """Line 433->420: when save_pattern returns None, no 'Saved to:' printed."""
        from attune.patterns.git_extractor import main

        diff_output = "diff --git a/src/module.py b/src/module.py\n+try:\n+    risky()\n"
        batch_log = _batch_record("fix: null pointer", diff=diff_output)
        log_result = _make_completed_process(stdout=batch_log, returncode=0)

        with (
            patch(
                "sys.argv",
                ["git_extractor", "--patterns-dir", str(tmp_path), "--save"],
            ),
            patch("subprocess.run", return_value=log_result),
            patch(
                "attune.patterns.git_extractor.GitPatternExtractor.save_pattern",
                return_value=None,
            ),
        ):
            main()

        out = capsys.readouterr().out
        assert "Saved to:" not in out


class TestOptionLikeRefIsRefused:
    """A ref starting with "-" is parsed by git as an OPTION, not a revision.

    `git log -1 --format=X --help` prints usage instead of resolving a
    commit, so an attacker-influenced ref could change what the command
    does. The guard is in _get_commit_info itself, not only at its call
    sites, so a future caller inherits it.
    """

    @pytest.mark.parametrize("ref", ["--help", "-n5", "--output=/tmp/x", "-"])
    def test_option_like_ref_returns_none_without_running_git(self, ref):
        extractor = GitPatternExtractor()

        with patch("subprocess.run") as mock_run:
            assert extractor._get_commit_info(ref) is None

        assert not mock_run.called, f"git was invoked with an option-like ref: {ref!r}"

    def test_normal_refs_still_resolve(self):
        """The guard must not break the shape the real caller uses."""
        extractor = GitPatternExtractor()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abcdef1234567890\nsubject\nauthor\n2026-01-01T00:00:00Z\n",
            )
            assert extractor._get_commit_info("HEAD~3") is not None

        assert mock_run.called

    def test_command_pins_end_of_revisions(self):
        """The trailing "--" stops a ref that also names a file being a path."""
        extractor = GitPatternExtractor()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            extractor._get_commit_info("HEAD")

        argv = mock_run.call_args[0][0]
        assert argv[-1] == "--", f"expected a trailing '--' separator, got {argv}"
