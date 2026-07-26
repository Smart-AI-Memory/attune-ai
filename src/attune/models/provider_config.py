"""Provider Configuration System

Handles user provider selection during install/update and runtime configuration.
Supports single-provider mode (default) and hybrid mode (multi-provider).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path

from .registry import MODEL_REGISTRY, ModelInfo, ModelTier

logger = logging.getLogger(__name__)


class ProviderMode(str, Enum):
    """Provider selection mode (Anthropic-only as of v5.0.0)."""

    SINGLE = "single"  # Anthropic for all tiers
    HYBRID = "hybrid"  # Deprecated: kept for backward compatibility


@dataclass
class ProviderConfig:
    """User's provider configuration."""

    # Primary mode
    mode: ProviderMode = ProviderMode.SINGLE

    # For SINGLE mode: which provider to use
    primary_provider: str = "anthropic"

    # For CUSTOM mode: per-tier provider overrides
    tier_providers: dict[str, str] = field(default_factory=dict)

    # API key availability (detected at runtime)
    available_providers: list[str] = field(default_factory=list)

    # User preferences
    prefer_local: bool = False  # Deprecated (v5.0.0)
    cost_optimization: bool = True  # Use cheaper tiers when appropriate

    @classmethod
    def detect_available_providers(cls) -> list[str]:
        """Detect if Anthropic API key is configured (Anthropic-only as of v5.0.0)."""
        available = []

        # Load .env files if they exist (project root and home)
        env_keys = cls._load_env_files()

        # Check for ANTHROPIC_API_KEY
        if os.getenv("ANTHROPIC_API_KEY") or env_keys.get("ANTHROPIC_API_KEY"):
            available.append("anthropic")

        return available

    @staticmethod
    def _load_env_files() -> dict[str, str]:
        """Load API keys from .env files without modifying os.environ."""
        env_keys: dict[str, str] = {}

        # Possible .env file locations
        env_paths = [
            Path.cwd() / ".env",
            Path.home() / ".env",
            Path.home() / ".attune" / ".env",
        ]

        for env_path in env_paths:
            if env_path.exists():
                try:
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, _, value = line.partition("=")
                                key = key.strip()
                                value = value.strip().strip("'\"")
                                if key and value:
                                    env_keys[key] = value
                except Exception:  # noqa: BLE001
                    # INTENTIONAL: .env reading is best-effort.
                    # Missing or unreadable .env files should
                    # not block provider detection.
                    logger.warning(
                        "env_file_read_failed: %s",
                        str(env_path),
                        exc_info=True,
                    )

        return env_keys

    @classmethod
    def auto_detect(cls) -> ProviderConfig:
        """Auto-detect configuration (Anthropic-only as of v5.0.0).

        Returns:
            ProviderConfig with Anthropic as primary provider

        """
        available = cls.detect_available_providers()

        return cls(
            mode=ProviderMode.SINGLE,
            primary_provider="anthropic",
            available_providers=available,
        )

    def get_model_for_tier(self, tier: str | ModelTier) -> ModelInfo | None:
        """Get the model to use for a given tier (Anthropic-only as of v5.0.0).

        Args:
            tier: Tier level (cheap, capable, premium)

        Returns:
            ModelInfo for the Anthropic model at the specified tier

        """
        tier_str = tier.value if isinstance(tier, ModelTier) else tier
        return MODEL_REGISTRY.get("anthropic", {}).get(tier_str)

    def get_effective_registry(self) -> dict[str, ModelInfo]:
        """Get the effective model registry based on current config."""
        result = {}
        for tier in ["cheap", "capable", "premium"]:
            model = self.get_model_for_tier(tier)
            if model:
                result[tier] = model
        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "mode": self.mode.value,
            "primary_provider": self.primary_provider,
            "tier_providers": self.tier_providers,
            "prefer_local": self.prefer_local,
            "cost_optimization": self.cost_optimization,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProviderConfig:
        """Deserialize from dictionary."""
        return cls(
            mode=ProviderMode(data.get("mode", "single")),
            primary_provider=data.get("primary_provider", "anthropic"),
            tier_providers=data.get("tier_providers", {}),
            prefer_local=data.get("prefer_local", False),
            cost_optimization=data.get("cost_optimization", True),
            available_providers=cls.detect_available_providers(),
        )

    def save(self, path: Path | None = None) -> None:
        """Save configuration to file."""
        if path is None:
            path = Path.home() / ".attune" / "provider_config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        validated_path = _validate_file_path(str(path))  # type: ignore[misc]
        with open(validated_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path | None = None) -> ProviderConfig:
        """Load configuration from file, or auto-detect if not found."""
        if path is None:
            path = Path.home() / ".attune" / "provider_config.json"

        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Graceful fallback to auto_detect()
                # when saved config is corrupt or unreadable.
                logger.warning(
                    "provider_config_load_failed: %s",
                    str(path),
                    exc_info=True,
                )

        # Auto-detect if no config exists
        return cls.auto_detect()


