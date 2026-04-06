"""Tests for plugin help hooks.

Covers:
- help_freshness_check.py (SessionStart hook)
- help_on_error.py (PostToolUse hook)
- help_post_commit.py (PostToolUse hook)

Each hook reads JSON from stdin and writes to stderr.
All hooks exit 0 always (informational, never block).
"""

from __future__ import annotations

import hashlib
import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# ── help_freshness_check ─────────────────────────────────


class TestHelpFreshnessCheck:
    """Tests for plugin/hooks/help_freshness_check.py."""

    def _run_main(self, plugin_root: Path) -> str:
        """Run freshness check main() and capture stderr."""
        import importlib

        # Load the module from the plugin hooks directory
        spec_path = (
            Path(__file__).resolve().parents[3] / "plugin" / "hooks" / "help_freshness_check.py"
        )
        spec = importlib.util.spec_from_file_location("help_freshness_check", spec_path)
        mod = importlib.util.module_from_spec(spec)

        stderr_capture = StringIO()
        with (
            patch.object(mod, "__file__", str(plugin_root / "hooks" / "check.py")),
            patch("sys.stderr", stderr_capture),
        ):
            # Patch the Path(__file__) resolution inside main
            with patch(
                "pathlib.Path.resolve",
                side_effect=lambda self: (
                    plugin_root / "hooks" / "check.py"
                    if "check" in str(self) or "freshness" in str(self)
                    else Path.resolve(self)
                ),
            ):
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                mod.main()

        return stderr_capture.getvalue()

    def test_returns_early_when_no_manifest(self, tmp_path: Path) -> None:
        """Exits silently when source_manifest.json absent."""
        import importlib.util

        spec_path = (
            Path(__file__).resolve().parents[3] / "plugin" / "hooks" / "help_freshness_check.py"
        )
        spec = importlib.util.spec_from_file_location("help_freshness_check", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        # Create a fake plugin structure with no manifest
        hooks_dir = tmp_path / "plugin" / "hooks"
        hooks_dir.mkdir(parents=True)
        generated_dir = tmp_path / "plugin" / "help" / "generated"
        generated_dir.mkdir(parents=True)
        # No source_manifest.json

        stderr_capture = StringIO()
        with (
            patch("sys.stderr", stderr_capture),
            patch.object(Path, "resolve", return_value=hooks_dir / "check.py"),
        ):
            mod.main()

        assert stderr_capture.getvalue() == ""

    def test_returns_early_when_manifest_fresh(self, tmp_path: Path) -> None:
        """Exits silently when mtime < 24h old."""
        import importlib.util

        spec_path = (
            Path(__file__).resolve().parents[3] / "plugin" / "hooks" / "help_freshness_check.py"
        )
        spec = importlib.util.spec_from_file_location("help_freshness_check", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        # Build fake plugin structure
        plugin_root = tmp_path / "plugin"
        hooks_dir = plugin_root / "hooks"
        hooks_dir.mkdir(parents=True)
        generated_dir = plugin_root / "help" / "generated"
        generated_dir.mkdir(parents=True)
        manifest_path = generated_dir / "source_manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        # mtime is now (< 24h)

        stderr_capture = StringIO()
        with (
            patch("sys.stderr", stderr_capture),
            patch.object(Path, "resolve", return_value=hooks_dir / "check.py"),
        ):
            mod.main()

        assert stderr_capture.getvalue() == ""

    def test_hash_file(self, tmp_path: Path) -> None:
        """Verifies correct SHA-256 hash."""
        import importlib.util

        spec_path = (
            Path(__file__).resolve().parents[3] / "plugin" / "hooks" / "help_freshness_check.py"
        )
        spec = importlib.util.spec_from_file_location("help_freshness_check", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        test_file = tmp_path / "test.txt"
        content = b"hello world"
        test_file.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()
        assert mod._hash_file(test_file) == expected


# ── help_on_error ─────────────────────────────────────────


class TestHelpOnError:
    """Tests for plugin/hooks/help_on_error.py."""

    @pytest.fixture()
    def mod(self):
        """Load the help_on_error module."""
        import importlib.util

        spec_path = Path(__file__).resolve().parents[3] / "plugin" / "hooks" / "help_on_error.py"
        spec = importlib.util.spec_from_file_location("help_on_error", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    def test_ignores_non_bash_tool(self, mod) -> None:
        """Non-Bash tool_name produces no output."""
        payload = json.dumps(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "x.py"},
                "tool_result": {"stderr": "ModuleNotFoundError: no mod"},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_matches_module_not_found_error(self, mod) -> None:
        """ModuleNotFoundError triggers /coach imports suggestion."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "python x.py"},
                "tool_result": {"stderr": "ModuleNotFoundError: No module named 'foo'"},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert "/coach imports" in stderr_capture.getvalue()

    def test_matches_pytest_pattern(self, mod) -> None:
        """pytest in stderr triggers /coach smart-test suggestion."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "pytest tests/"},
                "tool_result": {"stderr": "pytest: error: unrecognized args"},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert "/coach smart-test" in stderr_capture.getvalue()

    def test_no_output_for_unrecognized_error(self, mod) -> None:
        """Unrecognized stderr produces no output."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls /bad"},
                "tool_result": {"stderr": "No such file or directory"},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_handles_empty_stdin(self, mod) -> None:
        """Empty input exits silently."""
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO("")),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_handles_result_as_string(self, mod) -> None:
        """Uses string result as stderr."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "python x.py"},
                "tool_result": "ImportError: cannot import name 'foo'",
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert "/coach imports" in stderr_capture.getvalue()

    def test_no_stderr_in_result(self, mod) -> None:
        """No output when stderr is empty."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "echo hi"},
                "tool_result": {"stderr": ""},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""


# ── help_post_commit ──────────────────────────────────────


class TestHelpPostCommit:
    """Tests for plugin/hooks/help_post_commit.py."""

    @pytest.fixture()
    def mod(self):
        """Load the help_post_commit module."""
        import importlib.util

        spec_path = Path(__file__).resolve().parents[3] / "plugin" / "hooks" / "help_post_commit.py"
        spec = importlib.util.spec_from_file_location("help_post_commit", spec_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    def test_ignores_non_bash_tool(self, mod) -> None:
        """Non-Bash tool_name exits silently."""
        payload = json.dumps(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "x.py"},
                "tool_result": "ok",
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_ignores_non_git_commit(self, mod) -> None:
        """Non-commit Bash command exits silently."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git status"},
                "tool_result": "on branch main",
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_ignores_nothing_to_commit(self, mod) -> None:
        """'nothing to commit' in stdout exits silently."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m 'test'"},
                "tool_result": {"stdout": "nothing to commit, working tree clean"},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_returns_silently_when_no_features_yaml(self, mod, tmp_path: Path) -> None:
        """No .help/features.yaml in cwd tree exits silently."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m 'test'"},
                "tool_result": {"stdout": "[main abc1234] test"},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_handles_empty_stdin(self, mod) -> None:
        """Empty input exits silently."""
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO("")),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_handles_invalid_json(self, mod) -> None:
        """Invalid JSON exits silently."""
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO("{bad json")),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_handles_import_error_gracefully(self, mod, tmp_path: Path) -> None:
        """Import failure inside try/except exits silently."""
        # Create .help/features.yaml so the hook tries to import
        help_dir = tmp_path / ".help"
        help_dir.mkdir()
        (help_dir / "features.yaml").write_text("version: 1\n", encoding="utf-8")

        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m 'test'"},
                "tool_result": {"stdout": "[main abc1234] test"},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
            patch("pathlib.Path.cwd", return_value=tmp_path),
            # Make the import fail
            patch.dict(
                "sys.modules",
                {"attune": None, "attune.help": None, "attune.help.maintenance": None},
            ),
        ):
            mod.main()
        # Should not crash
        assert True

    def test_tool_input_as_string(self, mod) -> None:
        """Handles tool_input as a plain string."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": "git commit -m 'test'",
                "tool_result": {"stdout": "nothing to commit"},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""
