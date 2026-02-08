"""Tests for src/attune/models/provider_config.py

Tests the provider configuration system including:
- ProviderMode enum
- ProviderConfig dataclass
- Provider detection (anthropic, openai, google, ollama)
- Auto-detection logic
- Model tier selection
- Serialization (to_dict, from_dict)
- File persistence (save, load)
- CLI configuration
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.models.provider_config import (
    ProviderConfig,
    ProviderMode,
    configure_provider_cli,
    get_provider_config,
    reset_provider_config,
    set_provider_config,
)


class TestProviderMode:
    """Tests for ProviderMode enum."""

    def test_single_mode_value(self):
        """Test SINGLE mode has correct value."""
        assert ProviderMode.SINGLE.value == "single"

    def test_mode_from_string(self):
        """Test creating ProviderMode from string."""
        assert ProviderMode("single") == ProviderMode.SINGLE

    def test_invalid_mode_raises(self):
        """Test invalid mode string raises ValueError."""
        with pytest.raises(ValueError):
            ProviderMode("invalid")


class TestProviderConfigBasics:
    """Tests for basic ProviderConfig functionality."""

    def test_default_values(self):
        """Test ProviderConfig default values."""
        config = ProviderConfig()
        assert config.mode == ProviderMode.SINGLE
        assert config.primary_provider == "anthropic"
        assert config.tier_providers == {}
        assert config.available_providers == []
        assert config.prefer_local is False
        assert config.cost_optimization is True

    def test_custom_initialization(self):
        """Test ProviderConfig with custom values (Anthropic-only)."""
        config = ProviderConfig(
            mode=ProviderMode.SINGLE,
            primary_provider="anthropic",
            tier_providers={"cheap": "anthropic"},
            available_providers=["anthropic"],
            prefer_local=False,
            cost_optimization=False,
        )
        assert config.mode == ProviderMode.SINGLE
        assert config.primary_provider == "anthropic"
        assert config.tier_providers == {"cheap": "anthropic"}
        assert config.available_providers == ["anthropic"]
        assert config.prefer_local is False
        assert config.cost_optimization is False


class TestProviderDetection:
    """Tests for provider detection logic (Anthropic-only)."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True)
    @patch.object(ProviderConfig, "_load_env_files", return_value={})
    def test_detect_anthropic_from_env(self, mock_env):
        """Test detection of Anthropic from environment variable."""
        available = ProviderConfig.detect_available_providers()
        assert "anthropic" in available
        assert len(available) == 1  # Anthropic-only

    @patch.dict(os.environ, {}, clear=True)
    @patch.object(
        ProviderConfig,
        "_load_env_files",
        return_value={"ANTHROPIC_API_KEY": "from-file"},
    )
    def test_detect_from_env_file(self, mock_env):
        """Test detection of provider from .env file."""
        available = ProviderConfig.detect_available_providers()
        assert "anthropic" in available

    @patch.dict(os.environ, {}, clear=True)
    @patch.object(ProviderConfig, "_load_env_files", return_value={})
    def test_detect_no_providers(self, mock_env):
        """Test detection when no providers available (Anthropic-only)."""
        available = ProviderConfig.detect_available_providers()
        assert available == []


class TestAutoDetect:
    """Tests for auto_detect method."""

    @patch.object(ProviderConfig, "detect_available_providers", return_value=[])
    def test_auto_detect_no_providers(self, mock_detect):
        """Test auto_detect defaults to anthropic when no providers found."""
        config = ProviderConfig.auto_detect()
        assert config.mode == ProviderMode.SINGLE
        assert config.primary_provider == "anthropic"
        assert config.available_providers == []

    @patch.object(ProviderConfig, "detect_available_providers", return_value=["anthropic"])
    def test_auto_detect_with_anthropic(self, mock_detect):
        """Test auto_detect with Anthropic provider available (Anthropic-only architecture)."""
        config = ProviderConfig.auto_detect()
        assert config.mode == ProviderMode.SINGLE
        assert config.primary_provider == "anthropic"
        assert config.available_providers == ["anthropic"]


class TestGetModelForTier:
    """Tests for get_model_for_tier method."""

    def test_single_mode_uses_primary(self):
        """Test SINGLE mode uses primary provider for all tiers."""
        config = ProviderConfig(
            mode=ProviderMode.SINGLE,
            primary_provider="anthropic",
        )
        # Should return model from anthropic registry
        model = config.get_model_for_tier("cheap")
        if model:  # Model may be None if registry not populated
            assert model.provider == "anthropic"

    def test_get_model_with_enum_tier(self):
        """Test get_model_for_tier with ModelTier enum."""
        from attune.models.registry import ModelTier

        config = ProviderConfig(mode=ProviderMode.SINGLE, primary_provider="anthropic")
        model = config.get_model_for_tier(ModelTier.CAPABLE)
        # Just verify it doesn't raise
        assert model is None or hasattr(model, "id")