# Interactive configuration for install/update
def configure_provider_interactive() -> ProviderConfig:
    """Interactive provider configuration for install/update (Anthropic-only as of v5.0.0).

    Returns:
        ProviderConfig configured for Anthropic

    """
    print("\n" + "=" * 60)
    print("Attune AI - Provider Configuration (Claude-Native v5.0.0)")
    print("=" * 60)

    # Check for Anthropic API key
    config = ProviderConfig.auto_detect()
    available = config.available_providers

    if not available:
        print("\n⚠️  ANTHROPIC_API_KEY not detected.")
        print("\nPlease set your Anthropic API key:")
        print("   export ANTHROPIC_API_KEY='your-key-here'")
        print("\nGet your API key at: https://console.anthropic.com/settings/keys")
        print("\nDefaulting to Anthropic configuration.")
        print("You'll need to set ANTHROPIC_API_KEY before running workflows.")
        return ProviderConfig(
            mode=ProviderMode.SINGLE,
            primary_provider="anthropic",
            available_providers=[],
        )

    # Anthropic API key detected
    print("\n✓ ANTHROPIC_API_KEY detected")
    print("\nConfiguring Anthropic as provider...")

    config = ProviderConfig(
        mode=ProviderMode.SINGLE,
        primary_provider="anthropic",
        available_providers=available,
    )

    # Show effective models
    print("\nEffective model mapping:")
    effective = config.get_effective_registry()
    for tier, model in effective.items():
        print(f"  {tier:8} → {model.id}")

    # Save configuration
    config.save()
    print("\n✓ Configuration saved to ~/.attune/provider_config.json")

    return config


def configure_provider_cli(
    provider: str | None = None,
    mode: str | None = None,
) -> ProviderConfig:
    """CLI-based provider configuration (Anthropic-only as of v5.0.0).

    Args:
        provider: Provider name (must be 'anthropic' or None)
        mode: Mode (must be 'single' or None)

    Returns:
        Configured ProviderConfig for Anthropic

    Raises:
        ValueError: If provider is not 'anthropic'

    """
    if provider and provider.lower() != "anthropic":
        raise ValueError(
            f"Provider '{provider}' is not supported. "
            f"Attune AI is now Claude-native (v5.0.0). "
            f"Only 'anthropic' provider is available. "
            f"See docs/CLAUDE_NATIVE.md for migration guide.",
        )

    if mode and mode.lower() != "single":
        raise ValueError(
            f"Mode '{mode}' is not supported. "
            f"Only 'single' mode is available in v5.0.0 (Anthropic-only).",
        )

    # Always return Anthropic configuration
    return ProviderConfig.auto_detect()


# Global config instance (lazy-loaded)
_global_config: ProviderConfig | None = None


def get_provider_config() -> ProviderConfig:
    """Get the global provider configuration."""
    global _global_config
    if _global_config is None:
        _global_config = ProviderConfig.load()
    return _global_config


def set_provider_config(config: ProviderConfig) -> None:
    """Set the global provider configuration."""
    global _global_config
    _global_config = config


def reset_provider_config() -> None:
    """Reset the global provider configuration (forces reload)."""
    global _global_config
    _global_config = None


def configure_hybrid_interactive() -> ProviderConfig:
    """Interactive hybrid provider configuration (DEPRECATED in v5.0.0).

    Hybrid mode is no longer supported as of v5.0.0 (Claude-native).
    This function now configures Anthropic as the sole provider.

    Returns:
        ProviderConfig configured for Anthropic

    """
    print("\n" + "=" * 60)
    print("NOTE: Hybrid mode is deprecated (v5.0.0)")
    print("=" * 60)
    print("\nAttune AI is now Claude-native and uses Anthropic exclusively.")
    print("Configuring Anthropic as your provider...\n")

    return configure_provider_interactive()
