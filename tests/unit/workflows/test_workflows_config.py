"""Tests for workflows/config.py module.

Tests ModelConfig, WorkflowConfig, get_model, and create_example_config.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from unittest.mock import patch

from attune.workflows.config import (
    ModelConfig,
    WorkflowConfig,
    create_example_config,
    get_model,
)

# ---------------------------------------------------------------------------
# Tests for ModelConfig
# ---------------------------------------------------------------------------


class TestModelConfig:
    """Tests for the ModelConfig dataclass."""

    def test_basic_creation(self):
        """ModelConfig can be created with required fields."""
        mc = ModelConfig(name="claude-sonnet-5", provider="anthropic", tier="capable")

        assert mc.name == "claude-sonnet-5"
        assert mc.provider == "anthropic"
        assert mc.tier == "capable"
        assert mc.max_tokens == 4096

    def test_from_model_info(self):
        """from_model_info converts ModelInfo to ModelConfig."""
        from attune.models import MODEL_REGISTRY

        # Get a real ModelInfo from the registry
        info = MODEL_REGISTRY["anthropic"]["capable"]
        mc = ModelConfig.from_model_info(info)

        assert mc.name == info.id
        assert mc.provider == info.provider
        assert mc.tier == info.tier


# ---------------------------------------------------------------------------
# Tests for WorkflowConfig
# ---------------------------------------------------------------------------


class TestWorkflowConfig:
    """Tests for WorkflowConfig."""

    def test_default_values(self):
        """Default config uses anthropic provider."""
        config = WorkflowConfig()

        assert config.default_provider == "anthropic"
        assert config.compliance_mode == "standard"
        assert config.enabled_workflows == []
        assert config.disabled_workflows == []

    def test_get_provider_for_workflow_default(self):
        """Returns default provider when no override set."""
        config = WorkflowConfig(default_provider="openai")

        assert config.get_provider_for_workflow("code-review") == "openai"

    def test_get_provider_for_workflow_override(self):
        """Returns workflow-specific provider override."""
        config = WorkflowConfig(
            default_provider="openai",
            workflow_providers={"code-review": "anthropic"},
        )

        assert config.get_provider_for_workflow("code-review") == "anthropic"
        assert config.get_provider_for_workflow("bug-predict") == "openai"

    def test_get_model_for_tier_no_override(self):
        """Returns None when no custom model set."""
        config = WorkflowConfig()

        assert config.get_model_for_tier("anthropic", "cheap") is None

    def test_get_model_for_tier_with_override(self):
        """Returns custom model for specific provider/tier."""
        config = WorkflowConfig(
            custom_models={"anthropic": {"cheap": "custom-haiku"}},
        )

        assert config.get_model_for_tier("anthropic", "cheap") == "custom-haiku"

    def test_get_model_for_tier_env_override(self):
        """Env overrides take precedence over provider overrides."""
        config = WorkflowConfig(
            custom_models={
                "env": {"cheap": "env-model"},
                "anthropic": {"cheap": "provider-model"},
            },
        )

        assert config.get_model_for_tier("anthropic", "cheap") == "env-model"

    def test_get_pricing_no_override(self):
        """Returns None when no pricing override."""
        config = WorkflowConfig()

        assert config.get_pricing("claude-sonnet-5") is None

    def test_get_pricing_with_override(self):
        """Returns custom pricing dict."""
        config = WorkflowConfig(
            pricing_overrides={"my-model": {"input": 1.0, "output": 5.0}},
        )

        pricing = config.get_pricing("my-model")
        assert pricing["input"] == 1.0


class TestWorkflowConfigXml:
    """Tests for XML configuration methods."""

    def test_get_xml_config_defaults(self):
        """Returns default XML config when no workflow override."""
        config = WorkflowConfig(
            xml_prompt_defaults={"enabled": True, "schema_version": "1.0"},
        )

        xml_config = config.get_xml_config_for_workflow("code-review")

        assert xml_config["enabled"] is True
        assert xml_config["schema_version"] == "1.0"

    def test_get_xml_config_workflow_override(self):
        """Workflow-specific config overrides defaults."""
        config = WorkflowConfig(
            xml_prompt_defaults={"enabled": True},
            workflow_xml_configs={"code-review": {"enabled": False}},
        )

        xml_config = config.get_xml_config_for_workflow("code-review")

        assert xml_config["enabled"] is False

    def test_is_xml_enabled_default_true(self):
        """XML is enabled by default."""
        config = WorkflowConfig()

        assert config.is_xml_enabled_for_workflow("any-workflow") is True

    def test_is_xml_enabled_explicit_false(self):
        """XML can be explicitly disabled."""
        config = WorkflowConfig(
            workflow_xml_configs={"code-review": {"enabled": False}},
        )

        assert config.is_xml_enabled_for_workflow("code-review") is False


class TestWorkflowConfigCompliance:
    """Tests for compliance and feature flag methods."""

    def test_is_hipaa_mode_false(self):
        """Standard mode is not HIPAA."""
        config = WorkflowConfig(compliance_mode="standard")

        assert config.is_hipaa_mode() is False

    def test_is_hipaa_mode_true(self):
        """HIPAA compliance mode detection."""
        config = WorkflowConfig(compliance_mode="hipaa")

        assert config.is_hipaa_mode() is True

    def test_pii_scrubbing_explicit(self):
        """Explicit pii_scrubbing_enabled takes precedence."""
        config = WorkflowConfig(
            compliance_mode="standard",
            pii_scrubbing_enabled=True,
        )

        assert config.is_pii_scrubbing_enabled() is True

    def test_pii_scrubbing_hipaa_default(self):
        """HIPAA mode enables PII scrubbing by default."""
        config = WorkflowConfig(compliance_mode="hipaa")

        assert config.is_pii_scrubbing_enabled() is True

    def test_pii_scrubbing_standard_default(self):
        """Standard mode disables PII scrubbing by default."""
        config = WorkflowConfig(compliance_mode="standard")

        assert config.is_pii_scrubbing_enabled() is False

    def test_is_workflow_enabled_disabled(self):
        """Disabled workflows return False."""
        config = WorkflowConfig(disabled_workflows=["test-gen"])

        assert config.is_workflow_enabled("test-gen") is False

    def test_is_workflow_enabled_explicit(self):
        """Explicitly enabled workflows return True."""
        config = WorkflowConfig(enabled_workflows=["test-gen"])

        assert config.is_workflow_enabled("test-gen") is True

    def test_is_workflow_enabled_default(self):
        """Unspecified workflows return None (use registry default)."""
        config = WorkflowConfig()

        assert config.is_workflow_enabled("code-review") is None

    def test_is_workflow_enabled_hipaa_auto(self):
        """HIPAA mode auto-enables test-gen."""
        config = WorkflowConfig(compliance_mode="hipaa")

        assert config.is_workflow_enabled("test-gen") is True

    def test_effective_audit_level_standard(self):
        """Standard mode returns standard audit level."""
        config = WorkflowConfig()

        assert config.get_effective_audit_level() == "standard"

    def test_effective_audit_level_hipaa(self):
        """HIPAA mode returns hipaa audit level."""
        config = WorkflowConfig(compliance_mode="hipaa")

        assert config.get_effective_audit_level() == "hipaa"

    def test_effective_audit_level_explicit(self):
        """Explicit audit level takes precedence."""
        config = WorkflowConfig(audit_level="enhanced")

        assert config.get_effective_audit_level() == "enhanced"


class TestWorkflowConfigLoadSave:
    """Tests for load/save functionality."""

    def test_load_from_json(self, tmp_path):
        """Loads config from JSON file."""
        config_file = tmp_path / "workflows.json"
        config_file.write_text(json.dumps({"default_provider": "openai"}))

        config = WorkflowConfig.load(config_path=config_file)

        assert config.default_provider == "openai"

    def test_load_nonexistent_returns_defaults(self):
        """Loading from non-existent path returns defaults."""
        config = WorkflowConfig.load(config_path="/nonexistent/path.json")

        assert config.default_provider == "anthropic"

    def test_save_json(self, tmp_path):
        """Saves config to JSON file."""
        config = WorkflowConfig(default_provider="openai")
        output = tmp_path / "config.json"

        config.save(output)

        data = json.loads(output.read_text())
        assert data["default_provider"] == "openai"

    def test_load_with_env_overrides(self):
        """Environment variables override file config."""
        with patch.dict(
            "os.environ",
            {"ATTUNE_WORKFLOW_PROVIDER": "openai"},
        ):
            config = WorkflowConfig.load()

        assert config.default_provider == "openai"

    def test_load_file_with_workflows_section(self, tmp_path):
        """Loads config from attune.config file with workflows section."""
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps(
                {
                    "provider": "openai",
                    "workflows": {"compliance_mode": "hipaa"},
                }
            )
        )

        config = WorkflowConfig.load(config_path=config_file)

        assert config.default_provider == "openai"
        assert config.compliance_mode == "hipaa"


# ---------------------------------------------------------------------------
# Tests for get_model
# ---------------------------------------------------------------------------


class TestGetModel:
    """Tests for the get_model function."""

    def test_get_model_default(self):
        """Returns a model name for default provider/tier."""
        model = get_model("anthropic", "capable")

        assert isinstance(model, str)
        assert len(model) > 0

    def test_get_model_with_config_override(self):
        """Config override takes precedence over defaults."""
        config = WorkflowConfig(
            custom_models={"anthropic": {"cheap": "my-custom-model"}},
        )

        model = get_model("anthropic", "cheap", config=config)

        assert model == "my-custom-model"

    def test_get_model_unknown_provider_falls_back(self):
        """Unknown provider falls back to anthropic capable."""
        model = get_model("nonexistent", "cheap")

        # Should fall back to anthropic capable
        assert isinstance(model, str)


# ---------------------------------------------------------------------------
# Tests for create_example_config
# ---------------------------------------------------------------------------


class TestCreateExampleConfig:
    """Tests for create_example_config."""

    def test_returns_yaml_string(self):
        """Returns a non-empty YAML string."""
        content = create_example_config()

        assert isinstance(content, str)
        assert "default_provider" in content
        assert "anthropic" in content
        assert len(content) > 100
