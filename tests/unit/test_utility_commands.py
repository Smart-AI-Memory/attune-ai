"""Tests for utility_commands.py.

Tests for setup, validate, version, and features commands.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.cli_commands.utility_commands import (
    cmd_features,
    cmd_setup,
    cmd_validate,
    cmd_version,
)


# ---------------------------------------------------------------------------
# cmd_setup tests
# ---------------------------------------------------------------------------
class TestCmdSetup:
    """Tests for cmd_setup."""

    def _make_args(self) -> argparse.Namespace:
        """Create args namespace for setup command."""
        return argparse.Namespace()

    def test_setup_source_dir_not_found(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test setup returns 1 when no source directory found."""
        args = self._make_args()

        # Create a fake package layout with no "commands" directory at any
        # of the fallback locations.
        fake_pkg = tmp_path / "fake_pkg" / "cli_commands"
        fake_pkg.mkdir(parents=True)
        fake_file = fake_pkg / "utility_commands.py"
        fake_file.write_text("")

        # Point __file__ at the fake location so Path(__file__).parent.parent
        # resolves to tmp_path/fake_pkg  (which has no "commands" subdir)
        import attune.cli_commands.utility_commands as mod

        monkeypatch.setattr(mod, "__file__", str(fake_file))

        # cwd also has no .claude/commands
        monkeypatch.chdir(tmp_path)

        # Force importlib.resources.files to fail so fallback paths are tried
        with patch("importlib.resources.files", side_effect=ImportError("no resources")):
            result = cmd_setup(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Could not find" in captured.out

    def test_setup_copies_md_files(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test setup copies .md files from source to target."""
        args = self._make_args()

        # Build a fake package layout: fake_pkg/commands/ with .md files
        fake_pkg = tmp_path / "fake_pkg" / "cli_commands"
        fake_pkg.mkdir(parents=True)
        fake_file = fake_pkg / "utility_commands.py"
        fake_file.write_text("")

        source_dir = tmp_path / "fake_pkg" / "commands"
        source_dir.mkdir()
        (source_dir / "dev.md").write_text("# Dev Hub")
        (source_dir / "testing.md").write_text("# Testing Hub")
        (source_dir / "not_a_command.txt").write_text("ignore me")
        # Create agents subdir so iterdir() does not raise FileNotFoundError
        (source_dir / "agents").mkdir()

        import attune.cli_commands.utility_commands as mod

        monkeypatch.setattr(mod, "__file__", str(fake_file))
        monkeypatch.chdir(tmp_path)

        # Redirect Path.home() so target goes to tmp_path
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

        with patch("importlib.resources.files", side_effect=ImportError):
            result = cmd_setup(args)

        # Should find the source dir and install .md files
        captured = capsys.readouterr()
        assert "dev.md" in captured.out
        assert "testing.md" in captured.out
        assert "not_a_command.txt" not in captured.out
        assert result == 0

    def test_setup_no_command_files_found(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test setup returns 1 when source dir exists but has no .md files."""
        args = self._make_args()

        # Create source dir via cwd fallback: .claude/commands with no .md files
        cwd_dir = tmp_path / "project"
        cwd_dir.mkdir()
        source_dir = cwd_dir / ".claude" / "commands"
        source_dir.mkdir(parents=True)
        (source_dir / "readme.txt").write_text("not a command")
        # Create agents subdir (empty) to avoid FileNotFoundError from iterdir()
        (source_dir / "agents").mkdir()

        # The package fallback paths should not have "commands" either
        fake_pkg = tmp_path / "fake_pkg" / "cli_commands"
        fake_pkg.mkdir(parents=True)
        fake_file = fake_pkg / "utility_commands.py"
        fake_file.write_text("")

        import attune.cli_commands.utility_commands as mod

        monkeypatch.setattr(mod, "__file__", str(fake_file))
        monkeypatch.chdir(cwd_dir)

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

        with patch("importlib.resources.files", side_effect=ImportError):
            result = cmd_setup(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No command files found" in captured.out


# ---------------------------------------------------------------------------
# cmd_validate tests
# ---------------------------------------------------------------------------
class TestCmdValidate:
    """Tests for cmd_validate."""

    def _make_args(self) -> argparse.Namespace:
        """Create args namespace for validate command."""
        return argparse.Namespace()

    def test_validate_no_api_keys(
        self,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test validate returns 1 when no API keys and no subscription auth."""
        args = self._make_args()

        env = {
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "CLAUDE_CODE_OAUTH_TOKEN": "",
        }
        # No ~/.claude dir under tmp_path → no subscription-auth evidence
        # (setup-friction F2/F3: keyless is only an error when there's no
        # Claude Code login evidence either).
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch.dict("os.environ", env, clear=False):
            with patch("os.environ.get", side_effect=lambda k, *a: env.get(k, "")):
                with patch(
                    "attune.workflows.WORKFLOW_REGISTRY",
                    {"wf1": MagicMock(), "wf2": MagicMock()},
                ):
                    result = cmd_validate(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Validation failed" in captured.out
        assert "No auth found" in captured.out

    def test_validate_with_anthropic_key(self, capsys: pytest.CaptureFixture) -> None:
        """Test validate succeeds with ANTHROPIC_API_KEY set."""
        args = self._make_args()

        env_patch = {
            "ANTHROPIC_API_KEY": "sk-test-key-123",
            "OPENAI_API_KEY": "",
            "GOOGLE_API_KEY": "",
        }

        with (
            patch.dict("os.environ", env_patch, clear=False),
            patch(
                "attune.workflows.WORKFLOW_REGISTRY",
                {"wf1": MagicMock()},
            ),
        ):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Anthropic" in captured.out
        assert "Configuration is valid" in captured.out

    def test_validate_without_any_key(
        self,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test validate fails when no API key and no subscription auth."""
        args = self._make_args()

        env_patch = {
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_CODE_OAUTH_TOKEN": "",
        }
        # No ~/.claude dir under tmp_path → no subscription-auth evidence,
        # regardless of the developer machine running the test.
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with (
            patch.dict("os.environ", env_patch, clear=False),
            patch(
                "attune.workflows.WORKFLOW_REGISTRY",
                {"wf1": MagicMock()},
            ),
        ):
            result = cmd_validate(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.out

    def test_validate_config_file_found(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test validate detects config file when present."""
        args = self._make_args()

        # Create a config file in the working directory
        config_file = tmp_path / "attune.config.json"
        config_file.write_text('{"test": true}')
        monkeypatch.chdir(tmp_path)

        env_patch = {
            "ANTHROPIC_API_KEY": "sk-test",
        }

        with (
            patch.dict("os.environ", env_patch, clear=False),
            patch(
                "attune.workflows.WORKFLOW_REGISTRY",
                {"wf1": MagicMock()},
            ),
        ):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Config file" in captured.out
        assert "attune.config.json" in captured.out

    def test_validate_no_config_file_warning(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test validate warns when no config file exists."""
        args = self._make_args()

        monkeypatch.chdir(tmp_path)

        env_patch = {
            "ANTHROPIC_API_KEY": "sk-test",
        }

        with (
            patch.dict("os.environ", env_patch, clear=False),
            patch(
                "attune.workflows.WORKFLOW_REGISTRY",
                {"wf1": MagicMock()},
            ),
        ):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No attune.config file found" in captured.out or "Warnings" in captured.out

    def test_validate_workflow_import_error(
        self,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test validate handles workflow import failure gracefully."""
        args = self._make_args()

        env_patch = {
            "ANTHROPIC_API_KEY": "sk-test",
        }

        # Force the WORKFLOW_REGISTRY import inside cmd_validate to raise ImportError.
        # The function does: from attune.workflows import WORKFLOW_REGISTRY
        # We remove the module from sys.modules temporarily and insert a broken one.
        sys.modules.get("attune.workflows")

        def _fake_import(name: str, *a: object, **kw: object) -> object:
            if name == "attune.workflows":
                raise ImportError("Workflows unavailable for testing")
            return original_import(name, *a, **kw)

        import builtins

        original_import = builtins.__import__

        with patch.dict("os.environ", env_patch, clear=False):
            monkeypatch.setattr(builtins, "__import__", _fake_import)
            try:
                result = cmd_validate(args)
            finally:
                monkeypatch.setattr(builtins, "__import__", original_import)

        # Should still succeed (warning, not error)
        assert result == 0
        captured = capsys.readouterr()
        assert "Configuration is valid" in captured.out

    def test_validate_shows_workflow_count(self, capsys: pytest.CaptureFixture) -> None:
        """Test validate displays number of registered workflows."""
        args = self._make_args()

        env_patch = {"ANTHROPIC_API_KEY": "sk-test"}
        mock_workflows = {"sec-audit": MagicMock(), "code-review": MagicMock(), "perf": MagicMock()}

        with (
            patch.dict("os.environ", env_patch, clear=False),
            patch(
                "attune.workflows.discover_workflows",
                return_value=mock_workflows,
            ),
        ):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "3 workflows available" in captured.out


# ---------------------------------------------------------------------------
# cmd_version tests
# ---------------------------------------------------------------------------
class TestCmdVersion:
    """Tests for cmd_version."""

    def test_version_basic(self, capsys: pytest.CaptureFixture) -> None:
        """Test basic version output."""
        args = argparse.Namespace(verbose=False)

        with patch("attune.cli_minimal.get_version", return_value="2.6.3"):
            result = cmd_version(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "attune-ai 2.6.3" in captured.out

    def test_version_verbose(self, capsys: pytest.CaptureFixture) -> None:
        """Test verbose version output includes Python and platform info."""
        args = argparse.Namespace(verbose=True)

        with patch("attune.cli_minimal.get_version", return_value="2.6.3"):
            result = cmd_version(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "attune-ai 2.6.3" in captured.out
        assert "Python:" in captured.out
        assert "Platform:" in captured.out
        assert sys.platform in captured.out

    def test_version_verbose_with_dependencies(self, capsys: pytest.CaptureFixture) -> None:
        """Test verbose version shows dependency count."""
        args = argparse.Namespace(verbose=True)

        mock_reqs = ["dep1>=1.0", "dep2>=2.0", "dep3>=3.0"]

        with patch("attune.cli_minimal.get_version", return_value="2.6.3"):
            with patch("importlib.metadata.requires", return_value=mock_reqs):
                result = cmd_version(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Dependencies: 3" in captured.out

    def test_version_verbose_no_metadata(self, capsys: pytest.CaptureFixture) -> None:
        """Test verbose version handles missing metadata gracefully."""
        args = argparse.Namespace(verbose=True)

        with (
            patch("attune.cli_minimal.get_version", return_value="dev"),
            patch(
                "importlib.metadata.requires",
                side_effect=Exception("Package not found"),
            ),
        ):
            result = cmd_version(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "attune-ai dev" in captured.out
        # Should not crash; dependencies line is optional
        assert "Dependencies" not in captured.out

    def test_version_non_verbose_no_python_info(self, capsys: pytest.CaptureFixture) -> None:
        """Test non-verbose output does not include Python/platform info."""
        args = argparse.Namespace(verbose=False)

        with patch("attune.cli_minimal.get_version", return_value="1.0.0"):
            result = cmd_version(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Python:" not in captured.out
        assert "Platform:" not in captured.out

    def test_version_returns_zero(self) -> None:
        """Test version always returns 0."""
        args = argparse.Namespace(verbose=False)

        with patch("attune.cli_minimal.get_version", return_value="0.0.1"):
            result = cmd_version(args)

        assert result == 0


# ---------------------------------------------------------------------------
# cmd_features tests
# ---------------------------------------------------------------------------
class TestCmdFeatures:
    """Tests for cmd_features."""

    def _make_args(self) -> argparse.Namespace:
        """Create args namespace for features command."""
        return argparse.Namespace()

    def test_features_runs_without_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test cmd_features executes and returns 0."""
        args = self._make_args()

        # Mock both feature classes to control output
        mock_memory_features = self._make_mock_memory_features()
        mock_telemetry_features = self._make_mock_telemetry_features()

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory_features,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry_features,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=False,
            ),
        ):
            result = cmd_features(args)

        assert result == 0

    def test_features_displays_memory_section(self, capsys: pytest.CaptureFixture) -> None:
        """Test cmd_features displays MEMORY FEATURES section."""
        args = self._make_args()

        mock_memory_features = self._make_mock_memory_features()
        mock_telemetry_features = self._make_mock_telemetry_features()

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory_features,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry_features,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=False,
            ),
        ):
            cmd_features(args)

        captured = capsys.readouterr()
        assert "MEMORY FEATURES" in captured.out

    def test_features_displays_telemetry_section(self, capsys: pytest.CaptureFixture) -> None:
        """Test cmd_features displays TELEMETRY FEATURES section."""
        args = self._make_args()

        mock_memory_features = self._make_mock_memory_features()
        mock_telemetry_features = self._make_mock_telemetry_features()

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory_features,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry_features,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=False,
            ),
        ):
            cmd_features(args)

        captured = capsys.readouterr()
        assert "TELEMETRY FEATURES" in captured.out

    def test_features_displays_feature_names(self, capsys: pytest.CaptureFixture) -> None:
        """Test cmd_features displays individual feature names."""
        args = self._make_args()

        mock_memory_features = self._make_mock_memory_features()
        mock_telemetry_features = self._make_mock_telemetry_features()

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory_features,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry_features,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=False,
            ),
        ):
            cmd_features(args)

        captured = capsys.readouterr()
        assert "Long-term memory" in captured.out
        assert "Short-term memory" in captured.out
        assert "Usage tracking" in captured.out

    def test_features_redis_not_available_shows_install(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test cmd_features shows install instructions when Redis is not available."""
        args = self._make_args()

        mock_memory_features = self._make_mock_memory_features()
        mock_telemetry_features = self._make_mock_telemetry_features()

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory_features,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry_features,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=False,
            ),
        ):
            cmd_features(args)

        captured = capsys.readouterr()
        assert "pip install" in captured.out
        assert "--force-reinstall 'redis>=5.0.0,<9.0.0'" in captured.out

    def test_features_redis_available_and_running(self, capsys: pytest.CaptureFixture) -> None:
        """Test cmd_features shows all-good when Redis is available and running."""
        args = self._make_args()

        mock_memory_features = self._make_mock_memory_features(redis_available=True)
        mock_telemetry_features = self._make_mock_telemetry_features(redis_available=True)

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory_features,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry_features,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=True,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_running",
                return_value=True,
            ),
        ):
            cmd_features(args)

        captured = capsys.readouterr()
        assert "all features available" in captured.out

    def test_features_redis_available_not_running(self, capsys: pytest.CaptureFixture) -> None:
        """Test cmd_features warns when Redis is installed but server not running."""
        args = self._make_args()

        mock_memory_features = self._make_mock_memory_features(redis_available=True)
        mock_telemetry_features = self._make_mock_telemetry_features(redis_available=True)

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory_features,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry_features,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=True,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_running",
                return_value=False,
            ),
        ):
            cmd_features(args)

        captured = capsys.readouterr()
        assert "not running" in captured.out

    def test_features_shows_install_command_for_missing_deps(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test cmd_features shows install_command for unavailable features."""
        args = self._make_args()

        from attune.memory.features import FeatureInfo
        from attune.memory.features import FeatureStatus as MemFeatureStatus

        # One feature with missing dependency and install command
        mock_memory = {
            "short_term": FeatureInfo(
                name="Short-term memory",
                status=MemFeatureStatus.MISSING_DEPENDENCY,
                message="Redis package not importable",
                install_command="pip install --force-reinstall 'redis>=5.0.0,<9.0.0'",
            ),
        }

        from attune.telemetry.features import FeatureInfo as TelFeatureInfo
        from attune.telemetry.features import FeatureStatus as TelFeatureStatus

        mock_telemetry = {
            "usage_tracking": TelFeatureInfo(
                name="Usage tracking",
                status=TelFeatureStatus.AVAILABLE,
                message="Core feature",
            ),
        }

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=False,
            ),
        ):
            cmd_features(args)

        captured = capsys.readouterr()
        assert "Install:" in captured.out
        assert "--force-reinstall 'redis>=5.0.0,<9.0.0'" in captured.out

    def test_features_shows_header(self, capsys: pytest.CaptureFixture) -> None:
        """Test cmd_features shows the FEATURE AVAILABILITY header."""
        args = self._make_args()

        mock_memory_features = self._make_mock_memory_features()
        mock_telemetry_features = self._make_mock_telemetry_features()

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory_features,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry_features,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=False,
            ),
        ):
            cmd_features(args)

        captured = capsys.readouterr()
        assert "FEATURE AVAILABILITY" in captured.out

    def test_features_returns_zero(self) -> None:
        """Test cmd_features always returns 0."""
        args = self._make_args()

        mock_memory_features = self._make_mock_memory_features()
        mock_telemetry_features = self._make_mock_telemetry_features()

        with (
            patch(
                "attune.memory.features.MemoryFeatures.list_all_features",
                return_value=mock_memory_features,
            ),
            patch(
                "attune.telemetry.features.TelemetryFeatures.list_all_features",
                return_value=mock_telemetry_features,
            ),
            patch(
                "attune.memory.features.MemoryFeatures.is_redis_available",
                return_value=False,
            ),
        ):
            result = cmd_features(args)

        assert result == 0

    # --- Helpers ---

    @staticmethod
    def _make_mock_memory_features(redis_available: bool = False) -> dict:
        """Create mock memory features dict."""
        from attune.memory.features import FeatureInfo
        from attune.memory.features import FeatureStatus as MemFeatureStatus

        if redis_available:
            short_term_status = MemFeatureStatus.AVAILABLE
            short_term_msg = "Short-term memory (Redis-based) is available"
            short_term_install = None
        else:
            short_term_status = MemFeatureStatus.MISSING_DEPENDENCY
            short_term_msg = "Redis package not importable"
            short_term_install = "pip install --force-reinstall 'redis>=5.0.0,<9.0.0'"

        return {
            "short_term": FeatureInfo(
                name="Short-term memory",
                status=short_term_status,
                message=short_term_msg,
                install_command=short_term_install,
            ),
            "long_term": FeatureInfo(
                name="Long-term memory",
                status=MemFeatureStatus.AVAILABLE,
                message="Core feature (always available)",
            ),
        }

    @staticmethod
    def _make_mock_telemetry_features(redis_available: bool = False) -> dict:
        """Create mock telemetry features dict."""
        from attune.telemetry.features import FeatureInfo as TelFeatureInfo
        from attune.telemetry.features import FeatureStatus as TelFeatureStatus

        return {
            "usage_tracking": TelFeatureInfo(
                name="Usage tracking",
                status=TelFeatureStatus.AVAILABLE,
                message="Core feature (always available)",
            ),
            "event_streaming": TelFeatureInfo(
                name="Real-time event streaming",
                status=(
                    TelFeatureStatus.AVAILABLE
                    if redis_available
                    else TelFeatureStatus.MISSING_DEPENDENCY
                ),
                message=(
                    "Real-time event streaming is available"
                    if redis_available
                    else "Redis package not importable"
                ),
                install_command=(
                    None
                    if redis_available
                    else "pip install --force-reinstall 'redis>=5.0.0,<9.0.0'"
                ),
            ),
        }
