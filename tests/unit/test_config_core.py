"""Comprehensive unit tests for src/attune/config.py.

Tests _validate_file_path, EmpathyConfig (defaults, serialization, env loading,
validation, merge, update), and load_config.

Copyright 2026 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import json
import os
from pathlib import Path

import pytest

from attune.config import EmpathyConfig, _validate_file_path, load_config

# ---------------------------------------------------------------------------
# _validate_file_path
# ---------------------------------------------------------------------------


class TestValidateFilePath:
    """Tests for _validate_file_path security function."""

    def test_valid_path_in_tmp(self, tmp_path: Path) -> None:
        """Valid path inside tmp_path resolves correctly."""
        target = tmp_path / "output.json"
        result = _validate_file_path(str(target))
        assert result == target.resolve()

    def test_valid_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Relative path resolves against cwd."""
        monkeypatch.chdir(tmp_path)
        result = _validate_file_path("data.json")
        assert result == (tmp_path / "data.json").resolve()

    def test_rejects_empty_string(self) -> None:
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            _validate_file_path("")

    def test_rejects_none(self) -> None:
        """None raises ValueError."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            _validate_file_path(None)  # type: ignore[arg-type]

    def test_rejects_null_bytes(self) -> None:
        """Path containing null bytes raises ValueError."""
        with pytest.raises(ValueError, match="contains null bytes"):
            _validate_file_path("file\x00.txt")

    @pytest.mark.parametrize(
        "dangerous",
        [
            "/etc/passwd",
            "/sys/kernel/config",
            "/proc/self/environ",
            "/dev/random",
            "/usr/bin/python",
            "/usr/sbin/nologin",
            "/bin/sh",
            pytest.param(
                "/sbin/init",
                marks=pytest.mark.skipif(
                    not Path("/sbin/init").exists()
                    or not str(Path("/sbin/init").resolve()).startswith(("/sbin", "/usr/sbin")),
                    reason="/sbin/init resolves outside /sbin on this OS (e.g. to systemd)",
                ),
            ),
        ],
    )
    def test_rejects_system_directories(self, dangerous: str) -> None:
        """System directory paths are blocked."""
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path(dangerous)

    def test_allowed_dir_accepts_child(self, tmp_path: Path) -> None:
        """Path within allowed_dir is accepted."""
        child = tmp_path / "sub" / "file.txt"
        result = _validate_file_path(str(child), allowed_dir=str(tmp_path))
        assert result == child.resolve()

    def test_allowed_dir_rejects_outside(self, tmp_path: Path) -> None:
        """Path outside allowed_dir is rejected."""
        outside = tmp_path.parent / "other.txt"
        with pytest.raises(ValueError, match="must be within"):
            _validate_file_path(str(outside), allowed_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# EmpathyConfig — defaults and basic construction
# ---------------------------------------------------------------------------


class TestEmpathyConfigDefaults:
    """Tests for default values and construction."""

    def test_default_values(self) -> None:
        """Defaults match expected values."""
        cfg = EmpathyConfig()
        assert cfg.user_id == "default_user"
        assert cfg.target_level == 3
        assert cfg.confidence_threshold == 0.75
        assert cfg.trust_building_rate == 0.05
        assert cfg.trust_erosion_rate == 0.10
        assert cfg.persistence_enabled is True
        assert cfg.persistence_backend == "sqlite"
        assert cfg.persistence_path == "./empathy_data"
        assert cfg.state_persistence is True
        assert cfg.metrics_enabled is True
        assert cfg.log_level == "INFO"
        assert cfg.log_file is None
        assert cfg.structured_logging is True
        assert cfg.pattern_library_enabled is True
        assert cfg.pattern_sharing is True
        assert cfg.pattern_confidence_threshold == 0.3
        assert cfg.async_enabled is True
        assert cfg.feedback_loop_monitoring is True
        assert cfg.leverage_point_analysis is True
        assert cfg.metadata == {}
        assert cfg.models == []
        assert cfg.default_model is None
        assert cfg.log_path is None
        assert cfg.max_threads == 4
        assert cfg.model_router is None

    def test_custom_values(self) -> None:
        """Custom values override defaults."""
        cfg = EmpathyConfig(user_id="alice", target_level=5, confidence_threshold=0.9)
        assert cfg.user_id == "alice"
        assert cfg.target_level == 5
        assert cfg.confidence_threshold == 0.9

    def test_post_init_invalid_default_model(self) -> None:
        """__post_init__ raises when default_model is not in models list."""
        with pytest.raises(ValueError, match="not in models"):
            EmpathyConfig(default_model="nonexistent")

    def test_post_init_valid_default_model(self) -> None:
        """__post_init__ passes when default_model matches a model."""
        from attune.workflows.config import ModelConfig

        model = ModelConfig(name="gpt-4", provider="openai", tier="premium")
        cfg = EmpathyConfig(models=[model], default_model="gpt-4")
        assert cfg.default_model == "gpt-4"

    def test_repr(self) -> None:
        """__repr__ contains key fields."""
        cfg = EmpathyConfig(user_id="bob", target_level=2, confidence_threshold=0.5)
        r = repr(cfg)
        assert "bob" in r
        assert "target_level=2" in r
        assert "0.5" in r
        assert r.startswith("EmpathyConfig(")


# ---------------------------------------------------------------------------
# to_dict / update / merge
# ---------------------------------------------------------------------------


class TestEmpathyConfigDictOps:
    """Tests for to_dict, update, and merge."""

    def test_to_dict_returns_all_fields(self) -> None:
        """to_dict returns a plain dict with all dataclass fields."""
        cfg = EmpathyConfig(user_id="zara")
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert d["user_id"] == "zara"
        assert "target_level" in d
        assert "metadata" in d

    def test_update_known_fields(self) -> None:
        """update modifies known fields in place."""
        cfg = EmpathyConfig()
        cfg.update(user_id="new_user", target_level=5)
        assert cfg.user_id == "new_user"
        assert cfg.target_level == 5

    def test_update_ignores_unknown_fields(self) -> None:
        """update silently ignores unknown attribute names."""
        cfg = EmpathyConfig()
        cfg.update(nonexistent_field="value")
        assert not hasattr(cfg, "nonexistent_field")

    def test_merge_other_overrides_non_defaults(self) -> None:
        """merge takes non-default values from other."""
        base = EmpathyConfig(user_id="base_user")
        other = EmpathyConfig(target_level=5)
        merged = base.merge(other)

        assert merged.user_id == "base_user"
        assert merged.target_level == 5

    def test_merge_returns_new_instance(self) -> None:
        """merge returns a new EmpathyConfig, not mutating originals."""
        base = EmpathyConfig(user_id="a")
        other = EmpathyConfig(user_id="b")
        merged = base.merge(other)

        assert merged is not base
        assert merged is not other
        assert merged.user_id == "b"
        assert base.user_id == "a"

    def test_merge_default_other_preserves_base(self) -> None:
        """Merging a default-valued other keeps base values."""
        base = EmpathyConfig(user_id="keep_me", target_level=4)
        other = EmpathyConfig()  # all defaults
        merged = base.merge(other)

        assert merged.user_id == "keep_me"
        assert merged.target_level == 4


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestEmpathyConfigValidate:
    """Tests for the validate method."""

    def test_valid_defaults_pass(self) -> None:
        """Default config passes validation."""
        assert EmpathyConfig().validate() is True

    def test_invalid_target_level_too_low(self) -> None:
        """target_level below 1 fails."""
        cfg = EmpathyConfig()
        cfg.target_level = 0
        with pytest.raises(ValueError, match="target_level must be 1-5"):
            cfg.validate()

    def test_invalid_target_level_too_high(self) -> None:
        """target_level above 5 fails."""
        cfg = EmpathyConfig()
        cfg.target_level = 6
        with pytest.raises(ValueError, match="target_level must be 1-5"):
            cfg.validate()

    def test_invalid_confidence_threshold(self) -> None:
        """confidence_threshold outside 0-1 fails."""
        cfg = EmpathyConfig()
        cfg.confidence_threshold = 1.5
        with pytest.raises(ValueError, match="confidence_threshold must be 0.0-1.0"):
            cfg.validate()

    def test_invalid_pattern_confidence_threshold(self) -> None:
        """pattern_confidence_threshold outside 0-1 fails."""
        cfg = EmpathyConfig()
        cfg.pattern_confidence_threshold = -0.1
        with pytest.raises(ValueError, match="pattern_confidence_threshold must be 0.0-1.0"):
            cfg.validate()

    def test_invalid_persistence_backend(self) -> None:
        """Unsupported persistence_backend fails."""
        cfg = EmpathyConfig()
        cfg.persistence_backend = "mysql"
        with pytest.raises(ValueError, match="persistence_backend"):
            cfg.validate()

    @pytest.mark.parametrize("backend", ["sqlite", "json", "none"])
    def test_valid_persistence_backends(self, backend: str) -> None:
        """All supported backends pass validation."""
        cfg = EmpathyConfig(persistence_backend=backend)
        assert cfg.validate() is True


# ---------------------------------------------------------------------------
# from_json / to_json roundtrip
# ---------------------------------------------------------------------------


class TestJsonRoundtrip:
    """Tests for JSON serialization and deserialization."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        """to_json then from_json produces equivalent config."""
        original = EmpathyConfig(user_id="roundtrip", target_level=4, confidence_threshold=0.85)
        filepath = str(tmp_path / "cfg.json")

        original.to_json(filepath)
        loaded = EmpathyConfig.from_json(filepath)

        assert loaded.user_id == "roundtrip"
        assert loaded.target_level == 4
        assert loaded.confidence_threshold == 0.85

    def test_from_json_ignores_unknown_fields(self, tmp_path: Path) -> None:
        """Unknown fields in JSON are silently ignored."""
        filepath = tmp_path / "extra.json"
        data = {"user_id": "extra", "unknown_field": "should_ignore", "workflow_stuff": [1, 2]}
        filepath.write_text(json.dumps(data))

        cfg = EmpathyConfig.from_json(str(filepath))
        assert cfg.user_id == "extra"
        assert not hasattr(cfg, "unknown_field")

    def test_to_json_custom_indent(self, tmp_path: Path) -> None:
        """to_json respects the indent parameter."""
        cfg = EmpathyConfig()
        filepath = str(tmp_path / "indented.json")
        cfg.to_json(filepath, indent=4)

        content = Path(filepath).read_text()
        # 4-space indent means lines should be indented with 4 spaces
        assert "    " in content

    def test_to_json_validates_path(self) -> None:
        """to_json rejects unsafe paths."""
        cfg = EmpathyConfig()
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            cfg.to_json("/sys/test.json")


# ---------------------------------------------------------------------------
# from_yaml / to_yaml roundtrip
# ---------------------------------------------------------------------------


class TestYamlRoundtrip:
    """Tests for YAML serialization and deserialization (requires PyYAML)."""

    @pytest.fixture(autouse=True)
    def _require_yaml(self) -> None:
        pytest.importorskip("yaml")

    def test_roundtrip(self, tmp_path: Path) -> None:
        """to_yaml then from_yaml produces equivalent config."""
        original = EmpathyConfig(user_id="yaml_user", target_level=2)
        filepath = str(tmp_path / "cfg.yml")

        original.to_yaml(filepath)
        loaded = EmpathyConfig.from_yaml(filepath)

        assert loaded.user_id == "yaml_user"
        assert loaded.target_level == 2

    def test_from_yaml_ignores_unknown_fields(self, tmp_path: Path) -> None:
        """Unknown fields in YAML are silently ignored."""
        import yaml

        filepath = tmp_path / "extra.yml"
        data = {"user_id": "yaml_extra", "provider": "openai", "workflows": ["a", "b"]}
        filepath.write_text(yaml.dump(data))

        cfg = EmpathyConfig.from_yaml(str(filepath))
        assert cfg.user_id == "yaml_extra"
        assert not hasattr(cfg, "provider")

    def test_to_yaml_validates_path(self) -> None:
        """to_yaml rejects unsafe paths."""
        cfg = EmpathyConfig()
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            cfg.to_yaml("/etc/test.yml")

    def test_to_yaml_creates_file(self, tmp_path: Path) -> None:
        """to_yaml creates a file on disk."""
        cfg = EmpathyConfig(user_id="file_check")
        filepath = tmp_path / "created.yml"
        cfg.to_yaml(str(filepath))
        assert filepath.exists()
        assert filepath.stat().st_size > 0


# ---------------------------------------------------------------------------
# from_env
# ---------------------------------------------------------------------------


class TestFromEnv:
    """Tests for loading config from environment variables."""

    def test_string_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """String env vars are loaded directly."""
        monkeypatch.setenv("EMPATHY_USER_ID", "env_alice")
        cfg = EmpathyConfig.from_env()
        assert cfg.user_id == "env_alice"

    def test_int_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Integer env vars are converted."""
        monkeypatch.setenv("EMPATHY_TARGET_LEVEL", "4")
        cfg = EmpathyConfig.from_env()
        assert cfg.target_level == 4

    def test_float_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Float env vars are converted."""
        monkeypatch.setenv("EMPATHY_CONFIDENCE_THRESHOLD", "0.95")
        cfg = EmpathyConfig.from_env()
        assert cfg.confidence_threshold == 0.95

    def test_bool_field_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Boolean env vars accept 'true', '1', 'yes'."""
        monkeypatch.setenv("EMPATHY_PERSISTENCE_ENABLED", "true")
        cfg = EmpathyConfig.from_env()
        assert cfg.persistence_enabled is True

    def test_bool_field_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Boolean env var 'yes' is truthy."""
        monkeypatch.setenv("EMPATHY_ASYNC_ENABLED", "yes")
        cfg = EmpathyConfig.from_env()
        assert cfg.async_enabled is True

    def test_bool_field_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Boolean env var 'false' is falsy."""
        monkeypatch.setenv("EMPATHY_METRICS_ENABLED", "false")
        cfg = EmpathyConfig.from_env()
        assert cfg.metrics_enabled is False

    def test_bool_field_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Boolean env var '0' is falsy."""
        monkeypatch.setenv("EMPATHY_STRUCTURED_LOGGING", "0")
        cfg = EmpathyConfig.from_env()
        assert cfg.structured_logging is False

    def test_unknown_env_vars_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unknown EMPATHY_ env vars are ignored."""
        monkeypatch.setenv("EMPATHY_MASTER_KEY", "secret123")
        cfg = EmpathyConfig.from_env()
        assert not hasattr(cfg, "master_key")

    def test_custom_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Custom prefix filters env vars correctly."""
        monkeypatch.setenv("MYAPP_USER_ID", "custom_user")
        cfg = EmpathyConfig.from_env(prefix="MYAPP_")
        assert cfg.user_id == "custom_user"

    def test_multiple_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Multiple env vars are combined."""
        monkeypatch.setenv("EMPATHY_USER_ID", "multi")
        monkeypatch.setenv("EMPATHY_TARGET_LEVEL", "5")
        monkeypatch.setenv("EMPATHY_CONFIDENCE_THRESHOLD", "0.6")
        cfg = EmpathyConfig.from_env()
        assert cfg.user_id == "multi"
        assert cfg.target_level == 5
        assert cfg.confidence_threshold == 0.6


