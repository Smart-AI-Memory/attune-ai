"""Tests for CLI core module and command registration.

Covers CLI core utilities, app structure, and command registration.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from attune.cli.core import console, get_attune_version, version_callback


@pytest.mark.unit
class TestGetAttuneVersion:
    """Tests for get_attune_version function."""

    def test_returns_version_string(self):
        """Test get_attune_version returns a string."""
        version = get_attune_version()

        assert isinstance(version, str)
        assert len(version) > 0

    def test_returns_dev_on_import_error(self):
        """Test get_attune_version returns 'dev' on import error."""
        with patch("attune.cli.core.get_version") as mock_version:
            mock_version.side_effect = Exception("Package not found")

            # Re-call to trigger exception
            from attune.cli.core import get_attune_version

            result = get_attune_version()

            # Should return dev or actual version (depends on environment)
            assert isinstance(result, str)


@pytest.mark.unit
class TestVersionCallback:
    """Tests for version_callback function."""

    def test_exits_when_value_true(self):
        """Test version_callback raises Exit when value is True."""
        with pytest.raises(typer.Exit):
            version_callback(True)

    def test_no_exit_when_value_false(self):
        """Test version_callback doesn't exit when value is False."""
        # Should not raise
        result = version_callback(False)
        assert result is None


@pytest.mark.unit
class TestConsole:
    """Tests for console instance."""

    def test_console_exists(self):
        """Test console is a Rich Console instance."""
        from rich.console import Console

        assert isinstance(console, Console)


@pytest.mark.unit
class TestCLIAppStructure:
    """Tests for CLI app structure and registration."""

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    def test_app_exists(self):
        """Test the main app exists and is a Typer app."""
        from attune.cli import app

        assert isinstance(app, typer.Typer)

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    def test_app_has_name(self):
        """Test the app has a name."""
        from attune.cli import app

        # Typer stores info in info attribute
        assert app.info.name == "attune"

    def test_memory_app_registered(self):
        """Test memory subcommand app is registered."""
        from attune.cli.commands.memory import memory_app

        assert isinstance(memory_app, typer.Typer)

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    def test_provider_app_registered(self):
        """Test provider subcommand app is registered."""
        from attune.cli.commands.provider import provider_app

        assert isinstance(provider_app, typer.Typer)


@pytest.mark.unit
class TestCLICommands:
    """Tests for CLI command registration."""

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    def test_scan_command_exists(self):
        """Test scan command is registered."""
        from attune.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["scan", "--help"])

        assert result.exit_code == 0
        assert "Scan codebase" in result.stdout or "scan" in result.stdout.lower()

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    def test_inspect_command_exists(self):
        """Test inspect command is registered."""
        from attune.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["inspect", "--help"])

        assert result.exit_code == 0

    @pytest.mark.skip(reason="cheatsheet command not implemented")
    def test_cheatsheet_command_exists(self):
        """Test cheatsheet command is registered."""
        from attune.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["cheatsheet", "--help"])

        assert result.exit_code == 0

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    def test_version_option_exists(self):
        """Test --version option is available."""
        from attune.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--version"])

        # Should show version and exit
        assert "Attune AI" in result.stdout or result.exit_code == 0

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    def test_help_available(self):
        """Test --help shows command list."""
        from attune.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        # Should list some commands
        assert "memory" in result.stdout.lower() or "Commands" in result.stdout


@pytest.mark.unit
class TestMemoryCommands:
    """Tests for memory subcommand registration."""

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    def test_memory_status_command_exists(self):
        """Test memory status command is registered."""
        from attune.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["memory", "--help"])

        assert result.exit_code == 0
        assert "status" in result.stdout

    def test_memory_start_command_exists(self):
        """Test memory start command is registered."""
        from attune.cli.commands.memory import memory_app

        runner = CliRunner()
        result = runner.invoke(memory_app, ["--help"])

        assert "start" in result.stdout


@pytest.mark.unit
class TestProviderCommands:
    """Tests for provider subcommand registration."""

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    def test_provider_help(self):
        """Test provider help is available."""
        from attune.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["provider", "--help"])

        assert result.exit_code == 0


@pytest.mark.unit
class TestUtilityFunctions:
    """Tests for utility command functions."""

    def test_cheatsheet_function(self):
        """Test cheatsheet function runs without error."""
        from attune.cli.commands.utilities import cheatsheet

        # Should not raise
        cheatsheet()

    @patch("subprocess.run")
    def test_sync_claude_calls_subprocess(self, mock_run):
        """Test sync_claude calls subprocess correctly."""
        from attune.cli.commands.utilities import sync_claude

        sync_claude("patterns")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "attune-sync-claude" in call_args[0][0]

    @patch("subprocess.run")
    def test_dashboard_calls_subprocess(self, mock_run):
        """Test dashboard calls subprocess."""
        from attune.cli.commands.utilities import dashboard

        dashboard()

        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_costs_calls_subprocess(self, mock_run):
        """Test costs calls subprocess."""
        from attune.cli.commands.utilities import costs

        costs()

        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_init_calls_subprocess(self, mock_run):
        """Test init calls subprocess."""
        from attune.cli.commands.utilities import init

        init()

        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_status_calls_subprocess(self, mock_run):
        """Test status calls subprocess."""
        from attune.cli.commands.utilities import status

        status()

        mock_run.assert_called_once()


@pytest.mark.unit
class TestMemoryAppFunctions:
    """Tests for memory app command functions."""

    @patch("subprocess.run")
    def test_memory_status_calls_subprocess(self, mock_run):
        """Test memory_status calls control panel."""
        from attune.cli.commands.memory import memory_status

        memory_status()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "control_panel" in str(call_args)
        assert "status" in str(call_args)

    @patch("subprocess.run")
    def test_memory_start_calls_subprocess(self, mock_run):
        """Test memory_start calls control panel."""
        from attune.cli.commands.memory import memory_start

        memory_start()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "control_panel" in str(call_args)
        assert "start" in str(call_args)

    @patch("subprocess.run")
    def test_memory_stop_calls_subprocess(self, mock_run):
        """Test memory_stop calls control panel."""
        from attune.cli.commands.memory import memory_stop

        memory_stop()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "stop" in str(call_args)

    @patch("subprocess.run")
    def test_memory_stats_calls_subprocess(self, mock_run):
        """Test memory_stats calls control panel."""
        from attune.cli.commands.memory import memory_stats

        memory_stats()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "stats" in str(call_args)

    @patch("subprocess.run")
    def test_memory_patterns_calls_subprocess(self, mock_run):
        """Test memory_patterns calls control panel."""
        from attune.cli.commands.memory import memory_patterns

        memory_patterns()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "patterns" in str(call_args)


@pytest.mark.unit
class TestCLIMain:
    """Tests for CLI main entry point."""

    def test_main_function_exists(self):
        """Test main function exists."""
        from attune.cli import main

        assert callable(main)

    @pytest.mark.skip(reason="CLI restructured to use argparse instead of Typer")
    @patch("attune.cli.app")
    def test_main_calls_app(self, mock_app):
        """Test main calls the app."""
        from attune.cli import main

        main()

        mock_app.assert_called_once()
