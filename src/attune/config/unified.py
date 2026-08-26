"""Unified configuration dataclass for Attune AI.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from attune.config.sections.analysis import AnalysisConfig
from attune.config.sections.auth import AuthConfig
from attune.config.sections.environment import EnvironmentConfig
from attune.config.sections.persistence import PersistenceConfig
from attune.config.sections.routing import RoutingConfig
from attune.config.sections.telemetry import TelemetryConfig
from attune.config.sections.workflows import WorkflowsConfig


@dataclass
class UnifiedConfig:
    """Unified configuration for Attune AI.

    Consolidates all configuration sections into a single dataclass
    for easy management, serialization, and validation.

    Attributes:
        auth: Authentication and API key settings.
        routing: Model routing and tier selection.
        workflows: Workflow execution settings.
        analysis: Code analysis configuration.
        persistence: Data persistence and memory settings.
        telemetry: Telemetry and usage tracking.
        environment: Environment and display settings.
        _version: Configuration schema version.
        _created: Timestamp when config was created.
        _modified: Timestamp when config was last modified.

    """

    auth: AuthConfig = field(default_factory=AuthConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    workflows: WorkflowsConfig = field(default_factory=WorkflowsConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    _version: str = "1.0.0"
    _created: str = ""
    _modified: str = ""

    def __post_init__(self) -> None:
        """Set timestamps if not provided."""
        now = datetime.now(timezone.utc).isoformat()
        if not self._created:
            self._created = now
        if not self._modified:
            self._modified = now

    def touch(self) -> None:
        """Update the modified timestamp."""
        self._modified = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "auth": self.auth.to_dict(),
            "routing": self.routing.to_dict(),
            "workflows": self.workflows.to_dict(),
            "analysis": self.analysis.to_dict(),
            "persistence": self.persistence.to_dict(),
            "telemetry": self.telemetry.to_dict(),
            "environment": self.environment.to_dict(),
            "_version": self._version,
            "_created": self._created,
            "_modified": self._modified,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UnifiedConfig":
        """Create from dictionary.

        Args:
            data: Dictionary with configuration data.

        Returns:
            UnifiedConfig instance.

        """
        return cls(
            auth=AuthConfig.from_dict(data.get("auth", {})),
            routing=RoutingConfig.from_dict(data.get("routing", {})),
            workflows=WorkflowsConfig.from_dict(data.get("workflows", {})),
            analysis=AnalysisConfig.from_dict(data.get("analysis", {})),
            persistence=PersistenceConfig.from_dict(data.get("persistence", {})),
            telemetry=TelemetryConfig.from_dict(data.get("telemetry", {})),
            environment=EnvironmentConfig.from_dict(data.get("environment", {})),
            _version=data.get("_version", "1.0.0"),
            _created=data.get("_created", ""),
            _modified=data.get("_modified", ""),
        )

    def get_value(self, key: str) -> object:
        """Get a configuration value by dot-notation key.

        Args:
            key: Dot-notation key like 'auth.strategy' or 'routing.default_tier'.

        Returns:
            The configuration value.

        Raises:
            KeyError: If key is not found.

        """
        parts = key.split(".", 1)
        if len(parts) == 1:
            raise KeyError(f"Invalid key format: {key}. Use section.setting format.")

        section_name, setting_name = parts
        section = getattr(self, section_name, None)
        if section is None:
            raise KeyError(f"Unknown section: {section_name}")

        if not hasattr(section, setting_name):
            raise KeyError(f"Unknown setting: {setting_name} in section {section_name}")

        return getattr(section, setting_name)

    def set_value(self, key: str, value: object) -> None:
        """Set a configuration value by dot-notation key.

        Args:
            key: Dot-notation key like 'auth.strategy' or 'routing.default_tier'.
            value: The value to set.

        Raises:
            KeyError: If key is not found.
            TypeError: If value type doesn't match expected type.

        """
        parts = key.split(".", 1)
        if len(parts) == 1:
            raise KeyError(f"Invalid key format: {key}. Use section.setting format.")

        section_name, setting_name = parts
        section = getattr(self, section_name, None)
        if section is None:
            raise KeyError(f"Unknown section: {section_name}")

        if not hasattr(section, setting_name):
            raise KeyError(f"Unknown setting: {setting_name} in section {section_name}")

        setattr(section, setting_name, value)
        self.touch()

    def get_all_keys(self) -> list[str]:
        """Get all configuration keys in dot-notation format.

        Returns:
            List of all configuration keys.

        """
        keys = []
        sections = [
            "auth",
            "routing",
            "workflows",
            "analysis",
            "persistence",
            "telemetry",
            "environment",
        ]

        for section_name in sections:
            section = getattr(self, section_name)
            for setting_name in section.to_dict().keys():
                keys.append(f"{section_name}.{setting_name}")

        return keys
