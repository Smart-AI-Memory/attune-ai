"""Unit tests for workflow configuration

Tests the WorkflowConfig class for loading, saving, and managing workflow settings.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.workflows.config import ModelConfig, WorkflowConfig, get_model

# Skip YAML tests if PyYAML not available
try:
    import yaml  # noqa: F401

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


@pytest.mark.unit
class TestWorkflowConfigInitialization:
    """Test workflow config initialization."""

    def test_default_initialization(self):
        """Test creating config with defaults."""
        config = WorkflowConfig()

        assert config.default_provider == "anthropic"
        assert config.workflow_providers == {}
        assert config.custom_models == {}
        assert config.pricing_overrides == {}
        assert config.xml_prompt_defaults == {}
        assert config.workflow_xml_configs == {}
        assert config.compliance_mode == "standard"
        assert config.enabled_workflows == []
        assert config.disabled_workflows == []
        assert config.pii_scrubbing_enabled is None
        assert config.audit_level == "standard"

    def test_initialization_with_custom_values(self):
        """Test creating config with custom values."""
        config = WorkflowConfig(
            default_provider="anthropic",
            workflow_providers={"research": "anthropic"},
            compliance_mode="hipaa",
            enabled_workflows=["test-gen"],
            pii_scrubbing_enabled=True,
        )

        assert config.default_provider == "anthropic"
        assert config.workflow_providers == {"research": "anthropic"}
        assert config.compliance_mode == "hipaa"
        assert config.enabled_workflows == ["test-gen"]
        assert config.pii_scrubbing_enabled is True


@pytest.mark.unit
class TestWorkflowConfigLoading:
    """Test loading config from files."""

    def test_load_from_json(self):
        """Test loading config from JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "workflows.json"
            config_data = {
                "default_provider": "openai",
                "workflow_providers": {"research": "anthropic"},
            }
            config_path.write_text(json.dumps(config_data))

            config = WorkflowConfig.load(config_path)

            assert config.default_provider == "openai"
            assert config.workflow_providers == {"research": "anthropic"}

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_load_from_yaml(self):
        """Test loading config from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "workflows.yaml"
            config_path.write_text(
                """
default_provider: openai
workflow_providers:
  research: anthropic
"""
            )

            config = WorkflowConfig.load(config_path)

            assert config.default_provider == "openai"
            assert config.workflow_providers == {"research": "anthropic"}

    def test_load_with_no_file(self):
        """Test loading when no config file exists."""
        with tempfile.TemporaryDirectory():
            # Change to temp dir so no config files are found
            with patch("pathlib.Path.exists", return_value=False):
                config = WorkflowConfig.load()

                # Should return defaults
                assert config.default_provider == "anthropic"
                assert config.workflow_providers == {}

    def test_load_with_env_overrides(self):
        """Test that environment variables override config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "workflows.json"
            config_path.write_text(json.dumps({"default_provider": "anthropic"}))

            # Set environment variable
            with patch.dict(os.environ, {"EMPATHY_WORKFLOW_PROVIDER": "openai"}):
                config = WorkflowConfig.load(config_path)

                assert config.default_provider == "openai"

    def test_load_with_workflow_specific_env(self):
        """Test workflow-specific provider env vars."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "workflows.json"
            config_path.write_text(json.dumps({}))

            with patch.dict(os.environ, {"EMPATHY_WORKFLOW_RESEARCH_PROVIDER": "openai"}):
                config = WorkflowConfig.load(config_path)

                assert config.workflow_providers["research"] == "openai"

    def test_load_with_model_tier_env(self):
        """Test tier-specific model env vars."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "workflows.json"
            config_path.write_text(json.dumps({}))

            with patch.dict(
                os.environ,
                {
                    "EMPATHY_MODEL_CHEAP": "gpt-4o-mini",
                    "EMPATHY_MODEL_CAPABLE": "claude-sonnet-4",
                },
            ):
                config = WorkflowConfig.load(config_path)

                assert config.custom_models["env"]["cheap"] == "gpt-4o-mini"
                assert config.custom_models["env"]["capable"] == "claude-sonnet-4"

    def test_load_from_empathy_config_yaml(self):
        """Test loading from attune.config.yaml format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "attune.config.yaml"
            # attune.config.yaml has root provider and model_preferences
            config_path.write_text(
                """
provider: openai
model_preferences:
  cheap: gpt-4o-mini
  capable: gpt-4o
