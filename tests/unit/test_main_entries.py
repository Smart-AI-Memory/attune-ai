"""Unit tests for __main__.py entry points.

Tests cover:
- attune.project_index.__main__: calls _emit_cli_deprecation and main()
- attune.test_generator.__main__: calls _emit_cli_deprecation and main()
- attune.telemetry.__main__: main() with show, savings, export subcommands
  and no-command fallback (help + return 1)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import importlib.util
import warnings
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# attune.project_index.__main__
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProjectIndexMain:
    """Tests for attune.project_index.__main__ entry point."""

    def test_emit_deprecation_format_for_project_index(self, capsys) -> None:
        """Test that the deprecation message for project_index follows expected format."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            from attune._deprecation import _emit_cli_deprecation

            _emit_cli_deprecation("attune.project_index", "attune workflow run")

        # Verify a DeprecationWarning was emitted
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        # Verify message format
        message_text = str(caught[0].message)
        assert "python -m attune.project_index" in message_text
        assert "attune workflow run" in message_text

    def test_module_imports_without_error(self) -> None:
        """Test that attune.project_index.__main__ can be imported without error."""
        import attune.project_index.__main__  # noqa: F401

    def test_deprecation_message_module_name(self, capsys) -> None:
        """Test the deprecation message includes attune.project_index."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            from attune._deprecation import _emit_cli_deprecation

            _emit_cli_deprecation("attune.project_index", "attune workflow run")

        captured = capsys.readouterr()
        assert "attune.project_index" in captured.err

    def test_deprecation_message_canonical_command(self, capsys) -> None:
        """Test the deprecation message includes the canonical command."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            from attune._deprecation import _emit_cli_deprecation

            _emit_cli_deprecation("attune.project_index", "attune workflow run")

        captured = capsys.readouterr()
        assert "attune workflow run" in captured.err


# ---------------------------------------------------------------------------
# attune.test_generator.__main__
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.skipif(
    not importlib.util.find_spec("jinja2"),
    reason="jinja2 not installed",
)
class TestTestGeneratorMain:
    """Tests for attune.test_generator.__main__ entry point."""

    def test_module_imports_without_error(self) -> None:
        """Test that attune.test_generator.__main__ can be imported without error."""
        import attune.test_generator.__main__  # noqa: F401

    def test_deprecation_message_module_name(self, capsys) -> None:
        """Test the deprecation message includes attune.test_generator."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            from attune._deprecation import _emit_cli_deprecation

            _emit_cli_deprecation("attune.test_generator", "attune workflow run test-gen")

        captured = capsys.readouterr()
        assert "attune.test_generator" in captured.err

    def test_deprecation_message_canonical_command(self, capsys) -> None:
        """Test the deprecation message includes attune workflow run test-gen."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            from attune._deprecation import _emit_cli_deprecation

            _emit_cli_deprecation("attune.test_generator", "attune workflow run test-gen")

        captured = capsys.readouterr()
        assert "attune workflow run test-gen" in captured.err


