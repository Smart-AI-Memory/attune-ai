"""Configuration Management for Attune AI

Supports:
- YAML configuration files
- JSON configuration files
- Environment variables
- Default configuration

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.workflows.config import ModelConfig

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


from attune.security.path_validation import _validate_file_path


@dataclass
class AttuneConfig:
    """Configuration for an Attune instance

    Can be loaded from:
    - YAML file (.attune.yml, attune.config.yml)
    - JSON file (.attune.json, attune.config.json)
    - Environment variables (ATTUNE_*)
    - Direct instantiation
    """

    # Core settings
    user_id: str = "default_user"
    target_level: int = 3
    confidence_threshold: float = 0.75

    # Trust settings
    trust_building_rate: float = 0.05
    trust_erosion_rate: float = 0.10

    # Persistence settings
    persistence_enabled: bool = True
    persistence_backend: str = "sqlite"  # "sqlite", "json", "none"
    persistence_path: str = "./attune_data"

    # State management
    state_persistence: bool = True
    state_path: str = "./attune_state"

    # Metrics settings
    metrics_enabled: bool = True
    metrics_path: str = "./metrics.db"

    # Output settings
    # None = auto: show cost metrics iff ANTHROPIC_API_KEY is set
    # (cost figures don't apply to subscription users; see
    # resolve_show_cost()).
    show_cost_metrics: bool | None = None

    # Logging settings
    log_level: str = "INFO"
    log_file: str | None = None
    structured_logging: bool = True

    # Pattern library settings
    pattern_library_enabled: bool = True
    pattern_sharing: bool = True
    pattern_confidence_threshold: float = 0.3

    # Advanced settings
    async_enabled: bool = True
    feedback_loop_monitoring: bool = True
    leverage_point_analysis: bool = True

    # Custom metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Model settings
    models: list["ModelConfig"] = field(default_factory=list)
    default_model: str | None = None
    log_path: str | None = None
    max_threads: int = 4
    model_router: dict[str, Any] | None = None

    def __post_init__(self):
        """Post-initialization validation."""
        if self.default_model and not any(m.name == self.default_model for m in self.models):
            raise ValueError(f"Default model '{self.default_model}' not in models.")

    @classmethod
    def from_yaml(cls, filepath: str) -> "AttuneConfig":
        """Load configuration from YAML file

        Args:
            filepath: Path to YAML configuration file

        Returns:
            AttuneConfig instance

        Raises:
            ImportError: If PyYAML is not installed
            FileNotFoundError: If file doesn't exist

        Example:
            >>> config = AttuneConfig.from_yaml("attune.config.yml")

        Note:
            Unknown fields in the YAML file are silently ignored.
            This allows config files to contain settings for other
            components (e.g., model_preferences, workflows) without
            breaking AttuneConfig loading.

        """
        if not YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is required for YAML configuration. Install with: pip install pyyaml",
            )

        with open(filepath) as f:
            data = yaml.safe_load(f)

        # Filter to only known fields (gracefully ignore unknown fields like
        # 'provider', 'model_preferences', 'workflows', etc.)
        from dataclasses import fields as dataclass_fields

        valid_fields = {f.name for f in dataclass_fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        return cls.from_dict(filtered_data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttuneConfig":
        """Create an AttuneConfig from a dictionary, ignoring unknown fields."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}

        # Handle nested ModelConfig objects
        if filtered_data.get("models"):
            from attune.workflows.config import ModelConfig

            filtered_data["models"] = [ModelConfig(**m) for m in filtered_data["models"]]

        return cls(**filtered_data)

    @classmethod
    def from_json(cls, filepath: str) -> "AttuneConfig":
        """Load configuration from JSON file

        Args:
            filepath: Path to JSON configuration file

        Returns:
            AttuneConfig instance

        Example:
            >>> config = AttuneConfig.from_json("attune.config.json")

        Note:
            Unknown fields in the JSON file are silently ignored.

        """
        with open(filepath) as f:
            data = json.load(f)

        # Filter to only known fields (gracefully ignore unknown fields)
        from dataclasses import fields as dataclass_fields

        valid_fields = {f.name for f in dataclass_fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**filtered_data)

    @classmethod
    def from_env(cls, prefix: str = "ATTUNE_") -> "AttuneConfig":
        """Load configuration from environment variables.

        Environment variables can be prefixed with ATTUNE_ (preferred)
        or EMPATHY_ (deprecated, still accepted). ATTUNE_ takes precedence.

        Example:
            ATTUNE_USER_ID=alice
            ATTUNE_TARGET_LEVEL=4
            ATTUNE_CONFIDENCE_THRESHOLD=0.8

        Args:
            prefix: Environment variable prefix (default: "ATTUNE_")

        Returns:
            AttuneConfig instance

        Example:
            >>> os.environ["ATTUNE_USER_ID"] = "alice"
            >>> config = AttuneConfig.from_env()
            >>> print(config.user_id)  # "alice"

        """
        from dataclasses import fields as dataclass_fields

        # Get valid field names from the dataclass
        valid_fields = {f.name for f in dataclass_fields(cls)}

        data: dict[str, Any] = {}

        # Check ATTUNE_ first, then EMPATHY_ as fallback (ATTUNE_ wins)
        prefixes = dict.fromkeys([prefix, "ATTUNE_", "EMPATHY_"])
        for check_prefix in prefixes:
            for key, value in os.environ.items():
                if not key.startswith(check_prefix):
                    continue

                field_name = key[len(check_prefix) :].lower()

                # Skip unknown fields
                if field_name not in valid_fields:
                    continue

                # Skip if ATTUNE_ already set this field
                if field_name in data:
                    continue

                # Type conversion based on field name
                if field_name in ("target_level",):
                    data[field_name] = int(value)
                elif field_name in (
                    "confidence_threshold",
                    "trust_building_rate",
                    "trust_erosion_rate",
                    "pattern_confidence_threshold",
                ):
                    data[field_name] = float(value)
                elif field_name in (
                    "persistence_enabled",
                    "state_persistence",
                    "metrics_enabled",
                    "structured_logging",
                    "pattern_library_enabled",
                    "pattern_sharing",
                    "async_enabled",
                    "feedback_loop_monitoring",
                    "leverage_point_analysis",
                    "show_cost_metrics",
                ):
                    data[field_name] = value.lower() in ("true", "1", "yes")
                else:
                    data[field_name] = value

        return cls(**data)

    @classmethod
    def from_file(cls, filepath: str | None = None) -> "AttuneConfig":
        """Automatically detect and load configuration from file

        Looks for configuration files in this order:
        1. Provided filepath
        2. .empathy.yml
        3. .empathy.yaml
        4. .attune.yml
        5. .attune.yaml
        6. attune.config.yml
        7. attune.config.yaml
        8. .empathy.json
        9. .attune.json
        10. attune.config.json

        Args:
            filepath: Optional explicit path to config file

        Returns:
            AttuneConfig instance, or default if no file found

        Example:
            >>> config = AttuneConfig.from_file()  # Auto-detect
            >>> config = AttuneConfig.from_file("my-config.yml")

        """
        search_paths = [
            filepath,
            ".empathy.yml",
            ".empathy.yaml",
            ".attune.yml",
            ".attune.yaml",
            "attune.config.yml",
            "attune.config.yaml",
            ".empathy.json",
            ".attune.json",
            "attune.config.json",
        ]

        for path in search_paths:
            if path and Path(path).exists():
                if path.endswith((".yml", ".yaml")):
                    return cls.from_yaml(path)
                if path.endswith(".json"):
                    return cls.from_json(path)

        # No config file found - return default
        return cls()

    def to_yaml(self, filepath: str) -> None:
        """Save configuration to YAML file

        Args:
            filepath: Path to save YAML file

        Example:
            >>> config = AttuneConfig(user_id="alice", target_level=4)
            >>> config.to_yaml("my-config.yml")

        """
        if not YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is required for YAML export. Install with: pip install pyyaml",
            )

        validated_path = _validate_file_path(filepath)
        data = asdict(self)

        with open(validated_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def to_json(self, filepath: str, indent: int = 2) -> None:
        """Save configuration to JSON file

        Args:
            filepath: Path to save JSON file
            indent: JSON indentation (default: 2)

        Example:
            >>> config = AttuneConfig(user_id="alice", target_level=4)
            >>> config.to_json("my-config.json")

        """
        validated_path = _validate_file_path(filepath)
        data = asdict(self)

        with open(validated_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary"""
        return asdict(self)

    def update(self, **kwargs: Any) -> None:
        """Update configuration fields

        Args:
            **kwargs: Fields to update

        Example:
            >>> config = AttuneConfig()
            >>> config.update(user_id="bob", target_level=5)

        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def merge(self, other: "AttuneConfig") -> "AttuneConfig":
        """Merge with another configuration (other takes precedence)

        Args:
            other: Configuration to merge

        Returns:
            New merged configuration

        Example:
            >>> base = AttuneConfig(user_id="alice")
            >>> override = AttuneConfig(target_level=5)
            >>> merged = base.merge(override)

        """
        # Start with base values
        base_dict = self.to_dict()
        other_dict = other.to_dict()

        # Get default values for comparison
        defaults = AttuneConfig().to_dict()

        # Only update fields from 'other' that differ from defaults
        for key, value in other_dict.items():
            if value != defaults.get(key):
                base_dict[key] = value

        return AttuneConfig(**base_dict)

    def validate(self) -> bool:
        """Validate configuration values

        Returns:
            True if valid, raises ValueError if invalid

        Raises:
            ValueError: If configuration is invalid

        """
        if self.target_level not in range(1, 6):
            raise ValueError(f"target_level must be 1-5, got {self.target_level}")

        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be 0.0-1.0, got {self.confidence_threshold}",
            )

        if not 0.0 <= self.pattern_confidence_threshold <= 1.0:
            threshold_val = self.pattern_confidence_threshold
            raise ValueError(f"pattern_confidence_threshold must be 0.0-1.0, got {threshold_val}")

        if self.persistence_backend not in ("sqlite", "json", "none"):
            backend_val = self.persistence_backend
            raise ValueError(
                f"persistence_backend must be 'sqlite', 'json', or 'none', got {backend_val}",
            )

        return True

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"AttuneConfig(user_id={self.user_id!r}, target_level={self.target_level}, "
            f"confidence_threshold={self.confidence_threshold})"
        )