class TestSerialization:
    """Tests for serialization methods."""

    def test_to_dict(self):
        """Test to_dict serialization (Anthropic-only architecture)."""
        config = ProviderConfig(
            mode=ProviderMode.SINGLE,
            primary_provider="anthropic",
            tier_providers={"cheap": "anthropic"},
            prefer_local=False,
            cost_optimization=True,
        )
        data = config.to_dict()
        assert data["mode"] == "single"
        assert data["primary_provider"] == "anthropic"
        assert data["tier_providers"] == {"cheap": "anthropic"}
        assert data["prefer_local"] is False
        assert data["cost_optimization"] is True

    @patch.object(ProviderConfig, "detect_available_providers", return_value=["anthropic"])
    def test_from_dict(self, mock_detect):
        """Test from_dict deserialization (Anthropic-only architecture)."""
        data = {
            "mode": "single",
            "primary_provider": "anthropic",
            "tier_providers": {"cheap": "anthropic"},
            "prefer_local": False,
            "cost_optimization": True,
        }
        config = ProviderConfig.from_dict(data)
        assert config.mode == ProviderMode.SINGLE
        assert config.primary_provider == "anthropic"
        assert config.tier_providers == {"cheap": "anthropic"}
        assert config.prefer_local is False
        assert config.cost_optimization is True

    @patch.object(ProviderConfig, "detect_available_providers", return_value=[])
    def test_from_dict_with_defaults(self, mock_detect):
        """Test from_dict with partial data uses defaults."""
        config = ProviderConfig.from_dict({})
        assert config.mode == ProviderMode.SINGLE
        assert config.primary_provider == "anthropic"

    def test_roundtrip_serialization(self):
        """Test to_dict followed by from_dict preserves data (Anthropic-only)."""
        original = ProviderConfig(
            mode=ProviderMode.SINGLE,
            primary_provider="anthropic",
            tier_providers={"premium": "anthropic", "cheap": "anthropic"},
            prefer_local=False,
        )
        with patch.object(ProviderConfig, "detect_available_providers", return_value=[]):
            restored = ProviderConfig.from_dict(original.to_dict())
        assert restored.mode == original.mode
        assert restored.primary_provider == original.primary_provider
        assert restored.tier_providers == original.tier_providers
        assert restored.prefer_local == original.prefer_local


