"""Unit tests for attune.mcp.handlers.auth_handlers."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def _make_server() -> MagicMock:
    """Return a minimal server mock."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Helpers — build fake attune.models module trees for lazy-import patching
# ---------------------------------------------------------------------------


def _make_models_module(strategy: MagicMock | None = None) -> ModuleType:
    """Return a fake attune.models module."""
    mod = ModuleType("attune.models")
    mod.AuthStrategy = MagicMock()
    if strategy is not None:
        mod.AuthStrategy.load.return_value = strategy
    return mod


class TestGetAuthStatus:
    """Tests for get_auth_status()."""

    @pytest.mark.asyncio
    async def test_get_auth_status_returns_success_dict(self):
        """Happy path: strategy loaded, returns expected keys."""
        from attune.mcp.handlers.auth_handlers import get_auth_status

        strategy = MagicMock()
        strategy.subscription_tier.value = "FREE"
        strategy.default_mode.value = "subscription"
        strategy.setup_completed = True

        fake_models = _make_models_module(strategy)

        with patch.dict(sys.modules, {"attune.models": fake_models}):
            result = await get_auth_status(_make_server())

        assert result["success"] is True
        assert result["subscription_tier"] == "FREE"
        assert result["default_mode"] == "subscription"
        assert result["setup_completed"] is True

    @pytest.mark.asyncio
    async def test_get_auth_status_setup_completed_false(self):
        """Returns setup_completed=False when not yet configured."""
        from attune.mcp.handlers.auth_handlers import get_auth_status

        strategy = MagicMock()
        strategy.subscription_tier.value = "FREE"
        strategy.default_mode.value = "api"
        strategy.setup_completed = False

        fake_models = _make_models_module(strategy)

        with patch.dict(sys.modules, {"attune.models": fake_models}):
            result = await get_auth_status(_make_server())

        assert result["setup_completed"] is False

    @pytest.mark.asyncio
    async def test_get_auth_status_different_tier_values(self):
        """Tier and mode values are read from the strategy enum .value."""
        from attune.mcp.handlers.auth_handlers import get_auth_status

        strategy = MagicMock()
        strategy.subscription_tier.value = "PRO"
        strategy.default_mode.value = "hybrid"
        strategy.setup_completed = True

        fake_models = _make_models_module(strategy)

        with patch.dict(sys.modules, {"attune.models": fake_models}):
            result = await get_auth_status(_make_server())

        assert result["subscription_tier"] == "PRO"
        assert result["default_mode"] == "hybrid"

    @pytest.mark.asyncio
    async def test_get_auth_status_ignores_server_argument(self):
        """Server argument is accepted but not used by get_auth_status."""
        from attune.mcp.handlers.auth_handlers import get_auth_status

        strategy = MagicMock()
        strategy.subscription_tier.value = "FREE"
        strategy.default_mode.value = "api"
        strategy.setup_completed = False

        fake_models = _make_models_module(strategy)
        server = _make_server()

        with patch.dict(sys.modules, {"attune.models": fake_models}):
            result = await get_auth_status(server)

        assert result["success"] is True


class TestGetAuthRecommend:
    """Tests for get_auth_recommend()."""

    def _make_models_for_recommend(
        self, lines: int = 200, category: str = "medium", recommended_mode: str = "subscription"
    ) -> ModuleType:
        mod = ModuleType("attune.models")
        mod.count_lines_of_code = MagicMock(return_value=lines)
        mod.get_module_size_category = MagicMock(return_value=category)

        strategy = MagicMock()
        recommended = MagicMock()
        recommended.value = recommended_mode
        strategy.get_recommended_mode.return_value = recommended
        mod.get_auth_strategy = MagicMock(return_value=strategy)
        return mod

    @pytest.mark.asyncio
    async def test_get_auth_recommend_returns_success_dict(self, tmp_path):
        """Happy path: returns all expected keys."""
        from attune.mcp.handlers.auth_handlers import get_auth_recommend

        target = tmp_path / "sample.py"
        target.write_text("x = 1\n", encoding="utf-8")
        fake_models = self._make_models_for_recommend(lines=50, category="small")

        with patch.dict(sys.modules, {"attune.models": fake_models}):
            result = await get_auth_recommend(_make_server(), {"file_path": str(target)})

        assert result["success"] is True
        assert result["lines_of_code"] == 50
        assert result["category"] == "small"
        assert result["recommended_mode"] == "subscription"
        assert "file_path" in result

    @pytest.mark.asyncio
    async def test_get_auth_recommend_large_module(self, tmp_path):
        """Large module returns api recommended mode."""
        from attune.mcp.handlers.auth_handlers import get_auth_recommend

        target = tmp_path / "big.py"
        target.write_text("pass\n", encoding="utf-8")
        fake_models = self._make_models_for_recommend(
            lines=5000, category="large", recommended_mode="api"
        )

        with patch.dict(sys.modules, {"attune.models": fake_models}):
            result = await get_auth_recommend(_make_server(), {"file_path": str(target)})

        assert result["lines_of_code"] == 5000
        assert result["category"] == "large"
        assert result["recommended_mode"] == "api"

    @pytest.mark.asyncio
    async def test_get_auth_recommend_file_path_in_result(self, tmp_path):
        """file_path key in result matches the input path string."""
        from attune.mcp.handlers.auth_handlers import get_auth_recommend

        target = tmp_path / "mod.py"
        target.write_text("", encoding="utf-8")
        fake_models = self._make_models_for_recommend()

        with patch.dict(sys.modules, {"attune.models": fake_models}):
            result = await get_auth_recommend(_make_server(), {"file_path": str(target)})

        # file_path is str(Path(args["file_path"]))
        assert result["file_path"] == str(target)

    @pytest.mark.asyncio
    async def test_get_auth_recommend_calls_count_lines(self, tmp_path):
        """count_lines_of_code is called with the resolved Path."""
        from attune.mcp.handlers.auth_handlers import get_auth_recommend

        target = tmp_path / "mod.py"
        target.write_text("", encoding="utf-8")
        fake_models = self._make_models_for_recommend(lines=10)

        with patch.dict(sys.modules, {"attune.models": fake_models}):
            await get_auth_recommend(_make_server(), {"file_path": str(target)})

        fake_models.count_lines_of_code.assert_called_once()
