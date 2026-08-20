"""Tests for worktree_path_guard.py PreToolUse hook.

Validates the first concrete enforcement under the framework in
docs/specs/enforcement-vs-documentation/.

Covers:

- Allow when target path matches session worktree
- Block (exit 2) when target path is in a different worktree
- Allow when target is under an allowlisted external root
  (default ~/.attune/memory, extendable via
  ATTUNE_WORKTREE_GUARD_ALLOW)
- Allow when target file's directory doesn't exist yet (degraded)
- Allow when tool isn't Edit/Write
- Allow when path is relative (no wrong-tree risk)
- Allow when file_path is missing
- Metrics log appended per fire
- Hook errors don't break tool calls (exit 0 on exception)
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import runpy
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
# Allowlisted external roots → allow
# ---------------------------------------------------------------------


def _read_metrics(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line]


class TestAllowlist:
    def test_default_allowlist_contains_attune_memory(self, hook_module):
        """The shipped default allowlist covers the curated-memory repo."""
        roots = hook_module._allowed_external_roots()
        assert Path.home() / ".attune" / "memory" in roots

    def test_default_allowlist_covers_sibling_project_repos(self, hook_module):
        """Sibling project repos are allowlisted (retro 2026-08-12) —
        cross-repo work from an attune-ai session is deliberate."""
        roots = hook_module._allowed_external_roots()
        for repo in ("attune-forms", "attune-author", "attune-help", "attune-verify"):
            assert Path.home() / repo in roots

    def test_main_checkout_stays_off_the_allowlist(self, hook_module):
        """~/attune-ai must NEVER be allowlisted: worktree-vs-main
        confusion is the accident class this guard exists to catch."""
        roots = hook_module._allowed_external_roots()
        assert Path.home() / "attune-ai" not in roots

    def test_default_attune_memory_write_passes(
        self, hook_module, isolated_metrics_log, two_git_trees, monkeypatch, tmp_path
    ):
        """A write into ~/.attune/memory (a separate git tree) passes
        via the default allowlist even from inside another worktree."""
        tree_a, _ = two_git_trees
        fake_home = tmp_path / "fake-home"
        memory = fake_home / ".attune" / "memory"
        memory.mkdir(parents=True)
        subprocess.run(["git", "init", "--quiet"], cwd=memory, check=True, timeout=5)
        # ~ expands via HOME on POSIX, USERPROFILE on Windows.
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.setenv("USERPROFILE", str(fake_home))
        monkeypatch.chdir(tree_a)
        target = memory / "note.md"
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert code == 0
        records = _read_metrics(isolated_metrics_log)
        assert len(records) == 1
        assert records[0]["outcome"] == "allowlisted"

    def test_env_var_extends_allowlist(
        self, hook_module, isolated_metrics_log, two_git_trees, monkeypatch
    ):
        """ATTUNE_WORKTREE_GUARD_ALLOW adds roots without a code edit."""
        tree_a, tree_b = two_git_trees
        monkeypatch.setenv(hook_module.ALLOWLIST_ENV_VAR, str(tree_b))
        monkeypatch.chdir(tree_a)
        target = tree_b / "external.md"
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert code == 0
        records = _read_metrics(isolated_metrics_log)
        assert records[0]["outcome"] == "allowlisted"

    def test_env_var_multiple_entries(
        self, hook_module, isolated_metrics_log, two_git_trees, monkeypatch, tmp_path
    ):
        """The env var is os.pathsep-separated; a match in any entry allows."""
        tree_a, tree_b = two_git_trees
        other = tmp_path / "some-other-root"
        other.mkdir()
        monkeypatch.setenv(
            hook_module.ALLOWLIST_ENV_VAR, os.pathsep.join([str(other), str(tree_b)])
        )
        monkeypatch.chdir(tree_a)
        target = tree_b / "external.md"
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert code == 0
        records = _read_metrics(isolated_metrics_log)
        assert records[0]["outcome"] == "allowlisted"

    def test_non_allowlisted_cross_tree_still_blocks(
        self, hook_module, isolated_metrics_log, two_git_trees, monkeypatch, tmp_path, capsys
    ):
        """Default-deny survives: a cross-tree write to a root NOT on the
        allowlist still blocks, and the message names the allowlist."""
        tree_a, tree_b = two_git_trees
        unrelated = tmp_path / "unrelated-allowed-root"
        unrelated.mkdir()
        monkeypatch.setenv(hook_module.ALLOWLIST_ENV_VAR, str(unrelated))
        monkeypatch.chdir(tree_a)
        target = tree_b / "wrong_tree.py"
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert code == 2
        captured = capsys.readouterr()
        assert "BLOCKED" in captured.err
        assert hook_module.ALLOWLIST_ENV_VAR in captured.err
        assert "DEFAULT_ALLOWED_EXTERNAL_ROOTS" in captured.err
        records = _read_metrics(isolated_metrics_log)
        assert records[0]["outcome"] == "fired"

    def test_sibling_of_allowlisted_root_blocks(
        self, hook_module, isolated_metrics_log, two_git_trees, monkeypatch
    ):
        """A sibling dir sharing the allowlisted root's name as a prefix
        (memory vs memory-evil) must NOT match the allowlist."""
        tree_a, tree_b = two_git_trees
        allowed = tree_b / "memory"
        sibling = tree_b / "memory-evil"
        allowed.mkdir()
        sibling.mkdir()
        monkeypatch.setenv(hook_module.ALLOWLIST_ENV_VAR, str(allowed))
        monkeypatch.chdir(tree_a)
        target = sibling / "sneaky.md"
        code = hook_module.main({"tool_name": "Write", "tool_input": {"file_path": str(target)}})
        assert code == 2
        records = _read_metrics(isolated_metrics_log)
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
    def test_main_propagates_unexpected_errors(self, hook_module, tmp_path):
        """The script's __main__ block catches all Exceptions and
        exits 0 — but main() itself should propagate so callers can
        observe errors in tests."""
        # Patch _git_toplevel to raise to verify the script-level
        # exception handler at __main__ would catch it. Use tmp_path
        # so the input is absolute on Windows too (a literal "/tmp/x.py"
        # is_absolute() returns False on Windows because there's no
        # drive letter — main() would early-return before reaching
        # the patched _git_toplevel).
        target = tmp_path / "x.py"
        with patch.object(hook_module, "_git_toplevel", side_effect=RuntimeError("oops")):
            with pytest.raises(RuntimeError):
                hook_module.main(
                    {
                        "tool_name": "Write",
                        "tool_input": {"file_path": str(target)},
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


# ---------------------------------------------------------------------
# Script-level coverage: _read_stdin_context + __main__ block
# ---------------------------------------------------------------------


class TestReadStdinContext:
    def test_empty_stdin_returns_empty_dict(self, hook_module, monkeypatch):
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        assert hook_module._read_stdin_context() == {}

    def test_invalid_json_returns_empty_dict(self, hook_module, monkeypatch):
        monkeypatch.setattr(sys, "stdin", io.StringIO("not-json{"))
        assert hook_module._read_stdin_context() == {}

    def test_valid_json_returns_parsed_dict(self, hook_module, monkeypatch):
        payload = '{"tool_name": "Write", "tool_input": {"file_path": "x"}}'
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        assert hook_module._read_stdin_context() == {
            "tool_name": "Write",
            "tool_input": {"file_path": "x"},
        }


class TestScriptMainEntry:
    """Cover the `if __name__ == "__main__":` block via runpy."""

    def test_script_with_empty_stdin_exits_0(self, monkeypatch):
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
        assert exc_info.value.code == 0

    def test_script_with_skip_context_exits_0(self, monkeypatch):
        """A Bash tool context routes through main() and exits 0."""
        ctx = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(ctx))
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
        assert exc_info.value.code == 0

    def test_script_catches_main_exception_and_exits_0(self, monkeypatch, capsys):
        """If main() raises, the wrapper prints to stderr and exits 0 —
        a hook bug must never block real work."""
        # Pass a malformed tool_input (string, not dict) to provoke an
        # AttributeError inside main() when it calls .get on tool_input.
        bad_ctx = '{"tool_name": "Write", "tool_input": "not-a-dict"}'
        monkeypatch.setattr(sys, "stdin", io.StringIO(bad_ctx))
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "hook error" in captured.err
        assert "AttributeError" in captured.err


def test_deeply_nested_json_exits_0():
    """Library-review L4: 3000-deep JSON overflows the parser (which
    runs before main()'s guard); the reader must absorb the
    RecursionError and fail open (exit 0)."""
    import subprocess
    import sys

    payload = '{"a":' * 3000 + "1" + "}" * 3000
    result = subprocess.run(
        [sys.executable, "src/attune/hooks/scripts/worktree_path_guard.py"],
        input=payload,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