"""
            )

            config = WorkflowConfig.load(config_path)

            assert config.default_provider == "openai"
            assert config.custom_models["openai"]["cheap"] == "gpt-4o-mini"
            assert config.custom_models["openai"]["capable"] == "gpt-4o"


@pytest.mark.unit
class TestWorkflowConfigProviderMethods:
    """Test provider and model selection methods."""

    def test_get_provider_for_workflow_default(self):
        """Test getting default provider for workflow."""
        config = WorkflowConfig(default_provider="anthropic")

        provider = config.get_provider_for_workflow("research")

        assert provider == "anthropic"

    def test_get_provider_for_workflow_override(self):
        """Test getting overridden provider for workflow."""
        config = WorkflowConfig(
            default_provider="anthropic",
            workflow_providers={"research": "openai"},
        )

        provider = config.get_provider_for_workflow("research")

        assert provider == "openai"

    def test_get_model_for_tier_no_override(self):
        """Test getting model when no override exists."""
        config = WorkflowConfig()

        model = config.get_model_for_tier("anthropic", "capable")

        assert model is None  # No override, should return None

    def test_get_model_for_tier_with_provider_override(self):
        """Test getting model with provider-specific override."""
        config = WorkflowConfig(
            custom_models={
                "anthropic": {
                    "capable": "claude-sonnet-4-custom",
                }
            }
        )

        model = config.get_model_for_tier("anthropic", "capable")

        assert model == "claude-sonnet-4-custom"

    def test_get_model_for_tier_with_env_override(self):
        """Test that env overrides take precedence."""
        config = WorkflowConfig(
            custom_models={
                "env": {"capable": "env-model"},
                "anthropic": {"capable": "provider-model"},
            }
        )

        model = config.get_model_for_tier("anthropic", "capable")

        assert model == "env-model"  # env takes precedence

    def test_get_pricing_exists(self):
        """Test getting pricing override."""
        config = WorkflowConfig(
            pricing_overrides={
                "custom-model": {"input": 1.0, "output": 5.0},
            }
        )

        pricing = config.get_pricing("custom-model")

        assert pricing == {"input": 1.0, "output": 5.0}

    def test_get_pricing_not_exists(self):
        """Test getting pricing when no override exists."""
        config = WorkflowConfig()

        pricing = config.get_pricing("unknown-model")

        assert pricing is None


@pytest.mark.unit
class TestWorkflowConfigXMLMethods:
    """Test XML prompt configuration methods."""

    def test_get_xml_config_defaults_only(self):
        """Test getting XML config with only defaults."""
        config = WorkflowConfig(
            xml_prompt_defaults={"enabled": True, "version": "1.0"},
        )

        xml_config = config.get_xml_config_for_workflow("research")

        assert xml_config == {"enabled": True, "version": "1.0"}

    def test_get_xml_config_with_workflow_override(self):
        """Test getting XML config with workflow-specific override."""
        config = WorkflowConfig(
            xml_prompt_defaults={"enabled": False, "version": "1.0"},
            workflow_xml_configs={
                "research": {"enabled": True, "custom": "value"},
            },
        )

        xml_config = config.get_xml_config_for_workflow("research")

        assert xml_config["enabled"] is True  # Overridden
        assert xml_config["version"] == "1.0"  # From defaults
        assert xml_config["custom"] == "value"  # From workflow config

    def test_is_xml_enabled_true(self):
        """Test checking if XML is enabled for workflow."""
        config = WorkflowConfig(
            workflow_xml_configs={
                "research": {"enabled": True},
            },
        )

        assert config.is_xml_enabled_for_workflow("research") is True

    def test_is_xml_enabled_false(self):
        """Test checking if XML is disabled for workflow."""
        config = WorkflowConfig(
            xml_prompt_defaults={"enabled": False},
        )

        assert config.is_xml_enabled_for_workflow("research") is False


@pytest.mark.unit
class TestWorkflowConfigComplianceMethods:
    """Test compliance and feature flag methods."""

    def test_is_hipaa_mode_false(self):
        """Test HIPAA mode check when standard."""
        config = WorkflowConfig(compliance_mode="standard")

        assert config.is_hipaa_mode() is False

    def test_is_hipaa_mode_true(self):
        """Test HIPAA mode check when enabled."""
        config = WorkflowConfig(compliance_mode="hipaa")

        assert config.is_hipaa_mode() is True

    def test_is_pii_scrubbing_explicit_true(self):
        """Test PII scrubbing when explicitly enabled."""
        config = WorkflowConfig(
            compliance_mode="standard",
            pii_scrubbing_enabled=True,
        )

        assert config.is_pii_scrubbing_enabled() is True

    def test_is_pii_scrubbing_explicit_false(self):
        """Test PII scrubbing when explicitly disabled."""
        config = WorkflowConfig(
            compliance_mode="hipaa",
            pii_scrubbing_enabled=False,
        )

        assert config.is_pii_scrubbing_enabled() is False

    def test_is_pii_scrubbing_hipaa_default(self):
        """Test PII scrubbing defaults to true in HIPAA mode."""
        config = WorkflowConfig(compliance_mode="hipaa")

        assert config.is_pii_scrubbing_enabled() is True

    def test_is_pii_scrubbing_standard_default(self):
        """Test PII scrubbing defaults to false in standard mode."""
        config = WorkflowConfig(compliance_mode="standard")

        assert config.is_pii_scrubbing_enabled() is False

    def test_is_workflow_enabled_explicitly_enabled(self):
        """Test workflow explicitly enabled."""
        config = WorkflowConfig(enabled_workflows=["test-gen"])

        assert config.is_workflow_enabled("test-gen") is True

    def test_is_workflow_enabled_explicitly_disabled(self):
        """Test workflow explicitly disabled."""
        config = WorkflowConfig(disabled_workflows=["test-gen"])

        assert config.is_workflow_enabled("test-gen") is False

    def test_is_workflow_enabled_hipaa_auto_enable(self):
        """Test HIPAA mode auto-enables certain workflows."""
        config = WorkflowConfig(compliance_mode="hipaa")

        assert config.is_workflow_enabled("test-gen") is True

    def test_is_workflow_enabled_default(self):
        """Test workflow with default behavior."""
        config = WorkflowConfig()

        result = config.is_workflow_enabled("research")

        assert result is None  # None means use default registry

    def test_is_workflow_enabled_disabled_takes_precedence(self):
        """Test that disabled list takes precedence over enabled."""
        config = WorkflowConfig(
            enabled_workflows=["test-gen"],
            disabled_workflows=["test-gen"],
        )

        assert config.is_workflow_enabled("test-gen") is False

    def test_get_effective_audit_level_standard(self):
        """Test getting audit level in standard mode."""
        config = WorkflowConfig(compliance_mode="standard")

        assert config.get_effective_audit_level() == "standard"

    def test_get_effective_audit_level_hipaa(self):
        """Test getting audit level in HIPAA mode."""
        config = WorkflowConfig(compliance_mode="hipaa")

        assert config.get_effective_audit_level() == "hipaa"

    def test_get_effective_audit_level_explicit(self):
        """Test explicit audit level takes precedence."""
        config = WorkflowConfig(
            compliance_mode="standard",
            audit_level="enhanced",
        )

        assert config.get_effective_audit_level() == "enhanced"


@pytest.mark.unit
class TestWorkflowConfigSaving:
    """Test saving configuration to file."""

    def test_save_to_json(self):
        """Test saving config to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = WorkflowConfig(
                default_provider="anthropic",
                workflow_providers={"research": "anthropic"},
            )

            config_path = Path(tmpdir) / "test.json"
            config.save(config_path)

            # Verify file was created and content is correct
            assert config_path.exists()
            data = json.loads(config_path.read_text())
            assert data["default_provider"] == "anthropic"
            assert data["workflow_providers"] == {"research": "anthropic"}

    @pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
    def test_save_to_yaml(self):
        """Test saving config to YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = WorkflowConfig(
                default_provider="anthropic",
                workflow_providers={"research": "anthropic"},
            )

            config_path = Path(tmpdir) / "test.yaml"
            config.save(config_path)

            # Verify file was created
            assert config_path.exists()
            content = config_path.read_text()
            assert "default_provider: anthropic" in content
            assert "research: anthropic" in content

    def test_save_creates_parent_directory(self):
        """Test that save creates parent directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = WorkflowConfig()

            config_path = Path(tmpdir) / "subdir" / "test.json"
            config.save(config_path)

            assert config_path.exists()
            assert config_path.parent.exists()


