"""Unit tests for authentication CLI commands.

Covers cmd_auth_setup, cmd_auth_status, cmd_auth_reset,
cmd_auth_recommend, and main() argument routing.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from attune.models.auth_cli import (
    cmd_auth_recommend,
    cmd_auth_reset,
    cmd_auth_setup,
    cmd_auth_status,
    main,
)

# ------------------------------------------------------------------
# cmd_auth_setup
# ------------------------------------------------------------------


class TestCmdAuthSetup:
    """Tests for cmd_auth_setup()."""

    @patch("attune.models.auth_cli.configure_auth_interactive")
    def test_success_returns_zero(self, mock_interactive):
        """Successful setup returns exit code 0."""
        mock_strategy = MagicMock()
        mock_strategy.subscription_tier.value = "free"
        mock_strategy.default_mode.value = "subscription"
        mock_interactive.return_value = mock_strategy

        result = cmd_auth_setup(SimpleNamespace())
        assert result == 0
        mock_interactive.assert_called_once()

    @patch("attune.models.auth_cli.configure_auth_interactive")
    def test_keyboard_interrupt_returns_one(self, mock_interactive):
        """KeyboardInterrupt during setup returns exit code 1."""
        mock_interactive.side_effect = KeyboardInterrupt()

        result = cmd_auth_setup(SimpleNamespace())
        assert result == 1

    @patch("attune.models.auth_cli.configure_auth_interactive")
    def test_exception_returns_one(self, mock_interactive):
        """Unexpected exception returns exit code 1."""
        mock_interactive.side_effect = RuntimeError("setup failed")

        result = cmd_auth_setup(SimpleNamespace())
        assert result == 1


# ------------------------------------------------------------------
# cmd_auth_status
# ------------------------------------------------------------------


class TestCmdAuthStatus:
    """Tests for cmd_auth_status()."""

    @patch("attune.models.auth_cli.AuthStrategy")
    def test_json_output(self, mock_strategy_cls, capsys):
        """--json flag produces JSON output."""
        mock_strategy = MagicMock()
        mock_strategy.subscription_tier.value = "free"
        mock_strategy.default_mode.value = "subscription"
        mock_strategy.small_module_threshold = 500
        mock_strategy.medium_module_threshold = 2000
        mock_strategy.loc_to_tokens_multiplier = 3
        mock_strategy.prefer_subscription = True
        mock_strategy.cost_optimization = True
        mock_strategy.setup_completed = True
        mock_strategy_cls.load.return_value = mock_strategy

        args = SimpleNamespace(json=True)
        result = cmd_auth_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert '"subscription_tier": "free"' in captured.out

    @patch("attune.models.auth_cli.AuthStrategy")
    def test_plain_text_output(self, mock_strategy_cls, capsys):
        """Default output produces readable text."""
        mock_strategy = MagicMock()
        mock_strategy.subscription_tier.value = "free"
        mock_strategy.default_mode.value = "subscription"
        mock_strategy.small_module_threshold = 500
        mock_strategy.medium_module_threshold = 2000
        mock_strategy.setup_completed = True
        mock_strategy.subscription_tier = MagicMock()
        mock_strategy.subscription_tier.value = "free"
        mock_strategy_cls.load.return_value = mock_strategy

        args = SimpleNamespace(json=False)
        with patch("attune.models.auth_cli.RICH_AVAILABLE", False):
            result = cmd_auth_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "AUTHENTICATION STRATEGY" in captured.out

    @patch("attune.models.auth_cli.AuthStrategy")
    def test_no_config_returns_one(self, mock_strategy_cls):
        """Missing config file returns exit code 1."""
        mock_strategy_cls.load.side_effect = FileNotFoundError()

        result = cmd_auth_status(SimpleNamespace(json=False))
        assert result == 1


# ------------------------------------------------------------------
# cmd_auth_reset
# ------------------------------------------------------------------


class TestCmdAuthReset:
    """Tests for cmd_auth_reset()."""

    def test_without_confirm_returns_one(self, capsys):
        """Without --confirm, prints warning and returns 1."""
        result = cmd_auth_reset(SimpleNamespace(confirm=False))
        assert result == 1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    @patch("attune.models.auth_cli.AUTH_STRATEGY_FILE")
    def test_with_confirm_deletes_file(self, mock_file):
        """With --confirm, deletes the config file."""
        mock_file.exists.return_value = True

        result = cmd_auth_reset(SimpleNamespace(confirm=True))
        assert result == 0
        mock_file.unlink.assert_called_once()

    @patch("attune.models.auth_cli.AUTH_STRATEGY_FILE")
    def test_with_confirm_no_file(self, mock_file):
        """With --confirm but no file, returns 0."""
        mock_file.exists.return_value = False

        result = cmd_auth_reset(SimpleNamespace(confirm=True))
        assert result == 0


# ------------------------------------------------------------------
# cmd_auth_recommend
# ------------------------------------------------------------------


class TestCmdAuthRecommend:
    """Tests for cmd_auth_recommend()."""

    def test_missing_file_path_returns_one(self):
        """No file_path argument returns exit code 1."""
        result = cmd_auth_recommend(SimpleNamespace(file_path=None))
        assert result == 1

    def test_nonexistent_file_returns_one(self, tmp_path):
        """Nonexistent file returns exit code 1."""
        missing = tmp_path / "missing.py"
        result = cmd_auth_recommend(SimpleNamespace(file_path=str(missing)))
        assert result == 1

    def test_directory_path_returns_one(self, tmp_path):
        """Directory path (not a file) returns exit code 1."""
        result = cmd_auth_recommend(SimpleNamespace(file_path=str(tmp_path)))
        assert result == 1

    @patch("attune.models.auth_cli.AuthStrategy")
    @patch("attune.models.auth_cli.count_lines_of_code")
    @patch("attune.models.auth_cli.get_module_size_category")
    def test_success_returns_zero(self, mock_category, mock_loc, mock_strategy_cls, tmp_path):
        """Valid file with loaded strategy returns 0."""
        test_file = tmp_path / "module.py"
        test_file.write_text("print('hello')\n")

        mock_loc.return_value = 100
        mock_category.return_value = "small"
        mock_strategy = MagicMock()
        mock_strategy.get_recommended_mode.return_value = MagicMock(value="subscription")
        mock_strategy.estimate_cost.return_value = {
            "mode": "subscription",
            "quota_cost": "low",
            "fits_in_context": True,
            "tokens_used": 300,
        }
        mock_strategy_cls.load.return_value = mock_strategy

        with patch("attune.models.auth_cli.RICH_AVAILABLE", False):
            result = cmd_auth_recommend(SimpleNamespace(file_path=str(test_file)))

        assert result == 0

    @patch("attune.models.auth_cli.AuthStrategy")
    def test_no_strategy_returns_one(self, mock_strategy_cls, tmp_path):
        """Missing auth strategy returns exit code 1."""
        test_file = tmp_path / "module.py"
        test_file.write_text("print('hello')\n")
        mock_strategy_cls.load.side_effect = FileNotFoundError()

        result = cmd_auth_recommend(SimpleNamespace(file_path=str(test_file)))
        assert result == 1


# ------------------------------------------------------------------
# main() routing
# ------------------------------------------------------------------


class TestMain:
    """Tests for main() argument routing."""

    @patch("attune.models.auth_cli.cmd_auth_setup", return_value=0)
    def test_routes_setup(self, mock_setup):
        """'setup' subcommand routes to cmd_auth_setup."""
        with patch("sys.argv", ["auth_cli", "setup"]):
            result = main()
        assert result == 0
        mock_setup.assert_called_once()

    @patch("attune.models.auth_cli.cmd_auth_status", return_value=0)
    def test_routes_status(self, mock_status):
        """'status' subcommand routes to cmd_auth_status."""
        with patch("sys.argv", ["auth_cli", "status"]):
            result = main()
        assert result == 0
        mock_status.assert_called_once()

    @patch("attune.models.auth_cli.cmd_auth_reset", return_value=0)
    def test_routes_reset(self, mock_reset):
        """'reset' subcommand routes to cmd_auth_reset."""
        with patch("sys.argv", ["auth_cli", "reset"]):
            result = main()
        assert result == 0
        mock_reset.assert_called_once()

    def test_no_command_returns_one(self):
        """No subcommand prints help and returns 1."""
        with patch("sys.argv", ["auth_cli"]):
            result = main()
        assert result == 1
