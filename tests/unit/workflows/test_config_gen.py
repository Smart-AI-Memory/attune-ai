"""Unit tests for src/attune/workflows/config.py

Tests cover WorkflowConfig dataclass, load() classmethod, getter methods,
compliance/HIPAA mode, XML config helpers, save(), and security validation.

Key corrections vs naive generation:
- WorkflowConfig has NO 'provider', 'model', 'timeout', 'max_retries', or
  'workflows' fields — those don't exist
- Actual fields: default_provider, workflow_providers, custom_models,
  pricing_overrides, xml_prompt_defaults, workflow_xml_configs,
  compliance_mode, enabled_workflows, disabled_workflows,
  pii_scrubbing_enabled, audit_level
- Load via WorkflowConfig.load(config_path) classmethod
- No ATTUNE_PROVIDER or ATTUNE_MODEL env vars — the real vars are
  ATTUNE_WORKFLOW_PROVIDER and ATTUNE_MODEL_<TIER>
- pii_scrubbing_enabled defaults to None (not False)
- is_workflow_enabled() returns True/False/None (three-valued)
"""

from __future__ import annotations

import json
from dataclasses import fields
from typing import Any

import pytest

from attune.workflows.config import WorkflowConfig, get_model

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides: Any) -> WorkflowConfig:
    """Return a WorkflowConfig with sane defaults, overridable per-test."""
    defaults: dict[str, Any] = {
        "default_provider": "anthropic",
        "workflow_providers": {},
        "custom_models": {},
        "pricing_overrides": {},
        "xml_prompt_defaults": {},
        "workflow_xml_configs": {},
        "compliance_mode": "standard",
        "enabled_workflows": [],
        "disabled_workflows": [],
        "pii_scrubbing_enabled": None,
        "audit_level": "standard",
    }
    defaults.update(overrides)
    return WorkflowConfig(**defaults)


@pytest.fixture
def config() -> WorkflowConfig:
    return _make_config()


# ---------------------------------------------------------------------------
# 1. Dataclass fields
# ---------------------------------------------------------------------------


class TestWorkflowConfigFields:
    def test_all_expected_fields_present(self):
        field_names = {f.name for f in fields(WorkflowConfig)}
        expected = {
            "default_provider",
            "workflow_providers",
            "custom_models",
            "pricing_overrides",
            "xml_prompt_defaults",
            "workflow_xml_configs",
            "compliance_mode",
            "enabled_workflows",
            "disabled_workflows",
            "pii_scrubbing_enabled",
            "audit_level",
        }
        assert expected == field_names

    def test_no_provider_field(self):
        """'provider' is NOT a field — it's 'default_provider'."""
        field_names = {f.name for f in fields(WorkflowConfig)}
        assert "provider" not in field_names

    def test_no_model_field(self):
        field_names = {f.name for f in fields(WorkflowConfig)}
        assert "model" not in field_names

    def test_no_timeout_field(self):
        field_names = {f.name for f in fields(WorkflowConfig)}
        assert "timeout" not in field_names

    def test_no_max_retries_field(self):
        field_names = {f.name for f in fields(WorkflowConfig)}
        assert "max_retries" not in field_names

    def test_no_workflows_field(self):
        field_names = {f.name for f in fields(WorkflowConfig)}
        assert "workflows" not in field_names


# ---------------------------------------------------------------------------
# 2. Default values
# ---------------------------------------------------------------------------


class TestWorkflowConfigDefaults:
    def test_default_provider_is_anthropic(self, config):
        assert config.default_provider == "anthropic"

    def test_workflow_providers_defaults_empty(self, config):
        assert config.workflow_providers == {}

    def test_custom_models_defaults_empty(self, config):
        assert config.custom_models == {}

    def test_pricing_overrides_defaults_empty(self, config):
        assert config.pricing_overrides == {}

    def test_xml_prompt_defaults_defaults_empty(self, config):
        assert config.xml_prompt_defaults == {}

    def test_workflow_xml_configs_defaults_empty(self, config):
        assert config.workflow_xml_configs == {}

    def test_compliance_mode_default_is_standard(self, config):
        assert config.compliance_mode == "standard"

    def test_enabled_workflows_defaults_empty(self, config):
        assert config.enabled_workflows == []

    def test_disabled_workflows_defaults_empty(self, config):
        assert config.disabled_workflows == []

    def test_pii_scrubbing_enabled_defaults_none(self, config):
        """pii_scrubbing_enabled defaults to None, not False."""
        assert config.pii_scrubbing_enabled is None

    def test_audit_level_default_is_standard(self, config):
        assert config.audit_level == "standard"


