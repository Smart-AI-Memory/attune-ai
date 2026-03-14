"""Tests for src/attune/workflows/document_gen.py

Tests the document generation workflow including:
- TOKEN_COSTS configuration
- DOC_GEN_STEPS configuration
- DocumentGenerationWorkflow class attributes
- Cost tier ordering
"""

from attune.workflows.base import ModelTier
from attune.workflows.document_gen import DOC_GEN_STEPS, TOKEN_COSTS, DocumentGenerationWorkflow


class TestTokenCosts:
    """Tests for TOKEN_COSTS configuration."""

    def test_has_cheap_tier(self):
        """Test TOKEN_COSTS has CHEAP tier."""
        assert ModelTier.CHEAP in TOKEN_COSTS

    def test_has_capable_tier(self):
        """Test TOKEN_COSTS has CAPABLE tier."""
        assert ModelTier.CAPABLE in TOKEN_COSTS

    def test_has_premium_tier(self):
        """Test TOKEN_COSTS has PREMIUM tier."""
        assert ModelTier.PREMIUM in TOKEN_COSTS

    def test_cheap_has_input_cost(self):
        """Test CHEAP tier has input cost."""
        assert "input" in TOKEN_COSTS[ModelTier.CHEAP]
        assert TOKEN_COSTS[ModelTier.CHEAP]["input"] > 0

    def test_cheap_has_output_cost(self):
        """Test CHEAP tier has output cost."""
        assert "output" in TOKEN_COSTS[ModelTier.CHEAP]
        assert TOKEN_COSTS[ModelTier.CHEAP]["output"] > 0

    def test_capable_costs_higher_than_cheap(self):
        """Test CAPABLE costs more than CHEAP."""
        assert TOKEN_COSTS[ModelTier.CAPABLE]["input"] > TOKEN_COSTS[ModelTier.CHEAP]["input"]
        assert TOKEN_COSTS[ModelTier.CAPABLE]["output"] > TOKEN_COSTS[ModelTier.CHEAP]["output"]

    def test_premium_costs_higher_than_capable(self):
        """Test PREMIUM costs more than CAPABLE."""
        assert TOKEN_COSTS[ModelTier.PREMIUM]["input"] > TOKEN_COSTS[ModelTier.CAPABLE]["input"]
        assert TOKEN_COSTS[ModelTier.PREMIUM]["output"] > TOKEN_COSTS[ModelTier.CAPABLE]["output"]

    def test_output_costs_higher_than_input(self):
        """Test output costs are higher than input costs for all tiers."""
        for tier in [ModelTier.CHEAP, ModelTier.CAPABLE, ModelTier.PREMIUM]:
            assert TOKEN_COSTS[tier]["output"] > TOKEN_COSTS[tier]["input"]


class TestDocGenSteps:
    """Tests for DOC_GEN_STEPS configuration."""

    def test_has_polish_step(self):
        """Test DOC_GEN_STEPS has polish step."""
        assert "polish" in DOC_GEN_STEPS

    def test_polish_step_name(self):
        """Test polish step name is correct."""
        assert DOC_GEN_STEPS["polish"].name == "polish"

    def test_polish_task_type(self):
        """Test polish step has final_review task type."""
        assert DOC_GEN_STEPS["polish"].task_type == "final_review"

    def test_polish_tier_hint(self):
        """Test polish step has premium tier hint."""
        assert DOC_GEN_STEPS["polish"].tier_hint == "premium"

    def test_polish_has_description(self):
        """Test polish step has a description."""
        assert DOC_GEN_STEPS["polish"].description
        assert len(DOC_GEN_STEPS["polish"].description) > 10

    def test_polish_max_tokens(self):
        """Test polish step has reasonable max_tokens."""
        assert DOC_GEN_STEPS["polish"].max_tokens >= 1000


class TestWorkflowClassAttributes:
    """Tests for workflow class attributes."""

    def test_workflow_name(self):
        """Test workflow name attribute."""
        assert DocumentGenerationWorkflow.name == "doc-gen"

    def test_workflow_description(self):
        """Test workflow description attribute."""
        assert "documentation" in DocumentGenerationWorkflow.description.lower()


class TestWorkflowInheritance:
    """Tests for workflow inheritance from BaseWorkflow."""

    def test_is_base_workflow_subclass(self):
        """Test DocumentGenerationWorkflow inherits from BaseWorkflow."""
        from attune.workflows.base import BaseWorkflow

        assert issubclass(DocumentGenerationWorkflow, BaseWorkflow)

    def test_has_name_attribute(self):
        """Test workflow has name attribute."""
        assert hasattr(DocumentGenerationWorkflow, "name")

    def test_has_description_attribute(self):
        """Test workflow has description attribute."""
        assert hasattr(DocumentGenerationWorkflow, "description")

    def test_has_stages_attribute(self):
        """Test workflow has stages attribute."""
        assert hasattr(DocumentGenerationWorkflow, "stages")

    def test_has_tier_map_attribute(self):
        """Test workflow has tier_map attribute."""
        assert hasattr(DocumentGenerationWorkflow, "tier_map")


class TestTierOrdering:
    """Tests for tier cost ordering."""

    def test_cheap_is_cheapest(self):
        """Test CHEAP tier is the cheapest."""
        cheap = TOKEN_COSTS[ModelTier.CHEAP]
        capable = TOKEN_COSTS[ModelTier.CAPABLE]
        premium = TOKEN_COSTS[ModelTier.PREMIUM]

        cheap_cost = cheap["input"] + cheap["output"]
        capable_cost = capable["input"] + capable["output"]
        premium_cost = premium["input"] + premium["output"]

        assert cheap_cost < capable_cost < premium_cost

    def test_premium_is_most_expensive(self):
        """Test PREMIUM tier is most expensive."""
        cheap = TOKEN_COSTS[ModelTier.CHEAP]
        premium = TOKEN_COSTS[ModelTier.PREMIUM]

        assert premium["input"] > cheap["input"]
        assert premium["output"] > cheap["output"]
