"""Configuration system for XML-enhanced prompting features.

Provides feature flags and settings for all 6 XML enhancement options:
1. Workflow migration settings
2. XML schema validation
3. Prompt metrics tracking
4. Context window optimization
5. Dynamic prompt adaptation
6. Multi-language support

Copyright 2026 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _validate_file_path(path: str, allowed_dir: str | None = None) -> Path:
    """Validate file path to prevent path traversal and arbitrary writes.

    Args:
        path: File path to validate
        allowed_dir: Optional directory to restrict writes to

    Returns:
        Validated Path object

    Raises:
        ValueError: If path is invalid or unsafe
    """
    if not path or not isinstance(path, str):
        raise ValueError("path must be a non-empty string")

    # Check for null bytes
    if "\x00" in path:
        raise ValueError("path contains null bytes")

    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}")

    # Check if within allowed directory
    if allowed_dir:
        try:
            allowed = Path(allowed_dir).resolve()
            resolved.relative_to(allowed)
        except ValueError:
            raise ValueError(f"path must be within {allowed_dir}")

    # Check for dangerous system paths (cross-platform)
    import sys

    resolved_str = str(resolved)
    if sys.platform == "win32":
        resolved_lower = resolved_str.lower()
        win_dangerous = [
            "\\windows\\system32",
            "\\windows\\syswow64",
            "\\program files",
        ]
        for dangerous in win_dangerous:
            if dangerous in resolved_lower:
                raise ValueError(f"Cannot write to system directory: {dangerous}")
        for marker in ["\\etc\\", "\\sys\\", "\\proc\\", "\\dev\\"]:
            if marker in resolved_lower or resolved_lower.endswith(marker.rstrip("\\")):
                raise ValueError(f"Cannot write to system directory: {marker.strip(chr(92))}")
    else:
        dangerous_paths = ["/etc", "/sys", "/proc", "/dev"]
        for dangerous in dangerous_paths:
            if resolved_str.startswith(dangerous + "/") or resolved_str == dangerous:
                raise ValueError(f"Cannot write to system directory: {dangerous}")

    return resolved


@dataclass
class XMLConfig:
    """XML prompting configuration.

    Controls XML-enhanced prompt behavior and validation.
    """

    use_xml_structure: bool = True  # Default to XML prompts
    validate_schemas: bool = False  # Feature flag for validation
    schema_dir: str = ".attune/schemas"
    strict_validation: bool = False  # Fail on validation errors


@dataclass
class OptimizationConfig:
    """Context window optimization configuration.

    Controls prompt compression and token reduction strategies.
    """

    compression_level: str = "moderate"  # none, light, moderate, aggressive
    use_short_tags: bool = True
    strip_whitespace: bool = True
    cache_system_prompts: bool = True
    max_context_tokens: int = 8000


@dataclass
class AdaptiveConfig:
    """Adaptive prompting configuration.

    Controls dynamic model tier and compression selection based on task complexity.
    """

    enable_adaptation: bool = True
    model_tier_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "simple": "gpt-3.5-turbo",
            "moderate": "gpt-4",
            "complex": "gpt-4",
            "very_complex": "gpt-4-turbo-preview",
        }
    )
    complexity_thresholds: dict[str, int] = field(
        default_factory=lambda: {
            "simple_tokens": 100,
            "moderate_tokens": 500,
            "complex_tokens": 2000,
        }
    )


@dataclass
class I18nConfig:
    """Internationalization configuration.

    Controls multi-language support for XML prompts.
    """

    default_language: str = "en"
    translate_tags: bool = False  # Keep tags in English by default
    translate_content: bool = True
    fallback_to_english: bool = True
    translation_dir: str = ".attune/translations"


@dataclass
class MetricsConfig:
    """Metrics tracking configuration.

    Controls prompt performance metrics collection and storage.
    """

    enable_tracking: bool = True
    metrics_file: str = ".attune/prompt_metrics.json"
    track_token_usage: bool = True
    track_latency: bool = True
    track_retries: bool = True
    track_parsing_success: bool = True


@dataclass
class EmpathyXMLConfig:
    """Main Empathy XML enhancement configuration.

    Combines all feature configurations with centralized management.

    Usage:
        config = EmpathyXMLConfig.load_from_file()
        if config.xml.use_xml_structure:
            use_xml_prompts()

        # Or create custom config
        config = EmpathyXMLConfig(
            xml=XMLConfig(validate_schemas=True),
            metrics=MetricsConfig(enable_tracking=True)
        )
        config.save_to_file()
    """

    xml: XMLConfig = field(default_factory=XMLConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    adaptive: AdaptiveConfig = field(default_factory=AdaptiveConfig)
    i18n: I18nConfig = field(default_factory=I18nConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)

    @classmethod
    def load_from_file(cls, config_file: str = ".attune/config.json") -> "EmpathyXMLConfig":
        """Load configuration from JSON file.

        Args:
            config_file: Path to config file (default: .attune/config.json)

        Returns:
            EmpathyXMLConfig instance loaded from file, or default config if file doesn't exist
        """
        # Validate path to prevent path traversal attacks
        try:
            validated_path = _validate_file_path(config_file)
        except ValueError:
            # Return default config if path is invalid
            return cls()

        if not validated_path.exists():
            # Return default config if file doesn't exist
            return cls()

        try:
            with open(validated_path) as f:
                data = json.load(f)

            # Reconstruct nested dataclasses
            return cls(
                xml=XMLConfig(**data.get("xml", {})),
                optimization=OptimizationConfig(**data.get("optimization", {})),
                adaptive=AdaptiveConfig(**data.get("adaptive", {})),
                i18n=I18nConfig(**data.get("i18n", {})),
                metrics=MetricsConfig(**data.get("metrics", {})),
            )
        except Exception as e:
            # Return default config on error
            print(f"Warning: Failed to load config from {config_file}: {e}")
            return cls()

    def save_to_file(self, config_file: str = ".attune/config.json") -> None:
        """Save configuration to JSON file.

        Args:
            config_file: Path to save config (default: .attune/config.json)
        """
        validated_path = _validate_file_path(config_file)
        validated_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "xml": asdict(self.xml),
            "optimization": asdict(self.optimization),
            "adaptive": asdict(self.adaptive),
            "i18n": asdict(self.i18n),
            "metrics": asdict(self.metrics),
        }

        with open(validated_path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def from_env(cls) -> "EmpathyXMLConfig":
        """Load configuration from environment variables.

        Environment variables:
            EMPATHY_XML_ENABLED: Enable XML prompts (default: true)
            EMPATHY_VALIDATION_ENABLED: Enable schema validation (default: false)
            EMPATHY_METRICS_ENABLED: Enable metrics tracking (default: true)
            EMPATHY_OPTIMIZATION_LEVEL: Compression level (default: moderate)
            EMPATHY_ADAPTIVE_ENABLED: Enable adaptive prompts (default: true)

        Returns:
            EmpathyXMLConfig with settings from environment variables
        """
        return cls(
            xml=XMLConfig(
                use_xml_structure=os.getenv("EMPATHY_XML_ENABLED", "true").lower() == "true",
                validate_schemas=os.getenv("EMPATHY_VALIDATION_ENABLED", "false").lower() == "true",
            ),
            optimization=OptimizationConfig(
                compression_level=os.getenv("EMPATHY_OPTIMIZATION_LEVEL", "moderate"),
            ),
            adaptive=AdaptiveConfig(
                enable_adaptation=os.getenv("EMPATHY_ADAPTIVE_ENABLED", "true").lower() == "true",
            ),
            metrics=MetricsConfig(
                enable_tracking=os.getenv("EMPATHY_METRICS_ENABLED", "true").lower() == "true",
            ),
        )


# Global default configuration instance
_global_config: EmpathyXMLConfig | None = None


def get_config() -> EmpathyXMLConfig:
    """Get global configuration instance.

    Returns cached config or loads from file if not yet loaded.

    Returns:
        Global EmpathyXMLConfig instance
    """
    global _global_config

    if _global_config is None:
        # Try to load from file, fall back to defaults
        _global_config = EmpathyXMLConfig.load_from_file()

    return _global_config


def set_config(config: EmpathyXMLConfig) -> None:
    """Set global configuration instance.

    Args:
        config: EmpathyXMLConfig to use globally
    """
    global _global_config
    _global_config = config
