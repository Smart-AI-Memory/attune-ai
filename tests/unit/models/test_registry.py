"""Educational Tests for Model Registry (Phase 4 - Models & Providers)

Learning Objectives:
- Model registration and lookup
- Provider-tier mapping
- Model capability queries
- Protocol-based architecture testing

Key Patterns:
- Testing abstract interfaces
- Registry pattern testing
- Provider abstraction
"""

import pytest

from attune.models.registry import ModelInfo, ModelProvider, ModelTier


@pytest.mark.unit
class TestModelTier:
    """Educational tests for model tier enum."""

    def test_model_tier_hierarchy(self):
        """Teaching Pattern: Testing tier hierarchy.

        CHEAP < CAPABLE < PREMIUM for cost optimization.
        """
        assert ModelTier.CHEAP.value == "cheap"
        assert ModelTier.CAPABLE.value == "capable"
        assert ModelTier.PREMIUM.value == "premium"

    def test_tier_comparison(self):
        """Teaching Pattern: Testing enum ordering.

        Lower tiers should be less expensive.
        """
        # Tiers represent cost/capability levels
        tiers = [ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM]
        assert len(tiers) == 3


@pytest.mark.unit
class TestModelProvider:
    """Educational tests for model provider enum (Anthropic-only as of v5.0.0)."""

    def test_provider_values(self):
        """Teaching Pattern: Testing provider enumeration.

        Claude-native architecture supports only Anthropic provider.
        """
        assert ModelProvider.ANTHROPIC.value == "anthropic"

    def test_provider_to_string(self):
        """Teaching Pattern: Testing enum serialization.

        Providers need to serialize for API calls.
        """
        provider = ModelProvider.ANTHROPIC
        assert provider.value == "anthropic"
        assert str(provider.value) == "anthropic"

    def test_anthropic_provider(self):
        """Teaching Pattern: Testing Anthropic provider.

        Anthropic is the only supported provider in v5.0.0.
        """
        assert ModelProvider.ANTHROPIC.value == "anthropic"


@pytest.mark.unit
class TestModelInfo:
    """Educational tests for ModelInfo dataclass."""

    def test_model_info_creation(self):
        """Teaching Pattern: Testing dataclass initialization.

        ModelInfo stores model configuration.
        """
        model = ModelInfo(
            id="test-model",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=5.0,
            max_tokens=8192,
        )

        assert model.id == "test-model"
        assert model.provider == "anthropic"
        assert model.tier == "cheap"
        assert model.input_cost_per_million == 1.0
        assert model.output_cost_per_million == 5.0

    def test_model_info_compatibility_properties(self):
        """Teaching Pattern: Testing computed properties.

        ModelInfo provides compatibility properties for different systems.
        """
        model = ModelInfo(
            id="test-model",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1000.0,
            output_cost_per_million=5000.0,
        )

        # Compatibility aliases
        assert model.model_id == "test-model"
        assert model.name == "test-model"

        # Per-1k conversion (divide by 1000)
        assert model.cost_per_1k_input == 1.0
        assert model.cost_per_1k_output == 5.0

    def test_model_info_to_router_config(self):
        """Teaching Pattern: Testing conversion methods.

        ModelInfo can convert to different config formats.
        """
        model = ModelInfo(
            id="test-model",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1000.0,
            output_cost_per_million=5000.0,
            max_tokens=8192,
            supports_tools=True,
        )

        router_config = model.to_router_config()

        assert router_config["model_id"] == "test-model"
        assert router_config["cost_per_1k_input"] == 1.0
        assert router_config["max_tokens"] == 8192
        assert router_config["supports_tools"] is True

    def test_model_info_to_workflow_config(self):
        """Teaching Pattern: Testing workflow config conversion.

        Different systems need different config formats.
        """
        model = ModelInfo(
            id="test-model",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=5.0,
            supports_vision=True,
        )

        workflow_config = model.to_workflow_config()

        assert workflow_config["name"] == "test-model"
        assert workflow_config["provider"] == "anthropic"
        assert workflow_config["tier"] == "cheap"
        assert workflow_config["supports_vision"] is True

    def test_model_info_to_cost_tracker_pricing(self):
        """Teaching Pattern: Testing cost tracker conversion.

        Cost tracking needs pricing information.
        """
        model = ModelInfo(
            id="test-model",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=5.0,
        )

        pricing = model.to_cost_tracker_pricing()

        assert pricing["input"] == 1.0
        assert pricing["output"] == 5.0

    def test_model_info_frozen_dataclass(self):
        """Teaching Pattern: Testing immutability.

        ModelInfo is frozen - cannot be modified after creation.
        """
        model = ModelInfo(
            id="test-model",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=5.0,
        )

        # Attempting to modify should raise error
        with pytest.raises(AttributeError):  # FrozenInstanceError from dataclass
            model.id = "new-id"


