"""Tests for provider CLI commands.

Tests cmd_provider_show and cmd_provider_set from
src/attune/cli_commands/provider_commands.py, covering all branches:
success paths, ImportError, generic Exception, hybrid vs single mode,
empty available_providers, and cost_optimization flag states.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from attune.cli_commands.provider_commands import cmd_provider_set, cmd_provider_show

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    mode_value: str = "single",
    primary_provider: str = "anthropic",
    cost_optimization: bool = True,
    available_providers: list[str] | None = None,
) -> MagicMock:
    """Create a mock provider config object."""
    config = MagicMock()
    config.mode.value = mode_value
    config.primary_provider = primary_provider
    config.cost_optimization = cost_optimization
    config.available_providers = (
        available_providers if available_providers is not None else ["anthropic", "openai"]
    )
    return config


# ===========================================================================
# cmd_provider_show
# ===========================================================================


class TestCmdProviderShow:
    """Tests for cmd_provider_show."""

    # -- Success paths -------------------------------------------------------

    def test_show_success_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show returns 0 on success."""
        config = _make_config()
        with patch(
            "attune.cli_commands.provider_commands.get_provider_config",
            create=True,
        ) as mock_get:
            # The function does a late import; we must patch the import mechanism.
            mock_module = MagicMock()
            mock_module.get_provider_config = MagicMock(return_value=config)
            with patch.dict(
                "sys.modules",
                {"attune.models.provider_config": mock_module},
            ):
                result = cmd_provider_show(SimpleNamespace())

        assert result == 0

    def test_show_prints_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show prints the current mode value."""
        config = _make_config(mode_value="hybrid")
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "hybrid" in captured

    def test_show_prints_primary_provider(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show prints the primary provider name."""
        config = _make_config(primary_provider="openai")
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "openai" in captured

    def test_show_prints_cost_optimization_enabled(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cmd_provider_show prints enabled indicator when cost_optimization is True."""
        config = _make_config(cost_optimization=True)
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "Enabled" in captured

    def test_show_prints_cost_optimization_disabled(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cmd_provider_show prints disabled indicator when cost_optimization is False."""
        config = _make_config(cost_optimization=False)
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "Disabled" in captured

    # -- Available providers listing -----------------------------------------

    def test_show_lists_available_providers(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show lists each available provider."""
        config = _make_config(
            primary_provider="anthropic",
            available_providers=["anthropic", "openai", "google"],
        )
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "anthropic" in captured
        assert "openai" in captured
        assert "google" in captured

    def test_show_marks_primary_provider_with_checkmark(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cmd_provider_show marks the primary provider with a checkmark."""
        config = _make_config(
            primary_provider="openai",
            available_providers=["anthropic", "openai"],
        )
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        # The primary provider line should have the checkmark character
        for line in captured.splitlines():
            if "openai" in line and "[" in line:
                assert "\u2713" in line or "✓" in line
                break
        else:
            pytest.fail("Primary provider line with checkmark not found")

    def test_show_non_primary_provider_has_no_checkmark(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cmd_provider_show does not mark non-primary providers with a checkmark."""
        config = _make_config(
            primary_provider="openai",
            available_providers=["anthropic", "openai"],
        )
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        for line in captured.splitlines():
            if "anthropic" in line and "[" in line:
                # Non-primary should have "[ ]" not "[✓]"
                assert "✓" not in line
                break

    # -- Empty available providers -------------------------------------------

    def test_show_empty_available_providers_prints_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cmd_provider_show prints warning when no providers are available."""
        config = _make_config(available_providers=[])
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            result = cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert result == 0
        assert "No API keys detected" in captured

    def test_show_empty_providers_suggests_env_vars(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cmd_provider_show suggests setting API keys when none are detected."""
        config = _make_config(available_providers=[])
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "ANTHROPIC_API_KEY" in captured
        assert "OPENAI_API_KEY" in captured
        assert "GOOGLE_API_KEY" in captured

    # -- Error paths ---------------------------------------------------------

    def test_show_import_error_returns_one(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show returns 1 when ImportError is raised."""
        with patch.dict("sys.modules", {"attune.models.provider_config": None}):
            result = cmd_provider_show(SimpleNamespace())

        assert result == 1

    def test_show_import_error_prints_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show prints error message on ImportError."""
        with patch.dict("sys.modules", {"attune.models.provider_config": None}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "Provider module not available" in captured

    def test_show_generic_exception_returns_one(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show returns 1 when a generic exception is raised."""
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(side_effect=RuntimeError("connection failed"))
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            result = cmd_provider_show(SimpleNamespace())

        assert result == 1

    def test_show_generic_exception_prints_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show prints the exception message on generic error."""
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(side_effect=RuntimeError("connection failed"))
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "connection failed" in captured

    def test_show_prints_header(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show prints the Provider Configuration header."""
        config = _make_config()
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "Provider Configuration" in captured

    def test_show_prints_separator_lines(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_show prints separator lines."""
        config = _make_config()
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(return_value=config)
        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_show(SimpleNamespace())

        captured = capsys.readouterr().out
        assert "-" * 60 in captured


# ===========================================================================
# cmd_provider_set
# ===========================================================================


class TestCmdProviderSet:
    """Tests for cmd_provider_set."""

    # -- Hybrid mode ---------------------------------------------------------

    def test_set_hybrid_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_set returns 0 when setting hybrid mode."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.HYBRID = "HYBRID"
        mock_mode.SINGLE = "SINGLE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            result = cmd_provider_set(SimpleNamespace(name="hybrid"))

        assert result == 0

    def test_set_hybrid_sets_hybrid_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_set sets config.mode to ProviderMode.HYBRID for 'hybrid' name."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.HYBRID = "HYBRID_MODE"
        mock_mode.SINGLE = "SINGLE_MODE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="hybrid"))

        assert config.mode == "HYBRID_MODE"

    def test_set_hybrid_prints_confirmation(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_set prints hybrid confirmation message."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.HYBRID = "HYBRID"
        mock_mode.SINGLE = "SINGLE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="hybrid"))

        captured = capsys.readouterr().out
        assert "hybrid" in captured
        assert "multi-provider" in captured

    def test_set_hybrid_calls_set_provider_config(self) -> None:
        """cmd_provider_set calls set_provider_config with updated config for hybrid."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.HYBRID = "HYBRID"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="hybrid"))

        mock_module.set_provider_config.assert_called_once_with(config)

    def test_set_hybrid_does_not_change_primary_provider(self) -> None:
        """cmd_provider_set does not change primary_provider when setting hybrid."""
        config = _make_config(primary_provider="anthropic")
        mock_mode = MagicMock()
        mock_mode.HYBRID = "HYBRID"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="hybrid"))

        # primary_provider should remain unchanged for hybrid mode
        assert config.primary_provider == "anthropic"

    # -- Single mode ---------------------------------------------------------

    def test_set_single_provider_returns_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_set returns 0 when setting a single provider."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.SINGLE = "SINGLE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            result = cmd_provider_set(SimpleNamespace(name="openai"))

        assert result == 0

    def test_set_single_provider_sets_single_mode(self) -> None:
        """cmd_provider_set sets config.mode to ProviderMode.SINGLE for non-hybrid names."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.SINGLE = "SINGLE_MODE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="openai"))

        assert config.mode == "SINGLE_MODE"

    def test_set_single_provider_updates_primary_provider(self) -> None:
        """cmd_provider_set updates primary_provider to the specified name."""
        config = _make_config(primary_provider="anthropic")
        mock_mode = MagicMock()
        mock_mode.SINGLE = "SINGLE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="google"))

        assert config.primary_provider == "google"

    def test_set_single_provider_prints_confirmation(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cmd_provider_set prints confirmation with the provider name."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.SINGLE = "SINGLE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="openai"))

        captured = capsys.readouterr().out
        assert "openai" in captured

    def test_set_single_provider_calls_set_provider_config(self) -> None:
        """cmd_provider_set calls set_provider_config with updated config for single mode."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.SINGLE = "SINGLE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock()

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="anthropic"))

        mock_module.set_provider_config.assert_called_once_with(config)

    # -- Error paths ---------------------------------------------------------

    def test_set_import_error_returns_one(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_set returns 1 when ImportError is raised."""
        with patch.dict("sys.modules", {"attune.models.provider_config": None}):
            result = cmd_provider_set(SimpleNamespace(name="openai"))

        assert result == 1

    def test_set_import_error_prints_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_set prints error message on ImportError."""
        with patch.dict("sys.modules", {"attune.models.provider_config": None}):
            cmd_provider_set(SimpleNamespace(name="openai"))

        captured = capsys.readouterr().out
        assert "Provider module not available" in captured

    def test_set_generic_exception_returns_one(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_set returns 1 when a generic exception is raised."""
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(side_effect=ValueError("invalid provider"))

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            result = cmd_provider_set(SimpleNamespace(name="openai"))

        assert result == 1

    def test_set_generic_exception_prints_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_set prints the exception message on generic error."""
        mock_module = MagicMock()
        mock_module.get_provider_config = MagicMock(side_effect=ValueError("invalid provider"))

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="openai"))

        captured = capsys.readouterr().out
        assert "invalid provider" in captured

    def test_set_exception_during_set_provider_config_returns_one(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cmd_provider_set returns 1 when set_provider_config raises."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.SINGLE = "SINGLE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock(side_effect=OSError("disk full"))

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            result = cmd_provider_set(SimpleNamespace(name="openai"))

        assert result == 1

    def test_set_exception_during_set_provider_config_prints_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """cmd_provider_set prints error when set_provider_config raises."""
        config = _make_config()
        mock_mode = MagicMock()
        mock_mode.SINGLE = "SINGLE"

        mock_module = MagicMock()
        mock_module.ProviderMode = mock_mode
        mock_module.get_provider_config = MagicMock(return_value=config)
        mock_module.set_provider_config = MagicMock(side_effect=OSError("disk full"))

        with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
            cmd_provider_set(SimpleNamespace(name="openai"))

        captured = capsys.readouterr().out
        assert "disk full" in captured

    # -- Edge cases ----------------------------------------------------------

    def test_set_various_provider_names(self, capsys: pytest.CaptureFixture[str]) -> None:
        """cmd_provider_set works for different non-hybrid provider names."""
        provider_names = ["anthropic", "openai", "google", "custom-provider"]

        for name in provider_names:
            config = _make_config()
            mock_mode = MagicMock()
            mock_mode.SINGLE = "SINGLE"

            mock_module = MagicMock()
            mock_module.ProviderMode = mock_mode
            mock_module.get_provider_config = MagicMock(return_value=config)
            mock_module.set_provider_config = MagicMock()

            with patch.dict("sys.modules", {"attune.models.provider_config": mock_module}):
                result = cmd_provider_set(SimpleNamespace(name=name))

            assert result == 0, f"Expected 0 for provider '{name}', got {result}"
            assert config.primary_provider == name
