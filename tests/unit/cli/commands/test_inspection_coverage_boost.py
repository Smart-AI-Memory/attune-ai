"""Tests for inspection CLI commands.

Module: cli/commands/inspection.py (57 lines)
"""

from unittest.mock import Mock, patch

import pytest

from attune.cli.commands.inspection import inspect_cmd, scan


@pytest.mark.unit
class TestScan:
    """Test suite for scan function."""

    @patch("subprocess.run")
    @patch("attune.cli.commands.inspection.console")
    def test_scan_calls_ruff(self, mock_console, mock_run):
        """Test that scan calls ruff."""
        scan()

        # Should call ruff
        calls = [c[0][0] for c in mock_run.call_args_list]
        assert any("ruff" in call for call in calls)

    @patch("subprocess.run")
    @patch("attune.cli.commands.inspection.console")
    def test_scan_with_fix_flag(self, mock_console, mock_run):
        """Test scan with fix=True adds --fix flag."""
        scan(fix=True)

        # Check ruff call has --fix
        ruff_call = [c for c in mock_run.call_args_list if "ruff" in c[0][0]][0]
        assert "--fix" in ruff_call[0][0]


@pytest.mark.unit
class TestInspectCmd:
    """Test suite for inspect_cmd function."""

    @patch("subprocess.run")
    @patch("attune.cli.commands.inspection.console")
    def test_inspect_cmd_calls_subprocess(self, mock_console, mock_run):
        """Test that inspect_cmd calls subprocess."""
        mock_run.return_value = Mock(returncode=0)

        inspect_cmd()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "attune-inspect" in args[0]

    @patch("subprocess.run")
    @patch("attune.cli.commands.inspection.console")
    def test_inspect_cmd_with_format(self, mock_console, mock_run):
        """Test inspect_cmd with format parameter."""
        mock_run.return_value = Mock(returncode=0)

        inspect_cmd(format_out="json")

        args = mock_run.call_args[0][0]
        assert "--format" in args
        assert "json" in args
