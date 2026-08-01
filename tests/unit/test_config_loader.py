"""Tests for attune.config.loader module."""

import json
import logging
from pathlib import Path

import pytest

from attune.config import loader as loader_module
from attune.config.loader import ConfigLoader, load_unified_config, save_unified_config
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


class TestConfigLoaderGetConfigPath:
    """Covers ConfigLoader.get_config_path() — never exercised previously."""

    def test_returns_none_when_nothing_set(self):
        loader = ConfigLoader()
        assert loader.get_config_path() is None

    def test_returns_explicit_path_before_load(self, tmp_path):
        config_file = tmp_path / "explicit.json"
        config_file.write_text(json.dumps(UnifiedConfig().to_dict()))

        loader = ConfigLoader(config_path=str(config_file))
        # Not loaded yet: falls back to the explicit path.
        assert loader.get_config_path() == config_file.expanduser()

    def test_returns_loaded_path_after_load(self, tmp_path):
        config_file = tmp_path / "loaded.json"
        config_file.write_text(json.dumps(UnifiedConfig().to_dict()))

        loader = ConfigLoader(config_path=str(config_file))
        loader.load()
        assert loader.get_config_path() == config_file.expanduser()


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

    def test_save_falls_back_to_loaded_path_when_no_path_given(self, tmp_path):
        """save(path=None) with a previously-loaded path uses that path
        (the `elif self._loaded_path:` branch) — explicit tmp_path file,
        never touches the real default config location."""
        config_file = tmp_path / "existing.json"
        config_file.write_text(json.dumps(UnifiedConfig().to_dict()))

        loader = ConfigLoader(config_path=str(config_file))
        loader.load()
        assert loader.get_config_path() == config_file.expanduser()

        result = loader.save(UnifiedConfig())
        assert result == config_file.expanduser()
        assert result.exists()

    def test_save_falls_back_to_default_path_when_nothing_loaded(self, tmp_path, monkeypatch):
        """save(path=None) with NO explicit/loaded path resolves via
        get_default_config_path() (the `else:` branch). CRITICAL: the
        default path is monkeypatched to a tmp_path location BEFORE
        save() runs, so the real ~/.attune/config.json is never touched
        even if the branch under test is exactly the default-path one."""
        fake_default = tmp_path / "fake_home" / ".attune" / "config.json"
        monkeypatch.setattr(
            ConfigLoader,
            "get_default_config_path",
            staticmethod(lambda: fake_default),
        )

        loader = ConfigLoader()
        assert loader.get_config_path() is None  # nothing loaded/explicit

        result = loader.save(UnifiedConfig())
        assert result == fake_default
        assert fake_default.exists()

    def test_save_permission_error_propagates(self, tmp_path, monkeypatch):
        """PermissionError from the write is logged and re-raised as-is."""
        save_path = tmp_path / "cfg.json"

        def raise_permission_error(self, *args, **kwargs):
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "write_text", raise_permission_error)

        loader = ConfigLoader()
        with pytest.raises(PermissionError, match="denied"):
            loader.save(UnifiedConfig(), path=save_path)

    def test_save_oserror_wrapped_as_value_error(self, tmp_path, monkeypatch):
        """A generic OSError from the write is wrapped as ValueError."""
        save_path = tmp_path / "cfg.json"

        def raise_os_error(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_text", raise_os_error)

        loader = ConfigLoader()
        with pytest.raises(ValueError, match="Cannot save config"):
            loader.save(UnifiedConfig(), path=save_path)


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

    def test_apply_env_override_int(self, monkeypatch):
        config = UnifiedConfig()
        monkeypatch.setenv("ATTUNE_ROUTING_MAX_RETRIES", "7")
        result = ConfigLoader.apply_env_overrides(config)
        assert result.get_value("routing.max_retries") == 7
        assert isinstance(result.get_value("routing.max_retries"), int)

    def test_apply_env_override_float(self, monkeypatch):
        config = UnifiedConfig()
        monkeypatch.setenv("ATTUNE_ROUTING_TEMPERATURE_DEFAULT", "0.25")
        result = ConfigLoader.apply_env_overrides(config)
        assert result.get_value("routing.temperature_default") == pytest.approx(0.25)
        assert isinstance(result.get_value("routing.temperature_default"), float)

    def test_apply_env_override_list(self, monkeypatch):
        config = UnifiedConfig()
        monkeypatch.setenv("ATTUNE_ANALYSIS_INCLUDE_PATTERNS", "*.py,*.pyi")
        result = ConfigLoader.apply_env_overrides(config)
        assert result.get_value("analysis.include_patterns") == ["*.py", "*.pyi"]

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


class TestGetLoaderSingleton:
    """Covers the module-level get_loader() global singleton (never
    directly exercised previously). The prior value of the module
    global is restored automatically by monkeypatch after the test —
    no cross-test pollution."""

    def test_get_loader_returns_singleton(self, monkeypatch):
        monkeypatch.setattr(loader_module, "_global_loader", None)

        first = loader_module.get_loader()
        assert isinstance(first, ConfigLoader)

        second = loader_module.get_loader()
        assert first is second

    def test_get_loader_reuses_existing_instance(self, monkeypatch):
        existing = ConfigLoader()
        monkeypatch.setattr(loader_module, "_global_loader", existing)

        result = loader_module.get_loader()
        assert result is existing


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

    def test_save_unified_config_convenience(self, tmp_path, monkeypatch):
        """save_unified_config() delegates to get_loader().save(). Reset
        the global singleton first so this test doesn't depend on
        whatever state prior tests left it in, and pass an explicit
        tmp_path so the real default config path is never touched."""
        monkeypatch.setattr(loader_module, "_global_loader", None)

        config = UnifiedConfig()
        save_path = tmp_path / "convenience.json"

        result = save_unified_config(config, path=save_path)
        assert result == save_path
        assert save_path.exists()
