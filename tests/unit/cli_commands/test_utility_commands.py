"""Tests for utility_commands.py.

Tests for dashboard start, setup, validate, and version CLI commands.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.cli_commands.utility_commands import (
    cmd_dashboard_start,
    cmd_setup,
    cmd_validate,
    cmd_version,
)

# ---------------------------------------------------------------------------
# cmd_dashboard_start
# ---------------------------------------------------------------------------


class TestCmdDashboardStart:
    """Tests for cmd_dashboard_start."""

    def _make_args(self, host: str = "0.0.0.0", port: int = 8000) -> types.SimpleNamespace:
        """Create a mock args namespace for dashboard start."""
        return types.SimpleNamespace(host=host, port=port)

    @patch(
        "attune.cli_commands.utility_commands.cmd_dashboard_start.__module__",
        new="attune.cli_commands.utility_commands",
    )
    def test_success_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test dashboard starts successfully and returns 0."""
        args = self._make_args()

        with patch.dict(
            "sys.modules",
            {"attune.dashboard": MagicMock()},
        ):
            with patch(
                "attune.cli_commands.utility_commands.cmd_dashboard_start",
                wraps=cmd_dashboard_start,
            ):
                # Patch the late import inside the function
                mock_dashboard = MagicMock()
                mock_run = MagicMock()
                mock_dashboard.run_standalone_dashboard = mock_run

                with patch.dict("sys.modules", {"attune.dashboard": mock_dashboard}):
                    result = cmd_dashboard_start(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Starting Agent Coordination Dashboard" in captured.out
        assert "0.0.0.0" in captured.out
        assert "8000" in captured.out

    def test_success_calls_run_with_host_and_port(self) -> None:
        """Test that run_standalone_dashboard is called with correct host and port."""
        args = self._make_args(host="127.0.0.1", port=9999)
        mock_dashboard = MagicMock()
        mock_run = MagicMock()
        mock_dashboard.run_standalone_dashboard = mock_run

        with patch.dict("sys.modules", {"attune.dashboard": mock_dashboard}):
            result = cmd_dashboard_start(args)

        assert result == 0
        mock_run.assert_called_once_with(host="127.0.0.1", port=9999)

    def test_keyboard_interrupt_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that KeyboardInterrupt returns 0 and prints stop message."""
        args = self._make_args()
        mock_dashboard = MagicMock()
        mock_dashboard.run_standalone_dashboard.side_effect = KeyboardInterrupt

        with patch.dict("sys.modules", {"attune.dashboard": mock_dashboard}):
            result = cmd_dashboard_start(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Dashboard stopped" in captured.out

    def test_import_error_returns_one(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that ImportError returns 1 with helpful message."""
        args = self._make_args()

        # Remove any cached module so the import inside the function fails
        with patch.dict("sys.modules", {"attune.dashboard": None}):
            result = cmd_dashboard_start(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Dashboard not available" in captured.out
        assert "pip install redis" in captured.out

    def test_generic_exception_returns_one(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that a generic exception returns 1 and logs error."""
        args = self._make_args()
        mock_dashboard = MagicMock()
        mock_dashboard.run_standalone_dashboard.side_effect = RuntimeError("connection refused")

        with patch.dict("sys.modules", {"attune.dashboard": mock_dashboard}):
            result = cmd_dashboard_start(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error starting dashboard" in captured.out
        assert "connection refused" in captured.out

    def test_output_shows_custom_host_and_port(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that the printed URL uses the custom host and port."""
        args = self._make_args(host="192.168.1.10", port=3000)
        mock_dashboard = MagicMock()
        mock_dashboard.run_standalone_dashboard = MagicMock()

        with patch.dict("sys.modules", {"attune.dashboard": mock_dashboard}):
            cmd_dashboard_start(args)

        captured = capsys.readouterr()
        assert "http://192.168.1.10:3000" in captured.out


# ---------------------------------------------------------------------------
# cmd_setup
# ---------------------------------------------------------------------------


class TestCmdSetup:
    """Tests for cmd_setup."""

    def _make_args(self) -> types.SimpleNamespace:
        """Create a mock args namespace for setup."""
        return types.SimpleNamespace()

    def test_returns_one_when_source_dir_not_found(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test returns 1 when no command source directory is found."""
        args = self._make_args()

        # Redirect __file__ so Path(__file__).parent.parent won't find real commands
        fake_file = tmp_path / "fake_pkg" / "cli_commands" / "utility_commands.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.touch()
        monkeypatch.setattr("attune.cli_commands.utility_commands.__file__", str(fake_file))

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: empty_dir))

        with patch("importlib.resources.files", side_effect=ImportError("no resources")):
            result = cmd_setup(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Could not find Attune command files" in captured.out

    def test_returns_one_when_no_md_files_found(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test returns 1 when source dir exists but contains no .md files."""
        args = self._make_args()

        # Redirect __file__ so Path(__file__).parent.parent won't find real commands
        fake_file = tmp_path / "fake_pkg" / "cli_commands" / "utility_commands.py"
        fake_file.parent.mkdir(parents=True)
        # Create a commands dir with no .md files (but with agents subdir to avoid iterdir error)
        commands_dir = tmp_path / "fake_pkg" / "commands"
        commands_dir.mkdir()
        (commands_dir / "readme.txt").write_text("not a command")
        (commands_dir / "agents").mkdir()

        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.setattr("attune.cli_commands.utility_commands.__file__", str(fake_file))
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path / "empty"))
        (tmp_path / "empty").mkdir()

        with patch("importlib.resources.files", side_effect=ImportError):
            result = cmd_setup(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No command files found" in captured.out

    def test_copies_md_files_and_returns_zero(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successfully copies .md files and returns 0."""
        args = self._make_args()

        # Set up source directory with .md files
        source_dir = tmp_path / "source" / ".claude" / "commands"
        source_dir.mkdir(parents=True)
        (source_dir / "dev.md").write_text("# Dev Hub")
        (source_dir / "testing.md").write_text("# Testing Hub")
        (source_dir / "not-a-command.txt").write_text("ignored")

        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path / "source"))

        with patch("importlib.resources.files", side_effect=ImportError):
            result = cmd_setup(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Installed: dev.md" in captured.out
        assert "Installed: testing.md" in captured.out

        # Verify files were actually copied
        target_dir = home_dir / ".claude" / "commands"
        assert (target_dir / "dev.md").exists()
        assert (target_dir / "testing.md").exists()
        assert not (target_dir / "not-a-command.txt").exists()

    def test_copies_agents_subdirectory(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test copies agent definitions from agents/ subdirectory."""
        args = self._make_args()

        # Redirect __file__ so fallback finds our test source, not the real package
        fake_file = tmp_path / "source" / "attune" / "cli_commands" / "utility_commands.py"
        fake_file.parent.mkdir(parents=True)

        source_dir = tmp_path / "source" / ".claude" / "commands"
        source_dir.mkdir(parents=True)
        (source_dir / "dev.md").write_text("# Dev")

        agents_dir = source_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "security-agent.md").write_text("# Security Agent")
        (agents_dir / "test-agent.md").write_text("# Test Agent")

        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.setattr("attune.cli_commands.utility_commands.__file__", str(fake_file))
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path / "source"))

        with patch("importlib.resources.files", side_effect=ImportError):
            result = cmd_setup(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Subagent Definitions:" in captured.out
        assert "security-agent.md" in captured.out
        assert "test-agent.md" in captured.out

        # Verify agent files copied
        target_agents = home_dir / ".claude" / "commands" / "agents"
        assert target_agents.exists()
        assert (target_agents / "security-agent.md").exists()

    def test_skips_existing_config_files(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that existing config files are not overwritten."""
        args = self._make_args()

        # Source commands
        source_dir = tmp_path / "source" / ".claude" / "commands"
        source_dir.mkdir(parents=True)
        (source_dir / "dev.md").write_text("# Dev")

        # Source config
        source_claude = tmp_path / "source" / ".claude"
        (source_claude / "settings.json").write_text('{"original": true}')

        # Home with pre-existing config
        home_dir = tmp_path / "home"
        home_claude = home_dir / ".claude"
        home_claude.mkdir(parents=True)
        (home_claude / "settings.json").write_text('{"existing": true}')

        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path / "source"))

        with patch("importlib.resources.files", side_effect=ImportError):
            result = cmd_setup(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Skipped: settings.json (already exists)" in captured.out

        # Verify the existing file was NOT overwritten
        content = (home_claude / "settings.json").read_text()
        assert '"existing": true' in content

    def test_copies_config_when_not_existing(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that config files are copied when they do not exist at target."""
        args = self._make_args()

        source_dir = tmp_path / "source" / ".claude" / "commands"
        source_dir.mkdir(parents=True)
        (source_dir / "dev.md").write_text("# Dev")

        source_claude = tmp_path / "source" / ".claude"
        (source_claude / "settings.json").write_text('{"source": true}')

        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path / "source"))

        with patch("importlib.resources.files", side_effect=ImportError):
            result = cmd_setup(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Installed: settings.json" in captured.out

        config_content = (home_dir / ".claude" / "settings.json").read_text()
        assert '"source": true' in config_content

    def test_creates_target_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the target ~/.claude/commands/ directory is created."""
        args = self._make_args()

        source_dir = tmp_path / "source" / ".claude" / "commands"
        source_dir.mkdir(parents=True)
        (source_dir / "hub.md").write_text("# Hub")

        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path / "source"))

        with patch("importlib.resources.files", side_effect=ImportError):
            cmd_setup(args)

        assert (home_dir / ".claude" / "commands").is_dir()

    def test_uses_importlib_resources_when_available(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that importlib.resources.files is used when available."""
        args = self._make_args()

        # files("attune") returns a package root; the function then does / "commands"
        pkg_root = tmp_path / "pkg_root"
        pkg_root.mkdir()
        commands_dir = pkg_root / "commands"
        commands_dir.mkdir()
        (commands_dir / "workflows.md").write_text("# Workflows")
        (commands_dir / "agents").mkdir()

        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path))

        # importlib.resources.files returns a Traversable that acts like Path
        with patch("importlib.resources.files", return_value=pkg_root):
            result = cmd_setup(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Installed: workflows.md" in captured.out

    def test_output_shows_total_counts(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that final output shows total counts of copied files."""
        args = self._make_args()

        # Redirect __file__ so only our test source is found
        fake_file = tmp_path / "source" / "attune" / "cli_commands" / "utility_commands.py"
        fake_file.parent.mkdir(parents=True)

        source_dir = tmp_path / "source" / ".claude" / "commands"
        source_dir.mkdir(parents=True)
        (source_dir / "a.md").write_text("# A")
        (source_dir / "b.md").write_text("# B")
        (source_dir / "c.md").write_text("# C")
        (source_dir / "agents").mkdir()

        home_dir = tmp_path / "home"
        home_dir.mkdir()

        monkeypatch.setattr("attune.cli_commands.utility_commands.__file__", str(fake_file))
        monkeypatch.setattr(Path, "home", staticmethod(lambda: home_dir))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: tmp_path / "source"))

        with patch("importlib.resources.files", side_effect=ImportError):
            result = cmd_setup(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "3 commands" in captured.out


# ---------------------------------------------------------------------------
# cmd_validate
# ---------------------------------------------------------------------------


class TestCmdValidate:
    """Tests for cmd_validate."""

    def _make_args(self) -> types.SimpleNamespace:
        """Create a mock args namespace for validate."""
        return types.SimpleNamespace()

    def test_valid_config_with_api_key_returns_zero(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test returns 0 when config file and API key are present."""
        args = self._make_args()

        # Create a config file
        monkeypatch.chdir(tmp_path)
        (tmp_path / "attune.config.json").write_text("{}")

        # Set API key
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key-123")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        # Mock workflow registry
        mock_registry = {"code-review": {}, "test-gen": {}, "security": {}}
        with patch.dict(
            "sys.modules", {"attune.workflows": MagicMock(WORKFLOW_REGISTRY=mock_registry)}
        ):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Anthropic (Claude) API key set" in captured.out
        assert "Configuration is valid" in captured.out

    def test_no_api_keys_returns_one(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test returns 1 when no API keys are set."""
        args = self._make_args()

        monkeypatch.chdir(tmp_path)
        (tmp_path / "attune.config.json").write_text("{}")

        # Remove all API keys
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with patch.dict("sys.modules", {"attune.workflows": MagicMock(WORKFLOW_REGISTRY={})}):
            result = cmd_validate(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Validation failed" in captured.out
        assert "No API keys found" in captured.out

    def test_no_config_file_shows_warning(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test shows warning when no config file is found but still passes if key exists."""
        args = self._make_args()

        # chdir to a directory with no config files
        monkeypatch.chdir(tmp_path)

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with patch.dict("sys.modules", {"attune.workflows": MagicMock(WORKFLOW_REGISTRY={})}):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Warnings:" in captured.out
        assert "No attune.config file found" in captured.out

    def test_detects_yml_config(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test detects attune.config.yml file."""
        args = self._make_args()

        monkeypatch.chdir(tmp_path)
        (tmp_path / "attune.config.yml").write_text("version: 1")

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with patch.dict("sys.modules", {"attune.workflows": MagicMock(WORKFLOW_REGISTRY={})}):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Config file: attune.config.yml" in captured.out

    def test_detects_yaml_config(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test detects attune.config.yaml file."""
        args = self._make_args()

        monkeypatch.chdir(tmp_path)
        (tmp_path / "attune.config.yaml").write_text("version: 1")

        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with patch.dict("sys.modules", {"attune.workflows": MagicMock(WORKFLOW_REGISTRY={})}):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Config file: attune.config.yaml" in captured.out

    def test_detects_multiple_api_keys(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test detects all configured API keys."""
        args = self._make_args()

        monkeypatch.chdir(tmp_path)
        (tmp_path / "attune.config.json").write_text("{}")

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "goog-test")

        with patch.dict("sys.modules", {"attune.workflows": MagicMock(WORKFLOW_REGISTRY={})}):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Anthropic (Claude) API key set" in captured.out
        assert "OpenAI (GPT) API key set" in captured.out
        assert "Google (Gemini) API key set" in captured.out

    def test_workflow_registry_count_displayed(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test shows number of registered workflows."""
        args = self._make_args()

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        mock_registry = {"wf1": {}, "wf2": {}, "wf3": {}, "wf4": {}, "wf5": {}}
        with patch.dict(
            "sys.modules",
            {"attune.workflows": MagicMock(WORKFLOW_REGISTRY=mock_registry)},
        ):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "5 workflows registered" in captured.out

    def test_workflow_import_error_shows_warning(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test shows warning when workflows cannot be imported."""
        args = self._make_args()

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        # Make importing WORKFLOW_REGISTRY fail
        with patch.dict("sys.modules", {"attune.workflows": None}):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Warnings:" in captured.out
        assert "Could not load workflows" in captured.out

    def test_prefers_json_config_over_yml(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that json config is found first when multiple config files exist."""
        args = self._make_args()

        monkeypatch.chdir(tmp_path)
        (tmp_path / "attune.config.json").write_text("{}")
        (tmp_path / "attune.config.yml").write_text("version: 1")

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with patch.dict("sys.modules", {"attune.workflows": MagicMock(WORKFLOW_REGISTRY={})}):
            result = cmd_validate(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Config file: attune.config.json" in captured.out

    def test_empty_api_key_not_counted(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that empty string API keys are not counted as set."""
        args = self._make_args()

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with patch.dict("sys.modules", {"attune.workflows": MagicMock(WORKFLOW_REGISTRY={})}):
            result = cmd_validate(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No API keys found" in captured.out


# ---------------------------------------------------------------------------
# cmd_version
# ---------------------------------------------------------------------------


class TestCmdVersion:
    """Tests for cmd_version."""

    def _make_args(self, verbose: bool = False) -> types.SimpleNamespace:
        """Create a mock args namespace for version."""
        return types.SimpleNamespace(verbose=verbose)

    def test_non_verbose_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test returns 0 and prints version string."""
        args = self._make_args(verbose=False)

        with patch("attune.cli_commands.utility_commands.get_version", create=True):
            with patch("attune.cli_minimal.get_version", return_value="2.5.0"):
                # Need to patch at the import site inside the function
                with patch.dict("sys.modules", {}):
                    mock_cli_minimal = MagicMock()
                    mock_cli_minimal.get_version.return_value = "2.5.0"
                    with patch.dict("sys.modules", {"attune.cli_minimal": mock_cli_minimal}):
                        result = cmd_version(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "attune-ai 2.5.0" in captured.out

    def test_non_verbose_does_not_show_python_info(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test non-verbose mode does not show Python info."""
        args = self._make_args(verbose=False)

        mock_cli_minimal = MagicMock()
        mock_cli_minimal.get_version.return_value = "1.0.0"
        with patch.dict("sys.modules", {"attune.cli_minimal": mock_cli_minimal}):
            cmd_version(args)

        captured = capsys.readouterr()
        assert "Python:" not in captured.out
        assert "Platform:" not in captured.out

    def test_verbose_shows_python_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test verbose mode shows Python version and platform."""
        args = self._make_args(verbose=True)

        mock_cli_minimal = MagicMock()
        mock_cli_minimal.get_version.return_value = "2.5.0"
        with patch.dict("sys.modules", {"attune.cli_minimal": mock_cli_minimal}):
            result = cmd_version(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "attune-ai 2.5.0" in captured.out
        assert "Python:" in captured.out
        assert "Platform:" in captured.out

    def test_verbose_shows_dependency_count(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test verbose mode shows dependency count when importlib.metadata works."""
        args = self._make_args(verbose=True)

        mock_cli_minimal = MagicMock()
        mock_cli_minimal.get_version.return_value = "2.5.0"

        mock_requires = MagicMock(return_value=["dep1", "dep2", "dep3"])

        with patch.dict("sys.modules", {"attune.cli_minimal": mock_cli_minimal}):
            with patch("importlib.metadata.requires", mock_requires):
                result = cmd_version(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Dependencies: 3" in captured.out

    def test_verbose_handles_metadata_failure_gracefully(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test verbose mode handles importlib.metadata failure gracefully."""
        args = self._make_args(verbose=True)

        mock_cli_minimal = MagicMock()
        mock_cli_minimal.get_version.return_value = "2.5.0"

        with patch.dict("sys.modules", {"attune.cli_minimal": mock_cli_minimal}):
            with patch(
                "importlib.metadata.requires",
                side_effect=Exception("metadata unavailable"),
            ):
                result = cmd_version(args)

        # Should still return 0 -- failure is gracefully swallowed
        assert result == 0
        captured = capsys.readouterr()
        assert "attune-ai 2.5.0" in captured.out
        # Should NOT contain Dependencies since the call failed
        assert "Dependencies:" not in captured.out

    def test_verbose_handles_none_requires(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test verbose mode handles requires() returning None."""
        args = self._make_args(verbose=True)

        mock_cli_minimal = MagicMock()
        mock_cli_minimal.get_version.return_value = "2.5.0"

        with patch.dict("sys.modules", {"attune.cli_minimal": mock_cli_minimal}):
            with patch("importlib.metadata.requires", return_value=None):
                result = cmd_version(args)

        assert result == 0
        captured = capsys.readouterr()
        # requires() returns None, so `reqs = requires(...) or []` -> []
        assert "Dependencies: 0" in captured.out

    def test_always_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that cmd_version always returns 0."""
        args = self._make_args(verbose=False)

        mock_cli_minimal = MagicMock()
        mock_cli_minimal.get_version.return_value = "0.0.1-dev"
        with patch.dict("sys.modules", {"attune.cli_minimal": mock_cli_minimal}):
            result = cmd_version(args)

        assert result == 0

    def test_version_string_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that version output matches expected format."""
        args = self._make_args(verbose=False)

        mock_cli_minimal = MagicMock()
        mock_cli_minimal.get_version.return_value = "3.1.4"
        with patch.dict("sys.modules", {"attune.cli_minimal": mock_cli_minimal}):
            cmd_version(args)

        captured = capsys.readouterr()
        assert captured.out.strip() == "attune-ai 3.1.4"
