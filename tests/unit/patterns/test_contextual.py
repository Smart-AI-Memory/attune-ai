"""Unit tests for attune.patterns.contextual.

Covers ContextualPatternInjector and the CLI main() entry point.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from attune.patterns.contextual import ContextualPatternInjector, main

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_bug(dir_path: Path, bug_id: str, **fields):
    dir_path.mkdir(parents=True, exist_ok=True)
    bug = {"bug_id": bug_id, **fields}
    (dir_path / f"bug_{bug_id}.json").write_text(json.dumps(bug))
    return bug


def _write_security_decisions(dir_path: Path, decisions):
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "team_decisions.json").write_text(json.dumps({"decisions": decisions}))


# ---------------------------------------------------------------------------
# _load_all_bugs
# ---------------------------------------------------------------------------


class TestLoadAllBugs:
    def test_loads_bugs_from_debugging_dirs(self, tmp_path):
        debug_dir = tmp_path / "debugging"
        _write_bug(
            debug_dir,
            "001",
            status="resolved",
            error_type="null_reference",
            file_path="src/api.py",
        )

        injector = ContextualPatternInjector(str(tmp_path))
        bugs = injector._load_all_bugs()
        assert len(bugs) == 1
        assert bugs[0]["bug_id"] == "001"
        assert "_source" in bugs[0]

    def test_loads_from_multiple_debug_dirs(self, tmp_path):
        _write_bug(tmp_path / "debugging", "001")
        _write_bug(tmp_path / "debugging_demo", "002")
        _write_bug(tmp_path / "repo_test" / "debugging", "003")

        injector = ContextualPatternInjector(str(tmp_path))
        bugs = injector._load_all_bugs()
        assert len(bugs) == 3

    def test_skips_missing_dirs(self, tmp_path):
        # No debugging dirs created
        injector = ContextualPatternInjector(str(tmp_path))
        assert injector._load_all_bugs() == []

    def test_skips_malformed_json(self, tmp_path):
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        # Valid bug
        (debug_dir / "bug_ok.json").write_text(json.dumps({"bug_id": "ok"}))
        # Malformed JSON
        (debug_dir / "bug_bad.json").write_text("not-json{")

        injector = ContextualPatternInjector(str(tmp_path))
        bugs = injector._load_all_bugs()
        assert len(bugs) == 1
        assert bugs[0]["bug_id"] == "ok"

    def test_uses_cache_on_second_call(self, tmp_path):
        debug_dir = tmp_path / "debugging"
        _write_bug(debug_dir, "001")

        injector = ContextualPatternInjector(str(tmp_path))
        bugs1 = injector._load_all_bugs()
        # Add another bug to disk after first load
        _write_bug(debug_dir, "002")
        # Cache should still return the original list
        bugs2 = injector._load_all_bugs()
        assert len(bugs2) == 1
        assert bugs1 is bugs2  # exact same cached list


# ---------------------------------------------------------------------------
# _load_all_security
# ---------------------------------------------------------------------------


class TestLoadAllSecurity:
    def test_loads_decisions(self, tmp_path):
        sec_dir = tmp_path / "security"
        _write_security_decisions(
            sec_dir,
            [{"finding_hash": "sql_injection", "decision": "block"}],
        )

        injector = ContextualPatternInjector(str(tmp_path))
        decisions = injector._load_all_security()
        assert len(decisions) == 1
        assert decisions[0]["finding_hash"] == "sql_injection"

    def test_loads_from_multiple_security_dirs(self, tmp_path):
        _write_security_decisions(tmp_path / "security", [{"finding_hash": "a"}])
        _write_security_decisions(tmp_path / "security_demo", [{"finding_hash": "b"}])
        _write_security_decisions(tmp_path / "repo_test" / "security", [{"finding_hash": "c"}])

        injector = ContextualPatternInjector(str(tmp_path))
        decisions = injector._load_all_security()
        assert len(decisions) == 3

    def test_skips_missing_files(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        assert injector._load_all_security() == []

    def test_skips_malformed_json(self, tmp_path):
        sec_dir = tmp_path / "security"
        sec_dir.mkdir()
        (sec_dir / "team_decisions.json").write_text("not-json{")

        injector = ContextualPatternInjector(str(tmp_path))
        assert injector._load_all_security() == []

    def test_uses_cache(self, tmp_path):
        sec_dir = tmp_path / "security"
        _write_security_decisions(sec_dir, [{"finding_hash": "x"}])

        injector = ContextualPatternInjector(str(tmp_path))
        first = injector._load_all_security()
        # Mutate file
        _write_security_decisions(sec_dir, [{"finding_hash": "y"}, {"finding_hash": "z"}])
        second = injector._load_all_security()
        assert first is second  # cached


# ---------------------------------------------------------------------------
# _score_bugs
# ---------------------------------------------------------------------------


class TestScoreBugs:
    def test_resolved_bug_gets_status_score(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{"status": "resolved"}]
        scored = injector._score_bugs(bugs, None, None, None)
        assert scored[0]["_relevance_score"] >= 0.3

    def test_unresolved_bug_no_status_score(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{"status": "open"}]
        scored = injector._score_bugs(bugs, None, None, None)
        assert scored[0]["_relevance_score"] == 0.0

    def test_error_type_match_boosts_score(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{"error_type": "null_reference"}]
        scored = injector._score_bugs(bugs, None, "null_reference", None)
        assert scored[0]["_relevance_score"] >= 0.5

    def test_file_extension_match_boosts_score(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{"file_path": "src/api.py"}]
        scored = injector._score_bugs(bugs, "tests/test_api.py", None, None)
        # Both .py — should get +0.2
        assert scored[0]["_relevance_score"] >= 0.2

    def test_file_extension_mismatch_no_boost(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{"file_path": "src/api.py"}]
        scored = injector._score_bugs(bugs, "tests/test.js", None, None)
        # .py vs .js — no extension boost
        assert scored[0]["_relevance_score"] == 0.0

    def test_error_message_keyword_match(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{"error_message": "Connection timeout to database"}]
        scored = injector._score_bugs(
            bugs,
            None,
            None,
            "timeout connecting to database server",
        )
        # 'timeout' and 'database' / 'to' overlap → some boost
        assert scored[0]["_relevance_score"] > 0.0

    def test_error_message_no_overlap_no_boost(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{"error_message": "X Y Z"}]
        scored = injector._score_bugs(bugs, None, None, "A B C")
        assert scored[0]["_relevance_score"] == 0.0

    def test_error_message_overlap_capped(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        # Many overlapping words → score capped at 0.2
        msg = " ".join(f"word{i}" for i in range(100))
        bugs = [{"error_message": msg}]
        scored = injector._score_bugs(bugs, None, None, msg)
        assert scored[0]["_relevance_score"] == 0.2

    def test_recent_bug_boosted(self, tmp_path):
        from datetime import datetime, timezone

        injector = ContextualPatternInjector(str(tmp_path))
        recent_iso = datetime.now(timezone.utc).isoformat()
        bugs = [{"date": recent_iso}]
        scored = injector._score_bugs(bugs, None, None, None)
        assert scored[0]["_relevance_score"] >= 0.1

    def test_old_bug_not_boosted(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{"date": "2010-01-01T00:00:00Z"}]
        scored = injector._score_bugs(bugs, None, None, None)
        assert scored[0]["_relevance_score"] == 0.0

    def test_invalid_date_swallowed(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{"date": "not-a-date"}]
        # Should not raise
        scored = injector._score_bugs(bugs, None, None, None)
        assert scored[0]["_relevance_score"] == 0.0

    def test_missing_date_swallowed(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [{}]
        scored = injector._score_bugs(bugs, None, None, None)
        assert scored[0]["_relevance_score"] == 0.0

    def test_sorted_by_score_descending(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        bugs = [
            {"status": "open"},  # 0.0
            {"status": "resolved", "error_type": "x"},  # 0.3 + 0.5 = 0.8
            {"status": "resolved"},  # 0.3
        ]
        scored = injector._score_bugs(bugs, None, "x", None)
        assert scored[0]["_relevance_score"] == 0.8
        assert scored[-1]["_relevance_score"] == 0.0


# ---------------------------------------------------------------------------
# _filter_security
# ---------------------------------------------------------------------------


class TestFilterSecurity:
    def test_no_file_path_returns_top_three(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        decisions = [{"finding_hash": str(i)} for i in range(5)]
        result = injector._filter_security(decisions, None)
        assert len(result) == 3

    def test_filters_by_python_extension(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        decisions = [
            {"finding_hash": "sql_injection"},
            {"finding_hash": "xss"},  # not for .py
            {"finding_hash": "command_injection"},
        ]
        result = injector._filter_security(decisions, "src/api.py")
        hashes = {d["finding_hash"] for d in result}
        assert "sql_injection" in hashes
        assert "command_injection" in hashes
        assert "xss" not in hashes

    def test_unknown_extension_falls_back_to_top_two(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        decisions = [{"finding_hash": str(i)} for i in range(5)]
        result = injector._filter_security(decisions, "config.yaml")
        # No mapping for .yaml + no matches → fallback top 2
        assert len(result) == 2

    def test_known_extension_with_no_matches_falls_back(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        # .py expects sql_injection / command_injection / path_traversal,
        # but our decisions don't have any of those → fallback
        decisions = [
            {"finding_hash": "totally_unrelated_1"},
            {"finding_hash": "totally_unrelated_2"},
            {"finding_hash": "totally_unrelated_3"},
        ]
        result = injector._filter_security(decisions, "src/api.py")
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _file_type_matches
# ---------------------------------------------------------------------------


class TestFileTypeMatches:
    def test_match(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        assert injector._file_type_matches("a.py", ".py") is True

    def test_mismatch(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        assert injector._file_type_matches("a.py", ".js") is False


# ---------------------------------------------------------------------------
# _get_git_changed_files
# ---------------------------------------------------------------------------


class TestGetGitChangedFiles:
    def test_success(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = "a.py\nb.py\n"
        with patch(
            "attune.patterns.contextual.subprocess.run",
            return_value=fake_result,
        ):
            assert injector._get_git_changed_files() == ["a.py", "b.py"]

    def test_nonzero_returncode_returns_empty(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        fake_result = MagicMock()
        fake_result.returncode = 128
        fake_result.stdout = ""
        with patch(
            "attune.patterns.contextual.subprocess.run",
            return_value=fake_result,
        ):
            assert injector._get_git_changed_files() == []

    def test_subprocess_error_caught(self, tmp_path):
        import subprocess as sp

        injector = ContextualPatternInjector(str(tmp_path))
        with patch(
            "attune.patterns.contextual.subprocess.run",
            side_effect=sp.SubprocessError("git missing"),
        ):
            assert injector._get_git_changed_files() == []

    def test_unexpected_exception_caught(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        with patch(
            "attune.patterns.contextual.subprocess.run",
            side_effect=RuntimeError("weird"),
        ):
            assert injector._get_git_changed_files() == []


# ---------------------------------------------------------------------------
# get_relevant_patterns
# ---------------------------------------------------------------------------


class TestGetRelevantPatterns:
    def test_with_bugs_and_security(self, tmp_path):
        _write_bug(
            tmp_path / "debugging",
            "001",
            status="resolved",
            error_type="null_reference",
            file_path="src/api.py",
            root_cause="missing check",
            fix_applied="add check",
            fix_code="if x is not None:",
        )
        _write_security_decisions(
            tmp_path / "security",
            [
                {
                    "finding_hash": "sql_injection",
                    "decision": "block",
                    "reason": "always",
                }
            ],
        )

        injector = ContextualPatternInjector(str(tmp_path))
        out = injector.get_relevant_patterns(
            file_path="src/foo.py",
            error_type="null_reference",
            error_message="NoneType has no attribute",
            max_patterns=3,
        )
        assert "Bug Patterns" in out
        assert "001" in out
        assert "Security Decisions" in out
        assert "sql_injection" in out

    def test_without_security(self, tmp_path):
        _write_bug(tmp_path / "debugging", "001", status="resolved")
        injector = ContextualPatternInjector(str(tmp_path))
        out = injector.get_relevant_patterns(include_security=False)
        assert "Bug Patterns" in out
        assert "Security Decisions" not in out

    def test_no_patterns_yields_no_match_message(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        out = injector.get_relevant_patterns()
        assert "No matching bug patterns" in out


# ---------------------------------------------------------------------------
# get_patterns_for_review
# ---------------------------------------------------------------------------


class TestGetPatternsForReview:
    def test_returns_resolved_bugs_per_file(self, tmp_path):
        _write_bug(
            tmp_path / "debugging",
            "py1",
            status="resolved",
            file_path="src/a.py",
        )
        _write_bug(
            tmp_path / "debugging",
            "js1",
            status="resolved",
            file_path="src/b.js",
        )
        _write_bug(
            tmp_path / "debugging",
            "py_open",
            status="open",
            file_path="src/c.py",
        )

        injector = ContextualPatternInjector(str(tmp_path))
        result = injector.get_patterns_for_review(["app.py", "main.js"])
        # app.py gets the resolved .py bug; not the unresolved one
        py_ids = [b["bug_id"] for b in result["app.py"]]
        assert "py1" in py_ids
        assert "py_open" not in py_ids
        # main.js gets the .js bug
        assert any(b["bug_id"] == "js1" for b in result["main.js"])

    def test_max_per_file_truncates(self, tmp_path):
        debug_dir = tmp_path / "debugging"
        for i in range(5):
            _write_bug(debug_dir, f"py{i}", status="resolved", file_path="src/x.py")

        injector = ContextualPatternInjector(str(tmp_path))
        result = injector.get_patterns_for_review(["app.py"], max_per_file=2)
        assert len(result["app.py"]) == 2


# ---------------------------------------------------------------------------
# get_patterns_from_git_changes
# ---------------------------------------------------------------------------


class TestGetPatternsFromGitChanges:
    def test_no_changes_returns_message(self, tmp_path):
        injector = ContextualPatternInjector(str(tmp_path))
        with patch.object(injector, "_get_git_changed_files", return_value=[]):
            out = injector.get_patterns_from_git_changes()
        assert "No recent git changes" in out

    def test_returns_patterns_for_changed_extensions(self, tmp_path):
        _write_bug(
            tmp_path / "debugging",
            "py1",
            status="resolved",
            file_path="src/a.py",
            error_type="x",
        )
        _write_bug(
            tmp_path / "debugging",
            "js1",
            status="resolved",
            file_path="src/b.js",
            error_type="y",
        )

        injector = ContextualPatternInjector(str(tmp_path))
        with patch.object(
            injector,
            "_get_git_changed_files",
            return_value=["src/main.py", "src/util.py"],
        ):
            out = injector.get_patterns_from_git_changes()
        # Only .py bug should be included
        assert "py1" in out
        assert "js1" not in out

    def test_changed_files_without_extensions_skipped(self, tmp_path):
        _write_bug(
            tmp_path / "debugging",
            "py1",
            status="resolved",
            file_path="src/a.py",
        )
        injector = ContextualPatternInjector(str(tmp_path))
        # Files with no extension contribute nothing to the extensions set
        with patch.object(
            injector,
            "_get_git_changed_files",
            return_value=["Makefile", "Dockerfile"],
        ):
            out = injector.get_patterns_from_git_changes()
        # .py bug shouldn't match (no .py changed)
        assert "py1" not in out


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------


class TestClearCache:
    def test_clear_cache_invalidates(self, tmp_path):
        debug_dir = tmp_path / "debugging"
        _write_bug(debug_dir, "001")

        injector = ContextualPatternInjector(str(tmp_path))
        injector._load_all_bugs()  # populate cache
        assert "bugs" in injector._cache

        injector.clear_cache()
        assert injector._cache == {}


# ---------------------------------------------------------------------------
# CLI main()
# ---------------------------------------------------------------------------


class TestCLIMain:
    def test_main_with_args(self, tmp_path, capsys):
        _write_bug(
            tmp_path / "debugging",
            "001",
            status="resolved",
            error_type="null_reference",
        )
        argv = [
            "prog",
            "--patterns-dir",
            str(tmp_path),
            "--file",
            "src/api.py",
            "--error-type",
            "null_reference",
            "--max",
            "3",
        ]
        with patch.object(sys, "argv", argv):
            main()
        out = capsys.readouterr().out
        assert "Relevant Patterns" in out

    def test_main_with_git_flag(self, tmp_path, capsys):
        argv = ["prog", "--patterns-dir", str(tmp_path), "--git"]
        with (
            patch.object(sys, "argv", argv),
            patch(
                "attune.patterns.contextual.ContextualPatternInjector._get_git_changed_files",
                return_value=[],
            ),
        ):
            main()
        out = capsys.readouterr().out
        assert "No recent git changes" in out
