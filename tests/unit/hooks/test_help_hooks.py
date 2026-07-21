"""Tests for plugin help hooks.

Covers:
- help_on_error.py (PostToolUse hook)
- help_post_commit.py (PostToolUse hook)

Each hook reads JSON from stdin and writes to stderr.
All hooks exit 0 always (informational, never block).
"""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

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

    def test_skips_when_exit_code_zero(self, mod) -> None:
        """No suggestion when exit_code is explicitly 0."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "pip install foo"},
                "tool_result": {
                    "exit_code": 0,
                    "stderr": "ModuleNotFoundError: something",
                },
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert stderr_capture.getvalue() == ""

    def test_matches_when_exit_code_nonzero(self, mod) -> None:
        """Suggests help when exit_code is non-zero."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "python x.py"},
                "tool_result": {
                    "exit_code": 1,
                    "stderr": "ModuleNotFoundError: No module named 'x'",
                },
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert "/coach imports" in stderr_capture.getvalue()

    def test_matches_when_no_exit_code_field(self, mod) -> None:
        """Backward compat: matches when exit_code not in result."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "python x.py"},
                "tool_result": {"stderr": "ModuleNotFoundError: no module"},
            }
        )
        stderr_capture = StringIO()
        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
        ):
            mod.main()
        assert "/coach imports" in stderr_capture.getvalue()


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

    def test_stale_feature_warns_without_regenerating(self, mod, tmp_path: Path) -> None:
        """Check-only end-to-end: stale feature → stderr warning, no regen.

        Regression guard for docs/specs/post-commit-help-check-only:
        the generator stub raises if the hook path ever reaches the
        regenerating branch, and template bytes must be untouched.
        """
        pytest.importorskip("yaml")
        from attune.help.generator import generate_feature_templates
        from attune.help.manifest import Feature, FeatureManifest, save_manifest

        src = tmp_path / "src" / "auth"
        src.mkdir(parents=True)
        (src / "login.py").write_text("def login(): pass\n", encoding="utf-8")
        manifest = FeatureManifest(
            version=1,
            features={
                "auth": Feature(
                    name="auth",
                    description="Authentication",
                    files=["src/auth/**"],
                ),
            },
        )
        help_dir = tmp_path / ".help"
        save_manifest(manifest, help_dir)
        generate_feature_templates(manifest.features["auth"], help_dir, tmp_path)

        # Make the feature stale
        (src / "login.py").write_text("def login(user): pass\n", encoding="utf-8")

        template_dir = help_dir / "templates" / "auth"
        before = {p: p.read_bytes() for p in sorted(template_dir.rglob("*")) if p.is_file()}

        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m 'test'"},
                "tool_result": {"stdout": "[main abc1234] test"},
            }
        )
        stderr_capture = StringIO()

        def _forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("post-commit hook reached the regenerating branch")

        with (
            patch("sys.stdin", StringIO(payload)),
            patch("sys.stderr", stderr_capture),
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch(
                "attune.help.maintenance.get_changed_files",
                return_value=["src/auth/login.py"],
            ),
            patch(
                "attune.help.maintenance.generate_feature_templates",
                side_effect=_forbidden,
            ),
        ):
            mod.main()

        output = stderr_capture.getvalue()
        assert "1 help feature(s) are stale (auth)" in output
        assert "/coach maintain" in output
        assert "auto-updated" not in output
        after = {p: p.read_bytes() for p in sorted(template_dir.rglob("*")) if p.is_file()}
        assert after == before, "post-commit hook must not write template files"

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
