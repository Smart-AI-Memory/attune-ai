"""Branch tests for auth_cli rich-output, PRO/api, and error paths.

Complements tests/unit/models/test_auth_cli.py (which covers JSON,
plain-text-non-PRO, and not-found paths) by exercising the parts it
leaves uncovered: the rich-rendered status/recommend output, the PRO
threshold table and api-mode plain text, the generic exception arms,
and main()'s recommend routing. RICH_AVAILABLE is toggled via
monkeypatch/patch (auto-reverts — no module-global pollution).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from attune.models.auth_cli import (
    cmd_auth_recommend,
    cmd_auth_reset,
    cmd_auth_status,
    main,
)
from attune.models.auth_strategy import SubscriptionTier


def _status_strategy(tier: SubscriptionTier) -> MagicMock:
    s = MagicMock()
    s.subscription_tier = tier
    s.default_mode = MagicMock(value="subscription")
    s.small_module_threshold = 500
    s.medium_module_threshold = 2000
    s.setup_completed = True
    return s


def _write_module(tmp_path) -> str:
    f = tmp_path / "module.py"
    f.write_text("print('hello')\n", encoding="utf-8")
    return str(f)


class TestStatusRichOutput:
    """The RICH_AVAILABLE rendering branch of cmd_auth_status."""

    @patch("attune.models.auth_cli.AuthStrategy")
    def test_rich_non_pro_renders_subscription_thresholds(self, mock_cls, capsys):
        mock_cls.load.return_value = _status_strategy(SubscriptionTier.MAX)

        assert cmd_auth_status(SimpleNamespace(json=False)) == 0

        out = capsys.readouterr().out
        assert "Authentication Strategy" in out
        assert "Thresholds" in out

    @patch("attune.models.auth_cli.AuthStrategy")
    def test_rich_pro_renders_api_thresholds(self, mock_cls, capsys):
        mock_cls.load.return_value = _status_strategy(SubscriptionTier.PRO)

        assert cmd_auth_status(SimpleNamespace(json=False)) == 0
        assert "Thresholds" in capsys.readouterr().out

    @patch("attune.models.auth_cli.AuthStrategy")
    def test_plain_text_pro_recommends_api(self, mock_cls, capsys):
        mock_cls.load.return_value = _status_strategy(SubscriptionTier.PRO)

        with patch("attune.models.auth_cli.RICH_AVAILABLE", False):
            assert cmd_auth_status(SimpleNamespace(json=False)) == 0

        # PRO plain-text path prints the all-modules-to-API line.
        assert "API" in capsys.readouterr().out

    @patch("attune.models.auth_cli.AuthStrategy")
    def test_generic_error_returns_one(self, mock_cls):
        # A non-FileNotFoundError hits the generic except arm.
        mock_cls.load.side_effect = RuntimeError("corrupt config")

        assert cmd_auth_status(SimpleNamespace(json=False)) == 1


class TestResetErrorPath:
    @patch("attune.models.auth_cli.AUTH_STRATEGY_FILE")
    def test_unlink_error_returns_one(self, mock_file):
        mock_file.exists.return_value = True
        mock_file.unlink.side_effect = OSError("permission denied")

        assert cmd_auth_reset(SimpleNamespace(confirm=True)) == 1


class TestRecommendRichOutput:
    """The RICH_AVAILABLE rendering branch of cmd_auth_recommend."""

    @patch("attune.models.auth_cli.get_module_size_category", return_value="small")
    @patch("attune.models.auth_cli.count_lines_of_code", return_value=120)
    @patch("attune.models.auth_cli.AuthStrategy")
    def test_rich_subscription_recommendation(self, mock_cls, _loc, _cat, tmp_path, capsys):
        s = MagicMock()
        s.get_recommended_mode.return_value = MagicMock(value="subscription")
        s.estimate_cost.return_value = {
            "mode": "subscription",
            "quota_cost": "low",
            "fits_in_context": True,
            "tokens_used": 300,
        }
        mock_cls.load.return_value = s

        result = cmd_auth_recommend(SimpleNamespace(file_path=_write_module(tmp_path)))

        assert result == 0
        assert "Recommendation" in capsys.readouterr().out

    @patch("attune.models.auth_cli.get_module_size_category", return_value="large")
    @patch("attune.models.auth_cli.count_lines_of_code", return_value=8000)
    @patch("attune.models.auth_cli.AuthStrategy")
    def test_rich_api_recommendation(self, mock_cls, _loc, _cat, tmp_path, capsys):
        s = MagicMock()
        s.get_recommended_mode.return_value = MagicMock(value="api")
        s.estimate_cost.return_value = {
            "mode": "api",
            "monetary_cost": 0.1234,
            "fits_in_context": True,
            "tokens_used": 8000,
        }
        mock_cls.load.return_value = s

        result = cmd_auth_recommend(SimpleNamespace(file_path=_write_module(tmp_path)))

        assert result == 0
        assert "Recommendation" in capsys.readouterr().out

    @patch("attune.models.auth_cli.get_module_size_category", return_value="large")
    @patch("attune.models.auth_cli.count_lines_of_code", return_value=8000)
    @patch("attune.models.auth_cli.AuthStrategy")
    def test_plain_text_api_recommendation(self, mock_cls, _loc, _cat, tmp_path, capsys):
        s = MagicMock()
        s.get_recommended_mode.return_value = MagicMock(value="api")
        s.estimate_cost.return_value = {
            "mode": "api",
            "monetary_cost": 0.1234,
            "fits_in_context": True,
            "tokens_used": 8000,
        }
        mock_cls.load.return_value = s

        with patch("attune.models.auth_cli.RICH_AVAILABLE", False):
            result = cmd_auth_recommend(SimpleNamespace(file_path=_write_module(tmp_path)))

        assert result == 0
        out = capsys.readouterr().out
        assert "1M context window" in out

    @patch("attune.models.auth_cli.count_lines_of_code", side_effect=RuntimeError("boom"))
    @patch("attune.models.auth_cli.AuthStrategy")
    def test_generic_error_returns_one(self, mock_cls, _loc, tmp_path):
        # File checks pass; a non-FileNotFoundError inside hits the
        # generic except arm.
        mock_cls.load.return_value = MagicMock()

        result = cmd_auth_recommend(SimpleNamespace(file_path=_write_module(tmp_path)))

        assert result == 1


class TestMainRoutesRecommend:
    @patch("attune.models.auth_cli.cmd_auth_recommend", return_value=0)
    def test_routes_recommend(self, mock_rec):
        with patch("sys.argv", ["auth_cli", "recommend", "some_file.py"]):
            assert main() == 0
        mock_rec.assert_called_once()