def load_config(
    filepath: str | None = None,
    use_env: bool = True,
    defaults: dict[str, Any] | None = None,
) -> AttuneConfig:
    """Load configuration with flexible precedence

    Precedence (highest to lowest):
    1. Environment variables (if use_env=True)
    2. Configuration file (if provided/found)
    3. Defaults (if provided)
    4. Built-in defaults

    Args:
        filepath: Optional path to config file
        use_env: Whether to check environment variables (default: True)
        defaults: Optional default values

    Returns:
        AttuneConfig instance

    Example:
        >>> # Load from file, override with env vars
        >>> config = load_config("attune.config.yml", use_env=True)

        >>> # Load with custom defaults
        >>> config = load_config(defaults={"target_level": 4})

    """
    # Start with built-in defaults
    config = AttuneConfig()

    # Apply custom defaults
    if defaults:
        config.update(**defaults)

    # Load from file if provided/found
    # First check if a file actually exists
    file_found = False
    if filepath and Path(filepath).exists():
        file_found = True
    else:
        # Check default config file locations
        for default_path in [
            ".empathy.yml",
            ".empathy.yaml",
            ".attune.yml",
            ".attune.yaml",
            "attune.config.yml",
            "attune.config.yaml",
            ".empathy.json",
            ".attune.json",
            "attune.config.json",
        ]:
            if Path(default_path).exists():
                file_found = True
                break

    if file_found:
        try:
            file_config = AttuneConfig.from_file(filepath)
            config = config.merge(file_config)
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # Use defaults

    # Override with environment variables
    if use_env:
        try:
            env_config = AttuneConfig.from_env()
            config = config.merge(env_config)
        except (ValueError, TypeError):
            # Graceful fallback: invalid env var type conversion
            pass  # Use current config if environment parsing fails

    # Validate final configuration
    config.validate()

    return config