@pytest.mark.unit
class TestGetModelFunction:
    """Test get_model helper function."""

    def test_get_model_default(self):
        """Test getting default model."""
        model = get_model("anthropic", "capable")

        assert isinstance(model, str)
        assert len(model) > 0

    def test_get_model_with_config_override(self):
        """Test getting model with config override."""
        config = WorkflowConfig(
            custom_models={
                "anthropic": {"capable": "custom-model"},
            }
        )

        model = get_model("anthropic", "capable", config)

        assert model == "custom-model"

    def test_get_model_fallback_to_default(self):
        """Test fallback to default when provider not found."""
        model = get_model("unknown-provider", "unknown-tier")

        # Should fallback to anthropic capable
        assert isinstance(model, str)
        assert len(model) > 0


@pytest.mark.unit
class TestModelConfig:
    """Test ModelConfig dataclass."""

    def test_model_config_initialization(self):
        """Test creating ModelConfig."""
        config = ModelConfig(
            name="test-model",
            provider="anthropic",
            tier="capable",
            input_cost_per_million=1.0,
            output_cost_per_million=5.0,
            max_tokens=8192,
            supports_vision=True,
            supports_tools=True,
        )

        assert config.name == "test-model"
        assert config.provider == "anthropic"
        assert config.tier == "capable"
        assert config.input_cost_per_million == 1.0
        assert config.output_cost_per_million == 5.0
        assert config.max_tokens == 8192
        assert config.supports_vision is True
        assert config.supports_tools is True

    def test_model_config_defaults(self):
        """Test ModelConfig with default values."""
        config = ModelConfig(
            name="test-model",
            provider="anthropic",
            tier="capable",
        )

        assert config.input_cost_per_million == 0.0
        assert config.output_cost_per_million == 0.0
        assert config.max_tokens == 4096
        assert config.supports_vision is False
        assert config.supports_tools is True
