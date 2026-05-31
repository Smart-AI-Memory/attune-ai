"""Tests for worktree_path_guard.py PreToolUse hook.

Validates the first concrete enforcement under the framework in
docs/specs/enforcement-vs-documentation/.

Covers:

- Allow when target path matches session worktree
- Block (exit 2) when target path is in a different worktree
- Allow when target file's directory doesn't exist yet (degraded)
- Allow when tool isn't Edit/Write
- Allow when path is relative (no wrong-tree risk)
- Allow when file_path is missing
- Metrics log appended per fire
- Hook errors don't break tool calls (exit 0 on exception)
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "attune"
    / "hooks"
    / "scripts"
    / "worktree_path_guard.py"
)


@pytest.fixture(scope="module")
def hook_module():
    """Load worktree_path_guard.py for direct function testing."""
    spec = importlib.util.spec_from_file_location("_worktree_path_guard", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_worktree_path_guard"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def isolated_metrics_log(tmp_path, hook_module, monkeypatch):
    """Redirect the metrics log to a tmp file so tests don't pollute
    the user's real ~/.attune/enforcement-metrics.jsonl."""
    log_path = tmp_path / "enforcement-metrics.jsonl"
    monkeypatch.setattr(hook_module, "METRICS_LOG", log_path)
    return log_path


@pytest.fixture
def two_git_trees(tmp_path):
    """Create two separate git worktrees so we can test mismatch."""
    tree_a = tmp_path / "tree-a"
    tree_b = tmp_path / "tree-b"
    for tree in (tree_a, tree_b):
        tree.mkdir()
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=tree,
            check=True,
            timeout=5,
        )
    return tree_a, tree_b


# ---------------------------------------------------------------------
# Skip cases (early returns)
# ---------------------------------------------------------------------


class TestSkipCases:
    def test_skips_non_edit_write_tool(self, hook_module, isolated_metrics_log):
        code = hook_module.main({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        assert code == 0
        # No metric should be logged for skipped tools.
        assert not isolated_metrics_log.exists() or isolated_metrics_log.read_text() == ""

    def test_skips_missing_file_path(self, hook_module, isolated_metrics_log):
        code = hook_module.main({"tool_name": "Write", "tool_input": {}})
        assert code == 0

    def test_skips_relative_path(self, hook_module, isolated_metrics_log):
        """Relative paths resolve against session cwd; no wrong-tree risk."""
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": "foo.py"}})
        assert code == 0


# ---------------------------------------------------------------------
# Same worktree → allow
# ---------------------------------------------------------------------


class TestSameWorktreeAllow:
    def test_allows_when_target_in_same_tree(
        self, hook_module, isolated_metrics_log, two_git_trees, monkeypatch
    ):
        tree_a, _ = two_git_trees
        target = tree_a / "new_file.py"
        # Run hook with session cwd inside tree_a, target also inside tree_a
        monkeypatch.chdir(tree_a)
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert code == 0
        # Should have logged "allowed"
        records = [
            json.loads(line)
            for line in isolated_metrics_log.read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert len(records) == 1
        assert records[0]["outcome"] == "allowed"


# ---------------------------------------------------------------------
# Different worktree → block
# ---------------------------------------------------------------------


class TestDifferentWorktreeBlock:
    def test_blocks_when_target_in_different_tree(
        self, hook_module, isolated_metrics_log, two_git_trees, monkeypatch, capsys
    ):
        tree_a, tree_b = two_git_trees
        target = tree_b / "wrong_tree.py"
        monkeypatch.chdir(tree_a)
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert code == 2
        captured = capsys.readouterr()
        assert "BLOCKED" in captured.err
        assert str(tree_a) in captured.err
        assert str(tree_b) in captured.err
        # Metric: "fired"
        records = [
            json.loads(line)
            for line in isolated_metrics_log.read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert len(records) == 1
        assert records[0]["outcome"] == "fired"


# ---------------------------------------------------------------------
# Degraded modes (allow when unsure)
# ---------------------------------------------------------------------


class TestDegradedAllows:
    def test_allows_when_target_parent_missing(
        self, hook_module, isolated_metrics_log, two_git_trees, monkeypatch
    ):
        tree_a, _ = two_git_trees
        monkeypatch.chdir(tree_a)
        target = tree_a / "nonexistent" / "subdir" / "file.py"
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert code == 0
        records = [
            json.loads(line)
            for line in isolated_metrics_log.read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert records[0]["outcome"] == "unknown"

    def test_allows_when_target_not_in_git_tree(
        self, hook_module, isolated_metrics_log, tmp_path, two_git_trees, monkeypatch
    ):
        """Target file is in a non-git directory → can't compare; allow."""
        tree_a, _ = two_git_trees
        monkeypatch.chdir(tree_a)
        non_git = tmp_path / "non-git-dir"
        non_git.mkdir()
        target = non_git / "file.py"
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert code == 0
        records = [
            json.loads(line)
            for line in isolated_metrics_log.read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert records[0]["outcome"] == "unknown"


# ---------------------------------------------------------------------
# Hook error handling (script-level, exception path)
# ---------------------------------------------------------------------


class TestHookErrorHandling:
    def test_main_propagates_unexpected_errors(self, hook_module):
        """The script's __main__ block catches all Exceptions and
        exits 0 — but main() itself should propagate so callers can
        observe errors in tests."""
        # Patch _git_toplevel to raise to verify the script-level
        # exception handler at __main__ would catch it.
        with patch.object(hook_module, "_git_toplevel", side_effect=RuntimeError("oops")):
            with pytest.raises(RuntimeError):
                hook_module.main(
                    {
                        "tool_name": "Write",
                        "tool_input": {"file_path": "/tmp/x.py"},
                    }
                )


# ---------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------


class TestMetrics:
    def test_metric_record_shape(
        self, hook_module, isolated_metrics_log, two_git_trees, monkeypatch
    ):
        """Each metric record has ts, enforcement, outcome, session_root,
        target_root keys."""
        tree_a, _ = two_git_trees
        monkeypatch.chdir(tree_a)
        target = tree_a / "x.py"
        hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        records = [
            json.loads(line)
            for line in isolated_metrics_log.read_text(encoding="utf-8").splitlines()
            if line
        ]
        record = records[0]
        assert set(record.keys()) >= {
            "ts",
            "enforcement",
            "outcome",
            "session_root",
            "target_root",
        }
        assert record["enforcement"] == "worktree_path_guard"

    def test_metric_log_failure_does_not_break_main(
        self, hook_module, two_git_trees, monkeypatch, tmp_path
    ):
        """If the metrics log can't be written, main() must still
        return the right exit code."""
        tree_a, _ = two_git_trees
        # Point the log at a path we can't write to.
        unwritable = tmp_path / "no-perm" / "log.jsonl"
        monkeypatch.setattr(hook_module, "METRICS_LOG", unwritable)
        monkeypatch.chdir(tree_a)
        # _log_metric internally swallows OSError; main() returns 0.
        code = hook_module.main(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": str(tree_a / "x.py")},
            }
        )
        assert code == 0