@pytest.mark.unit
class TestModelRegistry:
    """Educational tests for MODEL_REGISTRY."""

    def test_registry_has_anthropic_provider(self):
        """Teaching Pattern: Testing registry structure.

        Registry should have Anthropic provider (Claude-native v5.0.0).
        """
        from attune.models.registry import MODEL_REGISTRY

        assert "anthropic" in MODEL_REGISTRY
        # v5.0.0: Only Anthropic provider supported
        assert len(MODEL_REGISTRY) == 1

    def test_anthropic_has_all_tiers(self):
        """Teaching Pattern: Testing registry completeness.

        Anthropic provider should have all tier levels.
        """
        from attune.models.registry import MODEL_REGISTRY

        anthropic = MODEL_REGISTRY["anthropic"]
        assert "cheap" in anthropic
        assert "capable" in anthropic
        assert "premium" in anthropic

    def test_anthropic_models(self):
        """Teaching Pattern: Testing specific provider models.

        Anthropic should have Haiku, Sonnet, and Opus.
        """
        from attune.models.registry import MODEL_REGISTRY

        anthropic = MODEL_REGISTRY["anthropic"]

        assert "haiku" in anthropic["cheap"].id.lower()
        assert "sonnet" in anthropic["capable"].id.lower()
        assert "opus" in anthropic["premium"].id.lower()


@pytest.mark.unit
class TestRegistryHelpers:
    """Educational tests for registry helper functions."""

    def test_get_model_success(self):
        """Teaching Pattern: Testing model lookup.

        get_model retrieves models by provider and tier.
        """
        from attune.models.registry import get_model

        model = get_model("anthropic", "cheap")

        assert model is not None
        assert model.provider == "anthropic"
        assert model.tier == "cheap"

    def test_get_model_case_insensitive(self):
        """Teaching Pattern: Testing case insensitivity.

        Lookups should work regardless of case.
        """
        from attune.models.registry import get_model

        model1 = get_model("ANTHROPIC", "CHEAP")
        model2 = get_model("anthropic", "cheap")

        assert model1 is not None
        assert model1.id == model2.id

    def test_get_model_invalid_provider(self):
        """Teaching Pattern: Testing error handling.

        Invalid provider should raise ValueError (v5.0.0: Anthropic-only).
        """
        from attune.models.registry import get_model

        with pytest.raises(ValueError, match="not supported"):
            get_model("invalid_provider", "cheap")

    def test_get_model_invalid_tier(self):
        """Teaching Pattern: Testing invalid tier.

        Invalid tier should return None.
        """
        from attune.models.registry import get_model

        model = get_model("anthropic", "invalid_tier")

        assert model is None

    def test_get_all_models(self):
        """Teaching Pattern: Testing registry access.

        get_all_models returns the complete registry (Anthropic-only v5.0.0).
        """
        from attune.models.registry import get_all_models

        all_models = get_all_models()

        assert isinstance(all_models, dict)
        assert "anthropic" in all_models
        assert len(all_models) == 1  # v5.0.0: Anthropic only

    def test_get_pricing_for_model(self):
        """Teaching Pattern: Testing pricing lookup by model ID.

        Can retrieve pricing for specific model ID.
        """
        from attune.models.registry import get_pricing_for_model

        pricing = get_pricing_for_model("claude-haiku-4-5-20251001")

        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] > 0

    def test_get_pricing_for_nonexistent_model(self):
        """Teaching Pattern: Testing pricing lookup failure.

        Non-existent model should return None.
        """
        from attune.models.registry import get_pricing_for_model

        pricing = get_pricing_for_model("nonexistent-model")

        assert pricing is None

    def test_get_supported_providers(self):
        """Teaching Pattern: Testing provider list.

        Can get list of all supported providers (Anthropic-only v5.0.0).
        """
        from attune.models.registry import get_supported_providers

        providers = get_supported_providers()

        assert isinstance(providers, list)
        assert "anthropic" in providers
        assert len(providers) == 1  # v5.0.0: Anthropic only

    def test_get_tiers(self):
        """Teaching Pattern: Testing tier list.

        Can get list of all available tiers.
        """
        from attune.models.registry import get_tiers

        tiers = get_tiers()

        assert isinstance(tiers, list)
        assert "cheap" in tiers
        assert "capable" in tiers
        assert "premium" in tiers
        assert len(tiers) == 3


@pytest.mark.unit
class TestTierPricing:
    """Educational tests for TIER_PRICING."""

    def test_tier_pricing_exists(self):
        """Teaching Pattern: Testing tier-level pricing.

        TIER_PRICING provides fallback pricing.
        """
        from attune.models.registry import TIER_PRICING

        assert "cheap" in TIER_PRICING
        assert "capable" in TIER_PRICING
        assert "premium" in TIER_PRICING

    def test_tier_pricing_structure(self):
        """Teaching Pattern: Testing pricing structure.

        Each tier has input and output pricing.
        """
        from attune.models.registry import TIER_PRICING

        for _tier, pricing in TIER_PRICING.items():
            assert "input" in pricing
            assert "output" in pricing
            assert pricing["input"] > 0
            assert pricing["output"] > 0

    def test_tier_pricing_hierarchy(self):
        """Teaching Pattern: Testing cost hierarchy.

        Premium should cost more than capable, which costs more than cheap.
        """
        from attune.models.registry import TIER_PRICING

        cheap_input = TIER_PRICING["cheap"]["input"]
        capable_input = TIER_PRICING["capable"]["input"]
        premium_input = TIER_PRICING["premium"]["input"]

        assert cheap_input < capable_input < premium_input
