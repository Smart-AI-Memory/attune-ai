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

from attune.cli_minimal import (
    _SUBCOMMAND_DISPATCH,
    _OneLineLogFormatter,
    create_parser,
    get_version,
    main,
)

_CLI = "attune.cli_minimal"


def _mock_subcmd(command: str, subcommand: str, return_value: int = 0):
    """Patch a subcommand handler inside _SUBCOMMAND_DISPATCH."""
    mock_fn = MagicMock(return_value=return_value)
    orig = _SUBCOMMAND_DISPATCH[command].copy()
    patched = {**orig, subcommand: mock_fn}
    return patch.dict(f"{_CLI}._SUBCOMMAND_DISPATCH", {command: patched}), mock_fn


def _mock_simple(command: str, return_value: int = 0):
    """Patch a simple command handler inside _SIMPLE_DISPATCH."""
    mock_fn = MagicMock(return_value=return_value)
    return patch.dict(f"{_CLI}._SIMPLE_DISPATCH", {command: mock_fn}), mock_fn


# ---------------------------------------------------------------------------
# get_version
# ---------------------------------------------------------------------------


class TestGetVersion:
    """Tests for get_version()."""

    def test_returns_string(self) -> None:
        assert isinstance(get_version(), str)

    @patch("importlib.metadata.version", side_effect=Exception("no package"))
    def test_fallback_on_import_error(self, mock_ver) -> None:
        assert get_version() == "dev"

    def test_returns_version_from_metadata(self) -> None:
        version = get_version()
        # Should be a proper version string like "5.3.2"
        parts = version.split(".")
        assert len(parts) >= 2 or version == "dev"


# ---------------------------------------------------------------------------
# create_parser
# ---------------------------------------------------------------------------


class TestCreateParser:
    """Tests for create_parser()."""

    @pytest.fixture
    def parser(self) -> argparse.ArgumentParser:
        return create_parser()

    def test_returns_argument_parser(self, parser: argparse.ArgumentParser) -> None:
        assert isinstance(parser, argparse.ArgumentParser)

    def test_workflow_list(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["workflow", "list"])
        assert args.command == "workflow"
        assert args.workflow_command == "list"

    def test_workflow_info(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["workflow", "info", "wf-name"])
        assert args.command == "workflow"
        assert args.workflow_command == "info"

    def test_workflow_run(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["workflow", "run", "wf-name"])
        assert args.command == "workflow"
        assert args.workflow_command == "run"
        assert args.name == "wf-name"

    def test_workflow_run_path_defaults_to_cwd(self, parser: argparse.ArgumentParser) -> None:
        """``--path`` defaults to ``"."`` so workflows that need a path
        (dependency-check, code-review, etc.) don't fail when run bare.
        """
        args = parser.parse_args(["workflow", "run", "dependency-check"])
        assert args.path == "."

    def test_workflow_run_path_explicit_overrides_default(
        self, parser: argparse.ArgumentParser
    ) -> None:
        args = parser.parse_args(["workflow", "run", "dependency-check", "--path", "/tmp/proj"])
        assert args.path == "/tmp/proj"

    def test_telemetry_show(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "show"])
        assert args.command == "telemetry"
        assert args.telemetry_command == "show"

    def test_telemetry_export(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "export", "-o", "out.json"])
        assert args.command == "telemetry"
        assert args.telemetry_command == "export"
        assert args.output == "out.json"

    def test_telemetry_routing_stats(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "routing-stats"])
        assert args.command == "telemetry"
        assert args.telemetry_command == "routing-stats"

    def test_telemetry_models(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "models"])
        assert args.telemetry_command == "models"

    def test_telemetry_signals(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["telemetry", "signals", "--agent", "a1"])
        assert args.telemetry_command == "signals"

    def test_provider_show(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["provider", "show"])
        assert args.command == "provider"

    def test_provider_set(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["provider", "set", "anthropic"])
        assert args.command == "provider"
        assert args.name == "anthropic"

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

    def test_workflow_list(self) -> None:
        ctx, mock_fn = _mock_subcmd("workflow", "list")
        with ctx:
            assert main(["workflow", "list"]) == 0
        mock_fn.assert_called_once()

    def test_workflow_info(self) -> None:
        ctx, mock_fn = _mock_subcmd("workflow", "info")
        with ctx:
            assert main(["workflow", "info", "wf-name"]) == 0
        mock_fn.assert_called_once()

    def test_workflow_run(self) -> None:
        ctx, mock_fn = _mock_subcmd("workflow", "run")
        with ctx:
            assert main(["workflow", "run", "wf-name"]) == 0
        mock_fn.assert_called_once()

    def test_workflow_no_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        assert main(["workflow"]) == 1
        captured = capsys.readouterr()
        assert "workflow" in captured.out.lower()


