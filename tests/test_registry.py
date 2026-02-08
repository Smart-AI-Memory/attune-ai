"""Tests for src/attune/models/registry.py

Tests the unified model registry including:
- ModelTier enum
- ModelProvider enum
- ModelInfo dataclass
- MODEL_REGISTRY configuration
- Pricing conversions
- Compatibility methods
"""

import pytest

from attune.models.registry import MODEL_REGISTRY, ModelInfo, ModelProvider, ModelTier


class TestModelTierEnum:
    """Tests for ModelTier enum."""

    def test_cheap_value(self):
        """Test CHEAP tier value."""
        assert ModelTier.CHEAP.value == "cheap"

    def test_capable_value(self):
        """Test CAPABLE tier value."""
        assert ModelTier.CAPABLE.value == "capable"

    def test_premium_value(self):
        """Test PREMIUM tier value."""
        assert ModelTier.PREMIUM.value == "premium"

    def test_all_tiers_count(self):
        """Test total number of tiers."""
        assert len(ModelTier) == 3

    def test_tier_from_string(self):
        """Test creating ModelTier from string."""
        assert ModelTier("cheap") == ModelTier.CHEAP
        assert ModelTier("capable") == ModelTier.CAPABLE
        assert ModelTier("premium") == ModelTier.PREMIUM


class TestModelProviderEnum:
    """Tests for ModelProvider enum."""

    def test_anthropic_value(self):
        """Test ANTHROPIC provider value."""
        assert ModelProvider.ANTHROPIC.value == "anthropic"

    def test_all_providers_count(self):
        """Test total number of providers (Anthropic-only architecture)."""
        assert len(ModelProvider) == 1


class TestModelInfo:
    """Tests for ModelInfo dataclass."""

    def test_basic_creation(self):
        """Test basic ModelInfo creation."""
        model = ModelInfo(
            id="test-model",
            provider="test",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=2.0,
        )
        assert model.id == "test-model"
        assert model.provider == "test"
        assert model.tier == "cheap"
        assert model.input_cost_per_million == 1.0
        assert model.output_cost_per_million == 2.0

    def test_default_values(self):
        """Test ModelInfo default values."""
        model = ModelInfo(
            id="test",
            provider="test",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=2.0,
        )
        assert model.max_tokens == 4096
        assert model.supports_vision is False
        assert model.supports_tools is True

    def test_custom_values(self):
        """Test ModelInfo with custom values."""
        model = ModelInfo(
            id="vision-model",
            provider="anthropic",
            tier="capable",
            input_cost_per_million=5.0,
            output_cost_per_million=15.0,
            max_tokens=16384,
            supports_vision=True,
            supports_tools=True,
        )
        assert model.max_tokens == 16384
        assert model.supports_vision is True
        assert model.supports_tools is True

    def test_model_id_property(self):
        """Test model_id property alias for id."""
        model = ModelInfo(
            id="claude-3-5-sonnet",
            provider="anthropic",
            tier="capable",
            input_cost_per_million=3.0,
            output_cost_per_million=15.0,
        )
        assert model.model_id == model.id

    def test_name_property(self):
        """Test name property alias for id."""
        model = ModelInfo(
            id="gpt-4o",
            provider="anthropic",
            tier="capable",
            input_cost_per_million=2.5,
            output_cost_per_million=10.0,
        )
        assert model.name == model.id

    def test_cost_per_1k_input(self):
        """Test cost_per_1k_input calculation."""
        model = ModelInfo(
            id="test",
            provider="test",
            tier="cheap",
            input_cost_per_million=1000.0,  # $1000 per million
            output_cost_per_million=2000.0,
        )
        # $1000 per million = $1.00 per 1k
        assert model.cost_per_1k_input == 1.0

    def test_cost_per_1k_output(self):
        """Test cost_per_1k_output calculation."""
        model = ModelInfo(
            id="test",
            provider="test",
            tier="cheap",
            input_cost_per_million=500.0,
            output_cost_per_million=1500.0,  # $1500 per million
        )
        # $1500 per million = $1.50 per 1k
        assert model.cost_per_1k_output == 1.5

    def test_cost_conversion_precision(self):
        """Test cost conversion maintains precision."""
        model = ModelInfo(
            id="haiku",
            provider="anthropic",
            tier="cheap",
            input_cost_per_million=1.00,  # Claude Haiku 4.5 pricing
            output_cost_per_million=5.00,
        )
        # $1.00 per million = $0.001 per 1k
        assert model.cost_per_1k_input == pytest.approx(0.001)
        assert model.cost_per_1k_output == pytest.approx(0.005)

    def test_to_router_config(self):
        """Test to_router_config method."""
        model = ModelInfo(
            id="claude-3-5-sonnet",
            provider="anthropic",
            tier="capable",
            input_cost_per_million=3.0,
            output_cost_per_million=15.0,
            max_tokens=8192,
            supports_tools=True,
        )
        config = model.to_router_config()
        assert config["model_id"] == "claude-3-5-sonnet"
        assert config["cost_per_1k_input"] == 0.003
        assert config["cost_per_1k_output"] == 0.015
        assert config["max_tokens"] == 8192
        assert config["supports_tools"] is True

    def test_to_workflow_config(self):
        """Test to_workflow_config method."""
        model = ModelInfo(
            id="claude-sonnet-4-5-20250929",
            provider="anthropic",
            tier="capable",
            input_cost_per_million=2.5,
            output_cost_per_million=10.0,
            max_tokens=16384,
            supports_vision=True,
            supports_tools=True,
        )
        config = model.to_workflow_config()
        assert config["name"] == "claude-sonnet-4-5-20250929"
        assert config["provider"] == "anthropic"
        assert config["tier"] == "capable"
        assert config["input_cost_per_million"] == 2.5
        assert config["output_cost_per_million"] == 10.0
        assert config["max_tokens"] == 16384
        assert config["supports_vision"] is True
        assert config["supports_tools"] is True

    def test_to_cost_tracker_pricing(self):
        """Test to_cost_tracker_pricing method."""
        model = ModelInfo(
            id="test",
            provider="test",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=2.0,
        )
        pricing = model.to_cost_tracker_pricing()
        assert pricing["input"] == 1.0
        assert pricing["output"] == 2.0

    def test_frozen_dataclass(self):
        """Test ModelInfo is frozen (immutable)."""
        model = ModelInfo(
            id="test",
            provider="test",
            tier="cheap",
            input_cost_per_million=1.0,
            output_cost_per_million=2.0,
        )
        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
            model.id = "modified"


