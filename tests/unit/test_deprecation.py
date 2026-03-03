"""Unit tests for attune._deprecation module.

Tests cover:
- _emit_cli_deprecation emits a DeprecationWarning
- _emit_cli_deprecation writes the expected message to stderr
- Correct formatting of the warning and stderr message

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

import pytest

from attune._deprecation import _emit_cli_deprecation


@pytest.mark.unit
class TestEmitCliDeprecation:
    """Tests for _emit_cli_deprecation helper."""

    def test_emit_cli_deprecation_raises_deprecation_warning(self) -> None:
        """Test that calling _emit_cli_deprecation emits a DeprecationWarning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _emit_cli_deprecation("attune.telemetry", "attune telemetry <command>")

        assert len(caught) == 1
        assert issubclass(caught[0].category, DeprecationWarning)

    def test_emit_cli_deprecation_warning_message_contains_module_name(self) -> None:
        """Test that the warning message includes the deprecated module name."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _emit_cli_deprecation("attune.project_index", "attune workflow run")

        assert "attune.project_index" in str(caught[0].message)

    def test_emit_cli_deprecation_warning_message_contains_canonical_command(self) -> None:
        """Test that the warning message includes the canonical command."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _emit_cli_deprecation("attune.project_index", "attune workflow run")

        assert "attune workflow run" in str(caught[0].message)

    def test_emit_cli_deprecation_warning_full_message_format(self) -> None:
        """Test that the warning message follows the expected format."""
        module = "attune.test_generator"
        canonical = "attune workflow run test-gen"

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _emit_cli_deprecation(module, canonical)

        expected = f"'python -m {module}' is deprecated. Use '{canonical}' instead."
        assert str(caught[0].message) == expected

    def test_emit_cli_deprecation_writes_to_stderr(self, capsys) -> None:
        """Test that _emit_cli_deprecation prints the warning to stderr."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            _emit_cli_deprecation("attune.telemetry", "attune telemetry <command>")

        captured = capsys.readouterr()
        assert "attune.telemetry" in captured.err
        assert "attune telemetry <command>" in captured.err

    def test_emit_cli_deprecation_stderr_message_format(self, capsys) -> None:
        """Test that stderr message follows the expected WARNING format."""
        module = "attune.telemetry"
        canonical = "attune telemetry <command>"

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            _emit_cli_deprecation(module, canonical)

        captured = capsys.readouterr()
        expected = f"WARNING: 'python -m {module}' is deprecated. Use '{canonical}' instead."
        assert expected in captured.err

    def test_emit_cli_deprecation_nothing_written_to_stdout(self, capsys) -> None:
        """Test that nothing is written to stdout."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            _emit_cli_deprecation("attune.telemetry", "attune telemetry <command>")

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_emit_cli_deprecation_returns_none(self) -> None:
        """Test that the function returns None."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _emit_cli_deprecation("attune.telemetry", "attune telemetry <command>")

        assert result is None

    def test_emit_cli_deprecation_different_module_names(self, capsys) -> None:
        """Test with various module names to verify interpolation works correctly."""
        cases = [
            ("attune.project_index", "attune workflow run"),
            ("attune.test_generator", "attune workflow run test-gen"),
            ("attune.telemetry", "attune telemetry <command>"),
        ]
        for module, canonical in cases:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                _emit_cli_deprecation(module, canonical)

            assert module in str(caught[0].message)
            assert canonical in str(caught[0].message)
            capsys.readouterr()  # clear buffer
