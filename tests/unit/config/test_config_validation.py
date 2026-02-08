"""Tests for configuration validation.

Tests ConfigValidator, ValidationError, and the validate_config convenience
function against all configuration sections (auth, routing, workflows,
analysis, persistence, telemetry, environment).
"""

import pytest

from attune.config.sections.analysis import AnalysisConfig
from attune.config.sections.auth import AuthConfig
from attune.config.sections.environment import EnvironmentConfig
from attune.config.sections.persistence import PersistenceConfig
from attune.config.sections.routing import RoutingConfig
from attune.config.sections.telemetry import TelemetryConfig
from attune.config.sections.workflows import WorkflowConfig
from attune.config.unified import UnifiedConfig
from attune.config.validation import ConfigValidator, ValidationError, validate_config


class TestValidationError:
    """Tests for the ValidationError dataclass."""

    def test_creation_with_defaults(self):
        """Test creating a ValidationError with default severity."""
        err = ValidationError(key="auth.strategy", message="Invalid strategy")
        assert err.key == "auth.strategy"
        assert err.message == "Invalid strategy"
        assert err.severity == "error"

    def test_creation_with_warning_severity(self):
        """Test creating a ValidationError with warning severity."""
        err = ValidationError(
            key="auth.api_key_env",
            message="Environment variable not set",
            severity="warning",
        )
        assert err.severity == "warning"

    def test_str_error_severity(self):
        """Test __str__ formats error severity correctly."""
        err = ValidationError(key="routing.default_tier", message="Invalid tier")
        assert str(err) == "[ERROR] routing.default_tier: Invalid tier"

    def test_str_warning_severity(self):
        """Test __str__ formats warning severity correctly."""
        err = ValidationError(
            key="auth.api_key_env",
            message="Not set",
            severity="warning",
        )
        assert str(err) == "[WARNING] auth.api_key_env: Not set"


class TestConfigValidatorDefaultConfig:
    """Tests that a default UnifiedConfig passes validation with no errors."""

    def test_default_config_valid_with_subscription_strategy(self, monkeypatch):
        """Test that default config with subscription strategy produces no errors."""
        config = UnifiedConfig()
        config.auth.strategy = "subscription"
        validator = ConfigValidator()
        errors = validator.validate(config)
        assert errors == []

    def test_default_config_with_hybrid_warns_about_api_key(self, monkeypatch):
        """Test that default hybrid config warns when ANTHROPIC_API_KEY is unset."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config = UnifiedConfig()  # default strategy is "hybrid"
        validator = ConfigValidator()
        errors = validator.validate(config)
        # Should have exactly one warning about the missing API key
        assert len(errors) == 1
        assert errors[0].key == "auth.api_key_env"
        assert errors[0].severity == "warning"

    def test_default_config_no_errors_when_api_key_set(self, monkeypatch):
        """Test that default hybrid config is fully valid when API key env is set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        config = UnifiedConfig()
        validator = ConfigValidator()
        errors = validator.validate(config)
        assert errors == []


