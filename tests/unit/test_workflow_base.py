"""Unit tests for workflow base module

Tests ModelTier, ModelProvider enums and base workflow functionality.
These tests import modules directly to contribute to coverage.
"""

import pytest

from attune.models import ModelProvider as UnifiedModelProvider
from attune.models import ModelTier as UnifiedModelTier
from attune.workflows.base import (
    WORKFLOW_HISTORY_FILE,
    ModelProvider,
    ModelTier,
    _build_provider_models,
)


@pytest.mark.unit
class TestModelTier:
    """Test ModelTier enum and conversions"""

    def test_model_tier_values(self):
        """Test that all model tiers have correct values"""
        assert ModelTier.CHEAP.value == "cheap"
        assert ModelTier.CAPABLE.value == "capable"
        assert ModelTier.PREMIUM.value == "premium"

    def test_model_tier_to_unified(self):
        """Test conversion to unified ModelTier"""
        cheap = ModelTier.CHEAP.to_unified()
        assert isinstance(cheap, UnifiedModelTier)
        assert cheap.value == "cheap"

        capable = ModelTier.CAPABLE.to_unified()
        assert isinstance(capable, UnifiedModelTier)
        assert capable.value == "capable"

        premium = ModelTier.PREMIUM.to_unified()
        assert isinstance(premium, UnifiedModelTier)
        assert premium.value == "premium"

    def test_model_tier_enum_members(self):
        """Test that all expected tiers exist"""
        tiers = list(ModelTier)
        assert len(tiers) == 3
        assert ModelTier.CHEAP in tiers
        assert ModelTier.CAPABLE in tiers
        assert ModelTier.PREMIUM in tiers


@pytest.mark.unit
class TestModelProvider:
    """Test ModelProvider enum and conversions"""

    def test_model_provider_values(self):
        """Test that all providers have correct values"""
        assert ModelProvider.ANTHROPIC.value == "anthropic"
        assert ModelProvider.OPENAI.value == "openai"
        assert ModelProvider.GOOGLE.value == "google"
        assert ModelProvider.OLLAMA.value == "ollama"
        assert ModelProvider.HYBRID.value == "hybrid"
        assert ModelProvider.CUSTOM.value == "custom"

    def test_model_provider_to_unified(self):
        """Test conversion to unified ModelProvider.

        As of v5.0.0, framework is Claude-native. All providers map to ANTHROPIC.
        """
        anthropic = ModelProvider.ANTHROPIC.to_unified()
        assert isinstance(anthropic, UnifiedModelProvider)
        assert anthropic.value == "anthropic"

        # v5.0.0: All providers map to ANTHROPIC (Claude-native)
        openai = ModelProvider.OPENAI.to_unified()
        assert isinstance(openai, UnifiedModelProvider)
        assert openai.value == "anthropic"  # Maps to anthropic in v5.0

    def test_all_providers_can_convert(self):
        """Test that all provider enums can convert to unified.

        As of v5.0.0, framework is Claude-native. All providers map to ANTHROPIC.
        """
        for provider in ModelProvider:
            unified = provider.to_unified()
            assert isinstance(unified, UnifiedModelProvider)
            # v5.0.0: All providers map to ANTHROPIC
            assert unified.value == "anthropic"


@pytest.mark.unit
class TestProviderModels:
    """Test provider models building from registry"""

    def test_build_provider_models_returns_dict(self):
        """Test that _build_provider_models returns a valid dict"""
        provider_models = _build_provider_models()
        assert isinstance(provider_models, dict)

    def test_build_provider_models_has_providers(self):
        """Test that built models include expected providers"""
        provider_models = _build_provider_models()

        # Should have at least some providers
        assert len(provider_models) > 0

    def test_build_provider_models_structure(self):
        """Test that each provider maps tiers to model names"""
        provider_models = _build_provider_models()

        for _provider, tiers in provider_models.items():
            assert isinstance(tiers, dict)
            # Each tier should map to a string (model name)
            for _tier, model_name in tiers.items():
                assert isinstance(model_name, str)
                assert len(model_name) > 0


@pytest.mark.unit
class TestWorkflowConstants:
    """Test workflow module constants"""

    def test_workflow_history_file_path(self):
        """Test that workflow history file constant is defined"""
        assert WORKFLOW_HISTORY_FILE == ".attune/workflow_runs.json"
        assert isinstance(WORKFLOW_HISTORY_FILE, str)
        assert WORKFLOW_HISTORY_FILE.endswith(".json")
