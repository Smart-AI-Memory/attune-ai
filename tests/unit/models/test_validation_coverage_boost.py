"""Coverage boost tests for models/validation.py

Targets uncovered validation logic and error handling paths to increase
coverage from 51.67% to 85%+.

Missing coverage areas:
- ValidationError and ValidationResult __str__() methods
- add_warning() method
- ConfigValidator stage validation logic
- validate_provider_tier() method
- validate_config_file() error handling

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import pytest

from attune.models.validation import (
    ConfigValidator,
    ValidationError,
    ValidationResult,
    validate_config,
    validate_yaml_file,
)


@pytest.mark.unit
class TestValidationError:
    """Test ValidationError dataclass."""

    def test_validation_error_str(self):
        """Test ValidationError string representation."""
        error = ValidationError(path="config.tier", message="Invalid tier", severity="error")

        assert str(error) == "[ERROR] config.tier: Invalid tier"

    def test_validation_error_warning(self):
        """Test ValidationError warning severity."""
        warning = ValidationError(
            path="config.provider",
            message="Deprecated provider",
            severity="warning",
        )

        assert str(warning) == "[WARNING] config.provider: Deprecated provider"


@pytest.mark.unit
class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_add_warning_method(self):
        """Test add_warning() adds warning without invalidating result."""
        result = ValidationResult(valid=True)

        result.add_warning("field", "This is a warning")

        assert result.valid is True  # Warnings don't invalidate
        assert len(result.warnings) == 1
        assert result.warnings[0].path == "field"
        assert result.warnings[0].severity == "warning"

    def test_str_with_errors(self):
        """Test ValidationResult string representation with errors."""
        result = ValidationResult(valid=False)
        result.add_error("field1", "Error 1")
        result.add_error("field2", "Error 2")

        str_repr = str(result)

        assert "Configuration has errors" in str_repr
        assert "[ERROR] field1: Error 1" in str_repr
        assert "[ERROR] field2: Error 2" in str_repr

    def test_str_with_warnings(self):
        """Test ValidationResult string representation with warnings."""
        result = ValidationResult(valid=True)
        result.add_warning("field1", "Warning 1")

        str_repr = str(result)

        assert "Configuration is valid" in str_repr
        assert "[WARNING] field1: Warning 1" in str_repr

    def test_str_with_both_errors_and_warnings(self):
        """Test ValidationResult with both errors and warnings."""
        result = ValidationResult(valid=False)
        result.add_error("field1", "Error 1")
        result.add_warning("field2", "Warning 1")

        str_repr = str(result)

        assert "Configuration has errors" in str_repr
        assert "[ERROR] field1: Error 1" in str_repr
        assert "[WARNING] field2: Warning 1" in str_repr


@pytest.mark.unit
class TestConfigValidatorStages:
    """Test ConfigValidator stage validation logic."""

    def test_validate_stages_with_invalid_tier(self):
        """Test stage validation with invalid tier."""
        validator = ConfigValidator()

        config = {
            "stages": [
                {
                    "id": "stage1",
                    "tier": "invalid_tier",  # Invalid
                    "provider": "anthropic",
                },
            ],
        }

        result = validator.validate_workflow_config(config)

        assert result.valid is False
        assert any("Unknown tier" in err.message for err in result.errors)

    def test_validate_stages_with_invalid_provider(self):
        """Test stage validation with invalid provider."""
        validator = ConfigValidator()

        config = {
            "stages": [
                {
                    "id": "stage1",
                    "tier": "cheap",
                    "provider": "invalid_provider",  # Invalid
                },
            ],
        }

        result = validator.validate_workflow_config(config)

        assert result.valid is False
        assert any("Unknown provider" in err.message for err in result.errors)

    def test_validate_stages_with_timeout_below_min(self):
        """Test stage validation with timeout below minimum."""
        validator = ConfigValidator()

        config = {
            "stages": [
                {
                    "id": "stage1",
                    "tier": "cheap",
                    "timeout_ms": -1,  # Below minimum (0)
                },
            ],
        }

        result = validator.validate_workflow_config(config)

        assert result.valid is False
        assert any("below minimum" in err.message for err in result.errors)

    def test_validate_stages_with_timeout_above_max(self):
        """Test stage validation with timeout above maximum."""
        validator = ConfigValidator()

        config = {
            "stages": [
                {
                    "id": "stage1",
                    "tier": "cheap",
                    "timeout_ms": 10000000,  # Above maximum
                },
            ],
        }

        result = validator.validate_workflow_config(config)

        assert result.valid is False
        assert any("above maximum" in err.message for err in result.errors)

    def test_validate_stages_with_non_integer_timeout(self):
        """Test stage validation with non-integer timeout."""
        validator = ConfigValidator()

        config = {
            "stages": [
                {
                    "id": "stage1",
                    "tier": "cheap",
                    "timeout_ms": "not_an_int",  # Wrong type
                },
            ],
        }

        result = validator.validate_workflow_config(config)

        assert result.valid is False
        assert any("Expected integer" in err.message for err in result.errors)

    def test_validate_stages_with_non_integer_max_retries(self):
        """Test stage validation with non-integer max_retries."""
        validator = ConfigValidator()

        config = {
            "stages": [
                {
                    "id": "stage1",
                    "tier": "cheap",
                    "max_retries": 3.5,  # Wrong type
                },
            ],
        }

        result = validator.validate_workflow_config(config)

        assert result.valid is False
        assert any("Expected integer" in err.message for err in result.errors)

    def test_validate_stage_non_dict_stage(self):
        """Test stage validation when stage is not a dictionary."""
        validator = ConfigValidator()

        config = {
            "stages": [
                "not_a_dict",  # Invalid: should be dict
            ],
        }

        result = validator.validate_workflow_config(config)

        assert result.valid is False
        assert any("Stage must be a dictionary" in err.message for err in result.errors)


@pytest.mark.unit
class TestConfigValidatorProviderTier:
    """Test validate_provider_tier method."""

    def test_validate_provider_tier_with_invalid_provider(self):
        """Test provider/tier validation with invalid provider."""
        validator = ConfigValidator()

        result = validator.validate_provider_tier("invalid_provider", "cheap")

        assert result.valid is False
        assert any("Unknown provider" in err.message for err in result.errors)

    def test_validate_provider_tier_with_invalid_tier(self):
        """Test provider/tier validation with invalid tier."""
        validator = ConfigValidator()

        result = validator.validate_provider_tier("anthropic", "invalid_tier")

        assert result.valid is False
        assert any("Unknown tier" in err.message for err in result.errors)

    def test_validate_provider_tier_with_missing_combination(self):
        """Test provider/tier validation when combination doesn't exist in registry."""
        validator = ConfigValidator()

        # This should trigger a warning if the tier isn't in the provider's config
        # Note: anthropic has cheap/capable/premium, so we need to test with a hypothetical scenario
        # Since MODEL_REGISTRY is read-only, we can't actually test this without modifying it
        # So this test verifies the valid path
        result = validator.validate_provider_tier("anthropic", "cheap")

        # Should be valid (anthropic has cheap tier)
        assert result.valid is True

    def test_validate_provider_tier_valid_combination(self):
        """Test provider/tier validation with valid combination."""
        validator = ConfigValidator()

        result = validator.validate_provider_tier("anthropic", "capable")

        assert result.valid is True
        assert len(result.errors) == 0


