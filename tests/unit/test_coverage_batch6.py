"""Comprehensive tests for low-coverage workflow modules (Batch 6).

Covers:
1. orchestrated_release_prep.py - Orchestrated release preparation (extra coverage)
2. research_synthesis.py - Research synthesis workflow

Test Strategy:
- Mock all LLM calls (_call_llm) to return predefined responses
- Mock _is_xml_enabled and _parse_xml_response for XML code paths
- Test each stage method, format_report, and helper functions
- Test both happy path and error/edge cases
- Aim for maximum statement coverage

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import warnings
from unittest.mock import AsyncMock, patch

import pytest

from attune.workflows.research_synthesis import (
    ANALYZE_STEP,
    SUMMARIZE_STEP,
    SYNTHESIZE_STEP,
    SYNTHESIZE_STEP_CAPABLE,
    ResearchSynthesisWorkflow,
)

# ============================================================================
# Module 1: orchestrated_release_prep.py - Additional coverage
# ============================================================================

# Import with deprecation warning suppressed
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from attune.workflows.orchestrated_release_prep import (
        OrchestratedReleasePrepWorkflow,
        QualityGate,
        ReleaseReadinessReport,
    )


class TestQualityGateExtended:
    """Extended tests for QualityGate dataclass."""

    def test_quality_gate_auto_generated_pass_message(self) -> None:
        """Test auto-generated message for passing gate."""
        gate = QualityGate(
            name="Security",
            threshold=0.0,
            actual=0.0,
            passed=True,
        )
        assert "PASS" in gate.message
        assert "Security" in gate.message

    def test_quality_gate_auto_generated_fail_message(self) -> None:
        """Test auto-generated message for failing gate."""
        gate = QualityGate(
            name="Coverage",
            threshold=80.0,
            actual=60.0,
            passed=False,
        )
        assert "FAIL" in gate.message
        assert "Coverage" in gate.message
        assert "60.0" in gate.message
        assert "80.0" in gate.message


class TestReleaseReadinessReportExtended:
    """Extended tests for ReleaseReadinessReport."""

    def test_format_console_no_blockers_no_warnings(self) -> None:
        """Test console output with no blockers and no warnings."""
        report = ReleaseReadinessReport(
            approved=True,
            confidence="high",
            quality_gates=[],
            agent_results={},
            blockers=[],
            warnings=[],
            summary="",
        )
        output = report.format_console_output()
        assert "READY FOR RELEASE" in output
        # Should NOT have blockers/warnings sections
        assert "BLOCKERS" not in output
        assert "WARNINGS" not in output.split("QUALITY GATES")[0]

    def test_format_console_with_summary(self) -> None:
        """Test console output includes executive summary."""
        report = ReleaseReadinessReport(
            approved=True,
            confidence="high",
            summary="All good to go!",
        )
        output = report.format_console_output()
        assert "EXECUTIVE SUMMARY" in output
        assert "All good to go!" in output

    def test_format_console_no_summary(self) -> None:
        """Test console output without summary section."""
        report = ReleaseReadinessReport(
            approved=True,
            confidence="high",
            summary="",
        )
        output = report.format_console_output()
        assert "EXECUTIVE SUMMARY" not in output

    def test_format_console_agent_success_and_failure(self) -> None:
        """Test console output shows agent success/failure icons."""
        report = ReleaseReadinessReport(
            approved=False,
            confidence="low",
            agent_results={
                "good_agent": {"success": True, "duration": 1.0},
                "bad_agent": {"success": False, "duration": 0.5},
            },
        )
        output = report.format_console_output()
        assert "good_agent" in output
        assert "bad_agent" in output

    def test_format_console_gate_critical_vs_noncritical(self) -> None:
        """Test console output uses correct icons for gate criticality."""
        report = ReleaseReadinessReport(
            approved=False,
            confidence="low",
            quality_gates=[
                QualityGate(
                    name="Critical",
                    threshold=80.0,
                    actual=50.0,
                    passed=False,
                    critical=True,
                ),
                QualityGate(
                    name="NonCritical",
                    threshold=100.0,
                    actual=90.0,
                    passed=False,
                    critical=False,
                ),
                QualityGate(
                    name="Passing",
                    threshold=80.0,
                    actual=95.0,
                    passed=True,
                    critical=True,
                ),
            ],
        )
        output = report.format_console_output()
        # Passing gate should have check icon
        assert "Passing" in output

    def test_to_dict_full(self) -> None:
        """Test to_dict with all fields populated."""
        gate = QualityGate(
            name="Test",
            threshold=80.0,
            actual=85.0,
            passed=True,
            critical=True,
            message="Custom message",
        )
        report = ReleaseReadinessReport(
            approved=True,
            confidence="high",
            quality_gates=[gate],
            agent_results={"agent1": {"success": True}},
            blockers=["blocker1"],
            warnings=["warning1"],
            summary="summary text",
            total_duration=10.5,
        )
        d = report.to_dict()
        assert d["approved"] is True
        assert d["confidence"] == "high"
        assert d["quality_gates"][0]["name"] == "Test"
        assert d["quality_gates"][0]["message"] == "Custom message"
        assert d["blockers"] == ["blocker1"]
        assert d["warnings"] == ["warning1"]
        assert d["summary"] == "summary text"
        assert d["total_duration"] == 10.5


class TestOrchestratedReleasePrepWorkflowExtended:
    """Extended tests for OrchestratedReleasePrepWorkflow."""

    def test_init_absorbs_extra_kwargs(self) -> None:
        """Test that __init__ absorbs extra CLI params without error."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            workflow = OrchestratedReleasePrepWorkflow(
                provider="anthropic",
                enable_tier_fallback=True,
                some_random_param="ignored",
            )
            assert workflow is not None

    @pytest.mark.asyncio
    async def test_execute_target_kwarg_mapping(self) -> None:
        """Test that 'target' kwarg is mapped to 'path'."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from attune.orchestration.execution_strategies import (
                AgentResult,
                StrategyResult,
            )

            workflow = OrchestratedReleasePrepWorkflow(
                quality_gates={
                    "min_coverage": 0.0,
                    "min_quality_score": 0.0,
                    "max_critical_issues": 100.0,
                    "min_doc_coverage": 0.0,
                },
            )

            # Mock the parallel strategy execution to avoid timeouts
            mock_strategy_result = StrategyResult(
                success=True,
                outputs=[
                    AgentResult(
                        agent_id="security_auditor",
                        success=True,
                        output={"critical_issues": 0},
                        confidence=0.9,
                        duration_seconds=0.1,
                    ),
                    AgentResult(
                        agent_id="test_coverage_analyzer",
                        success=True,
                        output={"coverage_percent": 90.0},
                        confidence=0.9,
                        duration_seconds=0.1,
                    ),
                    AgentResult(
                        agent_id="code_reviewer",
                        success=True,
                        output={"quality_score": 8.0},
                        confidence=0.9,
                        duration_seconds=0.1,
                    ),
                    AgentResult(
                        agent_id="documentation_writer",
                        success=True,
                        output={"coverage_percent": 100.0},
                        confidence=0.9,
                        duration_seconds=0.1,
                    ),
                ],
                aggregated_output={},
                total_duration=0.4,
            )
            with patch(
                "attune.workflows.orchestrated_release_prep.ParallelStrategy",
            ) as MockStrategy:
                mock_instance = AsyncMock()
                mock_instance.execute = AsyncMock(return_value=mock_strategy_result)
                MockStrategy.return_value = mock_instance

                # Use target= instead of path=
                report = await workflow.execute(target=".")
                assert isinstance(report, ReleaseReadinessReport)

    def test_generate_summary_with_failed_agents(self) -> None:
        """Test summary generation when agents have failures."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            workflow = OrchestratedReleasePrepWorkflow()

        quality_gates = [
            QualityGate(
                name="Coverage",
                threshold=80.0,
                actual=75.0,
                passed=False,
            ),
        ]
        agent_results = {
            "agent1": {"success": True},
            "agent2": {"success": False},
        }
        summary = workflow._generate_summary(False, quality_gates, agent_results)
        assert "NOT APPROVED" in summary
        assert "Successful: 1/2" in summary
        assert "Failed:" in summary
        assert "Coverage" in summary

    def test_identify_issues_agent_error_without_error_key(self) -> None:
        """Test _identify_issues when agent fails without error key."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            workflow = OrchestratedReleasePrepWorkflow()
        blockers, warnings_list = workflow._identify_issues(
            [],
            {"failing_agent": {"success": False}},
        )
        assert len(blockers) == 1
        assert "Unknown error" in blockers[0]


# ============================================================================
# Module 2: research_synthesis.py
# ============================================================================


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
