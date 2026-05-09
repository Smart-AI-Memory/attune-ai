"""Coverage tests for attune.models.provider_config.

Targets previously-uncovered lines:
- 60->63: ANTHROPIC_API_KEY missing → empty available list
- 135->133: get_effective_registry skip when model is None
- 164: save() with path=None default
- 202-244: configure_provider_interactive
- 264-279: configure_provider_cli
- 316-322: configure_hybrid_interactive
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from attune.models.provider_config import (
    ProviderConfig,
    ProviderMode,
    configure_hybrid_interactive,
    configure_provider_cli,
    configure_provider_interactive,
)


class TestDetectAvailableProvidersFalse:
    """Cover line 60->63 branch: no ANTHROPIC_API_KEY."""

    def test_no_api_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Patch _load_env_files to also return empty
        with patch.object(
            ProviderConfig,
            "_load_env_files",
            return_value={},
        ):
            available = ProviderConfig.detect_available_providers()
        assert available == []


class TestGetEffectiveRegistrySkipNone:
    """Cover branch 135->133: get_model_for_tier returns None → skip tier."""

    def test_returns_only_available_tiers(self):
        """If get_model_for_tier returns None for some tiers, they're skipped."""
        config = ProviderConfig(
            mode=ProviderMode.SINGLE,
            primary_provider="anthropic",
            available_providers=["anthropic"],
        )
        # Patch get_model_for_tier to return None for "premium"
        original = config.get_model_for_tier

        def fake_get(tier):
            if (tier.value if hasattr(tier, "value") else tier) == "premium":
                return None
            return original(tier)

        with patch.object(config, "get_model_for_tier", side_effect=fake_get):
            result = config.get_effective_registry()
        # premium key should not be in result
        assert "premium" not in result
        # Other tiers may be present (depends on registry)


class TestSaveDefaultPath:
    """Cover line 164: save() with path=None uses default."""

    def test_save_with_default_path(self, monkeypatch, tmp_path):
        """Default path is ~/.attune/provider_config.json."""
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

        config = ProviderConfig(
            mode=ProviderMode.SINGLE,
            primary_provider="anthropic",
            available_providers=[],
        )
        config.save()
        # File should be at the default location
        expected = tmp_path / ".attune" / "provider_config.json"
        assert expected.exists()


class TestConfigureProviderInteractive:
    """Cover lines 202-244."""

    def test_with_api_key_saves_config(self, monkeypatch, tmp_path, capsys):
        """ANTHROPIC_API_KEY present → configure + save."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

        config = configure_provider_interactive()
        assert config.primary_provider == "anthropic"
        # Should have saved
        assert (tmp_path / ".attune" / "provider_config.json").exists()

        out = capsys.readouterr().out
        assert "ANTHROPIC_API_KEY detected" in out
        assert "Configuration saved" in out

    def test_without_api_key_returns_empty_available(self, monkeypatch, capsys):
        """No ANTHROPIC_API_KEY → returns config with empty available_providers."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch.object(ProviderConfig, "_load_env_files", return_value={}):
            config = configure_provider_interactive()
        assert config.available_providers == []
        assert config.primary_provider == "anthropic"

        out = capsys.readouterr().out
        assert "ANTHROPIC_API_KEY not detected" in out


class TestConfigureProviderCli:
    """Cover lines 264-279."""

    def test_anthropic_provider_succeeds(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        config = configure_provider_cli(provider="anthropic")
        assert config.primary_provider == "anthropic"

    def test_none_provider_succeeds(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        config = configure_provider_cli()
        assert config.primary_provider == "anthropic"

    def test_uppercase_anthropic_normalized(self, monkeypatch):
        """Lower-cased comparison → 'ANTHROPIC' is accepted."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        config = configure_provider_cli(provider="ANTHROPIC")
        assert config.primary_provider == "anthropic"

    def test_other_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Provider 'openai' is not supported"):
            configure_provider_cli(provider="openai")

    def test_other_mode_raises_value_error(self):
        with pytest.raises(ValueError, match="Mode 'hybrid' is not supported"):
            configure_provider_cli(mode="hybrid")

    def test_single_mode_succeeds(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        config = configure_provider_cli(mode="single")
        assert config.primary_provider == "anthropic"

    def test_uppercase_single_mode(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        config = configure_provider_cli(mode="SINGLE")
        assert config.primary_provider == "anthropic"


class TestConfigureHybridInteractive:
    """Cover lines 316-322."""

    def test_calls_provider_interactive(self, monkeypatch, tmp_path, capsys):
        """Hybrid is deprecated; just calls provider_interactive."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

        config = configure_hybrid_interactive()
        assert config.primary_provider == "anthropic"

        out = capsys.readouterr().out
        assert "Hybrid mode is deprecated" in out
        assert "Anthropic" in out
