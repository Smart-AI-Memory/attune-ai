"""Coverage supplement for src/attune/workflows/config.py

Targets uncovered lines from initial run (77.78%):
- _validate_file_path() edge cases (null bytes, empty, allowed_dir)
- WorkflowConfig._load_file() with provider/model_preferences/workflows keys
- WorkflowConfig._apply_env_overrides() with ATTUNE_* env vars set
- WorkflowConfig.save() YAML path
- create_example_config()
- get_model() fallback paths
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.workflows.config import (
    WorkflowConfig,
    _validate_file_path,
    create_example_config,
    get_model,
)

# ---------------------------------------------------------------------------
# _validate_file_path() edge cases
# ---------------------------------------------------------------------------


class TestValidateFilePath:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_file_path("")

    def test_none_raises(self):
        with pytest.raises(ValueError):
            _validate_file_path(None)  # type: ignore[arg-type]

    def test_null_bytes_raises(self):
        with pytest.raises(ValueError, match="null bytes"):
            _validate_file_path("file\x00.json")

    def test_system_directory_etc_raises(self):
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/etc/attune.json")

    @pytest.mark.skipif(sys.platform == "win32", reason="/usr/bin is Unix-only")
    def test_system_directory_usr_bin_raises(self):
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/usr/bin/attune")

    def test_valid_path_returns_path_object(self, tmp_path):
        result = _validate_file_path(str(tmp_path / "ok.json"))
        assert isinstance(result, Path)

    def test_allowed_dir_enforced(self, tmp_path):
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside" / "bad.json"
        with pytest.raises(ValueError, match="within"):
            _validate_file_path(str(outside), allowed_dir=str(allowed))

    def test_allowed_dir_permits_child_path(self, tmp_path):
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        child = allowed / "config.json"
        result = _validate_file_path(str(child), allowed_dir=str(allowed))
        assert "config.json" in str(result)


# ---------------------------------------------------------------------------
# WorkflowConfig._load_file() — JSON format variants
# ---------------------------------------------------------------------------


class TestLoadFileVariants:
    def test_root_provider_key_maps_to_default_provider(self, tmp_path):
        cfg_file = tmp_path / "attune.config.json"
        cfg_file.write_text(json.dumps({"provider": "openai"}))
        result = WorkflowConfig._load_file(cfg_file)
        assert result.get("default_provider") == "openai"

    def test_model_preferences_maps_to_custom_models(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(
            json.dumps(
                {
                    "provider": "anthropic",
                    "model_preferences": {"cheap": "my-haiku", "capable": "my-sonnet"},
                }
            )
        )
        result = WorkflowConfig._load_file(cfg_file)
        assert "custom_models" in result
        assert result["custom_models"]["anthropic"]["cheap"] == "my-haiku"

    def test_nested_workflows_key_merged(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(
            json.dumps(
                {
                    "workflows": {
                        "default_provider": "openai",
                        "compliance_mode": "hipaa",
                    }
                }
            )
        )
        result = WorkflowConfig._load_file(cfg_file)
        assert result.get("default_provider") == "openai"
        assert result.get("compliance_mode") == "hipaa"

    def test_legacy_flat_format_used_directly(self, tmp_path):
        """File with no 'workflows' or 'provider' key → treat as legacy format."""
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(
            json.dumps(
                {
                    "default_provider": "ollama",
                    "audit_level": "enhanced",
                }
            )
        )
        result = WorkflowConfig._load_file(cfg_file)
        assert result.get("default_provider") == "ollama"
        assert result.get("audit_level") == "enhanced"

    def test_yaml_file_loaded_when_yaml_available(self, tmp_path):
        pytest.importorskip("yaml")
        import yaml

        cfg_file = tmp_path / "cfg.yaml"
        cfg_file.write_text(yaml.dump({"default_provider": "openai"}))
        result = WorkflowConfig._load_file(cfg_file)
        assert result.get("default_provider") == "openai"

    def test_yaml_file_raises_import_error_when_yaml_unavailable(self, tmp_path):
        cfg_file = tmp_path / "cfg.yaml"
        cfg_file.write_text("default_provider: anthropic\n")
        with patch("attune.workflows.config.YAML_AVAILABLE", False):
            with pytest.raises(ImportError, match="PyYAML"):
                WorkflowConfig._load_file(cfg_file)


# ---------------------------------------------------------------------------
# WorkflowConfig._apply_env_overrides() — env var paths
# ---------------------------------------------------------------------------


class TestApplyEnvOverrides:
    def test_attune_workflow_provider_overrides_default(self):
        with patch(
            "attune.config.env_compat.get_attune_env",
            side_effect=lambda key: "openai" if key == "WORKFLOW_PROVIDER" else None,
        ):
            result = WorkflowConfig._apply_env_overrides({})
        assert result["default_provider"] == "openai"

    def test_attune_model_cheap_sets_env_custom_model(self):
        def _env(key: str):
            if key == "MODEL_CHEAP":
                return "my-cheap-model"
            return None

        with (
            patch("attune.config.env_compat.get_attune_env", side_effect=_env),
            patch("attune.config.env_compat.iter_attune_env_prefix", return_value=[]),
        ):
            result = WorkflowConfig._apply_env_overrides({})
        assert result["custom_models"]["env"]["cheap"] == "my-cheap-model"

    def test_null_nested_dicts_initialized(self):
        config = {"workflow_providers": None, "custom_models": None, "pricing_overrides": None}
        with (
            patch("attune.config.env_compat.get_attune_env", return_value=None),
            patch("attune.config.env_compat.iter_attune_env_prefix", return_value=[]),
        ):
            result = WorkflowConfig._apply_env_overrides(config)
        assert result["workflow_providers"] == {}
        assert result["custom_models"] == {}
        assert result["pricing_overrides"] == {}

    def test_per_workflow_provider_set_via_env(self):
        def _iter(prefix, suffix):
            if prefix == "WORKFLOW_" and suffix == "_PROVIDER":
                yield "RESEARCH", "anthropic"

        with (
            patch("attune.config.env_compat.get_attune_env", return_value=None),
            patch("attune.config.env_compat.iter_attune_env_prefix", side_effect=_iter),
        ):
            result = WorkflowConfig._apply_env_overrides({})
        assert result["workflow_providers"]["research"] == "anthropic"


# ---------------------------------------------------------------------------
# WorkflowConfig.save() — YAML path
# ---------------------------------------------------------------------------


class TestConfigSaveYaml:
    def test_save_yaml_creates_file(self, tmp_path):
        pytest.importorskip("yaml")
        cfg = WorkflowConfig()
        out = tmp_path / "cfg.yaml"
        cfg.save(str(out))
        assert out.exists()

    def test_save_yaml_round_trip(self, tmp_path):
        pytest.importorskip("yaml")
        cfg = WorkflowConfig(default_provider="ollama", compliance_mode="hipaa")
        out = tmp_path / "cfg.yaml"
        cfg.save(str(out))
        loaded = WorkflowConfig.load(config_path=str(out))
        assert loaded.default_provider == "ollama"
        assert loaded.compliance_mode == "hipaa"

    def test_save_yaml_raises_when_yaml_unavailable(self, tmp_path):
        cfg = WorkflowConfig()
        out = tmp_path / "cfg.yaml"
        with patch("attune.workflows.config.YAML_AVAILABLE", False):
            with pytest.raises(ImportError, match="PyYAML"):
                cfg.save(str(out))


# ---------------------------------------------------------------------------
# WorkflowConfig.load() — missing config file after explicit path
# ---------------------------------------------------------------------------


class TestLoadMissingFile:
    def test_explicit_nonexistent_path_still_returns_config(self, tmp_path):
        missing = tmp_path / "missing.json"
        cfg = WorkflowConfig.load(config_path=str(missing))
        assert isinstance(cfg, WorkflowConfig)
        assert cfg.default_provider == "anthropic"


# ---------------------------------------------------------------------------
# create_example_config()
# ---------------------------------------------------------------------------


class TestCreateExampleConfig:
    def test_returns_string(self):
        result = create_example_config()
        assert isinstance(result, str)

    def test_contains_provider_section(self):
        result = create_example_config()
        assert "default_provider" in result

    def test_contains_custom_models(self):
        result = create_example_config()
        assert "custom_models" in result

    def test_non_empty(self):
        result = create_example_config()
        assert len(result) > 100


# ---------------------------------------------------------------------------
# get_model() — fallback paths
# ---------------------------------------------------------------------------


class TestGetModelFallbacks:
    def test_unknown_provider_and_tier_falls_back_to_anthropic_capable(self):
        result = get_model("nonexistent-provider", "nonexistent-tier")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_config_returns_default(self):
        result = get_model("anthropic", "capable", config=None)
        assert isinstance(result, str)

    def test_config_with_env_override_takes_priority(self):
        cfg = WorkflowConfig(custom_models={"env": {"capable": "env-capable-model"}})
        result = get_model("anthropic", "capable", config=cfg)
        assert result == "env-capable-model"
