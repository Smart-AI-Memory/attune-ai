"""Tests for ResearchSynthesisWorkflow.

Covers initialization, source validation, tier downgrade logic,
stage routing, and end-to-end execute().

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import AsyncMock, patch

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.research_synthesis import ResearchSynthesisWorkflow


@pytest.mark.unit
class TestResearchSynthesisInit:
    """Verify class attributes and initialization."""

    def test_class_attributes(self, research_synthesis_workflow):
        wf = research_synthesis_workflow
        assert wf.name == "research"
        assert wf.stages == ["summarize", "analyze", "synthesize"]
        assert wf.tier_map == {
            "summarize": ModelTier.CHEAP,
            "analyze": ModelTier.CAPABLE,
            "synthesize": ModelTier.PREMIUM,
        }

    def test_default_complexity_threshold(self, research_synthesis_workflow):
        assert research_synthesis_workflow.complexity_threshold == 0.7

    def test_custom_complexity_threshold(self, cost_tracker):
        wf = ResearchSynthesisWorkflow(complexity_threshold=0.5, cost_tracker=cost_tracker)
        assert wf.complexity_threshold == 0.5

    def test_min_sources_constant(self):
        assert ResearchSynthesisWorkflow.MIN_SOURCES == 2


@pytest.mark.unit
class TestValidateSources:
    """Tests for validate_sources()."""

    def test_raises_on_empty_sources(self, research_synthesis_workflow):
        with pytest.raises(ValueError, match="at least 2"):
            research_synthesis_workflow.validate_sources([])

    def test_raises_on_one_source(self, research_synthesis_workflow):
        with pytest.raises(ValueError, match="at least 2"):
            research_synthesis_workflow.validate_sources(["only one"])

    def test_raises_on_none(self, research_synthesis_workflow):
        with pytest.raises(ValueError, match="at least 2"):
            research_synthesis_workflow.validate_sources(None)

    def test_passes_with_two_sources(self, research_synthesis_workflow):
        research_synthesis_workflow.validate_sources(["doc1", "doc2"])

    def test_passes_with_many_sources(self, research_synthesis_workflow):
        research_synthesis_workflow.validate_sources(["a", "b", "c", "d", "e"])


@pytest.mark.unit
class TestShouldSkipStage:
    """Tests for should_skip_stage() tier downgrade logic."""

    def test_downgrades_synthesize_when_low_complexity(self, research_synthesis_workflow):
        """When complexity < threshold, synthesize tier should downgrade."""
        research_synthesis_workflow._detected_complexity = 0.3
        skip, reason = research_synthesis_workflow.should_skip_stage("synthesize", {})

        assert skip is False  # doesn't skip, just downgrades
        assert research_synthesis_workflow.tier_map["synthesize"] == ModelTier.CAPABLE

    def test_keeps_premium_when_high_complexity(self, research_synthesis_workflow):
        """When complexity >= threshold, synthesize stays PREMIUM."""
        research_synthesis_workflow._detected_complexity = 0.9
        # Reset tier_map to PREMIUM (may have been modified by previous test)
        research_synthesis_workflow.tier_map["synthesize"] = ModelTier.PREMIUM

        skip, reason = research_synthesis_workflow.should_skip_stage("synthesize", {})

        assert skip is False
        assert research_synthesis_workflow.tier_map["synthesize"] == ModelTier.PREMIUM

    def test_does_not_skip_other_stages(self, research_synthesis_workflow):
        skip, reason = research_synthesis_workflow.should_skip_stage("summarize", {})
        assert skip is False

        skip, reason = research_synthesis_workflow.should_skip_stage("analyze", {})
        assert skip is False


@pytest.mark.unit
class TestRunStage:
    """Tests for run_stage() routing."""

    @pytest.mark.asyncio
    async def test_summarize_stage(self, research_synthesis_workflow):
        """Summarize should call _call_llm once per source."""
        input_data = {
            "sources": ["Source A content", "Source B content"],
            "question": "Compare approaches",
        }

        with patch.object(
            research_synthesis_workflow,
            "_call_llm",
            new_callable=AsyncMock,
            return_value=("Summary text", 100, 50),
        ) as mock_llm:
            result, inp, out = await research_synthesis_workflow.run_stage(
                "summarize", ModelTier.CHEAP, input_data
            )

        assert mock_llm.call_count == 2
        assert result["source_count"] == 2
        assert len(result["summaries"]) == 2
        assert inp == 200
        assert out == 100

    @pytest.mark.asyncio
    async def test_analyze_stage_sets_complexity(self, research_synthesis_workflow):
        """Analyze should estimate complexity from response length."""
        input_data = {
            "summaries": [
                {"source": "A", "summary": "Summary A"},
                {"source": "B", "summary": "Summary B"},
            ],
            "question": "Compare",
        }

        # Return a long response to test complexity calculation
        long_response = "x" * 1500  # 1500 / 2000 = 0.75

        with patch.object(
            research_synthesis_workflow,
            "_call_llm",
            new_callable=AsyncMock,
            return_value=(long_response, 200, 150),
        ):
            result, _, _ = await research_synthesis_workflow.run_stage(
                "analyze", ModelTier.CAPABLE, input_data
            )

        assert result["complexity"] == pytest.approx(0.75)
        assert research_synthesis_workflow._detected_complexity == pytest.approx(0.75)

    @pytest.mark.asyncio
    async def test_synthesize_stage(self, research_synthesis_workflow):
        input_data = {
            "patterns": [{"pattern": "test", "sources": [], "confidence": 0.85}],
            "complexity": 0.5,
            "question": "What are the key patterns?",
            "analysis": "Test analysis",
        }

        with (
            patch.object(
                research_synthesis_workflow,
                "_call_llm",
                new_callable=AsyncMock,
                return_value=("Synthesis result", 300, 200),
            ),
            patch.object(
                research_synthesis_workflow,
                "_is_xml_enabled",
                return_value=False,
            ),
            patch.object(
                research_synthesis_workflow,
                "_parse_xml_response",
                return_value={},
            ),
        ):
            result, inp, out = await research_synthesis_workflow.run_stage(
                "synthesize", ModelTier.PREMIUM, input_data
            )

        assert result["answer"] == "Synthesis result"
        assert result["model_tier_used"] == ModelTier.PREMIUM.value

    @pytest.mark.asyncio
    async def test_unknown_stage_raises(self, research_synthesis_workflow):
        with pytest.raises(ValueError, match="Unknown stage"):
            await research_synthesis_workflow.run_stage("nonexistent", ModelTier.CHEAP, {})


@pytest.mark.unit
class TestExecute:
    """Tests for the execute() entry point."""

    @pytest.mark.asyncio
    async def test_execute_validates_sources(self, research_synthesis_workflow):
        """execute() should raise ValueError before running stages."""
        with pytest.raises(ValueError, match="at least 2"):
            await research_synthesis_workflow.execute(sources=["only one"], question="test")
