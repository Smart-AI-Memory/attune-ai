"""Tests for cli_minimal.py - main CLI entry point.

Tests for the argument parser, main() routing, and version detection.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import logging
from unittest.mock import MagicMock, patch

import pytest

from attune.cli_minimal import create_parser, get_version, main

_CLI = "attune.cli_minimal"


# ---------------------------------------------------------------------------
# get_version
# ---------------------------------------------------------------------------


class TestGetVersion:
    """Tests for get_version()."""

    def test_returns_string(self) -> None:
        """get_version should always return a string."""
        result = get_version()
        assert isinstance(result, str)

    def test_fallback_on_import_error(self) -> None:
        """get_version should return 'dev' when importlib.metadata fails."""
        with patch("importlib.metadata.version", side_effect=Exception("not found")):
            result = get_version()
        assert result == "dev"

    def test_returns_version_from_metadata(self) -> None:
        """get_version should return the version from importlib.metadata."""
        with patch("importlib.metadata.version", return_value="2.5.0"):
            result = get_version()
        assert result == "2.5.0"


# ---------------------------------------------------------------------------
# create_parser
# ---------------------------------------------------------------------------


class TestCreateParser:
    """Tests for create_parser()."""

    @pytest.fixture()
    def parser(self) -> argparse.ArgumentParser:
        return create_parser()

    def test_returns_argument_parser(self, parser: argparse.ArgumentParser) -> None:
        """create_parser should return an ArgumentParser."""
        assert isinstance(parser, argparse.ArgumentParser)

    def test_workflow_list(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["workflow", "list"])
        assert args.command == "workflow"
        assert args.workflow_command == "list"

    def test_workflow_info(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["workflow", "info", "security-audit"])
        assert args.workflow_command == "info"
        assert args.name == "security-audit"

    def test_workflow_run(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["workflow", "run", "test-gen", "--json"])
        assert args.workflow_command == "run"
        assert args.name == "test-gen"
        assert args.json is True

    def test_telemetry_show(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "show", "--days", "7"])
        assert args.telemetry_command == "show"
        assert args.days == 7

    def test_telemetry_export(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "export", "-o", "out.json", "-f", "csv"])
        assert args.telemetry_command == "export"
        assert args.output == "out.json"
        assert args.format == "csv"

    def test_telemetry_routing_stats(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "routing-stats", "-w", "code-review", "-d", "30"])
        assert args.workflow == "code-review"
        assert args.days == 30

    def test_telemetry_models(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "models", "-p", "anthropic"])
        assert args.provider == "anthropic"

    def test_telemetry_signals(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "signals", "--agent", "agent-1"])
        assert args.agent == "agent-1"

    def test_provider_show(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["provider", "show"])
        assert args.provider_command == "show"

    def test_provider_set(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["provider", "set", "openai"])
        assert args.provider_command == "set"
        assert args.name == "openai"

    def test_dashboard_start(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["dashboard", "start", "--host", "0.0.0.0", "--port", "9090"])
        assert args.dashboard_command == "start"
        assert args.host == "0.0.0.0"
        assert args.port == 9090

    def test_setup(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["setup"])
        assert args.command == "setup"

    def test_validate(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["validate"])
        assert args.command == "validate"

    def test_version(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["version"])
        assert args.command == "version"

    def test_version_verbose(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["version", "-v"])
        assert args.verbose is True

    def test_verbose_flag(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["version", "-v"])
        assert args.verbose is True


# ---------------------------------------------------------------------------
# main() routing
# ---------------------------------------------------------------------------


class TestMainWorkflowRouting:
    """Tests that main() routes workflow subcommands correctly."""

    @patch(f"{_CLI}.cmd_workflow_list", return_value=0)
    def test_workflow_list(self, mock_fn: MagicMock) -> None:
        assert main(["workflow", "list"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_workflow_info", return_value=0)
    def test_workflow_info(self, mock_fn: MagicMock) -> None:
        assert main(["workflow", "info", "wf-name"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_workflow_run", return_value=0)
    def test_workflow_run(self, mock_fn: MagicMock) -> None:
        assert main(["workflow", "run", "wf-name"]) == 0
        mock_fn.assert_called_once()

    def test_workflow_no_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        assert main(["workflow"]) == 1
        captured = capsys.readouterr()
        assert "workflow" in captured.out.lower()


class TestMainTelemetryRouting:
    """Tests that main() routes telemetry subcommands correctly."""

    @patch(f"{_CLI}.cmd_telemetry_show", return_value=0)
    def test_show(self, mock_fn: MagicMock) -> None:
        assert main(["telemetry", "show"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_telemetry_savings", return_value=0)
    def test_savings(self, mock_fn: MagicMock) -> None:
        assert main(["telemetry", "savings"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_telemetry_export", return_value=0)
    def test_export(self, mock_fn: MagicMock) -> None:
        assert main(["telemetry", "export", "-o", "out.json"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_telemetry_routing_stats", return_value=0)
    def test_routing_stats(self, mock_fn: MagicMock) -> None:
        assert main(["telemetry", "routing-stats"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_telemetry_routing_check", return_value=0)
    def test_routing_check(self, mock_fn: MagicMock) -> None:
        assert main(["telemetry", "routing-check"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_telemetry_models", return_value=0)
    def test_models(self, mock_fn: MagicMock) -> None:
        assert main(["telemetry", "models"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_telemetry_agents", return_value=0)
    def test_agents(self, mock_fn: MagicMock) -> None:
        assert main(["telemetry", "agents"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_telemetry_signals", return_value=0)
    def test_signals(self, mock_fn: MagicMock) -> None:
        assert main(["telemetry", "signals", "--agent", "a1"]) == 0
        mock_fn.assert_called_once()

    def test_no_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        assert main(["telemetry"]) == 1
        captured = capsys.readouterr()
        assert "telemetry" in captured.out.lower()


class TestMainProviderRouting:
    """Tests that main() routes provider subcommands correctly."""

    @patch(f"{_CLI}.cmd_provider_show", return_value=0)
    def test_show(self, mock_fn: MagicMock) -> None:
        assert main(["provider", "show"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_provider_set", return_value=0)
    def test_set(self, mock_fn: MagicMock) -> None:
        assert main(["provider", "set", "anthropic"]) == 0
        mock_fn.assert_called_once()

    def test_no_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        assert main(["provider"]) == 1
        captured = capsys.readouterr()
        assert "provider" in captured.out.lower()


class TestMainDashboardRouting:
    """Tests that main() routes dashboard subcommands correctly."""

    @patch(f"{_CLI}.cmd_dashboard_start", return_value=0)
    def test_start(self, mock_fn: MagicMock) -> None:
        assert main(["dashboard", "start"]) == 0
        mock_fn.assert_called_once()

    def test_no_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        assert main(["dashboard"]) == 1
        captured = capsys.readouterr()
        assert "dashboard" in captured.out.lower()


class TestMainUtilityRouting:
    """Tests that main() routes utility commands correctly."""

    @patch(f"{_CLI}.cmd_setup", return_value=0)
    def test_setup(self, mock_fn: MagicMock) -> None:
        assert main(["setup"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_validate", return_value=0)
    def test_validate(self, mock_fn: MagicMock) -> None:
        assert main(["validate"]) == 0
        mock_fn.assert_called_once()

    @patch(f"{_CLI}.cmd_version", return_value=0)
    def test_version(self, mock_fn: MagicMock) -> None:
        assert main(["version"]) == 0
        mock_fn.assert_called_once()


class TestMainEdgeCases:
    """Tests for main() edge cases."""

    def test_no_args_prints_help(self, capsys: pytest.CaptureFixture) -> None:
        assert main([]) == 0
        captured = capsys.readouterr()
        assert "attune" in captured.out.lower()

    def test_none_argv(self, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["attune"]):
            assert main(None) == 0

    @patch(f"{_CLI}.cmd_version", return_value=0)
    def test_verbose_enables_debug(self, mock_fn: MagicMock) -> None:
        with patch("logging.basicConfig") as mock_config:
            main(["version", "-v"])
            assert any(
                c.kwargs.get("level") == logging.DEBUG for c in mock_config.call_args_list
            )

    @patch(f"{_CLI}.cmd_workflow_list", return_value=1)
    def test_propagates_nonzero(self, mock_fn: MagicMock) -> None:
        assert main(["workflow", "list"]) == 1
