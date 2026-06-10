"""Unit tests for config module

Tests EmpathyConfig class including loading from YAML/JSON,
validation, and environment variable handling.
"""

import json
import os
import tempfile

import pytest

from attune.config import YAML_AVAILABLE, EmpathyConfig, resolve_show_cost
from attune.workflows.config import ModelConfig


@pytest.mark.unit
class TestEmpathyConfigDefaults:
    """Test default EmpathyConfig values"""

    def test_default_config_creation(self):
        """Test creating config with defaults"""
        config = EmpathyConfig()

        assert config.user_id == "default_user"
        assert config.target_level == 3
        assert config.confidence_threshold == 0.75
        assert config.trust_building_rate == 0.05
        assert config.trust_erosion_rate == 0.10
        assert config.persistence_enabled is True
        assert config.persistence_backend == "sqlite"

    def test_default_logging_settings(self):
        """Test default logging configuration"""
        config = EmpathyConfig()

        assert config.log_level == "INFO"
        assert config.log_file is None
        assert config.structured_logging is True

    def test_default_feature_flags(self):
        """Test default feature flag values"""
        config = EmpathyConfig()

        assert config.pattern_library_enabled is True
        assert config.pattern_sharing is True
        assert config.async_enabled is True
        assert config.feedback_loop_monitoring is True
        assert config.leverage_point_analysis is True

    def test_default_metadata_empty(self):
        """Test that metadata defaults to empty dict"""
        config = EmpathyConfig()
        assert config.metadata == {}
        assert isinstance(config.metadata, dict)


@pytest.mark.unit
class TestEmpathyConfigCustomization:
    """Test customizing EmpathyConfig values"""

    def test_custom_user_id(self):
        """Test setting custom user_id"""
        config = EmpathyConfig(user_id="test_user_123")
        assert config.user_id == "test_user_123"

    def test_custom_thresholds(self):
        """Test setting custom threshold values"""
        config = EmpathyConfig(confidence_threshold=0.9, pattern_confidence_threshold=0.5)
        assert config.confidence_threshold == 0.9
        assert config.pattern_confidence_threshold == 0.5

    def test_custom_persistence_settings(self):
        """Test customizing persistence settings"""
        config = EmpathyConfig(
            persistence_enabled=False,
            persistence_backend="json",
            persistence_path="/custom/path",
        )
        assert config.persistence_enabled is False
        assert config.persistence_backend == "json"
        assert config.persistence_path == "/custom/path"

    def test_custom_metadata(self):
        """Test setting custom metadata"""
        custom_meta = {"project": "test", "version": "1.0"}
        config = EmpathyConfig(metadata=custom_meta)
        assert config.metadata == custom_meta
        assert config.metadata["project"] == "test"


@pytest.mark.unit
class TestEmpathyConfigValidation:
    """Test EmpathyConfig validation rules"""

    def test_validation_fails_with_invalid_default_model(self):
        """Test that invalid default_model raises ValueError"""
        model = ModelConfig(name="test-model", provider="anthropic", tier="capable")

        with pytest.raises(ValueError, match="Default model 'nonexistent' not in models"):
            EmpathyConfig(models=[model], default_model="nonexistent")

    def test_validation_passes_with_valid_default_model(self):
        """Test that valid default_model is accepted"""
        model = ModelConfig(name="test-model", provider="anthropic", tier="capable")

        config = EmpathyConfig(models=[model], default_model="test-model")
        assert config.default_model == "test-model"

    def test_validation_passes_with_no_default_model(self):
        """Test that None default_model is valid"""
        model = ModelConfig(name="test-model", provider="anthropic", tier="capable")

        config = EmpathyConfig(models=[model])
        assert config.default_model is None


@pytest.mark.unit
@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
class TestEmpathyConfigYAML:
    """Test loading config from YAML files"""

    def test_load_from_yaml_basic(self):
        """Test loading basic YAML config"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(
                """
user_id: yaml_test_user
target_level: 5
confidence_threshold: 0.85
log_level: DEBUG
""",
            )
            yaml_path = f.name

        try:
            config = EmpathyConfig.from_yaml(yaml_path)
            assert config.user_id == "yaml_test_user"
            assert config.target_level == 5
            assert config.confidence_threshold == 0.85
            assert config.log_level == "DEBUG"
        finally:
            os.unlink(yaml_path)

    def test_load_from_yaml_with_nested_settings(self):
        """Test loading YAML with nested structures"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write(
                """
user_id: nested_test
metadata:
  project: empathy_test
  environment: staging
  version: 2.0
""",
            )
            yaml_path = f.name

        try:
            config = EmpathyConfig.from_yaml(yaml_path)
            assert config.user_id == "nested_test"
            assert config.metadata["project"] == "empathy_test"
            assert config.metadata["environment"] == "staging"
        finally:
            os.unlink(yaml_path)