# ---------------------------------------------------------------------------
# from_file — auto-detection
# ---------------------------------------------------------------------------


class TestFromFile:
    """Tests for auto-detecting config files."""

    def test_explicit_json_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_file loads an explicit JSON path."""
        monkeypatch.chdir(tmp_path)
        filepath = tmp_path / "my.json"
        filepath.write_text(json.dumps({"user_id": "explicit"}))

        cfg = EmpathyConfig.from_file(str(filepath))
        assert cfg.user_id == "explicit"

    def test_explicit_yaml_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_file loads an explicit YAML path."""
        yaml = pytest.importorskip("yaml")
        monkeypatch.chdir(tmp_path)
        filepath = tmp_path / "my.yml"
        filepath.write_text(yaml.dump({"user_id": "yaml_explicit"}))

        cfg = EmpathyConfig.from_file(str(filepath))
        assert cfg.user_id == "yaml_explicit"

    def test_auto_detects_empathy_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """from_file auto-detects .empathy.json in cwd."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".empathy.json").write_text(json.dumps({"user_id": "auto_json"}))

        cfg = EmpathyConfig.from_file()
        assert cfg.user_id == "auto_json"

    def test_auto_detects_empathy_yml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """from_file auto-detects .empathy.yml in cwd."""
        yaml = pytest.importorskip("yaml")
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".empathy.yml").write_text(yaml.dump({"user_id": "auto_yaml"}))

        cfg = EmpathyConfig.from_file()
        assert cfg.user_id == "auto_yaml"

    def test_returns_default_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """from_file returns default config when no config file exists."""
        monkeypatch.chdir(tmp_path)
        cfg = EmpathyConfig.from_file()
        assert cfg.user_id == "default_user"


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------


class TestFromDict:
    """Tests for from_dict factory method."""

    def test_basic_dict(self) -> None:
        """from_dict creates config from plain dict."""
        cfg = EmpathyConfig.from_dict({"user_id": "dict_user", "target_level": 4})
        assert cfg.user_id == "dict_user"
        assert cfg.target_level == 4

    def test_unknown_fields_ignored(self) -> None:
        """Unknown fields in the dict are silently ignored."""
        cfg = EmpathyConfig.from_dict(
            {"user_id": "known", "totally_unknown": True, "another_garbage": [1, 2, 3]}
        )
        assert cfg.user_id == "known"
        assert not hasattr(cfg, "totally_unknown")

    def test_nested_model_config(self) -> None:
        """Nested model dicts are converted to ModelConfig objects."""
        data = {
            "user_id": "model_user",
            "models": [
                {"name": "gpt-4", "provider": "openai", "tier": "premium"},
                {"name": "claude-3", "provider": "anthropic", "tier": "capable"},
            ],
            "default_model": "gpt-4",
        }
        cfg = EmpathyConfig.from_dict(data)
        assert len(cfg.models) == 2
        assert cfg.models[0].name == "gpt-4"
        assert cfg.models[1].provider == "anthropic"
        assert cfg.default_model == "gpt-4"

    def test_empty_dict_returns_defaults(self) -> None:
        """Empty dict returns default config."""
        cfg = EmpathyConfig.from_dict({})
        assert cfg.user_id == "default_user"
        assert cfg.target_level == 3


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    """Tests for the load_config convenience function."""

    def test_defaults_applied(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Custom defaults are applied."""
        monkeypatch.chdir(tmp_path)
        # Clear any EMPATHY_ env vars that could interfere
        for key in list(os.environ):
            if key.startswith("EMPATHY_"):
                monkeypatch.delenv(key, raising=False)

        cfg = load_config(defaults={"user_id": "default_override", "target_level": 4})
        assert cfg.user_id == "default_override"
        assert cfg.target_level == 4

    def test_env_overrides_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env vars take precedence over defaults."""
        monkeypatch.chdir(tmp_path)
        # Clear other EMPATHY_ env vars
        for key in list(os.environ):
            if key.startswith("EMPATHY_"):
                monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("EMPATHY_USER_ID", "env_wins")
        cfg = load_config(defaults={"user_id": "should_lose"})
        assert cfg.user_id == "env_wins"

    def test_file_overrides_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Config file values override custom defaults."""
        monkeypatch.chdir(tmp_path)
        # Clear EMPATHY_ env vars
        for key in list(os.environ):
            if key.startswith("EMPATHY_"):
                monkeypatch.delenv(key, raising=False)

        config_file = tmp_path / "test_cfg.json"
        config_file.write_text(json.dumps({"user_id": "file_wins"}))

        cfg = load_config(
            filepath=str(config_file),
            use_env=False,
            defaults={"user_id": "should_lose"},
        )
        assert cfg.user_id == "file_wins"

    def test_no_env_flag(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """use_env=False skips environment variable loading."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("EMPATHY_USER_ID", "env_val")
        # Clear any config files
        cfg = load_config(use_env=False)
        # Without env loading, should keep the default
        assert cfg.user_id == "default_user"

    def test_validates_result(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """load_config validates the final configuration."""
        monkeypatch.chdir(tmp_path)
        for key in list(os.environ):
            if key.startswith("EMPATHY_"):
                monkeypatch.delenv(key, raising=False)

        # target_level=0 is invalid (must be 1-5)
        with pytest.raises(ValueError, match="target_level must be 1-5"):
            load_config(defaults={"target_level": 0})

    def test_returns_defaults_with_no_file_no_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns default config when no file or env vars exist."""
        monkeypatch.chdir(tmp_path)
        for key in list(os.environ):
            if key.startswith("EMPATHY_"):
                monkeypatch.delenv(key, raising=False)

        cfg = load_config(use_env=False)
        assert cfg.user_id == "default_user"
        assert cfg.target_level == 3