class TestMainTelemetryRouting:
    """Tests that main() routes telemetry subcommands correctly."""

    def test_show(self) -> None:
        ctx, mock_fn = _mock_subcmd("telemetry", "show")
        with ctx:
            assert main(["telemetry", "show"]) == 0
        mock_fn.assert_called_once()

    def test_savings(self) -> None:
        ctx, mock_fn = _mock_subcmd("telemetry", "savings")
        with ctx:
            assert main(["telemetry", "savings"]) == 0
        mock_fn.assert_called_once()

    def test_export(self) -> None:
        ctx, mock_fn = _mock_subcmd("telemetry", "export")
        with ctx:
            assert main(["telemetry", "export", "-o", "out.json"]) == 0
        mock_fn.assert_called_once()

    def test_routing_stats(self) -> None:
        ctx, mock_fn = _mock_subcmd("telemetry", "routing-stats")
        with ctx:
            assert main(["telemetry", "routing-stats"]) == 0
        mock_fn.assert_called_once()

    def test_routing_check(self) -> None:
        ctx, mock_fn = _mock_subcmd("telemetry", "routing-check")
        with ctx:
            assert main(["telemetry", "routing-check"]) == 0
        mock_fn.assert_called_once()

    def test_models(self) -> None:
        ctx, mock_fn = _mock_subcmd("telemetry", "models")
        with ctx:
            assert main(["telemetry", "models"]) == 0
        mock_fn.assert_called_once()

    def test_agents(self) -> None:
        ctx, mock_fn = _mock_subcmd("telemetry", "agents")
        with ctx:
            assert main(["telemetry", "agents"]) == 0
        mock_fn.assert_called_once()

    def test_signals(self) -> None:
        ctx, mock_fn = _mock_subcmd("telemetry", "signals")
        with ctx:
            assert main(["telemetry", "signals", "--agent", "a1"]) == 0
        mock_fn.assert_called_once()

    def test_no_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        assert main(["telemetry"]) == 1
        captured = capsys.readouterr()
        assert "telemetry" in captured.out.lower()


class TestMainProviderRouting:
    """Tests that main() routes provider subcommands correctly."""

    def test_show(self) -> None:
        ctx, mock_fn = _mock_subcmd("provider", "show")
        with ctx:
            assert main(["provider", "show"]) == 0
        mock_fn.assert_called_once()

    def test_set(self) -> None:
        ctx, mock_fn = _mock_subcmd("provider", "set")
        with ctx:
            assert main(["provider", "set", "anthropic"]) == 0
        mock_fn.assert_called_once()

    def test_no_subcommand(self, capsys: pytest.CaptureFixture) -> None:
        assert main(["provider"]) == 1
        captured = capsys.readouterr()
        assert "provider" in captured.out.lower()


class TestMainUtilityRouting:
    """Tests that main() routes utility commands correctly."""

    def test_setup(self) -> None:
        ctx, mock_fn = _mock_simple("setup")
        with ctx:
            assert main(["setup"]) == 0
        mock_fn.assert_called_once()

    def test_validate(self) -> None:
        ctx, mock_fn = _mock_simple("validate")
        with ctx:
            assert main(["validate"]) == 0
        mock_fn.assert_called_once()

    def test_version(self) -> None:
        ctx, mock_fn = _mock_simple("version")
        with ctx:
            assert main(["version"]) == 0
        mock_fn.assert_called_once()


class TestMainEdgeCases:
    """Tests for main() edge cases."""

    def test_no_args_prints_help(self, capsys: pytest.CaptureFixture) -> None:
        assert main([]) == 0
        captured = capsys.readouterr()
        assert "attune" in captured.out.lower()

    def test_no_args_includes_auth_status_hint(self, capsys: pytest.CaptureFixture) -> None:
        assert main([]) == 0
        captured = capsys.readouterr()
        assert "auth status" in captured.out

    def test_none_argv(self, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["attune"]):
            assert main(None) == 0

    def test_verbose_enables_debug(self) -> None:
        ctx, mock_fn = _mock_simple("version")
        with ctx, patch("logging.basicConfig") as mock_config:
            main(["version", "-v"])
            assert any(c.kwargs.get("level") == logging.DEBUG for c in mock_config.call_args_list)

    def test_propagates_nonzero(self) -> None:
        ctx, mock_fn = _mock_subcmd("workflow", "list", return_value=1)
        with ctx:
            assert main(["workflow", "list"]) == 1