@pytest.mark.unit
class TestEmpathyConfigJSON:
    """Test loading config from JSON files"""

    def test_load_from_json_basic(self):
        """Test loading basic JSON config"""
        config_data = {
            "user_id": "json_test_user",
            "target_level": 4,
            "confidence_threshold": 0.8,
            "log_level": "WARNING",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            json_path = f.name

        try:
            config = EmpathyConfig.from_json(json_path)
            assert config.user_id == "json_test_user"
            assert config.target_level == 4
            assert config.confidence_threshold == 0.8
            assert config.log_level == "WARNING"
        finally:
            os.unlink(json_path)

    def test_load_from_json_with_metadata(self):
        """Test loading JSON with custom metadata"""
        config_data = {
            "user_id": "json_meta_test",
            "metadata": {"custom_field": "custom_value", "number": 42},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            json_path = f.name

        try:
            config = EmpathyConfig.from_json(json_path)
            assert config.metadata["custom_field"] == "custom_value"
            assert config.metadata["number"] == 42
        finally:
            os.unlink(json_path)


@pytest.mark.unit
class TestEmpathyConfigEnvironment:
    """Test loading config from environment variables"""

    def test_load_from_env_basic(self, monkeypatch):
        """Test loading config from environment variables"""
        monkeypatch.setenv("EMPATHY_USER_ID", "env_user")
        monkeypatch.setenv("EMPATHY_TARGET_LEVEL", "6")
        monkeypatch.setenv("EMPATHY_LOG_LEVEL", "ERROR")

        config = EmpathyConfig.from_env()
        assert config.user_id == "env_user"
        assert config.target_level == 6
        assert config.log_level == "ERROR"

    def test_load_from_env_boolean_conversion(self, monkeypatch):
        """Test that environment booleans are converted correctly"""
        monkeypatch.setenv("EMPATHY_PERSISTENCE_ENABLED", "false")
        monkeypatch.setenv("EMPATHY_METRICS_ENABLED", "true")

        config = EmpathyConfig.from_env()
        assert config.persistence_enabled is False
        assert config.metrics_enabled is True

    def test_load_from_env_float_conversion(self, monkeypatch):
        """Test that environment floats are converted correctly"""
        monkeypatch.setenv("EMPATHY_CONFIDENCE_THRESHOLD", "0.95")
        monkeypatch.setenv("EMPATHY_TRUST_BUILDING_RATE", "0.1")

        config = EmpathyConfig.from_env()
        assert config.confidence_threshold == pytest.approx(0.95)
        assert config.trust_building_rate == pytest.approx(0.1)

    def test_show_cost_metrics_env_boolean_conversion(self, monkeypatch):
        """ATTUNE_SHOW_COST_METRICS parses as a boolean, not a string."""
        monkeypatch.setenv("ATTUNE_SHOW_COST_METRICS", "true")
        assert EmpathyConfig.from_env().show_cost_metrics is True

        monkeypatch.setenv("ATTUNE_SHOW_COST_METRICS", "false")
        assert EmpathyConfig.from_env().show_cost_metrics is False

    def test_show_cost_metrics_defaults_to_none(self, monkeypatch):
        """Unset show_cost_metrics stays None (auto mode)."""
        monkeypatch.delenv("ATTUNE_SHOW_COST_METRICS", raising=False)
        monkeypatch.delenv("EMPATHY_SHOW_COST_METRICS", raising=False)
        assert EmpathyConfig().show_cost_metrics is None
        assert EmpathyConfig.from_env().show_cost_metrics is None


@pytest.mark.unit
class TestResolveShowCost:
    """resolve_show_cost (workflow-result-formatting design D3)."""

    def test_explicit_true_wins_without_api_key(self, monkeypatch):
        """Config True overrides the missing-key auto default."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config = EmpathyConfig(show_cost_metrics=True)
        assert resolve_show_cost(config) is True

    def test_explicit_false_wins_with_api_key(self, monkeypatch):
        """Config False overrides the key-present auto default."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "FAKE_key_NOT_REAL")
        config = EmpathyConfig(show_cost_metrics=False)
        assert resolve_show_cost(config) is False

    def test_auto_on_when_api_key_set(self, monkeypatch):
        """None (auto) shows cost for pay-per-call API users."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "FAKE_key_NOT_REAL")
        assert resolve_show_cost(EmpathyConfig()) is True

    def test_auto_off_when_api_key_missing(self, monkeypatch):
        """None (auto) hides cost for subscription users (no key)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert resolve_show_cost(EmpathyConfig()) is False

    def test_auto_off_when_api_key_empty(self, monkeypatch):
        """Empty-string key (the CI convention) counts as no key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        assert resolve_show_cost(EmpathyConfig()) is False

    def test_loads_ambient_config_when_none(self, tmp_path, monkeypatch):
        """config=None reads the cwd config file's explicit override."""
        (tmp_path / ".attune.json").write_text('{"show_cost_metrics": true}')
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert resolve_show_cost() is True

    def test_ambient_config_false_wins_over_key(self, tmp_path, monkeypatch):
        """An explicit file-level False beats a present API key."""
        (tmp_path / ".attune.json").write_text('{"show_cost_metrics": false}')
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "FAKE_key_NOT_REAL")
        assert resolve_show_cost() is False

    def test_config_load_failure_falls_back_to_env(self, monkeypatch):
        """A crashing load_config degrades to the env auto default."""

        def _boom(*args, **kwargs):
            raise ValueError("malformed user config")

        monkeypatch.setitem(resolve_show_cost.__globals__, "load_config", _boom)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "FAKE_key_NOT_REAL")
        assert resolve_show_cost() is True
        monkeypatch.delenv("ANTHROPIC_API_KEY")
        assert resolve_show_cost() is False