class TestAuthValidation:
    """Tests for auth section validation rules."""

    def test_invalid_strategy(self):
        """Test that an invalid strategy value produces an error."""
        config = UnifiedConfig()
        config.auth.strategy = "invalid"
        validator = ConfigValidator()
        errors = validator.validate_section(config.auth, "auth")
        strategy_errors = [e for e in errors if e.key == "auth.strategy"]
        assert len(strategy_errors) == 1
        assert "Invalid strategy" in strategy_errors[0].message

    def test_api_strategy_warns_when_env_not_set(self, monkeypatch):
        """Test that API strategy warns when the API key env var is missing."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        auth = AuthConfig(strategy="api")
        validator = ConfigValidator()
        errors = validator.validate_section(auth, "auth")
        api_key_errors = [e for e in errors if e.key == "auth.api_key_env"]
        assert len(api_key_errors) == 1
        assert api_key_errors[0].severity == "warning"

    def test_api_strategy_no_warning_when_env_set(self, monkeypatch):
        """Test that API strategy produces no warning when the env var is set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        auth = AuthConfig(strategy="api")
        validator = ConfigValidator()
        errors = validator.validate_section(auth, "auth")
        api_key_errors = [e for e in errors if e.key == "auth.api_key_env"]
        assert len(api_key_errors) == 0

    def test_subscription_strategy_no_api_key_warning(self, monkeypatch):
        """Test that subscription strategy never warns about missing API key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        auth = AuthConfig(strategy="subscription")
        validator = ConfigValidator()
        errors = validator.validate_section(auth, "auth")
        api_key_errors = [e for e in errors if e.key == "auth.api_key_env"]
        assert len(api_key_errors) == 0

    def test_small_module_threshold_zero(self):
        """Test that small_module_threshold <= 0 is invalid."""
        auth = AuthConfig(strategy="subscription", small_module_threshold=0)
        validator = ConfigValidator()
        errors = validator.validate_section(auth, "auth")
        matched = [e for e in errors if e.key == "auth.small_module_threshold"]
        assert len(matched) == 1

    def test_small_module_threshold_negative(self):
        """Test that negative small_module_threshold is invalid."""
        auth = AuthConfig(strategy="subscription", small_module_threshold=-1)
        validator = ConfigValidator()
        errors = validator.validate_section(auth, "auth")
        matched = [e for e in errors if e.key == "auth.small_module_threshold"]
        assert len(matched) == 1

    def test_medium_must_exceed_small_threshold(self):
        """Test that medium_module_threshold must be greater than small_module_threshold."""
        auth = AuthConfig(
            strategy="subscription",
            small_module_threshold=500,
            medium_module_threshold=500,
        )
        validator = ConfigValidator()
        errors = validator.validate_section(auth, "auth")
        matched = [e for e in errors if e.key == "auth.medium_module_threshold"]
        assert len(matched) == 1
        assert "greater than small_module_threshold" in matched[0].message

    def test_subscription_daily_limit_zero(self):
        """Test that subscription_daily_limit <= 0 is invalid."""
        auth = AuthConfig(strategy="subscription", subscription_daily_limit=0)
        validator = ConfigValidator()
        errors = validator.validate_section(auth, "auth")
        matched = [e for e in errors if e.key == "auth.subscription_daily_limit"]
        assert len(matched) == 1

    def test_api_daily_limit_zero(self):
        """Test that api_daily_limit <= 0 is invalid."""
        auth = AuthConfig(strategy="subscription", api_daily_limit=0)
        validator = ConfigValidator()
        errors = validator.validate_section(auth, "auth")
        matched = [e for e in errors if e.key == "auth.api_daily_limit"]
        assert len(matched) == 1


class TestRoutingValidation:
    """Tests for routing section validation rules."""

    def test_invalid_default_tier(self):
        """Test that an invalid default_tier produces an error."""
        routing = RoutingConfig()
        routing.default_tier = "ultra"
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        matched = [e for e in errors if e.key == "routing.default_tier"]
        assert len(matched) == 1
        assert "Invalid tier" in matched[0].message

    def test_empty_cheap_model(self):
        """Test that an empty cheap_model is invalid."""
        routing = RoutingConfig(cheap_model="")
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        matched = [e for e in errors if e.key == "routing.cheap_model"]
        assert len(matched) == 1

    def test_empty_capable_model(self):
        """Test that an empty capable_model is invalid."""
        routing = RoutingConfig(capable_model="")
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        matched = [e for e in errors if e.key == "routing.capable_model"]
        assert len(matched) == 1

    def test_empty_premium_model(self):
        """Test that an empty premium_model is invalid."""
        routing = RoutingConfig(premium_model="")
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        matched = [e for e in errors if e.key == "routing.premium_model"]
        assert len(matched) == 1

    def test_max_tokens_zero(self):
        """Test that zero max_tokens values produce errors."""
        routing = RoutingConfig(
            max_tokens_cheap=0,
            max_tokens_capable=0,
            max_tokens_premium=0,
        )
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        token_errors = [e for e in errors if "max_tokens" in e.key]
        assert len(token_errors) == 3

    def test_max_tokens_negative(self):
        """Test that negative max_tokens values produce errors."""
        routing = RoutingConfig(max_tokens_cheap=-1)
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        matched = [e for e in errors if e.key == "routing.max_tokens_cheap"]
        assert len(matched) == 1

    def test_temperature_below_range(self):
        """Test that temperature below 0.0 is invalid."""
        routing = RoutingConfig(temperature_default=-0.1)
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        matched = [e for e in errors if e.key == "routing.temperature_default"]
        assert len(matched) == 1

    def test_temperature_above_range(self):
        """Test that temperature above 2.0 is invalid."""
        routing = RoutingConfig(temperature_default=2.1)
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        matched = [e for e in errors if e.key == "routing.temperature_default"]
        assert len(matched) == 1

    def test_temperature_boundary_valid(self):
        """Test that temperature at boundaries (0.0 and 2.0) is valid."""
        validator = ConfigValidator()
        for temp in [0.0, 2.0]:
            routing = RoutingConfig(temperature_default=temp)
            errors = validator.validate_section(routing, "routing")
            temp_errors = [e for e in errors if e.key == "routing.temperature_default"]
            assert len(temp_errors) == 0, f"temperature={temp} should be valid"

    def test_max_retries_negative(self):
        """Test that negative max_retries is invalid."""
        routing = RoutingConfig(max_retries=-1)
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        matched = [e for e in errors if e.key == "routing.max_retries"]
        assert len(matched) == 1

    def test_max_retries_zero_is_valid(self):
        """Test that max_retries=0 is valid (retries disabled)."""
        routing = RoutingConfig(max_retries=0)
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        matched = [e for e in errors if e.key == "routing.max_retries"]
        assert len(matched) == 0

    def test_valid_routing_config(self):
        """Test that a default RoutingConfig produces no errors."""
        routing = RoutingConfig()
        validator = ConfigValidator()
        errors = validator.validate_section(routing, "routing")
        assert errors == []


class TestWorkflowsValidation:
    """Tests for workflows section validation rules."""

    def test_timeout_zero(self):
        """Test that timeout_seconds <= 0 is invalid."""
        workflows = WorkflowConfig(timeout_seconds=0)
        validator = ConfigValidator()
        errors = validator.validate_section(workflows, "workflows")
        matched = [e for e in errors if e.key == "workflows.timeout_seconds"]
        assert len(matched) == 1

    def test_timeout_negative(self):
        """Test that negative timeout_seconds is invalid."""
        workflows = WorkflowConfig(timeout_seconds=-10)
        validator = ConfigValidator()
        errors = validator.validate_section(workflows, "workflows")
        matched = [e for e in errors if e.key == "workflows.timeout_seconds"]
        assert len(matched) == 1

    def test_valid_workflows_config(self):
        """Test that a default WorkflowConfig produces no errors."""
        workflows = WorkflowConfig()
        validator = ConfigValidator()
        errors = validator.validate_section(workflows, "workflows")
        assert errors == []


class TestAnalysisValidation:
    """Tests for analysis section validation rules."""

    def test_complexity_threshold_zero(self):
        """Test that complexity_threshold <= 0 is invalid."""
        analysis = AnalysisConfig(complexity_threshold=0)
        validator = ConfigValidator()
        errors = validator.validate_section(analysis, "analysis")
        matched = [e for e in errors if e.key == "analysis.complexity_threshold"]
        assert len(matched) == 1

    def test_max_file_size_zero(self):
        """Test that max_file_size_kb <= 0 is invalid."""
        analysis = AnalysisConfig(max_file_size_kb=0)
        validator = ConfigValidator()
        errors = validator.validate_section(analysis, "analysis")
        matched = [e for e in errors if e.key == "analysis.max_file_size_kb"]
        assert len(matched) == 1

    def test_coverage_target_below_range(self):
        """Test that test_coverage_target below 0 is invalid."""
        analysis = AnalysisConfig(test_coverage_target=-1)
        validator = ConfigValidator()
        errors = validator.validate_section(analysis, "analysis")
        matched = [e for e in errors if e.key == "analysis.test_coverage_target"]
        assert len(matched) == 1

    def test_coverage_target_above_range(self):
        """Test that test_coverage_target above 100 is invalid."""
        analysis = AnalysisConfig(test_coverage_target=101)
        validator = ConfigValidator()
        errors = validator.validate_section(analysis, "analysis")
        matched = [e for e in errors if e.key == "analysis.test_coverage_target"]
        assert len(matched) == 1

    def test_coverage_target_boundary_valid(self):
        """Test that coverage target at boundaries (0 and 100) is valid."""
        validator = ConfigValidator()
        for target in [0, 100]:
            analysis = AnalysisConfig(test_coverage_target=target)
            errors = validator.validate_section(analysis, "analysis")
            cov_errors = [e for e in errors if e.key == "analysis.test_coverage_target"]
            assert len(cov_errors) == 0, f"test_coverage_target={target} should be valid"

    def test_max_function_length_zero(self):
        """Test that max_function_length <= 0 is invalid."""
        analysis = AnalysisConfig(max_function_length=0)
        validator = ConfigValidator()
        errors = validator.validate_section(analysis, "analysis")
        matched = [e for e in errors if e.key == "analysis.max_function_length"]
        assert len(matched) == 1

    def test_valid_analysis_config(self):
        """Test that a default AnalysisConfig produces no errors."""
        analysis = AnalysisConfig()
        validator = ConfigValidator()
        errors = validator.validate_section(analysis, "analysis")
        assert errors == []


class TestPersistenceValidation:
    """Tests for persistence section validation rules."""

    def test_invalid_memory_backend(self):
        """Test that an invalid memory_backend produces an error."""
        persistence = PersistenceConfig()
        persistence.memory_backend = "mysql"
        validator = ConfigValidator()
        errors = validator.validate_section(persistence, "persistence")
        matched = [e for e in errors if e.key == "persistence.memory_backend"]
        assert len(matched) == 1
        assert "Invalid backend" in matched[0].message

    def test_cache_ttl_zero(self):
        """Test that cache_ttl_hours <= 0 is invalid."""
        persistence = PersistenceConfig(cache_ttl_hours=0)
        validator = ConfigValidator()
        errors = validator.validate_section(persistence, "persistence")
        matched = [e for e in errors if e.key == "persistence.cache_ttl_hours"]
        assert len(matched) == 1

    def test_max_history_entries_zero(self):
        """Test that max_history_entries <= 0 is invalid."""
        persistence = PersistenceConfig(max_history_entries=0)
        validator = ConfigValidator()
        errors = validator.validate_section(persistence, "persistence")
        matched = [e for e in errors if e.key == "persistence.max_history_entries"]
        assert len(matched) == 1

    def test_save_interval_zero(self):
        """Test that save_interval_seconds <= 0 is invalid."""
        persistence = PersistenceConfig(save_interval_seconds=0)
        validator = ConfigValidator()
        errors = validator.validate_section(persistence, "persistence")
        matched = [e for e in errors if e.key == "persistence.save_interval_seconds"]
        assert len(matched) == 1

    def test_backup_count_negative(self):
        """Test that backup_count < 0 is invalid."""
        persistence = PersistenceConfig(backup_count=-1)
        validator = ConfigValidator()
        errors = validator.validate_section(persistence, "persistence")
        matched = [e for e in errors if e.key == "persistence.backup_count"]
        assert len(matched) == 1

    def test_backup_count_zero_is_valid(self):
        """Test that backup_count=0 is valid (backups disabled)."""
        persistence = PersistenceConfig(backup_count=0)
        validator = ConfigValidator()
        errors = validator.validate_section(persistence, "persistence")
        matched = [e for e in errors if e.key == "persistence.backup_count"]
        assert len(matched) == 0

    def test_invalid_export_format(self):
        """Test that an invalid export_format produces an error."""
        persistence = PersistenceConfig()
        persistence.export_format = "xml"
        validator = ConfigValidator()
        errors = validator.validate_section(persistence, "persistence")
        matched = [e for e in errors if e.key == "persistence.export_format"]
        assert len(matched) == 1

    def test_invalid_import_merge_strategy(self):
        """Test that an invalid import_merge_strategy produces an error."""
        persistence = PersistenceConfig()
        persistence.import_merge_strategy = "replace"
        validator = ConfigValidator()
        errors = validator.validate_section(persistence, "persistence")
        matched = [e for e in errors if e.key == "persistence.import_merge_strategy"]
        assert len(matched) == 1

    def test_valid_persistence_config(self):
        """Test that a default PersistenceConfig produces no errors."""
        persistence = PersistenceConfig()
        validator = ConfigValidator()
        errors = validator.validate_section(persistence, "persistence")
        assert errors == []


class TestTelemetryValidation:
    """Tests for telemetry section validation rules."""

    def test_retention_days_zero(self):
        """Test that retention_days <= 0 is invalid."""
        telemetry = TelemetryConfig(retention_days=0)
        validator = ConfigValidator()
        errors = validator.validate_section(telemetry, "telemetry")
        matched = [e for e in errors if e.key == "telemetry.retention_days"]
        assert len(matched) == 1

    def test_retention_days_negative(self):
        """Test that negative retention_days is invalid."""
        telemetry = TelemetryConfig(retention_days=-5)
        validator = ConfigValidator()
        errors = validator.validate_section(telemetry, "telemetry")
        matched = [e for e in errors if e.key == "telemetry.retention_days"]
        assert len(matched) == 1

    def test_valid_telemetry_config(self):
        """Test that a default TelemetryConfig produces no errors."""
        telemetry = TelemetryConfig()
        validator = ConfigValidator()
        errors = validator.validate_section(telemetry, "telemetry")
        assert errors == []


class TestEnvironmentValidation:
    """Tests for environment section validation rules."""

    def test_invalid_log_level(self):
        """Test that an invalid log_level produces an error."""
        env = EnvironmentConfig()
        env.log_level = "VERBOSE"
        validator = ConfigValidator()
        errors = validator.validate_section(env, "environment")
        matched = [e for e in errors if e.key == "environment.log_level"]
        assert len(matched) == 1
        assert "Invalid log level" in matched[0].message

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR"])
    def test_valid_log_levels(self, level: str):
        """Test that all valid log levels produce no errors."""
        env = EnvironmentConfig(log_level=level)
        validator = ConfigValidator()
        errors = validator.validate_section(env, "environment")
        assert errors == []


class TestValidateSection:
    """Tests for the validate_section dispatch method."""

    def test_unknown_section_returns_error(self):
        """Test that an unknown section name returns an error."""
        validator = ConfigValidator()
        errors = validator.validate_section(object(), "nonexistent")
        assert len(errors) == 1
        assert errors[0].key == "nonexistent"
        assert "Unknown section" in errors[0].message

    @pytest.mark.parametrize(
        "section_name,section_factory",
        [
            ("auth", lambda: AuthConfig(strategy="subscription")),
            ("routing", RoutingConfig),
            ("workflows", WorkflowConfig),
            ("analysis", AnalysisConfig),
            ("persistence", PersistenceConfig),
            ("telemetry", TelemetryConfig),
            ("environment", EnvironmentConfig),
        ],
    )
    def test_dispatch_to_known_sections(self, section_name: str, section_factory):
        """Test that validate_section dispatches correctly for all known sections."""
        section = section_factory()
        validator = ConfigValidator()
        errors = validator.validate_section(section, section_name)
        # Default configs should produce no errors
        assert errors == []


class TestValidateConfigConvenience:
    """Tests for the validate_config convenience function."""

    def test_returns_empty_for_valid_config(self, monkeypatch):
        """Test that validate_config returns empty list for a valid config."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        config = UnifiedConfig()
        errors = validate_config(config)
        assert errors == []

    def test_returns_errors_for_invalid_config(self):
        """Test that validate_config returns errors for an invalid config."""
        config = UnifiedConfig()
        config.auth.strategy = "invalid"
        config.routing.default_tier = "ultra"
        errors = validate_config(config)
        keys = {e.key for e in errors}
        assert "auth.strategy" in keys
        assert "routing.default_tier" in keys

    def test_aggregates_errors_across_sections(self):
        """Test that validate_config collects errors from multiple sections."""
        config = UnifiedConfig()
        config.auth.strategy = "subscription"
        config.workflows.timeout_seconds = -1
        config.telemetry.retention_days = 0
        config.environment.log_level = "TRACE"
        errors = validate_config(config)
        keys = {e.key for e in errors}
        assert "workflows.timeout_seconds" in keys
        assert "telemetry.retention_days" in keys
        assert "environment.log_level" in keys
