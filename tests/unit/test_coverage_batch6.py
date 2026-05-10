"""Extended coverage tests for research_synthesis workflow.

Originally Batch 6 of a coverage push that also covered
orchestrated_release_prep.py; that module was retired in v7.0.0.
The research_synthesis section remains as edge-case coverage on top
of tests/unit/workflows/test_research_synthesis.py.

Test Strategy:
- Mock all LLM calls (_call_llm) to return predefined responses
- Mock _is_xml_enabled and _parse_xml_response for XML code paths
- Test each stage method, format_report, and helper functions
- Test both happy path and error/edge cases
- Aim for maximum statement coverage

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from attune.workflows.research_synthesis import (
    ANALYZE_STEP,
    SUMMARIZE_STEP,
    SYNTHESIZE_STEP,
    SYNTHESIZE_STEP_CAPABLE,
    ResearchSynthesisWorkflow,
)


class TestWorkflowStepConfigs:
    """Tests for the module-level step configuration objects."""

    def test_summarize_step(self) -> None:
        """Test SUMMARIZE_STEP configuration."""
        assert SUMMARIZE_STEP.name == "summarize"
        assert SUMMARIZE_STEP.max_tokens == 2048
        assert "Summarize" in SUMMARIZE_STEP.description

    def test_analyze_step(self) -> None:
        """Test ANALYZE_STEP configuration."""
        assert ANALYZE_STEP.name == "analyze"
        assert ANALYZE_STEP.max_tokens == 2048

    def test_synthesize_step(self) -> None:
        """Test SYNTHESIZE_STEP configuration."""
        assert SYNTHESIZE_STEP.name == "synthesize"
        assert SYNTHESIZE_STEP.max_tokens == 4096

    def test_synthesize_step_capable(self) -> None:
        """Test SYNTHESIZE_STEP_CAPABLE configuration."""
        assert SYNTHESIZE_STEP_CAPABLE.name == "synthesize"
        assert SYNTHESIZE_STEP_CAPABLE.tier_hint == "capable"
        assert SYNTHESIZE_STEP_CAPABLE.max_tokens == 4096


class TestResearchSynthesisWorkflow:
    """Tests for ResearchSynthesisWorkflow (SDK-native)."""

    def test_initialization(self) -> None:
        """Test workflow initializes correctly."""
        wf = ResearchSynthesisWorkflow()
        assert wf.name == "research-synthesis"
        assert wf.stages == ["agent-synthesis"]
        assert "Agent SDK" in wf.description

    def test_class_tier_map(self) -> None:
        """Test tier map has agent-synthesis stage."""
        assert "agent-synthesis" in ResearchSynthesisWorkflow.tier_map

    def test_default_construction(self) -> None:
        """Default constructor succeeds."""
        wf = ResearchSynthesisWorkflow()
        assert wf is not None

    def test_constants_importable(self) -> None:
        """Step constants are importable."""
        assert isinstance(SUMMARIZE_STEP.name, str)
        assert isinstance(ANALYZE_STEP.name, str)
        assert isinstance(SYNTHESIZE_STEP.name, str)
        assert isinstance(SYNTHESIZE_STEP_CAPABLE.name, str)
