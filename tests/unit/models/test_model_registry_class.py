"""Tests for ModelRegistry OOP Interface - Coverage Boost

This test file adds coverage for ModelRegistry class methods that weren't
fully tested in test_registry.py (which focuses on helper functions).

Coverage targets:
- ModelRegistry.__init__ with custom registry
- ModelRegistry.get_model_by_id (O(1) cache lookup)
- ModelRegistry.get_models_by_tier (O(1) cache lookup)
- ModelRegistry cache building
- Edge cases and error handling

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import pytest

from attune.models.registry import MODEL_REGISTRY, ModelInfo, ModelRegistry


@pytest.mark.unit
class TestModelRegistryInitialization:
    """Test ModelRegistry initialization and cache building."""

    def test_default_initialization(self):
        """Test initialization with default MODEL_REGISTRY."""
        registry = ModelRegistry()

        assert registry is not None
        assert registry._registry is MODEL_REGISTRY

    def test_custom_registry_initialization(self):
        """Test initialization with custom registry."""
        custom_registry = {
            "test_provider": {
                "cheap": ModelInfo(
                    id="test-model-1",
                    provider="test_provider",
                    tier="cheap",
                    input_cost_per_million=1.0,
                    output_cost_per_million=5.0,
                ),
                "capable": ModelInfo(
                    id="test-model-2",
                    provider="test_provider",
                    tier="capable",
                    input_cost_per_million=3.0,
                    output_cost_per_million=15.0,
                ),
            }
        }

        registry = ModelRegistry(registry=custom_registry)

        assert registry._registry is custom_registry
        assert registry._registry is not MODEL_REGISTRY

    def test_cache_building_on_init(self):
        """Test that caches are built during initialization."""
        registry = ModelRegistry()

        # Tier cache should exist
        assert hasattr(registry, "_tier_cache")
        assert isinstance(registry._tier_cache, dict)

        # Model ID cache should exist
        assert hasattr(registry, "_model_id_cache")
        assert isinstance(registry._model_id_cache, dict)

    def test_tier_cache_populated(self):
        """Test that tier cache is properly populated."""
        registry = ModelRegistry()

        # Should have cache entries for all tiers
        assert "cheap" in registry._tier_cache
        assert "capable" in registry._tier_cache
        assert "premium" in registry._tier_cache

        # Each tier should have at least one model (Anthropic)
        assert len(registry._tier_cache["cheap"]) >= 1
        assert len(registry._tier_cache["capable"]) >= 1
        assert len(registry._tier_cache["premium"]) >= 1

    def test_model_id_cache_populated(self):
        """Test that model ID cache is properly populated."""
        registry = ModelRegistry()

        # Should have cache entries for all Anthropic models
        assert "claude-haiku-4-5-20251001" in registry._model_id_cache
        assert "claude-sonnet-4-5-20250929" in registry._model_id_cache
        assert "claude-opus-4-6" in registry._model_id_cache


@pytest.mark.unit
class TestGetModelById:
    """Test get_model_by_id method (O(1) cache lookup)."""

    def test_get_haiku_by_id(self):
        """Test retrieving Haiku model by ID."""
        registry = ModelRegistry()

        model = registry.get_model_by_id("claude-haiku-4-5-20251001")

        assert model is not None
        assert model.id == "claude-haiku-4-5-20251001"
        assert model.provider == "anthropic"
        assert model.tier == "cheap"

    def test_get_sonnet_by_id(self):
        """Test retrieving Sonnet model by ID."""
        registry = ModelRegistry()

        model = registry.get_model_by_id("claude-sonnet-4-5-20250929")

        assert model is not None
        assert model.id == "claude-sonnet-4-5-20250929"
        assert model.provider == "anthropic"
        assert model.tier == "capable"

    def test_get_opus_by_id(self):
        """Test retrieving Opus model by ID."""
        registry = ModelRegistry()

        model = registry.get_model_by_id("claude-opus-4-6")

        assert model is not None
        assert model.id == "claude-opus-4-6"
        assert model.provider == "anthropic"
        assert model.tier == "premium"

    def test_get_nonexistent_model_returns_none(self):
        """Test that non-existent model ID returns None."""
        registry = ModelRegistry()

        model = registry.get_model_by_id("nonexistent-model-id")

        assert model is None

    def test_get_model_by_id_uses_cache(self):
        """Test that get_model_by_id uses O(1) cache lookup."""
        registry = ModelRegistry()

        # First call
        model1 = registry.get_model_by_id("claude-sonnet-4-5-20250929")

        # Second call should return same object from cache
        model2 = registry.get_model_by_id("claude-sonnet-4-5-20250929")

        assert model1 is model2  # Same object reference


@pytest.mark.unit
class TestGetModelsByTier:
    """Test get_models_by_tier method (O(1) cache lookup)."""

    def test_get_cheap_models(self):
        """Test retrieving all cheap tier models."""
        registry = ModelRegistry()

        models = registry.get_models_by_tier("cheap")

        assert isinstance(models, list)
        assert len(models) >= 1  # At least Anthropic Haiku

        # All models should be cheap tier
        for model in models:
            assert model.tier == "cheap"

    def test_get_capable_models(self):
        """Test retrieving all capable tier models."""
        registry = ModelRegistry()

        models = registry.get_models_by_tier("capable")

        assert isinstance(models, list)
        assert len(models) >= 1  # At least Anthropic Sonnet

        # All models should be capable tier
        for model in models:
            assert model.tier == "capable"

    def test_get_premium_models(self):
        """Test retrieving all premium tier models."""
        registry = ModelRegistry()

        models = registry.get_models_by_tier("premium")

        assert isinstance(models, list)
        assert len(models) >= 1  # At least Anthropic Opus

        # All models should be premium tier
        for model in models:
            assert model.tier == "premium"

    def test_get_nonexistent_tier_returns_empty_list(self):
        """Test that non-existent tier returns empty list."""
        registry = ModelRegistry()

        models = registry.get_models_by_tier("nonexistent_tier")

        assert isinstance(models, list)
        assert len(models) == 0

    def test_get_models_by_tier_case_insensitive(self):
        """Test that tier lookup is case-insensitive."""
        registry = ModelRegistry()

        models1 = registry.get_models_by_tier("CHEAP")
        models2 = registry.get_models_by_tier("cheap")

        assert len(models1) == len(models2)
        assert models1[0].id == models2[0].id

    def test_get_models_by_tier_uses_cache(self):
        """Test that get_models_by_tier uses O(1) cache lookup."""
        registry = ModelRegistry()

        # First call
        models1 = registry.get_models_by_tier("cheap")

        # Second call should return same list from cache
        models2 = registry.get_models_by_tier("cheap")

        assert models1 is models2  # Same list reference


@pytest.mark.unit
class TestGetModel:
    """Test get_model method (provider + tier lookup)."""

    def test_get_anthropic_cheap(self):
        """Test getting Anthropic cheap model."""
        registry = ModelRegistry()

        model = registry.get_model("anthropic", "cheap")

        assert model is not None
        assert model.provider == "anthropic"
        assert model.tier == "cheap"
        assert "haiku" in model.id.lower()

    def test_get_anthropic_capable(self):
        """Test getting Anthropic capable model."""
        registry = ModelRegistry()

        model = registry.get_model("anthropic", "capable")

        assert model is not None
        assert model.provider == "anthropic"
        assert model.tier == "capable"
        assert "sonnet" in model.id.lower()

    def test_get_anthropic_premium(self):
        """Test getting Anthropic premium model."""
        registry = ModelRegistry()

        model = registry.get_model("anthropic", "premium")

        assert model is not None
        assert model.provider == "anthropic"
        assert model.tier == "premium"
        assert "opus" in model.id.lower()

    def test_get_model_invalid_provider_raises_error(self):
        """Test that invalid provider raises ValueError."""
        registry = ModelRegistry()

        with pytest.raises(ValueError, match="not supported"):
            registry.get_model("openai", "cheap")

    def test_get_model_invalid_tier_returns_none(self):
        """Test that invalid tier returns None."""
        registry = ModelRegistry()

        model = registry.get_model("anthropic", "invalid_tier")

        assert model is None

    def test_get_model_case_insensitive(self):
        """Test that provider and tier are case-insensitive."""
        registry = ModelRegistry()

        model1 = registry.get_model("ANTHROPIC", "CHEAP")
        model2 = registry.get_model("anthropic", "cheap")

        assert model1 is not None
        assert model1.id == model2.id


@pytest.mark.unit
class TestListMethods:
    """Test list_providers and list_tiers methods."""

    def test_list_providers(self):
        """Test listing all providers."""
        registry = ModelRegistry()

        providers = registry.list_providers()

        assert isinstance(providers, list)
        assert "anthropic" in providers
        # v5.0.0: Only Anthropic supported
        assert len(providers) == 1

    def test_list_tiers(self):
        """Test listing all tiers."""
        registry = ModelRegistry()

        tiers = registry.list_tiers()

        assert isinstance(tiers, list)
        assert "cheap" in tiers
        assert "capable" in tiers
        assert "premium" in tiers
        assert len(tiers) == 3

    def test_list_tiers_returns_tier_values(self):
        """Test that list_tiers returns tier enum values."""
        registry = ModelRegistry()

        tiers = registry.list_tiers()

        # Should return string values, not enum objects
        for tier in tiers:
            assert isinstance(tier, str)


@pytest.mark.unit
class TestGetAllModels:
    """Test get_all_models method."""

    def test_get_all_models_returns_registry(self):
        """Test that get_all_models returns the registry."""
        registry = ModelRegistry()

        all_models = registry.get_all_models()

        assert isinstance(all_models, dict)
        assert all_models is registry._registry

    def test_get_all_models_has_anthropic(self):
        """Test that registry contains Anthropic provider."""
        registry = ModelRegistry()

        all_models = registry.get_all_models()

        assert "anthropic" in all_models

    def test_get_all_models_structure(self):
        """Test that registry has correct structure."""
        registry = ModelRegistry()

        all_models = registry.get_all_models()

        # Each provider should have tiers
        for provider, tiers in all_models.items():
            assert isinstance(tiers, dict)

            # Each tier should have ModelInfo
            for tier, model_info in tiers.items():
                assert isinstance(model_info, ModelInfo)
                assert model_info.provider == provider
                assert model_info.tier == tier


@pytest.mark.unit
class TestGetPricingForModel:
    """Test get_pricing_for_model method."""

    def test_get_pricing_for_haiku(self):
        """Test getting pricing for Haiku model."""
        registry = ModelRegistry()

        pricing = registry.get_pricing_for_model("claude-haiku-4-5-20251001")

        assert pricing is not None
        assert "input" in pricing
        assert "output" in pricing
        assert pricing["input"] == 1.00
        assert pricing["output"] == 5.00

    def test_get_pricing_for_sonnet(self):
        """Test getting pricing for Sonnet model."""
        registry = ModelRegistry()

        pricing = registry.get_pricing_for_model("claude-sonnet-4-5-20250929")

        assert pricing is not None
        assert pricing["input"] == 3.00
        assert pricing["output"] == 15.00

    def test_get_pricing_for_opus(self):
        """Test getting pricing for Opus model."""
        registry = ModelRegistry()

        pricing = registry.get_pricing_for_model("claude-opus-4-6")

        assert pricing is not None
        assert pricing["input"] == 15.00
        assert pricing["output"] == 75.00

    def test_get_pricing_for_nonexistent_model(self):
        """Test that non-existent model returns None."""
        registry = ModelRegistry()

        pricing = registry.get_pricing_for_model("nonexistent-model")

        assert pricing is None


@pytest.mark.unit
class TestRegistryPerformance:
    """Test that caches provide O(1) performance."""

    def test_tier_cache_provides_o1_lookup(self):
        """Test that tier cache enables O(1) lookups."""
        registry = ModelRegistry()

        # Multiple calls should all hit cache
        for _ in range(100):
            models = registry.get_models_by_tier("cheap")
            assert len(models) >= 1

        # All calls should return same list reference (cache hit)
        models1 = registry.get_models_by_tier("cheap")
        models2 = registry.get_models_by_tier("cheap")
        assert models1 is models2

    def test_model_id_cache_provides_o1_lookup(self):
        """Test that model ID cache enables O(1) lookups."""
        registry = ModelRegistry()

        # Multiple calls should all hit cache
        for _ in range(100):
            model = registry.get_model_by_id("claude-sonnet-4-5-20250929")
            assert model is not None

        # All calls should return same object reference (cache hit)
        model1 = registry.get_model_by_id("claude-sonnet-4-5-20250929")
        model2 = registry.get_model_by_id("claude-sonnet-4-5-20250929")
        assert model1 is model2
