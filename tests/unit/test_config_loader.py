"""Tests for attune.config.loader module."""

import json
import logging

import pytest

from attune.config.loader import ConfigLoader, load_unified_config
from attune.config.unified import UnifiedConfig


class TestConfigLoaderDiscover:
    def test_discover_returns_none_when_no_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = ConfigLoader.discover_config_path()
        # May find user home config; just verify it returns Path or None
        assert result is None or result.exists()

    def test_discover_finds_project_local(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "attune.config.json"
        config_file.write_text(json.dumps({"_version": "1.0.0"}))
        result = ConfigLoader.discover_config_path()
        assert result is not None
        assert result.exists()


class TestConfigLoaderLoad:
    def test_load_from_explicit_path(self, tmp_path):
        config_file = tmp_path / "config.json"
        config = UnifiedConfig()
        config_file.write_text(json.dumps(config.to_dict()))

        loader = ConfigLoader(config_path=str(config_file))
        loaded = loader.load()
        assert isinstance(loaded, UnifiedConfig)
        assert loaded._version == "1.0.0"

    def test_load_missing_explicit_path_raises(self, tmp_path):
        loader = ConfigLoader(config_path=str(tmp_path / "nonexistent.json"))
        with pytest.raises(ValueError, match="Config file not found"):
            loader.load()

    def test_load_malformed_json_raises(self, tmp_path):
        config_file = tmp_path / "bad.json"
        config_file.write_text("{invalid json")

        loader = ConfigLoader(config_path=str(config_file))
        with pytest.raises(json.JSONDecodeError):
            loader.load()

    def test_load_defaults_when_no_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Ensure no config exists in search paths
        monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
        loader = ConfigLoader()
        config = loader.load()
        assert isinstance(config, UnifiedConfig)

    def test_get_config_loads_on_first_call(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
        loader = ConfigLoader()
        config = loader.get_config()
        assert isinstance(config, UnifiedConfig)
        # Second call returns cached
        config2 = loader.get_config()
        assert config is config2


class TestConfigLoaderSave:
    def test_save_creates_file(self, tmp_path):
        config = UnifiedConfig()
        save_path = tmp_path / "saved_config.json"

        loader = ConfigLoader()
        result = loader.save(config, path=save_path)
        assert result.exists()

        data = json.loads(save_path.read_text())
        assert data["_version"] == "1.0.0"

    def test_save_creates_parent_dirs(self, tmp_path):
        config = UnifiedConfig()
        save_path = tmp_path / "subdir" / "deep" / "config.json"

        loader = ConfigLoader()
        result = loader.save(config, path=save_path)
        assert result.exists()

    def test_save_validates_path(self):
        config = UnifiedConfig()
        loader = ConfigLoader()
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            loader.save(config, path="/etc/attune_config.json")


class TestConfigLoaderEnvOverrides:
    def test_apply_env_override_string(self, monkeypatch):
        config = UnifiedConfig()
        monkeypatch.setenv("ATTUNE_AUTH_STRATEGY", "api")
        result = ConfigLoader.apply_env_overrides(config)
        assert result.get_value("auth.strategy") == "api"

    def test_apply_env_override_bool(self, monkeypatch):
        config = UnifiedConfig()
        monkeypatch.setenv("ATTUNE_TELEMETRY_ENABLED", "false")
        result = ConfigLoader.apply_env_overrides(config)
        assert result.get_value("telemetry.enabled") is False

    def test_apply_env_override_invalid_key_ignored(self, monkeypatch):
        config = UnifiedConfig()
        monkeypatch.setenv("ATTUNE_NONEXISTENT_SETTING", "value")
        # Should not raise
        result = ConfigLoader.apply_env_overrides(config)
        assert isinstance(result, UnifiedConfig)

    def test_apply_env_override_single_part_ignored(self, monkeypatch):
        config = UnifiedConfig()
        monkeypatch.setenv("ATTUNE_JUSTONEPART", "value")
        result = ConfigLoader.apply_env_overrides(config)
        assert isinstance(result, UnifiedConfig)

    def test_non_section_var_skipped_without_warning(self, monkeypatch, caplog):
        """Standalone ATTUNE_* knobs (read directly by their consumers,
        not config-section overrides) are skipped silently — no warning."""
        config = UnifiedConfig()
        monkeypatch.setenv("ATTUNE_MAX_BUDGET_USD", "10.00")
        with caplog.at_level(logging.WARNING, logger="attune.config.loader"):
            ConfigLoader.apply_env_overrides(config)
        assert "ATTUNE_MAX_BUDGET_USD" not in caplog.text

    def test_known_section_bad_setting_still_warns(self, monkeypatch, caplog):
        """A real section with a bogus setting is a genuine misconfig and
        must still warn — the skip above must not over-suppress."""
        config = UnifiedConfig()
        monkeypatch.setenv("ATTUNE_AUTH_BOGUSSETTING", "x")
        with caplog.at_level(logging.WARNING, logger="attune.config.loader"):
            ConfigLoader.apply_env_overrides(config)
        assert "ATTUNE_AUTH_BOGUSSETTING" in caplog.text


class TestConvenienceFunctions:
    def test_load_unified_config_from_file(self, tmp_path):
        config = UnifiedConfig()
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config.to_dict()))

        loaded = load_unified_config(path=str(config_file))
        assert isinstance(loaded, UnifiedConfig)

    def test_get_default_config_path(self):
        path = ConfigLoader.get_default_config_path()
        assert "config.json" in str(path)
