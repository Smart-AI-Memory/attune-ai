"""Tests for attune/config/legacy.py (AttuneConfig, load_config).

This module was at 0% coverage. Tests cover all factory methods,
serialization, validation, merge logic, and the load_config helper.
"""

from __future__ import annotations

import json
import os

import pytest
import yaml

from attune.config import AttuneConfig, EmpathyConfig, load_config

# ---------------------------------------------------------------------------
# Defaults and construction
# ---------------------------------------------------------------------------


class TestAttuneConfigDefaults:
    def test_default_construction(self):
        cfg = AttuneConfig()
        assert cfg.user_id == "default_user"
        assert cfg.target_level == 3
        assert cfg.confidence_threshold == 0.75
        assert cfg.persistence_enabled is True

    def test_custom_construction(self):
        cfg = AttuneConfig(user_id="alice", target_level=5)
        assert cfg.user_id == "alice"
        assert cfg.target_level == 5

    def test_post_init_invalid_default_model_raises(self):
        from attune.workflows.config import ModelConfig

        model = ModelConfig(name="gpt4", provider="openai", tier="capable")
        with pytest.raises(ValueError, match="not in models"):
            AttuneConfig(models=[model], default_model="nonexistent")

    def test_post_init_valid_default_model(self):
        from attune.workflows.config import ModelConfig

        model = ModelConfig(name="claude", provider="anthropic", tier="capable")
        cfg = AttuneConfig(models=[model], default_model="claude")
        assert cfg.default_model == "claude"

    def test_empathy_config_alias(self):
        assert EmpathyConfig is AttuneConfig


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------


class TestFromDict:
    def test_basic(self):
        cfg = AttuneConfig.from_dict({"user_id": "bob", "target_level": 4})
        assert cfg.user_id == "bob"
        assert cfg.target_level == 4

    def test_unknown_fields_ignored(self):
        cfg = AttuneConfig.from_dict({"user_id": "x", "unknown_field": "value"})
        assert cfg.user_id == "x"
        assert not hasattr(cfg, "unknown_field")

    def test_with_models_list(self):
        cfg = AttuneConfig.from_dict(
            {"models": [{"name": "m1", "provider": "anthropic", "tier": "capable"}]}
        )
        assert len(cfg.models) == 1
        assert cfg.models[0].name == "m1"


# ---------------------------------------------------------------------------
# from_yaml
# ---------------------------------------------------------------------------


class TestFromYaml:
    def test_loads_valid_yaml(self, tmp_path):
        f = tmp_path / "cfg.yml"
        f.write_text(yaml.safe_dump({"user_id": "yaml_user", "target_level": 2}))
        cfg = AttuneConfig.from_yaml(str(f))
        assert cfg.user_id == "yaml_user"
        assert cfg.target_level == 2

    def test_ignores_unknown_yaml_keys(self, tmp_path):
        f = tmp_path / "cfg.yml"
        f.write_text(yaml.safe_dump({"user_id": "u", "provider": "anthropic", "workflows": {}}))
        cfg = AttuneConfig.from_yaml(str(f))
        assert cfg.user_id == "u"


# ---------------------------------------------------------------------------
# from_json
# ---------------------------------------------------------------------------


class TestFromJson:
    def test_loads_valid_json(self, tmp_path):
        f = tmp_path / "cfg.json"
        f.write_text(json.dumps({"user_id": "json_user", "log_level": "DEBUG"}))
        cfg = AttuneConfig.from_json(str(f))
        assert cfg.user_id == "json_user"
        assert cfg.log_level == "DEBUG"

    def test_ignores_unknown_json_keys(self, tmp_path):
        f = tmp_path / "cfg.json"
        f.write_text(json.dumps({"user_id": "j", "extra_field": 99}))
        cfg = AttuneConfig.from_json(str(f))
        assert cfg.user_id == "j"


# ---------------------------------------------------------------------------
# from_env
# ---------------------------------------------------------------------------