# ---------------------------------------------------------------------------
# 3. WorkflowConfig.load() — no file
# ---------------------------------------------------------------------------


class TestWorkflowConfigLoadNoFile:
    def test_load_returns_workflow_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = WorkflowConfig.load()
        assert isinstance(cfg, WorkflowConfig)

    def test_load_without_file_uses_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = WorkflowConfig.load()
        assert cfg.default_provider == "anthropic"

    def test_load_with_nonexistent_path_returns_defaults(self, tmp_path):
        cfg = WorkflowConfig.load(config_path=str(tmp_path / "missing.json"))
        assert cfg.default_provider == "anthropic"


# ---------------------------------------------------------------------------
# 4. WorkflowConfig.load() — JSON file
# ---------------------------------------------------------------------------


class TestWorkflowConfigLoadFromJson:
    def test_load_from_json_reads_default_provider(self, tmp_path):
        cfg_file = tmp_path / "wf.json"
        cfg_file.write_text(json.dumps({"default_provider": "openai"}))
        cfg = WorkflowConfig.load(config_path=str(cfg_file))
        assert cfg.default_provider == "openai"

    def test_load_from_json_reads_workflow_providers(self, tmp_path):
        cfg_file = tmp_path / "wf.json"
        data = {"workflow_providers": {"research": "anthropic"}}
        cfg_file.write_text(json.dumps(data))
        cfg = WorkflowConfig.load(config_path=str(cfg_file))
        assert cfg.workflow_providers == {"research": "anthropic"}

    def test_load_from_json_reads_compliance_mode(self, tmp_path):
        cfg_file = tmp_path / "wf.json"
        cfg_file.write_text(json.dumps({"compliance_mode": "hipaa"}))
        cfg = WorkflowConfig.load(config_path=str(cfg_file))
        assert cfg.compliance_mode == "hipaa"

    def test_load_from_json_reads_enabled_workflows(self, tmp_path):
        cfg_file = tmp_path / "wf.json"
        cfg_file.write_text(json.dumps({"enabled_workflows": ["test-gen"]}))
        cfg = WorkflowConfig.load(config_path=str(cfg_file))
        assert "test-gen" in cfg.enabled_workflows

    def test_load_from_json_reads_disabled_workflows(self, tmp_path):
        cfg_file = tmp_path / "wf.json"
        cfg_file.write_text(json.dumps({"disabled_workflows": ["doc-gen"]}))
        cfg = WorkflowConfig.load(config_path=str(cfg_file))
        assert "doc-gen" in cfg.disabled_workflows

    def test_load_from_json_reads_audit_level(self, tmp_path):
        cfg_file = tmp_path / "wf.json"
        cfg_file.write_text(json.dumps({"audit_level": "enhanced"}))
        cfg = WorkflowConfig.load(config_path=str(cfg_file))
        assert cfg.audit_level == "enhanced"


# ---------------------------------------------------------------------------
# 5. get_provider_for_workflow()
# ---------------------------------------------------------------------------


class TestGetProviderForWorkflow:
    def test_falls_back_to_default_provider(self, config):
        assert config.get_provider_for_workflow("unknown-wf") == "anthropic"

    def test_returns_override_when_set(self):
        cfg = _make_config(
            workflow_providers={"research": "openai"},
            default_provider="anthropic",
        )
        assert cfg.get_provider_for_workflow("research") == "openai"

    def test_other_workflow_uses_default(self):
        cfg = _make_config(
            workflow_providers={"research": "openai"},
            default_provider="anthropic",
        )
        assert cfg.get_provider_for_workflow("code-review") == "anthropic"


# ---------------------------------------------------------------------------
# 6. get_model_for_tier()
# ---------------------------------------------------------------------------