def resolve_show_cost(config: "AttuneConfig | None" = None) -> bool:
    """Resolve whether human-facing output should show cost metrics.

    Resolution order (workflow-result-formatting design D3):

    1. ``config.show_cost_metrics`` when explicitly set (``True``/``False``).
    2. Auto default: ``True`` iff ``ANTHROPIC_API_KEY`` is set — cost
       figures only apply to pay-per-call API users, not subscription
       users.

    Cost data always stays in ``WorkflowReport.metadata`` and ``--json``
    output; this flag only gates the human-readable rendering.

    Args:
        config: Configuration to read the override from. ``None`` loads
            the ambient configuration via :func:`load_config`.

    Returns:
        True if cost metrics should be rendered.

    """
    if config is None:
        try:
            config = load_config()
        except Exception:  # noqa: BLE001
            # INTENTIONAL: a malformed user config must never break
            # output formatting — fall through to the env auto default.
            logging.getLogger(__name__).warning(
                "Failed to load config for show_cost resolution",
                exc_info=True,
            )
            config = None

    if config is not None and config.show_cost_metrics is not None:
        return bool(config.show_cost_metrics)

    return bool(os.environ.get("ANTHROPIC_API_KEY"))


# Backward-compatible alias (deprecated: use AttuneConfig)
EmpathyConfig = AttuneConfig