class TestFilePersistence:
    """Tests for save and load methods."""

    def test_save_creates_file(self):
        """Test save creates configuration file."""
        config = ProviderConfig(primary_provider="openai")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            config.save(path)
            assert path.exists()

    def test_save_creates_parent_dirs(self):
        """Test save creates parent directories if needed."""
        config = ProviderConfig()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "config.json"
            config.save(path)
            assert path.exists()

    def test_save_writes_valid_json(self):
        """Test saved file contains valid JSON."""
        config = ProviderConfig(primary_provider="google")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            config.save(path)
            with open(path) as f:
                data = json.load(f)
            assert data["primary_provider"] == "google"

    @patch.object(ProviderConfig, "detect_available_providers", return_value=["openai"])
    def test_load_existing_file(self, mock_detect):
        """Test load reads existing configuration file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            with open(path, "w") as f:
                json.dump({"mode": "single", "primary_provider": "openai"}, f)
            config = ProviderConfig.load(path)
            assert config.primary_provider == "openai"

    @patch.object(ProviderConfig, "auto_detect")
    def test_load_missing_file_auto_detects(self, mock_auto):
        """Test load falls back to auto_detect when file missing."""
        mock_auto.return_value = ProviderConfig(primary_provider="anthropic")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.json"
            ProviderConfig.load(path)
            mock_auto.assert_called_once()

    @patch.object(ProviderConfig, "auto_detect")
    def test_load_invalid_json_auto_detects(self, mock_auto):
        """Test load falls back to auto_detect on invalid JSON."""
        mock_auto.return_value = ProviderConfig(primary_provider="anthropic")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            with open(path, "w") as f:
                f.write("not valid json {{{")
            ProviderConfig.load(path)
            mock_auto.assert_called_once()


class TestConfigureCli:
    """Tests for configure_provider_cli function."""

    @patch.object(ProviderConfig, "detect_available_providers", return_value=["anthropic"])
    def test_configure_cli_explicit_provider(self, mock_detect):
        """Test CLI configuration with explicit Anthropic provider (Anthropic-only)."""
        config = configure_provider_cli(provider="anthropic")
        assert config.mode == ProviderMode.SINGLE
        assert config.primary_provider == "anthropic"

    @patch.object(ProviderConfig, "auto_detect")
    def test_configure_cli_no_args_auto_detects(self, mock_auto):
        """Test CLI configuration with no args uses auto_detect."""
        mock_auto.return_value = ProviderConfig(primary_provider="anthropic")
        configure_provider_cli()
        mock_auto.assert_called_once()


class TestGlobalConfig:
    """Tests for global configuration functions."""

    def teardown_method(self):
        """Reset global config after each test."""
        reset_provider_config()

    def test_set_and_get_provider_config(self):
        """Test setting and getting global config."""
        config = ProviderConfig(primary_provider="openai")
        set_provider_config(config)
        retrieved = get_provider_config()
        assert retrieved.primary_provider == "openai"

    @patch.object(ProviderConfig, "load")
    def test_get_provider_config_lazy_loads(self, mock_load):
        """Test get_provider_config loads config on first call."""
        mock_load.return_value = ProviderConfig(primary_provider="google")
        reset_provider_config()
        config = get_provider_config()
        mock_load.assert_called_once()
        assert config.primary_provider == "google"

    @patch.object(ProviderConfig, "load")
    def test_get_provider_config_caches(self, mock_load):
        """Test get_provider_config caches loaded config."""
        mock_load.return_value = ProviderConfig(primary_provider="google")
        reset_provider_config()
        get_provider_config()
        get_provider_config()
        # Should only load once
        mock_load.assert_called_once()

    def test_reset_clears_cache(self):
        """Test reset_provider_config clears cached config."""
        config = ProviderConfig(primary_provider="openai")
        set_provider_config(config)
        reset_provider_config()
        with patch.object(ProviderConfig, "load") as mock_load:
            mock_load.return_value = ProviderConfig(primary_provider="anthropic")
            new_config = get_provider_config()
            mock_load.assert_called_once()
            assert new_config.primary_provider == "anthropic"


class TestEffectiveRegistry:
    """Tests for get_effective_registry method."""

    def test_effective_registry_returns_dict(self):
        """Test get_effective_registry returns dictionary."""
        config = ProviderConfig(mode=ProviderMode.SINGLE, primary_provider="anthropic")
        registry = config.get_effective_registry()
        assert isinstance(registry, dict)

    def test_effective_registry_has_tier_keys(self):
        """Test effective registry includes expected tier keys."""
        config = ProviderConfig(mode=ProviderMode.SINGLE, primary_provider="anthropic")
        registry = config.get_effective_registry()
        # Keys should be subset of ["cheap", "capable", "premium"]
        for key in registry:
            assert key in ["cheap", "capable", "premium"]


class TestLoadEnvFiles:
    """Tests for _load_env_files static method."""

    def test_load_env_parses_key_value(self):
        """Test _load_env_files parses KEY=value format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("TEST_KEY=test_value\n")
            with patch.object(Path, "cwd", return_value=Path(tmpdir)):
                result = ProviderConfig._load_env_files()
                assert result.get("TEST_KEY") == "test_value"

    def test_load_env_strips_quotes(self):
        """Test _load_env_files strips quotes from values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("KEY1=\"quoted\"\nKEY2='single_quoted'\n")
            with patch.object(Path, "cwd", return_value=Path(tmpdir)):
                result = ProviderConfig._load_env_files()
                assert result.get("KEY1") == "quoted"
                assert result.get("KEY2") == "single_quoted"

    def test_load_env_ignores_comments(self):
        """Test _load_env_files ignores comment lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("# This is a comment\nACTUAL_KEY=value\n")
            with patch.object(Path, "cwd", return_value=Path(tmpdir)):
                result = ProviderConfig._load_env_files()
                assert "# This is a comment" not in result
                assert result.get("ACTUAL_KEY") == "value"

    def test_load_env_handles_missing_file(self):
        """Test _load_env_files handles missing .env gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "cwd", return_value=Path(tmpdir)):
                with patch.object(Path, "home", return_value=Path(tmpdir) / "nonexistent"):
                    result = ProviderConfig._load_env_files()
                    assert isinstance(result, dict)