class TestGetModelForTier:
    def test_returns_none_when_no_overrides(self, config):
        assert config.get_model_for_tier("anthropic", "cheap") is None

    def test_returns_provider_specific_model(self):
        cfg = _make_config(custom_models={"anthropic": {"cheap": "claude-haiku-custom"}})
        assert cfg.get_model_for_tier("anthropic", "cheap") == "claude-haiku-custom"

    def test_env_override_takes_priority_over_provider(self):
        cfg = _make_config(
            custom_models={
                "env": {"cheap": "env-model"},
                "anthropic": {"cheap": "provider-model"},
            }
        )
        assert cfg.get_model_for_tier("anthropic", "cheap") == "env-model"

    def test_returns_none_for_unknown_provider(self, config):
        assert config.get_model_for_tier("unknown-provider", "cheap") is None

    def test_returns_none_for_unknown_tier(self):
        cfg = _make_config(custom_models={"anthropic": {"cheap": "x"}})
        assert cfg.get_model_for_tier("anthropic", "premium") is None


# ---------------------------------------------------------------------------
# 7. get_pricing()
# ---------------------------------------------------------------------------


class TestGetPricing:
    def test_returns_none_when_not_set(self, config):
        assert config.get_pricing("gpt-4o") is None

    def test_returns_pricing_dict_when_set(self):
        cfg = _make_config(pricing_overrides={"gpt-4o": {"input": 2.5, "output": 10.0}})
        result = cfg.get_pricing("gpt-4o")
        assert result == {"input": 2.5, "output": 10.0}

    def test_returns_none_for_unknown_model(self):
        cfg = _make_config(pricing_overrides={"gpt-4o": {"input": 2.5, "output": 10.0}})
        assert cfg.get_pricing("llama3") is None


# ---------------------------------------------------------------------------
# 8. XML config helpers
# ---------------------------------------------------------------------------


class TestXmlConfigHelpers:
    def test_get_xml_config_empty_by_default(self, config):
        result = config.get_xml_config_for_workflow("security-audit")
        assert result == {}

    def test_get_xml_config_returns_defaults_when_no_override(self):
        cfg = _make_config(xml_prompt_defaults={"enabled": True, "schema": "1.0"})
        result = cfg.get_xml_config_for_workflow("any-workflow")
        assert result["enabled"] is True

    def test_get_xml_config_merges_defaults_with_overrides(self):
        cfg = _make_config(
            xml_prompt_defaults={"enabled": True, "schema": "1.0"},
            workflow_xml_configs={"security-audit": {"enabled": False}},
        )
        result = cfg.get_xml_config_for_workflow("security-audit")
        assert result["enabled"] is False
        assert result["schema"] == "1.0"

    def test_is_xml_enabled_defaults_to_true_when_no_config(self, config):
        assert config.is_xml_enabled_for_workflow("any-workflow") is True

    def test_is_xml_enabled_returns_false_when_disabled(self):
        cfg = _make_config(workflow_xml_configs={"code-review": {"enabled": False}})
        assert cfg.is_xml_enabled_for_workflow("code-review") is False

    def test_is_xml_enabled_returns_true_when_enabled(self):
        cfg = _make_config(workflow_xml_configs={"security-audit": {"enabled": True}})
        assert cfg.is_xml_enabled_for_workflow("security-audit") is True


# ---------------------------------------------------------------------------
# 9. Compliance / HIPAA mode
# ---------------------------------------------------------------------------


class TestComplianceMode:
    def test_is_hipaa_mode_false_by_default(self, config):
        assert config.is_hipaa_mode() is False

    def test_is_hipaa_mode_true_when_set(self):
        cfg = _make_config(compliance_mode="hipaa")
        assert cfg.is_hipaa_mode() is True

    def test_is_hipaa_mode_case_insensitive(self):
        cfg = _make_config(compliance_mode="HIPAA")
        assert cfg.is_hipaa_mode() is True

    def test_is_pii_scrubbing_enabled_false_in_standard_mode(self, config):
        assert config.is_pii_scrubbing_enabled() is False

    def test_is_pii_scrubbing_enabled_true_in_hipaa_mode(self):
        cfg = _make_config(compliance_mode="hipaa")
        assert cfg.is_pii_scrubbing_enabled() is True

    def test_explicit_true_overrides_standard_mode(self):
        cfg = _make_config(pii_scrubbing_enabled=True)
        assert cfg.is_pii_scrubbing_enabled() is True

    def test_explicit_false_overrides_hipaa_mode(self):
        cfg = _make_config(compliance_mode="hipaa", pii_scrubbing_enabled=False)
        assert cfg.is_pii_scrubbing_enabled() is False


# ---------------------------------------------------------------------------
# 10. is_workflow_enabled() — three-valued return
# ---------------------------------------------------------------------------


