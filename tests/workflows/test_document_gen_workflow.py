"""Tests for DocumentGenerationWorkflow.

Tests the multi-tier documentation generation pipeline with:
- TOKEN_COSTS configuration

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.workflows.base import ModelTier
from attune.workflows.document_gen import TOKEN_COSTS


class TestTokenCosts:
    """Tests for token cost constants."""

    def test_token_costs_exist(self):
        """Test that token costs are defined for all tiers."""
        assert ModelTier.CHEAP in TOKEN_COSTS
        assert ModelTier.CAPABLE in TOKEN_COSTS
        assert ModelTier.PREMIUM in TOKEN_COSTS

    def test_token_costs_structure(self):
        """Test that token costs have input and output keys."""
        for tier in [ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM]:
            assert "input" in TOKEN_COSTS[tier]
            assert "output" in TOKEN_COSTS[tier]
            assert TOKEN_COSTS[tier]["input"] > 0 or tier == ModelTier.CHEAP
            assert TOKEN_COSTS[tier]["output"] > 0

    def test_tier_cost_ordering(self):
        """Test that premium costs more than capable costs more than cheap."""
        assert TOKEN_COSTS[ModelTier.PREMIUM]["input"] > TOKEN_COSTS[ModelTier.CAPABLE]["input"]
        assert TOKEN_COSTS[ModelTier.CAPABLE]["input"] > TOKEN_COSTS[ModelTier.CHEAP]["input"]
