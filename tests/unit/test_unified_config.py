"""Tests for attune.config.unified module."""

import pytest

from attune.config.unified import UnifiedConfig


class TestUnifiedConfigDefaults:
    def test_default_config_has_timestamps(self):
        config = UnifiedConfig()
        assert config._created != ""
        assert config._modified != ""
        assert config._version == "1.0.0"

    def test_default_sections_exist(self):
        config = UnifiedConfig()
        assert config.auth is not None
        assert config.routing is not None
        assert config.workflows is not None
        assert config.analysis is not None
        assert config.persistence is not None
        assert config.telemetry is not None
        assert config.environment is not None


class TestUnifiedConfigSerialization:
    def test_to_dict_contains_all_sections(self):
        config = UnifiedConfig()
        data = config.to_dict()
        assert "auth" in data
        assert "routing" in data
        assert "workflows" in data
        assert "analysis" in data
        assert "persistence" in data
        assert "telemetry" in data
        assert "environment" in data
        assert "_version" in data
        assert "_created" in data
        assert "_modified" in data

    def test_from_dict_empty(self):
        config = UnifiedConfig.from_dict({})
        assert config._version == "1.0.0"
        assert config.auth is not None

    def test_round_trip(self):
        original = UnifiedConfig()
        data = original.to_dict()
        restored = UnifiedConfig.from_dict(data)
        assert restored._version == original._version
        assert restored.to_dict() == data


class TestUnifiedConfigGetSetValue:
    def test_get_value_valid_key(self):
        config = UnifiedConfig()
        value = config.get_value("auth.strategy")
        assert value is not None

    def test_get_value_invalid_format(self):
        config = UnifiedConfig()
        with pytest.raises(KeyError, match="Invalid key format"):
            config.get_value("nosection")

    def test_get_value_unknown_section(self):
        config = UnifiedConfig()
        with pytest.raises(KeyError, match="Unknown section"):
            config.get_value("nonexistent.setting")

    def test_get_value_unknown_setting(self):
        config = UnifiedConfig()
        with pytest.raises(KeyError, match="Unknown setting"):
            config.get_value("auth.nonexistent_setting")

    def test_set_value_valid(self):
        config = UnifiedConfig()
        old_modified = config._modified
        import time

        time.sleep(0.02)  # Ensure timestamp changes (Windows timer resolution ~15.6ms)
        config.set_value("auth.strategy", "api")
        assert config.get_value("auth.strategy") == "api"
        assert config._modified != old_modified

    def test_set_value_invalid_format(self):
        config = UnifiedConfig()
        with pytest.raises(KeyError, match="Invalid key format"):
            config.set_value("nosection", "value")

    def test_set_value_unknown_section(self):
        config = UnifiedConfig()
        with pytest.raises(KeyError, match="Unknown section"):
            config.set_value("nonexistent.setting", "value")

    def test_set_value_unknown_setting(self):
        config = UnifiedConfig()
        with pytest.raises(KeyError, match="Unknown setting"):
            config.set_value("auth.nonexistent_setting", "value")


class TestUnifiedConfigTouch:
    def test_touch_updates_modified(self):
        config = UnifiedConfig()
        old_modified = config._modified
        import time

        time.sleep(0.01)
        config.touch()
        assert config._modified != old_modified


class TestUnifiedConfigGetAllKeys:
    def test_get_all_keys_returns_dot_notation(self):
        config = UnifiedConfig()
        keys = config.get_all_keys()
        assert len(keys) > 0
        assert all("." in k for k in keys)
        assert any(k.startswith("auth.") for k in keys)
        assert any(k.startswith("routing.") for k in keys)
        assert any(k.startswith("telemetry.") for k in keys)