class TestIsWorkflowEnabled:
    def test_returns_none_for_default_workflow(self, config):
        """None means 'use default registry behavior'."""
        assert config.is_workflow_enabled("code-review") is None

    def test_returns_false_for_disabled_workflow(self):
        cfg = _make_config(disabled_workflows=["doc-gen"])
        assert cfg.is_workflow_enabled("doc-gen") is False

    def test_returns_true_for_enabled_workflow(self):
        cfg = _make_config(enabled_workflows=["test-gen"])
        assert cfg.is_workflow_enabled("test-gen") is True

    def test_disabled_takes_precedence_over_enabled(self):
        cfg = _make_config(
            enabled_workflows=["doc-gen"],
            disabled_workflows=["doc-gen"],
        )
        assert cfg.is_workflow_enabled("doc-gen") is False

    def test_hipaa_mode_auto_enables_test_gen(self):
        cfg = _make_config(compliance_mode="hipaa")
        assert cfg.is_workflow_enabled("test-gen") is True

    def test_hipaa_mode_does_not_affect_other_workflows(self):
        cfg = _make_config(compliance_mode="hipaa")
        assert cfg.is_workflow_enabled("code-review") is None


# ---------------------------------------------------------------------------
# 11. get_effective_audit_level()
# ---------------------------------------------------------------------------


class TestGetEffectiveAuditLevel:
    def test_standard_by_default(self, config):
        assert config.get_effective_audit_level() == "standard"

    def test_hipaa_mode_returns_hipaa_level(self):
        cfg = _make_config(compliance_mode="hipaa")
        assert cfg.get_effective_audit_level() == "hipaa"

    def test_explicit_enhanced_overrides_hipaa(self):
        cfg = _make_config(compliance_mode="hipaa", audit_level="enhanced")
        assert cfg.get_effective_audit_level() == "enhanced"

    def test_explicit_enhanced_in_standard_mode(self):
        cfg = _make_config(audit_level="enhanced")
        assert cfg.get_effective_audit_level() == "enhanced"


# ---------------------------------------------------------------------------
# 12. save() — JSON round-trip
# ---------------------------------------------------------------------------


class TestConfigSave:
    def test_save_creates_json_file(self, tmp_path, config):
        out = tmp_path / "wf_out.json"
        config.save(str(out))
        assert out.exists()

    def test_saved_json_contains_default_provider(self, tmp_path, config):
        out = tmp_path / "wf_out.json"
        config.save(str(out))
        data = json.loads(out.read_text())
        assert "default_provider" in data

    def test_save_round_trip_preserves_default_provider(self, tmp_path):
        cfg = _make_config(default_provider="openai")
        out = tmp_path / "cfg.json"
        cfg.save(str(out))
        loaded = WorkflowConfig.load(config_path=str(out))
        assert loaded.default_provider == "openai"

    def test_save_round_trip_preserves_compliance_mode(self, tmp_path):
        cfg = _make_config(compliance_mode="hipaa")
        out = tmp_path / "cfg.json"
        cfg.save(str(out))
        loaded = WorkflowConfig.load(config_path=str(out))
        assert loaded.compliance_mode == "hipaa"

    def test_save_creates_parent_directory(self, tmp_path):
        out = tmp_path / "subdir" / "nested" / "cfg.json"
        config = _make_config()
        config.save(str(out))
        assert out.exists()


# ---------------------------------------------------------------------------
# 13. save() — security: path traversal and null bytes
# ---------------------------------------------------------------------------


class TestConfigSaveSecurity:
    def test_save_rejects_null_bytes(self, config):
        with pytest.raises(ValueError, match="null bytes"):
            config.save("config\x00.json")

    def test_save_rejects_system_directories(self, config):
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            config.save("/etc/attune_config.json")


# ---------------------------------------------------------------------------
# 14. get_model() module-level function
# ---------------------------------------------------------------------------


class TestGetModel:
    def test_returns_string(self):
        result = get_model("anthropic", "cheap")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string_for_capable(self):
        result = get_model("anthropic", "capable")
        assert isinstance(result, str)

    def test_custom_config_overrides_default(self):
        cfg = _make_config(custom_models={"anthropic": {"cheap": "my-model"}})
        result = get_model("anthropic", "cheap", config=cfg)
        assert result == "my-model"

    def test_unknown_provider_falls_back_gracefully(self):
        result = get_model("unknown-provider", "cheap")
        assert isinstance(result, str)