# ---------------------------------------------------------------------------
# attune.telemetry.__main__ — main() function
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTelemetryMain:
    """Tests for attune.telemetry.__main__.main() function."""

    def _call_main_with_argv(self, argv: list[str], mock_cli_core: MagicMock) -> int:
        """Helper: run telemetry main() with patched argv and cli_core.

        Args:
            argv: sys.argv arguments (without the program name).
            mock_cli_core: Mock module for attune.telemetry.cli_core.

        Returns:
            Return code from main().

        """
        with (
            patch("sys.argv", ["prog"] + argv),
            patch.dict("sys.modules", {"attune.telemetry.cli_core": mock_cli_core}),
        ):
            from attune.telemetry.__main__ import main

            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                return main()

    def _make_cli_core(self, return_value: int = 0) -> MagicMock:
        """Build a mock cli_core module.

        Args:
            return_value: Integer return value for all cli commands.

        Returns:
            MagicMock with cmd_telemetry_show, savings, export attributes.

        """
        mock = MagicMock()
        mock.cmd_telemetry_show = MagicMock(return_value=return_value)
        mock.cmd_telemetry_savings = MagicMock(return_value=return_value)
        mock.cmd_telemetry_export = MagicMock(return_value=return_value)
        return mock

    def test_no_subcommand_returns_1(self) -> None:
        """Test that calling main() without a subcommand returns 1."""
        mock_cli_core = self._make_cli_core()
        with (
            patch("sys.argv", ["prog"]),
            patch.dict("sys.modules", {"attune.telemetry.cli_core": mock_cli_core}),
        ):
            from importlib import reload

            import attune.telemetry.__main__ as telemetry_main

            reload(telemetry_main)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = telemetry_main.main()
        assert result == 1

    def test_show_subcommand_calls_cmd_telemetry_show(self) -> None:
        """Test that 'show' subcommand calls cmd_telemetry_show."""
        mock_cli_core = self._make_cli_core(return_value=0)
        with (
            patch("sys.argv", ["prog", "show"]),
            patch.dict("sys.modules", {"attune.telemetry.cli_core": mock_cli_core}),
        ):
            from importlib import reload

            import attune.telemetry.__main__ as telemetry_main

            reload(telemetry_main)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = telemetry_main.main()

        assert result == 0
        mock_cli_core.cmd_telemetry_show.assert_called_once()

    def test_savings_subcommand_calls_cmd_telemetry_savings(self) -> None:
        """Test that 'savings' subcommand calls cmd_telemetry_savings."""
        mock_cli_core = self._make_cli_core(return_value=0)
        with (
            patch("sys.argv", ["prog", "savings"]),
            patch.dict("sys.modules", {"attune.telemetry.cli_core": mock_cli_core}),
        ):
            from importlib import reload

            import attune.telemetry.__main__ as telemetry_main

            reload(telemetry_main)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = telemetry_main.main()

        assert result == 0
        mock_cli_core.cmd_telemetry_savings.assert_called_once()

    def test_export_subcommand_calls_cmd_telemetry_export(self) -> None:
        """Test that 'export' subcommand calls cmd_telemetry_export."""
        mock_cli_core = self._make_cli_core(return_value=0)
        with (
            patch("sys.argv", ["prog", "export", "--output", "/tmp/out.json"]),
            patch.dict("sys.modules", {"attune.telemetry.cli_core": mock_cli_core}),
        ):
            from importlib import reload

            import attune.telemetry.__main__ as telemetry_main

            reload(telemetry_main)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = telemetry_main.main()

        assert result == 0
        mock_cli_core.cmd_telemetry_export.assert_called_once()

    def test_show_with_days_flag(self) -> None:
        """Test 'show --days 7' passes args to cmd_telemetry_show."""
        mock_cli_core = self._make_cli_core(return_value=0)
        with (
            patch("sys.argv", ["prog", "show", "--days", "7"]),
            patch.dict("sys.modules", {"attune.telemetry.cli_core": mock_cli_core}),
        ):
            from importlib import reload

            import attune.telemetry.__main__ as telemetry_main

            reload(telemetry_main)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = telemetry_main.main()

        assert result == 0
        call_args = mock_cli_core.cmd_telemetry_show.call_args
        assert call_args[0][0].days == 7

    def test_main_emits_deprecation_warning(self) -> None:
        """Test that main() emits a DeprecationWarning."""
        mock_cli_core = self._make_cli_core(return_value=0)
        with (
            patch("sys.argv", ["prog", "show"]),
            patch.dict("sys.modules", {"attune.telemetry.cli_core": mock_cli_core}),
        ):
            from importlib import reload

            import attune.telemetry.__main__ as telemetry_main

            reload(telemetry_main)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                telemetry_main.main()

        deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1

    def test_main_deprecation_stderr_message(self, capsys) -> None:
        """Test that main() writes deprecation warning to stderr."""
        mock_cli_core = self._make_cli_core(return_value=0)
        with (
            patch("sys.argv", ["prog", "show"]),
            patch.dict("sys.modules", {"attune.telemetry.cli_core": mock_cli_core}),
        ):
            from importlib import reload

            import attune.telemetry.__main__ as telemetry_main

            reload(telemetry_main)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                telemetry_main.main()

        captured = capsys.readouterr()
        assert "attune.telemetry" in captured.err

    def test_export_with_csv_format(self) -> None:
        """Test 'export --output file.csv --format csv' is dispatched correctly."""
        mock_cli_core = self._make_cli_core(return_value=0)
        with (
            patch(
                "sys.argv",
                ["prog", "export", "--output", "/tmp/out.csv", "--format", "csv"],
            ),
            patch.dict("sys.modules", {"attune.telemetry.cli_core": mock_cli_core}),
        ):
            from importlib import reload

            import attune.telemetry.__main__ as telemetry_main

            reload(telemetry_main)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = telemetry_main.main()

        assert result == 0
        mock_cli_core.cmd_telemetry_export.assert_called_once()
