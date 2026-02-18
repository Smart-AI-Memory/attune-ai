"""Unified Model Registry - Single Source of Truth

This module provides a centralized model configuration that is consumed by:
- attune.routing.ModelRouter (via compatibility properties)
- src/attune/workflows.config.WorkflowConfig
- src/attune.cost_tracker

Pricing is stored in per-million tokens (industry standard) with computed
properties for per-1k compatibility with legacy code.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ModelTier(Enum):
    """Model tier classification for routing.

    CHEAP: Fast, low-cost models for simple tasks (~$0.15-1.00/M input)
    CAPABLE: Balanced models for most development work (~$2.50-3.00/M input)
    PREMIUM: Highest capability for complex reasoning (~$15.00/M input)
    """

    CHEAP = "cheap"
    CAPABLE = "capable"
    PREMIUM = "premium"


class ModelProvider(Enum):
    """Supported model provider (Claude-native architecture as of v5.0.0)."""

    ANTHROPIC = "anthropic"


@dataclass(frozen=True)
class ModelInfo:
    """Unified model information - single source of truth.

    Pricing is stored in per-million tokens format. Use the cost_per_1k_*
    properties for compatibility with code expecting per-1k pricing.

    Attributes:
        id: Model identifier (e.g., "claude-haiku-4-5-20251001")
        provider: Provider name (e.g., "anthropic")
        tier: Tier level (e.g., "cheap")
        input_cost_per_million: Input token cost per million tokens
        output_cost_per_million: Output token cost per million tokens
        max_tokens: Maximum output tokens
        supports_vision: Whether model supports vision/images
        supports_tools: Whether model supports tool/function calling

    """

    id: str
    provider: str
    tier: str
    input_cost_per_million: float
    output_cost_per_million: float
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_tools: bool = True

    # Compatibility properties for toolkit (per-1k pricing)
    @property
    def model_id(self) -> str:
        """Alias for id - compatibility with ModelRouter.ModelConfig."""
        return self.id

    @property
    def name(self) -> str:
        """Alias for id - compatibility with WorkflowConfig.ModelConfig."""
        return self.id

    @property
    def cost_per_1k_input(self) -> float:
        """Input cost per 1k tokens - for ModelRouter compatibility."""
        return self.input_cost_per_million / 1000

    @property
    def cost_per_1k_output(self) -> float:
        """Output cost per 1k tokens - for ModelRouter compatibility."""
        return self.output_cost_per_million / 1000

    def to_router_config(self) -> dict[str, Any]:
        """Convert to ModelRouter.ModelConfig compatible dict."""
        return {
            "model_id": self.id,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "max_tokens": self.max_tokens,
            "supports_tools": self.supports_tools,
        }

    def to_workflow_config(self) -> dict[str, Any]:
        """Convert to WorkflowConfig.ModelConfig compatible dict."""
        return {
            "name": self.id,
            "provider": self.provider,
            "tier": self.tier,
            "input_cost_per_million": self.input_cost_per_million,
            "output_cost_per_million": self.output_cost_per_million,
            "max_tokens": self.max_tokens,
            "supports_vision": self.supports_vision,
            "supports_tools": self.supports_tools,
        }

    def to_cost_tracker_pricing(self) -> dict[str, float]:
        """Convert to cost_tracker MODEL_PRICING format."""
        return {
            "input": self.input_cost_per_million,
            "output": self.output_cost_per_million,
        }


# =============================================================================
# MODEL REGISTRY - Single Source of Truth
# =============================================================================
# All model configurations are defined here. Other modules should import
# from this registry rather than defining their own model configs.

MODEL_REGISTRY: dict[str, dict[str, ModelInfo]] = {
    # -------------------------------------------------------------------------
    # Anthropic Claude Models
    # Intelligent fallback: Sonnet 4.5 → Opus 4.6 (5x cost increase for complex tasks)
    # -------------------------------------------------------------------------
    "anthropic": {
        "cheap": ModelInfo(
            id="claude-haiku-4-5-20251001",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1.00,
            output_cost_per_million=5.00,
            max_tokens=8192,
            supports_vision=True,
            supports_tools=True,
        ),
        "capable": ModelInfo(
            id="claude-sonnet-4-5-20250929",
            provider="anthropic",
            tier="capable",
            input_cost_per_million=3.00,
            output_cost_per_million=15.00,
            max_tokens=8192,
            supports_vision=True,
            supports_tools=True,
        ),
        "premium": ModelInfo(
            id="claude-opus-4-6",
            provider="anthropic",
            tier="premium",
            input_cost_per_million=15.00,
            output_cost_per_million=75.00,
            max_tokens=8192,
            supports_vision=True,
            supports_tools=True,
        ),
    },
}


# =============================================================================
# MODEL REGISTRY CLASS - OOP Interface
# =============================================================================


class ModelRegistry:
    """Object-oriented interface to the model registry.

    Provides efficient lookup operations with built-in tier and model ID caching
    for O(1) performance on frequently accessed queries.

    Example:
        >>> registry = ModelRegistry()
        >>> model = registry.get_model("anthropic", "capable")
        >>> print(model.id)
        claude-sonnet-4-5-20250929

        >>> models = registry.get_models_by_tier("cheap")
        >>> print(len(models))
        1

        >>> model = registry.get_model_by_id("claude-opus-4-6")
        >>> print(model.tier)
        premium

        >>> providers = registry.list_providers()
        >>> print(providers)
        ['anthropic']

    """

    def __init__(self, registry: dict[str, dict[str, ModelInfo]] | None = None):
        """Initialize the model registry.

        Args:
            registry: Optional custom registry dict. If None, uses MODEL_REGISTRY.

        """
        self._registry = registry if registry is not None else MODEL_REGISTRY

        # Build performance caches
        self._build_caches()

    def _build_caches(self) -> None:
        """Build tier and model ID caches for O(1) lookups."""
        # Cache for get_models_by_tier (tier -> list[ModelInfo])
        self._tier_cache: dict[str, list[ModelInfo]] = {}
        for tier in ModelTier:
            self._tier_cache[tier.value] = [
                provider_models[tier.value]
                for provider_models in self._registry.values()
                if tier.value in provider_models
            ]

        # Cache for get_model_by_id (model_id -> ModelInfo)
        self._model_id_cache: dict[str, ModelInfo] = {}
        for provider_models in self._registry.values():
            for model_info in provider_models.values():
                self._model_id_cache[model_info.id] = model_info

    def get_model(self, provider: str, tier: str) -> ModelInfo | None:
        """Get model info for a provider/tier combination.

        Args:
            provider: Provider name (anthropic only as of v5.0.0)
            tier: Tier level (cheap, capable, premium)

        Returns:
            ModelInfo if found, None otherwise

        Raises:
            ValueError: If provider is not 'anthropic'

        Example:
            >>> registry = ModelRegistry()
            >>> model = registry.get_model("anthropic", "capable")
            >>> print(model.id)
            claude-sonnet-4-5-20250929

        """
        if provider.lower() != "anthropic":
            raise ValueError(
                f"Provider '{provider}' is not supported. "
                f"Attune AI is now Claude-native (v5.0.0). "
                f"Only 'anthropic' provider is available. "
                f"See docs/CLAUDE_NATIVE.md for migration guide."
            )

        provider_models = self._registry.get(provider.lower())
        if provider_models is None:
            return None
        return provider_models.get(tier.lower())

    def get_model_by_id(self, model_id: str) -> ModelInfo | None:
        """Get model info by model ID.

        Uses O(1) cache lookup for fast performance.

        Args:
            model_id: Model identifier (e.g., "claude-haiku-4-5-20251001")

        Returns:
            ModelInfo if found, None otherwise

        Example:
            >>> registry = ModelRegistry()
            >>> model = registry.get_model_by_id("claude-opus-4-6")
            >>> print(model.provider)
            anthropic
            >>> print(model.tier)
            premium

        """
        return self._model_id_cache.get(model_id)

    def get_models_by_tier(self, tier: str) -> list[ModelInfo]:
        """Get all models in a specific tier (Anthropic-only as of v5.0.0).

        Uses O(1) cache lookup for fast performance.

        Args:
            tier: Tier level (cheap, capable, premium)

        Returns:
            List of ModelInfo objects in the tier (may be empty)

        Example:
            >>> registry = ModelRegistry()
            >>> cheap_models = registry.get_models_by_tier("cheap")
            >>> print(len(cheap_models))
            1
            >>> print([m.provider for m in cheap_models])
            ['anthropic']

            >>> premium_models = registry.get_models_by_tier("premium")
            >>> for model in premium_models:
            ...     print(f"{model.provider}: {model.id}")
            anthropic: claude-opus-4-6

        """
        return self._tier_cache.get(tier.lower(), [])

    def list_providers(self) -> list[str]:
        """Get list of all provider names (Anthropic-only as of v5.0.0).

        Returns:
            List of provider names (['anthropic'])

        Example:
            >>> registry = ModelRegistry()
            >>> providers = registry.list_providers()
            >>> print(providers)
            ['anthropic']

        """
        return list(self._registry.keys())

    def list_tiers(self) -> list[str]:
        """Get list of all available tiers.

        Returns:
            List of tier names (e.g., ['cheap', 'capable', 'premium'])

        Example:
            >>> registry = ModelRegistry()
            >>> tiers = registry.list_tiers()
            >>> print(tiers)
            ['cheap', 'capable', 'premium']

        """
        return [tier.value for tier in ModelTier]

    def get_all_models(self) -> dict[str, dict[str, ModelInfo]]:
        """Get the complete model registry (Anthropic-only as of v5.0.0).

        Returns:
            Full registry dict (provider -> tier -> ModelInfo)

        Example:
            >>> registry = ModelRegistry()
            >>> all_models = registry.get_all_models()
            >>> print(all_models.keys())
            dict_keys(['anthropic'])

        """
        return self._registry

    def get_pricing_for_model(self, model_id: str) -> dict[str, float] | None:
        """Get pricing for a model by its ID.

        Args:
            model_id: Model identifier (e.g., "claude-haiku-4-5-20251001")

        Returns:
            Dict with 'input' and 'output' keys (per-million pricing), or None

        Example:
            >>> registry = ModelRegistry()
            >>> pricing = registry.get_pricing_for_model("claude-sonnet-4-5-20250929")
            >>> print(pricing)
            {'input': 3.0, 'output': 15.0}

            >>> pricing = registry.get_pricing_for_model("claude-opus-4-6")
            >>> print(f"${pricing['input']}/M input, ${pricing['output']}/M output")
            $15.0/M input, $75.0/M output

        """
        model = self.get_model_by_id(model_id)
        if model is None:
            return None
        return model.to_cost_tracker_pricing()


# =============================================================================
# DEFAULT REGISTRY INSTANCE
# =============================================================================
# Global singleton instance for convenience
_default_registry = ModelRegistry()


# =============================================================================
# HELPER FUNCTIONS - Backward Compatibility
# =============================================================================
# These functions wrap the default registry instance to maintain
# backward compatibility with existing code.


def get_model(provider: str, tier: str) -> ModelInfo | None:
    """Get model info for a provider/tier combination.

    Args:
        provider: Provider name (anthropic only as of v5.0.0)
        tier: Tier level (cheap, capable, premium)

    Returns:
        ModelInfo if found, None otherwise

    Raises:
        ValueError: If provider is not 'anthropic'

    Note:
        This is a convenience wrapper around the default ModelRegistry instance.
        For more features, consider using ModelRegistry directly.

    """
    return _default_registry.get_model(provider, tier)


def get_all_models() -> dict[str, dict[str, ModelInfo]]:
    """Get the complete model registry.

    Note:
        This is a convenience wrapper around the default ModelRegistry instance.

    """
    return _default_registry.get_all_models()


def get_pricing_for_model(model_id: str) -> dict[str, float] | None:
    """Get pricing for a model by its ID.

    Args:
        model_id: Model identifier (e.g., "claude-haiku-4-5-20251001")

    Returns:
        Dict with 'input' and 'output' keys (per-million pricing), or None

    Note:
        This is a convenience wrapper around the default ModelRegistry instance.

    """
    return _default_registry.get_pricing_for_model(model_id)


def get_supported_providers() -> list[str]:
    """Get list of supported provider names.

    Note:
        This is a convenience wrapper around the default ModelRegistry instance.

    """
    return _default_registry.list_providers()


def get_tiers() -> list[str]:
    """Get list of available tiers.

    Note:
        This is a convenience wrapper around the default ModelRegistry instance.

    """
    return _default_registry.list_tiers()


# =============================================================================
# TIER PRICING (for backward compatibility with cost_tracker)
# =============================================================================
# These are tier-level pricing aliases for when specific model isn't known

TIER_PRICING: dict[str, dict[str, float]] = {
    "cheap": {"input": 1.00, "output": 5.00},  # Haiku 4.5 pricing
    "capable": {"input": 3.00, "output": 15.00},  # Sonnet 4.5 pricing
    "premium": {"input": 15.00, "output": 75.00},  # Opus 4.6 pricing
}