class TestFromEnv:
    def test_reads_attune_prefix(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_USER_ID", "env_user")
        monkeypatch.setenv("ATTUNE_TARGET_LEVEL", "5")
        cfg = AttuneConfig.from_env()
        assert cfg.user_id == "env_user"
        assert cfg.target_level == 5

    def test_reads_empathy_prefix_fallback(self, monkeypatch):
        monkeypatch.delenv("ATTUNE_USER_ID", raising=False)
        monkeypatch.setenv("EMPATHY_USER_ID", "empathy_user")
        cfg = AttuneConfig.from_env()
        assert cfg.user_id == "empathy_user"

    def test_bool_conversion(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_PERSISTENCE_ENABLED", "false")
        cfg = AttuneConfig.from_env()
        assert cfg.persistence_enabled is False

    def test_float_conversion(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_CONFIDENCE_THRESHOLD", "0.9")
        cfg = AttuneConfig.from_env()
        assert abs(cfg.confidence_threshold - 0.9) < 1e-9

    def test_unknown_env_vars_ignored(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_NONEXISTENT_FIELD", "value")
        cfg = AttuneConfig.from_env()  # should not raise
        assert not hasattr(cfg, "nonexistent_field")

    def test_attune_wins_over_empathy(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_USER_ID", "attune_wins")
        monkeypatch.setenv("EMPATHY_USER_ID", "empathy_loses")
        cfg = AttuneConfig.from_env()
        assert cfg.user_id == "attune_wins"


# ---------------------------------------------------------------------------
# from_file (auto-detect)
# ---------------------------------------------------------------------------


class TestFromFile:
    def test_returns_default_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = AttuneConfig.from_file()
        assert cfg.user_id == "default_user"

    def test_loads_explicit_yaml_path(self, tmp_path):
        f = tmp_path / "explicit.yml"
        f.write_text(yaml.safe_dump({"user_id": "explicit_yaml"}))
        cfg = AttuneConfig.from_file(str(f))
        assert cfg.user_id == "explicit_yaml"

    def test_loads_explicit_json_path(self, tmp_path):
        f = tmp_path / "explicit.json"
        f.write_text(json.dumps({"user_id": "explicit_json"}))
        cfg = AttuneConfig.from_file(str(f))
        assert cfg.user_id == "explicit_json"

    def test_auto_detects_attune_yml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".attune.yml").write_text(yaml.safe_dump({"user_id": "autodetect"}))
        cfg = AttuneConfig.from_file()
        assert cfg.user_id == "autodetect"


# ---------------------------------------------------------------------------
# to_yaml / to_json
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_json_writes_file(self, tmp_path):
        cfg = AttuneConfig(user_id="serial_test", target_level=4)
        out = tmp_path / "out.json"
        cfg.to_json(str(out))
        loaded = json.loads(out.read_text())
        assert loaded["user_id"] == "serial_test"
        assert loaded["target_level"] == 4

    def test_to_yaml_writes_file(self, tmp_path):
        cfg = AttuneConfig(user_id="yaml_test", log_level="DEBUG")
        out = tmp_path / "out.yml"
        cfg.to_yaml(str(out))
        loaded = yaml.safe_load(out.read_text())
        assert loaded["user_id"] == "yaml_test"
        assert loaded["log_level"] == "DEBUG"

    def test_to_json_blocks_system_path(self):
        cfg = AttuneConfig()
        with pytest.raises(ValueError):
            cfg.to_json("/etc/attune-test.json")

    def test_to_yaml_blocks_system_path(self):
        cfg = AttuneConfig()
        with pytest.raises(ValueError):
            cfg.to_yaml("/etc/attune-test.yml")

    def test_to_dict_returns_dict(self):
        cfg = AttuneConfig(user_id="dict_test")
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert d["user_id"] == "dict_test"

    def test_round_trip_json(self, tmp_path):
        original = AttuneConfig(user_id="rt", target_level=2, log_level="WARNING")
        out = tmp_path / "rt.json"
        original.to_json(str(out))
        restored = AttuneConfig.from_json(str(out))
        assert restored.user_id == original.user_id
        assert restored.target_level == original.target_level
        assert restored.log_level == original.log_level


# ---------------------------------------------------------------------------
# update / merge
# ---------------------------------------------------------------------------


class TestUpdateAndMerge:
    def test_update_known_fields(self):
        cfg = AttuneConfig()
        cfg.update(user_id="updated", target_level=1)
        assert cfg.user_id == "updated"
        assert cfg.target_level == 1

    def test_update_unknown_fields_ignored(self):
        cfg = AttuneConfig()
        cfg.update(nonexistent_field="x")  # should not raise

    def test_merge_other_takes_precedence(self):
        base = AttuneConfig(user_id="base", target_level=2)
        override = AttuneConfig(target_level=5)
        merged = base.merge(override)
        assert merged.user_id == "base"  # only base set this
        assert merged.target_level == 5  # override wins

    def test_merge_default_values_do_not_override(self):
        base = AttuneConfig(user_id="keep_me")
        other = AttuneConfig()  # user_id is default "default_user"
        merged = base.merge(other)
        assert merged.user_id == "keep_me"


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestValidate:
    def test_valid_config_returns_true(self):
        assert AttuneConfig().validate() is True

    def test_invalid_target_level_raises(self):
        cfg = AttuneConfig()
        cfg.target_level = 0
        with pytest.raises(ValueError, match="target_level"):
            cfg.validate()

    def test_invalid_confidence_threshold_raises(self):
        cfg = AttuneConfig()
        cfg.confidence_threshold = 1.5
        with pytest.raises(ValueError, match="confidence_threshold"):
            cfg.validate()

    def test_invalid_pattern_threshold_raises(self):
        cfg = AttuneConfig()
        cfg.pattern_confidence_threshold = -0.1
        with pytest.raises(ValueError, match="pattern_confidence_threshold"):
            cfg.validate()

    def test_invalid_persistence_backend_raises(self):
        cfg = AttuneConfig()
        cfg.persistence_backend = "redis"
        with pytest.raises(ValueError, match="persistence_backend"):
            cfg.validate()


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------


class TestRepr:
    def test_repr_contains_key_fields(self):
        cfg = AttuneConfig(user_id="repr_test", target_level=4)
        r = repr(cfg)
        assert "repr_test" in r
        assert "4" in r


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_returns_defaults_with_no_file_or_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Suppress env vars that would interfere
        for key in list(os.environ):
            if key.startswith(("ATTUNE_", "EMPATHY_")):
                monkeypatch.delenv(key, raising=False)
        cfg = load_config()
        assert isinstance(cfg, AttuneConfig)

    def test_applies_defaults_arg(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for key in list(os.environ):
            if key.startswith(("ATTUNE_", "EMPATHY_")):
                monkeypatch.delenv(key, raising=False)
        cfg = load_config(defaults={"target_level": 1})
        assert cfg.target_level == 1

    def test_loads_from_explicit_file(self, tmp_path, monkeypatch):
        for key in list(os.environ):
            if key.startswith(("ATTUNE_", "EMPATHY_")):
                monkeypatch.delenv(key, raising=False)
        f = tmp_path / "cfg.json"
        f.write_text(json.dumps({"user_id": "from_file"}))
        cfg = load_config(filepath=str(f), use_env=False)
        assert cfg.user_id == "from_file"

    def test_env_overrides_file(self, tmp_path, monkeypatch):
        for key in list(os.environ):
            if key.startswith(("ATTUNE_", "EMPATHY_")):
                monkeypatch.delenv(key, raising=False)
        f = tmp_path / "cfg.json"
        f.write_text(json.dumps({"user_id": "from_file", "target_level": 2}))
        monkeypatch.setenv("ATTUNE_TARGET_LEVEL", "5")
        cfg = load_config(filepath=str(f), use_env=True)
        assert cfg.target_level == 5

    def test_use_env_false_skips_env(self, tmp_path, monkeypatch):
        for key in list(os.environ):
            if key.startswith(("ATTUNE_", "EMPATHY_")):
                monkeypatch.delenv(key, raising=False)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ATTUNE_TARGET_LEVEL", "5")
        cfg = load_config(use_env=False)
        assert cfg.target_level == 3  # default, not env

    def test_invalid_file_falls_back_to_defaults(self, tmp_path, monkeypatch):
        for key in list(os.environ):
            if key.startswith(("ATTUNE_", "EMPATHY_")):
                monkeypatch.delenv(key, raising=False)
        f = tmp_path / "bad.json"
        f.write_text("{not valid json}")
        cfg = load_config(filepath=str(f), use_env=False)
        assert cfg.user_id == "default_user"
