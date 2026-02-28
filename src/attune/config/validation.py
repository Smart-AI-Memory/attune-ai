"""Configuration validation for Attune AI.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

from attune.config.unified import UnifiedConfig

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a configuration validation error.

    Attributes:
        key: The configuration key that failed validation.
        message: Human-readable error message.
        severity: Error severity ('error' or 'warning').

    """

    key: str
    message: str
    severity: str = "error"  # 'error' or 'warning'

    def __str__(self) -> str:
        """Return string representation."""
        return f"[{self.severity.upper()}] {self.key}: {self.message}"


class ConfigValidator:
    """Validate Attune AI configuration.

    Performs validation checks on configuration values to ensure
    they are valid and consistent.
    """

    def validate(self, config: UnifiedConfig) -> list[ValidationError]:
        """Validate the entire configuration.

        Args:
            config: Configuration to validate.

        Returns:
            List of validation errors (empty if valid).

        """
        errors: list[ValidationError] = []

        errors.extend(self._validate_auth(config))
        errors.extend(self._validate_routing(config))
        errors.extend(self._validate_workflows(config))
        errors.extend(self._validate_analysis(config))
        errors.extend(self._validate_persistence(config))
        errors.extend(self._validate_telemetry(config))
        errors.extend(self._validate_environment(config))

        return errors

    def validate_section(self, section: Any, section_name: str) -> list[ValidationError]:
        """Validate a specific configuration section.

        Args:
            section: The section dataclass to validate.
            section_name: Name of the section for error messages.

        Returns:
            List of validation errors.

        """
        # Dispatch to appropriate validator
        validators = {
            "auth": lambda s: self._validate_auth_section(s),
            "routing": lambda s: self._validate_routing_section(s),
            "workflows": lambda s: self._validate_workflows_section(s),
            "analysis": lambda s: self._validate_analysis_section(s),
            "persistence": lambda s: self._validate_persistence_section(s),
            "telemetry": lambda s: self._validate_telemetry_section(s),
            "environment": lambda s: self._validate_environment_section(s),
        }

        validator = validators.get(section_name)
        if validator:
            return validator(section)

        return [ValidationError(section_name, f"Unknown section: {section_name}")]

    def _validate_auth(self, config: UnifiedConfig) -> list[ValidationError]:
        """Validate authentication configuration."""
        return self._validate_auth_section(config.auth)

    def _validate_auth_section(self, auth: Any) -> list[ValidationError]:
        """Validate auth section."""
        errors: list[ValidationError] = []

        # Check strategy is valid
        valid_strategies = {"subscription", "api", "hybrid"}
        if auth.strategy not in valid_strategies:
            errors.append(
                ValidationError(
                    "auth.strategy",
                    f"Invalid strategy '{auth.strategy}'. Must be one of: {valid_strategies}",
                ),
            )

        # Warn if API strategy but no API key env var set
        if auth.strategy in ("api", "hybrid"):
            if not os.environ.get(auth.api_key_env):
                errors.append(
                    ValidationError(
                        "auth.api_key_env",
                        f"Environment variable '{auth.api_key_env}' not set",
                        severity="warning",
                    ),
                )

        # Check thresholds are positive
        if auth.small_module_threshold <= 0:
            errors.append(
                ValidationError(
                    "auth.small_module_threshold",
                    "Must be a positive integer",
                ),
            )

        if auth.medium_module_threshold <= auth.small_module_threshold:
            errors.append(
                ValidationError(
                    "auth.medium_module_threshold",
                    "Must be greater than small_module_threshold",
                ),
            )

        # Check daily limits are positive
        if auth.subscription_daily_limit <= 0:
            errors.append(
                ValidationError(
                    "auth.subscription_daily_limit",
                    "Must be a positive integer",
                ),
            )

        if auth.api_daily_limit <= 0:
            errors.append(
                ValidationError(
                    "auth.api_daily_limit",
                    "Must be a positive integer",
                ),
            )

        return errors

    def _validate_routing(self, config: UnifiedConfig) -> list[ValidationError]:
        """Validate routing configuration."""
        return self._validate_routing_section(config.routing)

    def _validate_routing_section(self, routing: Any) -> list[ValidationError]:
        """Validate routing section."""
        errors: list[ValidationError] = []

        # Check tier is valid
        valid_tiers = {"cheap", "capable", "premium"}
        if routing.default_tier not in valid_tiers:
            errors.append(
                ValidationError(
                    "routing.default_tier",
                    f"Invalid tier '{routing.default_tier}'. Must be one of: {valid_tiers}",
                ),
            )

        # Check model IDs are non-empty
        if not routing.cheap_model:
            errors.append(ValidationError("routing.cheap_model", "Model ID cannot be empty"))

        if not routing.capable_model:
            errors.append(ValidationError("routing.capable_model", "Model ID cannot be empty"))

        if not routing.premium_model:
            errors.append(ValidationError("routing.premium_model", "Model ID cannot be empty"))

        # Check max_tokens are positive
        for tier in ["cheap", "capable", "premium"]:
            max_tokens = getattr(routing, f"max_tokens_{tier}")
            if max_tokens <= 0:
                errors.append(
                    ValidationError(
                        f"routing.max_tokens_{tier}",
                        "Must be a positive integer",
                    ),
                )

        # Check temperature is in valid range
        if not 0.0 <= routing.temperature_default <= 2.0:
            errors.append(
                ValidationError(
                    "routing.temperature_default",
                    "Must be between 0.0 and 2.0",
                ),
            )

        # Check max_retries is positive
        if routing.max_retries < 0:
            errors.append(
                ValidationError(
                    "routing.max_retries",
                    "Must be a non-negative integer",
                ),
            )

        return errors

    def _validate_workflows(self, config: UnifiedConfig) -> list[ValidationError]:
        """Validate workflows configuration."""
        return self._validate_workflows_section(config.workflows)

    def _validate_workflows_section(self, workflows: Any) -> list[ValidationError]:
        """Validate workflows section."""
        errors: list[ValidationError] = []

        # Check timeout is positive
        if workflows.timeout_seconds <= 0:
            errors.append(
                ValidationError(
                    "workflows.timeout_seconds",
                    "Must be a positive integer",
                ),
            )

        return errors

    def _validate_analysis(self, config: UnifiedConfig) -> list[ValidationError]:
        """Validate analysis configuration."""
        return self._validate_analysis_section(config.analysis)

    def _validate_analysis_section(self, analysis: Any) -> list[ValidationError]:
        """Validate analysis section."""
        errors: list[ValidationError] = []

        # Check complexity threshold
        if analysis.complexity_threshold <= 0:
            errors.append(
                ValidationError(
                    "analysis.complexity_threshold",
                    "Must be a positive integer",
                ),
            )

        # Check max file size
        if analysis.max_file_size_kb <= 0:
            errors.append(
                ValidationError(
                    "analysis.max_file_size_kb",
                    "Must be a positive integer",
                ),
            )

        # Check test coverage target
        if not 0 <= analysis.test_coverage_target <= 100:
            errors.append(
                ValidationError(
                    "analysis.test_coverage_target",
                    "Must be between 0 and 100",
                ),
            )

        # Check max function length
        if analysis.max_function_length <= 0:
            errors.append(
                ValidationError(
                    "analysis.max_function_length",
                    "Must be a positive integer",
                ),
            )

        return errors

    def _validate_persistence(self, config: UnifiedConfig) -> list[ValidationError]:
        """Validate persistence configuration."""
        return self._validate_persistence_section(config.persistence)

    def _validate_persistence_section(self, persistence: Any) -> list[ValidationError]:
        """Validate persistence section."""
        errors: list[ValidationError] = []

        # Check backend is valid
        valid_backends = {"json", "sqlite", "redis"}
        if persistence.memory_backend not in valid_backends:
            errors.append(
                ValidationError(
                    "persistence.memory_backend",
                    f"Invalid backend '{persistence.memory_backend}'. "
                    f"Must be one of: {valid_backends}",
                ),
            )

        # Check cache TTL is positive
        if persistence.cache_ttl_hours <= 0:
            errors.append(
                ValidationError(
                    "persistence.cache_ttl_hours",
                    "Must be a positive integer",
                ),
            )

        # Check max history entries
        if persistence.max_history_entries <= 0:
            errors.append(
                ValidationError(
                    "persistence.max_history_entries",
                    "Must be a positive integer",
                ),
            )

        # Check save interval
        if persistence.save_interval_seconds <= 0:
            errors.append(
                ValidationError(
                    "persistence.save_interval_seconds",
                    "Must be a positive integer",
                ),
            )

        # Check backup count
        if persistence.backup_count < 0:
            errors.append(
                ValidationError(
                    "persistence.backup_count",
                    "Must be a non-negative integer",
                ),
            )

        # Check export format
        valid_formats = {"json", "yaml"}
        if persistence.export_format not in valid_formats:
            errors.append(
                ValidationError(
                    "persistence.export_format",
                    f"Invalid format '{persistence.export_format}'. "
                    f"Must be one of: {valid_formats}",
                ),
            )

        # Check merge strategy
        valid_strategies = {"overwrite", "merge"}
        if persistence.import_merge_strategy not in valid_strategies:
            errors.append(
                ValidationError(
                    "persistence.import_merge_strategy",
                    f"Invalid strategy '{persistence.import_merge_strategy}'. "
                    f"Must be one of: {valid_strategies}",
                ),
            )

        return errors

    def _validate_telemetry(self, config: UnifiedConfig) -> list[ValidationError]:
        """Validate telemetry configuration."""
        return self._validate_telemetry_section(config.telemetry)

    def _validate_telemetry_section(self, telemetry: Any) -> list[ValidationError]:
        """Validate telemetry section."""
        errors: list[ValidationError] = []

        # Check retention days
        if telemetry.retention_days <= 0:
            errors.append(
                ValidationError(
                    "telemetry.retention_days",
                    "Must be a positive integer",
                ),
            )

        return errors

    def _validate_environment(self, config: UnifiedConfig) -> list[ValidationError]:
        """Validate environment configuration."""
        return self._validate_environment_section(config.environment)

    def _validate_environment_section(self, environment: Any) -> list[ValidationError]:
        """Validate environment section."""
        errors: list[ValidationError] = []

        # Check log level is valid
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if environment.log_level not in valid_levels:
            errors.append(
                ValidationError(
                    "environment.log_level",
                    f"Invalid log level '{environment.log_level}'. "
                    f"Must be one of: {valid_levels}",
                ),
            )

        return errors


def validate_config(config: UnifiedConfig) -> list[ValidationError]:
    """Convenience function to validate configuration.

    Args:
        config: Configuration to validate.

    Returns:
        List of validation errors.

    """
    validator = ConfigValidator()
    return validator.validate(config)