class TestOneLineLogFormatter:
    """Tests for _OneLineLogFormatter (setup-friction F1)."""

    def _record(self, exc_info=None) -> logging.LogRecord:
        return logging.LogRecord(
            name="attune.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="workflow failed",
            args=(),
            exc_info=exc_info,
        )

    def test_plain_record_formats_one_line(self) -> None:
        fmt = _OneLineLogFormatter(fmt="%(levelname)s:%(name)s:%(message)s")
        message = fmt.format(self._record())
        assert message == "ERROR:attune.test:workflow failed"

    def test_exception_record_suppresses_traceback(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = self._record(exc_info=sys.exc_info())
        fmt = _OneLineLogFormatter(fmt="%(levelname)s:%(name)s:%(message)s")
        message = fmt.format(record)
        assert "Traceback" not in message
        assert "\n" not in message
        assert message.endswith("(re-run with --verbose for the full traceback)")

    def test_record_exc_info_restored_after_format(self) -> None:
        # Other handlers on the same record must still see the exception.
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = self._record(exc_info=sys.exc_info())
        exc_info = record.exc_info
        _OneLineLogFormatter(fmt="%(message)s").format(record)
        assert record.exc_info == exc_info

    def test_main_non_verbose_installs_one_line_formatter(self) -> None:
        ctx, mock_fn = _mock_simple("version")
        with ctx, patch("logging.basicConfig") as mock_config:
            main(["version"])
        call = next(c for c in mock_config.call_args_list if "handlers" in c.kwargs)
        assert call.kwargs["level"] == logging.WARNING
        handlers = call.kwargs["handlers"]
        assert len(handlers) == 1
        assert isinstance(handlers[0].formatter, _OneLineLogFormatter)


class TestCreateParserAuth:
    """Tests for create_parser() — auth subcommands."""

    @pytest.fixture
    def parser(self) -> argparse.ArgumentParser:
        return create_parser()

    def test_auth_status(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["auth", "status"])
        assert args.command == "auth"
        assert args.auth_command == "status"
        assert args.json is False

    def test_auth_status_json(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["auth", "status", "--json"])
        assert args.auth_command == "status"
        assert args.json is True

    def test_auth_setup(self, parser: argparse.ArgumentParser) -> None:
        args = parser.parse_args(["auth", "setup"])
        assert args.command == "auth"
        assert args.auth_command == "setup"


class TestMainAuthRouting:
    """Tests that main() routes auth subcommands correctly."""

    def test_auth_status(self) -> None:
        ctx, mock_fn = _mock_subcmd("auth", "status")
        with ctx:
            assert main(["auth", "status"]) == 0
        mock_fn.assert_called_once()

    def test_auth_status_json(self) -> None:
        ctx, mock_fn = _mock_subcmd("auth", "status")
        with ctx:
            assert main(["auth", "status", "--json"]) == 0
        mock_fn.assert_called_once()

    def test_auth_setup(self) -> None:
        ctx, mock_fn = _mock_subcmd("auth", "setup")
        with ctx:
            assert main(["auth", "setup"]) == 0
        mock_fn.assert_called_once()


class TestMainConsentPrompt:
    """main() fires the first-run usage-ping consent prompt (best-effort)."""

    def test_prompt_invoked_for_non_meta_command(self) -> None:
        ctx, mock_fn = _mock_simple("validate")
        with ctx, patch("attune.telemetry.usage_ping.maybe_prompt_consent") as prompt:
            assert main(["validate"]) == 0
        prompt.assert_called_once()
        mock_fn.assert_called_once()

    def test_prompt_skipped_for_meta_command(self) -> None:
        # "version" is in _CONSENT_SKIP_COMMANDS — no prompt.
        ctx, mock_fn = _mock_simple("version")
        with ctx, patch("attune.telemetry.usage_ping.maybe_prompt_consent") as prompt:
            assert main(["version"]) == 0
        prompt.assert_not_called()

    def test_prompt_failure_never_breaks_the_cli(self) -> None:
        # A raising consent prompt must be swallowed; the command still runs.
        ctx, mock_fn = _mock_simple("validate")
        with (
            ctx,
            patch(
                "attune.telemetry.usage_ping.maybe_prompt_consent",
                side_effect=RuntimeError("boom"),
            ),
        ):
            assert main(["validate"]) == 0
        mock_fn.assert_called_once()
