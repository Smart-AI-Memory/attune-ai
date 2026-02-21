"""Backward compatibility module for deprecated workflow enums.

This module contains deprecated enums that were originally in base.py:
- ModelTier: Use attune.models.ModelTier instead
- ModelProvider: Use attune.models.ModelProvider instead

These are maintained for backward compatibility only.
New code should use attune.models imports directly.

Migration guide:
    # Old (deprecated):
    from attune.workflows.base import ModelTier, ModelProvider

    # New (recommended):
    from attune.models import ModelTier, ModelProvider

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import warnings
from enum import Enum
from typing import TYPE_CHECKING

# Import unified types for conversion
from attune.models import ModelProvider as UnifiedModelProvider
from attune.models import ModelTier as UnifiedModelTier

if TYPE_CHECKING:
    pass


class ModelTier(Enum):
    """DEPRECATED: Model tier for cost optimization.

    This enum is deprecated and will be removed in v5.0.
    Use attune.models.ModelTier instead.

    Migration:
        # Old:
        from attune.workflows.base import ModelTier

        # New:
        from attune.models import ModelTier

    Why deprecated:
        - Creates confusion with dual definitions
        - attune.models.ModelTier is the canonical location
        - Simplifies imports and reduces duplication
    """

    CHEAP = "cheap"  # Haiku/GPT-4o-mini - $0.25-1.25/M tokens
    CAPABLE = "capable"  # Sonnet/GPT-4o - $3-15/M tokens
    PREMIUM = "premium"  # Opus/o1 - $15-75/M tokens

    def __init__(self, value: str):
        """Initialize with deprecation warning."""
        # Only warn once per process, not per instance
        if not hasattr(self.__class__, "_deprecation_warned"):
            warnings.warn(
                "workflows.base.ModelTier is deprecated and will be removed in v5.0. "
                "Use attune.models.ModelTier instead. "
                "Update imports: from attune.models import ModelTier",
                DeprecationWarning,
                stacklevel=4,
            )
            self.__class__._deprecation_warned = True

    def to_unified(self) -> UnifiedModelTier:
        """Convert to unified ModelTier from attune.models."""
        return UnifiedModelTier(self.value)


class ModelProvider(Enum):
    """DEPRECATED: Supported model providers.

    This enum is deprecated and will be removed in v5.0.
    Use attune.models.ModelProvider instead.

    Migration:
        # Old:
        from attune.workflows.base import ModelProvider

        # New:
        from attune.models import ModelProvider
    """

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"  # Google Gemini models
    OLLAMA = "ollama"
    HYBRID = "hybrid"  # Mix of best models from different providers
    CUSTOM = "custom"  # User-defined custom models

    def to_unified(self) -> UnifiedModelProvider:
        """Convert to unified ModelProvider from attune.models.

        As of v5.0.0, framework is Claude-native. All providers map to ANTHROPIC.
        """
        # v5.0.0: Framework is Claude-native, only ANTHROPIC supported
        return UnifiedModelProvider.ANTHROPIC


def _build_provider_models() -> dict[ModelProvider, dict[ModelTier, str]]:
    """Build PROVIDER_MODELS from MODEL_REGISTRY.

    This ensures PROVIDER_MODELS stays in sync with the single source of truth.

    Returns:
        Dictionary mapping ModelProvider -> ModelTier -> model_id
    """
    # Lazy import to avoid circular dependencies
    from attune.models import MODEL_REGISTRY

    result: dict[ModelProvider, dict[ModelTier, str]] = {}

    # Map string provider names to ModelProvider enum
    provider_map = {
        "anthropic": ModelProvider.ANTHROPIC,
        "openai": ModelProvider.OPENAI,
        "google": ModelProvider.GOOGLE,
        "ollama": ModelProvider.OLLAMA,
        "hybrid": ModelProvider.HYBRID,
    }

    # Map string tier names to ModelTier enum
    tier_map = {
        "cheap": ModelTier.CHEAP,
        "capable": ModelTier.CAPABLE,
        "premium": ModelTier.PREMIUM,
    }

    for provider_str, tiers in MODEL_REGISTRY.items():
        if provider_str not in provider_map:
            continue  # Skip custom providers
        provider_enum = provider_map[provider_str]
        result[provider_enum] = {}
        for tier_str, model_info in tiers.items():
            if tier_str in tier_map:
                result[provider_enum][tier_map[tier_str]] = model_info.id

    return result


# Build PROVIDER_MODELS at module load time
PROVIDER_MODELS: dict[ModelProvider, dict[ModelTier, str]] = _build_provider_models()

# Expose all public symbols
__all__ = [
    "ModelTier",
    "ModelProvider",
    "PROVIDER_MODELS",
    "_build_provider_models",
]