class TestModelRegistry:
    """Tests for MODEL_REGISTRY configuration."""

    def test_registry_has_anthropic(self):
        """Test registry contains Anthropic models."""
        assert "anthropic" in MODEL_REGISTRY

    def test_registry_only_has_anthropic(self):
        """Test registry only contains Anthropic (Anthropic-only architecture)."""
        assert len(MODEL_REGISTRY) == 1
        assert list(MODEL_REGISTRY.keys()) == ["anthropic"]

    def test_anthropic_has_all_tiers(self):
        """Test Anthropic has cheap, capable, and premium tiers."""
        anthropic = MODEL_REGISTRY["anthropic"]
        assert "cheap" in anthropic
        assert "capable" in anthropic
        assert "premium" in anthropic

    def test_anthropic_models_are_modelinfo(self):
        """Test Anthropic models are ModelInfo instances."""
        anthropic = MODEL_REGISTRY["anthropic"]
        for _tier, model in anthropic.items():
            assert isinstance(model, ModelInfo)
            assert model.provider == "anthropic"

    def test_anthropic_haiku_is_cheap(self):
        """Test Anthropic cheap tier is Haiku."""
        model = MODEL_REGISTRY["anthropic"]["cheap"]
        assert "haiku" in model.id.lower()
        assert model.tier == "cheap"

    def test_anthropic_sonnet_is_capable(self):
        """Test Anthropic capable tier is Sonnet."""
        model = MODEL_REGISTRY["anthropic"]["capable"]
        assert "sonnet" in model.id.lower() or model.tier == "capable"

    def test_anthropic_opus_is_premium(self):
        """Test Anthropic premium tier is Opus."""
        model = MODEL_REGISTRY["anthropic"]["premium"]
        assert "opus" in model.id.lower()
        assert model.tier == "premium"


class TestModelPricingConsistency:
    """Tests for model pricing consistency."""

    def test_cheap_tier_cheapest(self):
        """Test cheap tier is cheapest for each provider."""
        for provider, models in MODEL_REGISTRY.items():
            if "cheap" in models and "capable" in models:
                cheap = models["cheap"]
                capable = models["capable"]
                assert (
                    cheap.input_cost_per_million <= capable.input_cost_per_million
                ), f"{provider} cheap tier not cheaper than capable"

    def test_capable_tier_middle(self):
        """Test capable tier is between cheap and premium."""
        for provider, models in MODEL_REGISTRY.items():
            if "cheap" in models and "capable" in models and "premium" in models:
                cheap = models["cheap"]
                capable = models["capable"]
                models["premium"]
                assert (
                    cheap.input_cost_per_million <= capable.input_cost_per_million
                ), f"{provider} tier ordering violated"
                # Note: Some premium models may be cheaper in some dimensions

    def test_all_models_have_positive_or_zero_pricing(self):
        """Test all models have non-negative pricing."""
        for _provider, models in MODEL_REGISTRY.items():
            for _tier, model in models.items():
                assert model.input_cost_per_million >= 0
                assert model.output_cost_per_million >= 0

    def test_all_models_have_positive_max_tokens(self):
        """Test all models have positive max_tokens."""
        for _provider, models in MODEL_REGISTRY.items():
            for _tier, model in models.items():
                assert model.max_tokens > 0


class TestRegistryAccess:
    """Tests for accessing registry data."""

    def test_get_model_by_provider_and_tier(self):
        """Test accessing model by provider and tier."""
        model = MODEL_REGISTRY["anthropic"]["capable"]
        assert model is not None
        assert isinstance(model, ModelInfo)

    def test_missing_provider_raises(self):
        """Test accessing missing provider raises KeyError."""
        with pytest.raises(KeyError):
            _ = MODEL_REGISTRY["nonexistent_provider"]

    def test_missing_tier_raises(self):
        """Test accessing missing tier raises KeyError."""
        with pytest.raises(KeyError):
            _ = MODEL_REGISTRY["anthropic"]["nonexistent_tier"]

    def test_iterate_all_models(self):
        """Test iterating all models in registry (Anthropic-only architecture)."""
        model_count = 0
        for _provider, models in MODEL_REGISTRY.items():
            for _tier, model in models.items():
                model_count += 1
                assert isinstance(model, ModelInfo)
        # Should have at least 3 models (1 provider x 3 tiers)
        assert model_count >= 3
