"""Configuration loader for Attune AI.

Handles discovering, loading, saving, and merging configuration files.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import os
from pathlib import Path

from attune.config.unified import UnifiedConfig
from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

# Configuration search paths in order of priority
CONFIG_SEARCH_PATHS = [
    "./attune.config.json",  # Project-local
    "~/.attune/config.json",  # User home
    "~/.config/attune/config.json",  # XDG standard
]

# Environment variable prefix for overrides
ENV_PREFIX = "ATTUNE_"


class ConfigLoader:
    """Load, save, and manage Attune AI configuration.

    Handles configuration file discovery, loading from JSON,
    saving, and applying environment variable overrides.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        """Initialize the config loader.

        Args:
            config_path: Explicit config path. If None, searches default locations.

        """
        self._explicit_path = Path(config_path).expanduser() if config_path else None
        self._loaded_path: Path | None = None
        self._config: UnifiedConfig | None = None

    @staticmethod
    def discover_config_path() -> Path | None:
        """Discover the configuration file path.

        Searches in order:
        1. ./attune.config.json (project-local)
        2. ~/.attune/config.json (user home)
        3. ~/.config/attune/config.json (XDG standard)

        Returns:
            Path to configuration file if found, None otherwise.

        """
        for path_str in CONFIG_SEARCH_PATHS:
            path = Path(path_str).expanduser()
            if path.exists():
                logger.debug(f"Found config at: {path}")
                return path

        logger.debug("No config file found in search paths")
        return None

    @staticmethod
    def get_default_config_path() -> Path:
        """Get the default configuration path for new configs.

        Returns:
            Path to ~/.attune/config.json

        """
        return Path("~/.attune/config.json").expanduser()

    def get_config_path(self) -> Path | None:
        """Get the current configuration path.

        Returns:
            Path to config file if loaded or explicit, None otherwise.

        """
        return self._loaded_path or self._explicit_path

    def load(self) -> UnifiedConfig:
        """Load configuration from file or create defaults.

        If an explicit path was provided, loads from that path.
        Otherwise, searches default locations.
        If no config exists, returns default UnifiedConfig.

        Returns:
            Loaded or default UnifiedConfig.

        Raises:
            ValueError: If explicit path doesn't exist.
            json.JSONDecodeError: If config file is malformed.

        """
        # Determine path
        if self._explicit_path:
            if not self._explicit_path.exists():
                raise ValueError(f"Config file not found: {self._explicit_path}")
            path = self._explicit_path
        else:
            path = self.discover_config_path()

        # Load from file or create defaults
        if path:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._config = UnifiedConfig.from_dict(data)
                self._loaded_path = path
                logger.info(f"Loaded config from: {path}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse config at {path}: {e}")
                raise
        else:
            self._config = UnifiedConfig()
            logger.info("Using default configuration")

        # Apply environment variable overrides
        self._config = self.apply_env_overrides(self._config)

        return self._config

    def save(self, config: UnifiedConfig, path: Path | None = None) -> Path:
        """Save configuration to file.

        Args:
            config: Configuration to save.
            path: Path to save to. If None, uses loaded path or default.

        Returns:
            Path where configuration was saved.

        Raises:
            ValueError: If path is invalid or targets system directory.
            PermissionError: If insufficient permissions.

        """
        # Determine save path
        if path:
            save_path = Path(path).expanduser()
        elif self._loaded_path:
            save_path = self._loaded_path
        else:
            save_path = self.get_default_config_path()

        # Validate path for security
        validated_path = _validate_file_path(str(save_path))

        # Ensure parent directory exists
        validated_path.parent.mkdir(parents=True, exist_ok=True)

        # Update modification timestamp
        config.touch()

        # Save to file
        try:
            data = config.to_dict()
            validated_path.write_text(
                json.dumps(data, indent=2, sort_keys=False),
                encoding="utf-8",
            )
            self._loaded_path = validated_path
            self._config = config
            logger.info(f"Saved config to: {validated_path}")
            return validated_path
        except PermissionError as e:
            logger.error(f"Permission denied writing to {validated_path}: {e}")
            raise
        except OSError as e:
            logger.error(f"Failed to save config to {validated_path}: {e}")
            raise ValueError(f"Cannot save config: {e}") from e

    @staticmethod
    def apply_env_overrides(config: UnifiedConfig) -> UnifiedConfig:
        """Apply environment variable overrides to configuration.

        Environment variables follow the pattern:
        ATTUNE_<SECTION>_<SETTING> = value

        For example:
        - ATTUNE_AUTH_STRATEGY=api
        - ATTUNE_ROUTING_DEFAULT_TIER=premium
        - ATTUNE_TELEMETRY_ENABLED=false

        Args:
            config: Configuration to apply overrides to.

        Returns:
            Configuration with environment overrides applied.

        """
        for key, value in os.environ.items():
            if not key.startswith(ENV_PREFIX):
                continue

            # Parse key: ATTUNE_AUTH_STRATEGY -> auth.strategy
            parts = key[len(ENV_PREFIX) :].lower().split("_", 1)
            if len(parts) != 2:
                continue

            section_name, setting_name = parts
            dot_key = f"{section_name}.{setting_name}"

            try:
                # Get current value to determine type
                current_value = config.get_value(dot_key)

                # Convert string value to appropriate type
                if isinstance(current_value, bool):
                    typed_value = value.lower() in ("true", "1", "yes", "on")
                elif isinstance(current_value, int):
                    typed_value = int(value)
                elif isinstance(current_value, float):
                    typed_value = float(value)
                elif isinstance(current_value, list):
                    typed_value = value.split(",")
                else:
                    typed_value = value

                config.set_value(dot_key, typed_value)
                logger.debug(f"Applied env override: {key} -> {dot_key}")
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to apply env override {key}: {e}")

        return config

    def get_config(self) -> UnifiedConfig:
        """Get the current configuration.

        Loads from file if not already loaded.

        Returns:
            Current UnifiedConfig.

        """
        if self._config is None:
            return self.load()
        return self._config


# Global loader instance for convenience
_global_loader: ConfigLoader | None = None


def get_loader() -> ConfigLoader:
    """Get the global ConfigLoader instance.

    Returns:
        Global ConfigLoader singleton.

    """
    global _global_loader
    if _global_loader is None:
        _global_loader = ConfigLoader()
    return _global_loader


def load_unified_config(path: str | Path | None = None) -> UnifiedConfig:
    """Convenience function to load unified configuration.

    Args:
        path: Optional explicit config path.

    Returns:
        Loaded UnifiedConfig.

    """
    loader = ConfigLoader(config_path=path)
    return loader.load()


def save_unified_config(config: UnifiedConfig, path: str | Path | None = None) -> Path:
    """Convenience function to save unified configuration.

    Args:
        config: Configuration to save.
        path: Optional save path.

    Returns:
        Path where configuration was saved.

    """
    return get_loader().save(config, Path(path) if path else None)