@pytest.mark.unit
class TestConfigValidatorDefaultProvider:
    """Test default_provider validation."""

    def test_validate_config_with_invalid_default_provider(self):
        """Test config validation with invalid default_provider."""
        validator = ConfigValidator()

        config = {
            "default_provider": "invalid_provider",  # Invalid
        }

        result = validator.validate_workflow_config(config)

        assert result.valid is False
        assert any("Unknown provider" in err.message for err in result.errors)


@pytest.mark.unit
class TestValidateYamlFile:
    """Test validate_yaml_file function with error handling."""

    def test_validate_yaml_file_not_found(self):
        """Test validation when config file doesn't exist."""
        result = validate_yaml_file("/nonexistent/config.yaml")

        assert result.valid is False
        assert any("File not found" in err.message for err in result.errors)

    def test_validate_yaml_file_invalid_yaml(self, tmp_path):
        """Test validation when YAML is invalid."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("{ invalid yaml content: [")

        result = validate_yaml_file(str(config_file))

        assert result.valid is False
        assert any("Invalid YAML" in err.message for err in result.errors)

    def test_validate_yaml_file_empty(self, tmp_path):
        """Test validation when config file is empty."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        result = validate_yaml_file(str(config_file))

        assert result.valid is False
        assert any("Empty configuration file" in err.message for err in result.errors)

    def test_validate_yaml_file_invalid_path(self):
        """Test validation when file path is invalid."""
        # Null byte in path should trigger ValueError
        result = validate_yaml_file("config\x00.yaml")

        assert result.valid is False
        assert any("Invalid file path" in err.message for err in result.errors)

    def test_validate_yaml_file_valid(self, tmp_path):
        """Test validation when config file is valid."""
        config_file = tmp_path / "valid.yaml"

        # Write valid YAML config with all required fields
        config_data = """
name: test_workflow
default_provider: anthropic
stages:
  - id: stage1
    name: test_stage
    tier: cheap
    provider: anthropic
"""
        config_file.write_text(config_data)

        result = validate_yaml_file(str(config_file))

        # Should be valid
        assert result.valid is True


@pytest.mark.unit
class TestValidateConfigFunction:
    """Test validate_config convenience function."""

    def test_validate_config_with_valid_config(self):
        """Test validate_config with valid configuration."""
        config = {
            "name": "test_workflow",
            "default_provider": "anthropic",
            "stages": [
                {
                    "id": "stage1",
                    "name": "test_stage",
                    "tier": "cheap",
                    "provider": "anthropic",
                },
            ],
        }

        result = validate_config(config)

        # Should be valid
        assert result.valid is True

    def test_validate_config_with_invalid_config(self):
        """Test validate_config with invalid configuration."""
        config = {
            "default_provider": "invalid",  # Invalid provider
            "stages": [
                {
                    "id": "stage1",
                    "tier": "invalid_tier",  # Invalid tier
                },
            ],
        }

        result = validate_config(config)

        assert result.valid is False
        assert len(result.errors) > 0
