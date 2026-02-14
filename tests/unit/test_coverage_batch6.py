"""Comprehensive tests for low-coverage workflow modules (Batch 6).

Covers:
1. manage_documentation.py - Documentation management crew workflow
2. orchestrated_release_prep.py - Orchestrated release preparation (extra coverage)
3. seo_optimization.py - SEO optimization workflow
4. research_synthesis.py - Research synthesis workflow

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
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============================================================================
# Module 1: manage_documentation.py
# ============================================================================
from attune.workflows.manage_documentation import (
    Agent,
    ManageDocumentationCrew,
    ManageDocumentationCrewResult,
    Task,
    format_manage_docs_report,
    parse_xml_response,
)
from attune.workflows.research_synthesis import (
    ANALYZE_STEP,
    SUMMARIZE_STEP,
    SYNTHESIZE_STEP,
    SYNTHESIZE_STEP_CAPABLE,
    ResearchSynthesisWorkflow,
)
from attune.workflows.seo_optimization import (
    SEOOptimizationConfig,
    SEOOptimizationWorkflow,
)


class TestManageDocumentationCrewResult:
    """Tests for the ManageDocumentationCrewResult dataclass."""

    def test_result_defaults(self) -> None:
        """Test ManageDocumentationCrewResult default values."""
        result = ManageDocumentationCrewResult(success=True)
        assert result.success is True
        assert result.findings == []
        assert result.recommendations == []
        assert result.files_analyzed == 0
        assert result.docs_needing_update == 0
        assert result.new_docs_needed == 0
        assert result.confidence == 0.0
        assert result.cost == 0.0
        assert result.duration_ms == 0
        assert result.formatted_report == ""

    def test_result_to_dict(self) -> None:
        """Test ManageDocumentationCrewResult.to_dict serialization."""
        result = ManageDocumentationCrewResult(
            success=True,
            findings=[{"agent": "test", "response": "data"}],
            recommendations=["Fix docs", "Add more coverage"],
            files_analyzed=42,
            docs_needing_update=5,
            new_docs_needed=3,
            confidence=0.85,
            cost=0.0123,
            duration_ms=1500,
            formatted_report="report text",
        )
        d = result.to_dict()
        assert d["success"] is True
        assert len(d["findings"]) == 1
        assert len(d["recommendations"]) == 2
        assert d["files_analyzed"] == 42
        assert d["docs_needing_update"] == 5
        assert d["new_docs_needed"] == 3
        assert d["confidence"] == 0.85
        assert d["cost"] == 0.0123
        assert d["duration_ms"] == 1500
        assert d["formatted_report"] == "report text"

    def test_result_to_dict_empty(self) -> None:
        """Test to_dict with all default (empty) values."""
        result = ManageDocumentationCrewResult(success=False)
        d = result.to_dict()
        assert d["success"] is False
        assert d["findings"] == []
        assert d["recommendations"] == []


class TestAgent:
    """Tests for the Agent dataclass."""

    def test_agent_defaults(self) -> None:
        """Test Agent default field values."""
        agent = Agent(
            role="Tester",
            goal="Test things",
            backstory="Expert tester",
        )
        assert agent.expertise_level == "expert"
        assert agent.use_xml_structure is True

    def test_get_system_prompt_xml(self) -> None:
        """Test XML-enhanced system prompt generation."""
        agent = Agent(
            role="Analyst",
            goal="Analyze code",
            backstory="Senior analyst",
            expertise_level="world-class",
            use_xml_structure=True,
        )
        prompt = agent.get_system_prompt()
        assert "<agent_role>" in prompt
        assert "Analyst" in prompt
        assert "world-class" in prompt
        assert "<agent_goal>" in prompt
        assert "Analyze code" in prompt
        assert "<agent_backstory>" in prompt
        assert "Senior analyst" in prompt
        assert "<instructions>" in prompt
        assert "<output_structure>" in prompt
        assert "<thinking>" in prompt
        assert "<answer>" in prompt

    def test_get_system_prompt_legacy(self) -> None:
        """Test legacy (non-XML) system prompt generation."""
        agent = Agent(
            role="Analyst",
            goal="Analyze code",
            backstory="Senior analyst",
            expertise_level="expert",
            use_xml_structure=False,
        )
        prompt = agent.get_system_prompt()
        # Legacy format should NOT have XML tags
        assert "<agent_role>" not in prompt
        assert "You are a Analyst" in prompt
        assert "Goal: Analyze code" in prompt
        assert "Background: Senior analyst" in prompt
        assert "actionable analysis" in prompt


class TestTask:
    """Tests for the Task dataclass."""

    def test_get_user_prompt_xml(self) -> None:
        """Test XML-enhanced user prompt generation."""
        agent = Agent(
            role="Reviewer",
            goal="Review docs",
            backstory="Experienced reviewer",
            use_xml_structure=True,
        )
        task = Task(
            description="Review the documentation",
            expected_output="Validated findings",
            agent=agent,
        )
        context = {
            "path": "./src",
            "python_files": "50 files",
            "empty_key": "",  # Should be excluded from context
        }
        prompt = task.get_user_prompt(context)
        assert "<task_description>" in prompt
        assert "Review the documentation" in prompt
        assert "<context>" in prompt
        assert "<path>" in prompt
        assert "./src" in prompt
        assert "<python_files>" in prompt
        assert "<expected_output>" in prompt
        # Empty values should be excluded from context XML
        assert "<empty_key>" not in prompt

    def test_get_user_prompt_legacy(self) -> None:
        """Test legacy (non-XML) user prompt generation."""
        agent = Agent(
            role="Reviewer",
            goal="Review docs",
            backstory="Experienced reviewer",
            use_xml_structure=False,
        )
        task = Task(
            description="Review the documentation",
            expected_output="Validated findings",
            agent=agent,
        )
        context = {"path": "./src", "files": "10 files"}
        prompt = task.get_user_prompt(context)
        assert "Review the documentation" in prompt
        assert "Context:" in prompt
        assert "path: ./src" in prompt
        assert "Expected output format: Validated findings" in prompt
        # Legacy should NOT have XML tags
        assert "<task_description>" not in prompt

    def test_get_user_prompt_xml_tag_name_sanitization(self) -> None:
        """Test that context keys with spaces/hyphens become valid XML tags."""
        agent = Agent(
            role="Test",
            goal="Test",
            backstory="Test",
            use_xml_structure=True,
        )
        task = Task(description="Test", expected_output="Test", agent=agent)
        context = {"sample-files": "data", "long name key": "value"}
        prompt = task.get_user_prompt(context)
        # Hyphens and spaces should be converted to underscores
        assert "<sample_files>" in prompt
        assert "<long_name_key>" in prompt


class TestParseXmlResponse:
    """Tests for the parse_xml_response function."""

    def test_parse_structured_response(self) -> None:
        """Test parsing response with both thinking and answer tags."""
        response = """<thinking>
I analyzed the codebase and found issues.
</thinking>

<answer>
Found 3 documentation gaps in src/attune/workflows.
</answer>"""
        parsed = parse_xml_response(response)
        assert parsed["has_structure"] is True
        assert "analyzed the codebase" in parsed["thinking"]
        assert "3 documentation gaps" in parsed["answer"]
        assert parsed["raw"] == response

    def test_parse_unstructured_response(self) -> None:
        """Test parsing response without XML tags."""
        response = "This is a plain text response with no XML structure."
        parsed = parse_xml_response(response)
        assert parsed["has_structure"] is False
        assert parsed["thinking"] == ""
        assert parsed["answer"] == response.strip()
        assert parsed["raw"] == response

    def test_parse_partial_xml_thinking_only(self) -> None:
        """Test parsing response with only thinking tag."""
        response = "<thinking>Just thinking</thinking>\nSome plain text."
        parsed = parse_xml_response(response)
        assert parsed["has_structure"] is False  # Both must be present
        assert parsed["thinking"] == "Just thinking"
        assert parsed["answer"] == response.strip()

    def test_parse_partial_xml_answer_only(self) -> None:
        """Test parsing response with only answer tag."""
        response = "Preamble\n<answer>The answer</answer>"
        parsed = parse_xml_response(response)
        assert parsed["has_structure"] is False
        assert parsed["thinking"] == ""
        assert parsed["answer"] == "The answer"

    def test_parse_empty_response(self) -> None:
        """Test parsing an empty string."""
        parsed = parse_xml_response("")
        assert parsed["has_structure"] is False
        assert parsed["thinking"] == ""
        assert parsed["answer"] == ""
        assert parsed["raw"] == ""


class TestFormatManageDocsReport:
    """Tests for the format_manage_docs_report function."""

    def test_format_report_high_confidence(self) -> None:
        """Test report formatting with high confidence (>=0.8)."""
        result = ManageDocumentationCrewResult(
            success=True,
            findings=[
                {
                    "agent": "Documentation Analyst",
                    "response": "Found gaps",
                    "thinking": "",
                    "answer": "",
                    "has_xml_structure": False,
                    "cost": 0.001,
                }
            ],
            recommendations=["Add docstrings", "Update README"],
            files_analyzed=100,
            docs_needing_update=5,
            new_docs_needed=2,
            confidence=0.9,
            cost=0.05,
            duration_ms=3000,
        )
        report = format_manage_docs_report(result, "./src")
        assert "DOCUMENTATION SYNC REPORT" in report
        assert "HIGH CONFIDENCE" in report
        assert "./src" in report
        assert "Files Analyzed: 100" in report
        assert "Docs Needing Update: 5" in report
        assert "New Docs Needed: 2" in report
        assert "Duration: 3000ms (3.0s)" in report
        assert "AGENT FINDINGS" in report
        assert "Documentation Analyst" in report
        assert "RECOMMENDATIONS" in report
        assert "Add docstrings" in report
        assert "NEXT STEPS" in report
        assert "Documentation sync analysis complete" in report

    def test_format_report_moderate_confidence(self) -> None:
        """Test report formatting with moderate confidence (0.5 <= c < 0.8)."""
        result = ManageDocumentationCrewResult(
            success=True,
            confidence=0.6,
        )
        report = format_manage_docs_report(result, ".")
        assert "MODERATE CONFIDENCE" in report

    def test_format_report_low_confidence(self) -> None:
        """Test report formatting with low confidence (<0.5)."""
        result = ManageDocumentationCrewResult(
            success=True,
            confidence=0.2,
        )
        report = format_manage_docs_report(result, ".")
        assert "LOW CONFIDENCE (Mock Mode)" in report

    def test_format_report_xml_structured_finding(self) -> None:
        """Test report with XML-structured finding (thinking and answer)."""
        result = ManageDocumentationCrewResult(
            success=True,
            findings=[
                {
                    "agent": "Analyst",
                    "response": "Full response text",
                    "thinking": "My analysis process",
                    "answer": "Final conclusions",
                    "has_xml_structure": True,
                    "cost": 0.002,
                }
            ],
            confidence=0.8,
        )
        report = format_manage_docs_report(result, ".")
        assert "XML-Structured" in report
        assert "Thinking:" in report
        assert "My analysis process" in report
        assert "Answer:" in report
        assert "Final conclusions" in report

    def test_format_report_long_thinking_truncated(self) -> None:
        """Test that long thinking text is truncated."""
        long_thinking = "A" * 500
        result = ManageDocumentationCrewResult(
            success=True,
            findings=[
                {
                    "agent": "Analyst",
                    "response": "x",
                    "thinking": long_thinking,
                    "answer": "short",
                    "has_xml_structure": True,
                    "cost": 0.0,
                }
            ],
            confidence=0.8,
        )
        report = format_manage_docs_report(result, ".")
        # Thinking should be truncated at 300 chars + "..."
        assert "..." in report

    def test_format_report_long_answer_truncated(self) -> None:
        """Test that long answer text is truncated."""
        long_answer = "B" * 500
        result = ManageDocumentationCrewResult(
            success=True,
            findings=[
                {
                    "agent": "Analyst",
                    "response": "x",
                    "thinking": "short",
                    "answer": long_answer,
                    "has_xml_structure": True,
                    "cost": 0.0,
                }
            ],
            confidence=0.8,
        )
        report = format_manage_docs_report(result, ".")
        assert "..." in report

    def test_format_report_long_response_truncated(self) -> None:
        """Test that long non-XML response is truncated."""
        long_response = "C" * 600
        result = ManageDocumentationCrewResult(
            success=True,
            findings=[
                {
                    "agent": "Analyst",
                    "response": long_response,
                    "thinking": "",
                    "answer": "",
                    "has_xml_structure": False,
                    "cost": 0.0,
                }
            ],
            confidence=0.8,
        )
        report = format_manage_docs_report(result, ".")
        assert "Truncated" in report

    def test_format_report_failed(self) -> None:
        """Test report formatting when workflow fails."""
        result = ManageDocumentationCrewResult(success=False, confidence=0.1)
        report = format_manage_docs_report(result, ".")
        assert "Documentation sync analysis failed" in report

    def test_format_report_no_findings_no_recommendations(self) -> None:
        """Test report with empty findings and recommendations."""
        result = ManageDocumentationCrewResult(success=True, confidence=0.5)
        report = format_manage_docs_report(result, ".")
        assert "AGENT FINDINGS" not in report
        assert "RECOMMENDATIONS" not in report
        assert "NEXT STEPS" in report  # Always present


class TestManageDocumentationCrew:
    """Tests for the ManageDocumentationCrew class."""

    @pytest.fixture
    def crew(self) -> "ManageDocumentationCrew":
        """Create a ManageDocumentationCrew with mocked dependencies.

        Suppresses the deprecation warning during test creation.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with patch.dict("os.environ", {}, clear=False):
                crew = ManageDocumentationCrew(project_root=".")
                return crew

    def test_initialization_emits_deprecation_warning(self) -> None:
        """Test that ManageDocumentationCrew emits a deprecation warning."""
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            with pytest.warns(DeprecationWarning, match="deprecated since v4.3.0"):
                ManageDocumentationCrew()

    def test_crew_attributes(self, crew: ManageDocumentationCrew) -> None:
        """Test crew has expected attributes."""
        assert crew.name == "Manage_Documentation"
        assert crew.process_type == "sequential"
        assert len(crew.agents) == 4
        assert crew.analyst.role == "Documentation Analyst"
        assert crew.reviewer.role == "Documentation Reviewer"
        assert crew.synthesizer.role == "Documentation Synthesizer"
        assert crew.manager.role == "Documentation Manager"
        assert crew.manager.expertise_level == "world-class"

    def test_define_tasks(self, crew: ManageDocumentationCrew) -> None:
        """Test that define_tasks returns correct tasks."""
        tasks = crew.define_tasks()
        assert len(tasks) == 3
        assert tasks[0].agent == crew.analyst
        assert tasks[1].agent == crew.reviewer
        assert tasks[2].agent == crew.synthesizer

    def test_mock_response(self, crew: ManageDocumentationCrew) -> None:
        """Test _mock_response returns correct mock data for each agent."""
        # Test analyst mock
        agent = crew.analyst
        task = crew.define_tasks()[0]
        response, in_tok, out_tok, cost = crew._mock_response(agent, task, {"path": "."}, "testing")
        assert "Mock Analysis" in response
        assert in_tok == 0
        assert out_tok == 0
        assert cost == 0.0

        # Test reviewer mock
        response, _, _, _ = crew._mock_response(crew.reviewer, task, {"path": "."}, "testing")
        assert "Mock Review" in response

        # Test synthesizer mock
        response, _, _, _ = crew._mock_response(crew.synthesizer, task, {"path": "."}, "testing")
        assert "Mock Synthesis" in response

        # Test unknown agent - falls back to default
        unknown_agent = Agent(role="Unknown Role", goal="g", backstory="b")
        response, _, _, _ = crew._mock_response(unknown_agent, task, {"path": "."}, "testing")
        assert "Mock response for Unknown Role" in response

    def test_scan_directory_nonexistent(self, crew: ManageDocumentationCrew) -> None:
        """Test _scan_directory with nonexistent path."""
        result = crew._scan_directory("/nonexistent/path/to/nowhere")
        assert "error" in result
        assert "does not exist" in result["error"]

    def test_scan_directory_valid(self, crew: ManageDocumentationCrew, tmp_path: Path) -> None:
        """Test _scan_directory with a valid directory."""
        # Create some test files
        (tmp_path / "module.py").write_text("# Python file")
        (tmp_path / "README.md").write_text("# Docs")
        (tmp_path / "notes.txt").write_text("text")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "other.py").write_text("# Another Python file")
        # Create __pycache__ directory (should be excluded)
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.py").write_text("cached")

        result = crew._scan_directory(str(tmp_path))
        assert "error" not in result
        assert result["python_file_count"] == 2  # module.py, sub/other.py
        assert result["doc_file_count"] >= 2  # README.md, notes.txt

    def test_get_index_context_no_index(self, crew: ManageDocumentationCrew) -> None:
        """Test _get_index_context when no ProjectIndex is available."""
        crew._project_index = None
        result = crew._get_index_context()
        assert result == {}

    def test_get_index_context_with_exception(self, crew: ManageDocumentationCrew) -> None:
        """Test _get_index_context when ProjectIndex raises an exception."""
        mock_index = MagicMock()
        mock_index.get_context_for_workflow.side_effect = RuntimeError("broken")
        crew._project_index = mock_index
        result = crew._get_index_context()
        assert result == {}

    @pytest.mark.asyncio
    async def test_call_llm_no_executor(self, crew: ManageDocumentationCrew) -> None:
        """Test _call_llm falls back to mock when no executor is available."""
        crew._executor = None
        agent = crew.analyst
        task = crew.define_tasks()[0]
        context = {"path": "."}
        response, in_tok, out_tok, cost = await crew._call_llm(agent, task, context)
        assert "Mock Analysis" in response
        assert in_tok == 0
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_call_llm_with_executor_success(self, crew: ManageDocumentationCrew) -> None:
        """Test _call_llm with a working executor."""
        # Mock the executor
        mock_response = MagicMock()
        mock_response.content = "Real LLM response"
        mock_response.tokens_input = 100
        mock_response.tokens_output = 50
        mock_response.cost_estimate = 0.005

        mock_executor = AsyncMock()
        mock_executor.run = AsyncMock(return_value=mock_response)
        crew._executor = mock_executor

        # Mock ExecutionContext
        mock_ec = MagicMock()
        with (
            patch("attune.workflows.manage_documentation.ExecutionContext", mock_ec),
            patch("attune.workflows.manage_documentation.HAS_EXECUTOR", True),
        ):
            agent = crew.analyst
            task = crew.define_tasks()[0]
            response, in_tok, out_tok, cost = await crew._call_llm(agent, task, {"path": "."})
            assert response == "Real LLM response"
            assert in_tok == 100
            assert out_tok == 50
            assert cost == 0.005

    @pytest.mark.asyncio
    async def test_call_llm_with_executor_error_fallback(
        self, crew: ManageDocumentationCrew
    ) -> None:
        """Test _call_llm falls back to mock when executor raises error."""
        mock_executor = AsyncMock()
        mock_executor.run = AsyncMock(side_effect=RuntimeError("API down"))
        crew._executor = mock_executor

        mock_ec = MagicMock()
        with (
            patch("attune.workflows.manage_documentation.ExecutionContext", mock_ec),
            patch("attune.workflows.manage_documentation.HAS_EXECUTOR", True),
        ):
            agent = crew.analyst
            task = crew.define_tasks()[0]
            response, in_tok, out_tok, cost = await crew._call_llm(agent, task, {"path": "."})
            # Should fall back to mock
            assert "Mock" in response
            assert in_tok == 0

    @pytest.mark.asyncio
    async def test_execute_with_path_error(self, crew: ManageDocumentationCrew) -> None:
        """Test execute with a path that does not exist (fallback scanning)."""
        crew._project_index = None  # Force fallback path
        result = await crew.execute(path="/nonexistent/path/xyz123")
        assert result.success is False
        assert result.findings[0].get("error") is not None

    @pytest.mark.asyncio
    async def test_execute_fallback_scanning(
        self, crew: ManageDocumentationCrew, tmp_path: Path
    ) -> None:
        """Test execute with fallback directory scanning (no ProjectIndex)."""
        crew._project_index = None  # Force fallback
        # Create a simple directory structure
        (tmp_path / "test.py").write_text("# test file\n")
        (tmp_path / "README.md").write_text("# README\n")

        # Ensure no executor is present for deterministic confidence
        crew._executor = None

        # Mock _call_llm to avoid actual async LLM calls / timeouts
        mock_llm_return = ("Mock response text", 0, 0, 0.0)
        with patch.object(crew, "_call_llm", new_callable=AsyncMock, return_value=mock_llm_return):
            result = await crew.execute(path=str(tmp_path))
        assert result.success is True
        assert result.files_analyzed >= 0
        assert len(result.findings) > 0
        assert len(result.recommendations) > 0
        assert result.formatted_report != ""
        assert result.confidence == 0.3  # No executor => low confidence

    @pytest.mark.asyncio
    async def test_execute_with_index_context(self, crew: ManageDocumentationCrew) -> None:
        """Test execute uses ProjectIndex context when available."""
        mock_index = MagicMock()
        mock_index.get_context_for_workflow.return_value = {
            "documentation_stats": {
                "total_python_files": 100,
                "files_with_docstrings": 80,
                "files_without_docstrings": 20,
                "docstring_coverage_pct": 80.0,
                "type_hint_coverage_pct": 75.0,
                "doc_file_count": 15,
                "loc_undocumented": 500,
                "recently_modified_source_count": 5,
                "stale_docs_count": 2,
                "priority_files": ["src/main.py"],
            },
            "files_without_docstrings": [
                {"path": "src/a.py"},
                {"path": "src/b.py"},
            ],
            "recently_modified_source": [
                {"path": "src/c.py", "last_modified": "2026-01-01"},
            ],
            "docs_needing_review": [
                {
                    "doc_file": "docs/api.md",
                    "related_source_files": ["src/api.py"],
                    "days_since_doc_update": 30,
                    "source_modified_after_doc": True,
                },
            ],
            "doc_files": [{"path": "docs/README.md"}],
        }
        crew._project_index = mock_index

        # Mock _call_llm to avoid actual async LLM calls / timeouts
        mock_llm_return = ("Mock response text", 0, 0, 0.0)
        with patch.object(crew, "_call_llm", new_callable=AsyncMock, return_value=mock_llm_return):
            result = await crew.execute(path=".")
        assert result.success is True
        assert result.files_analyzed == 100  # From index stats

    @pytest.mark.asyncio
    async def test_execute_task_type_routing(self, crew: ManageDocumentationCrew) -> None:
        """Test that task types are routed correctly based on agent role."""
        crew._project_index = None
        # Create a minimal valid directory
        # We just need to verify the code path handles different task types
        mock_llm_return = ("Mock response text", 0, 0, 0.0)
        with (
            patch.object(crew, "_scan_directory") as mock_scan,
            patch.object(crew, "_call_llm", new_callable=AsyncMock, return_value=mock_llm_return),
        ):
            mock_scan.return_value = {
                "python_files": [],
                "python_file_count": 0,
                "doc_files": [],
                "doc_file_count": 0,
            }
            result = await crew.execute(path=".")
            assert result.success is True


# ============================================================================
# Module 2: orchestrated_release_prep.py - Additional coverage
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
                "attune.workflows.orchestrated_release_prep.ParallelStrategy"
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
# Module 3: seo_optimization.py
# ============================================================================


class TestSEOOptimizationConfig:
    """Tests for SEOOptimizationConfig dataclass."""

    def test_config_defaults(self) -> None:
        """Test SEOOptimizationConfig default values."""
        config = SEOOptimizationConfig(
            docs_path=Path("docs"),
            site_url="https://example.com",
            target_keywords=["AI", "framework"],
        )
        assert config.mode == "audit"
        assert config.interactive is True

    def test_config_custom_values(self) -> None:
        """Test SEOOptimizationConfig with custom values."""
        config = SEOOptimizationConfig(
            docs_path=Path("/tmp/docs"),
            site_url="https://test.com",
            target_keywords=["key1"],
            mode="fix",
            interactive=False,
        )
        assert config.mode == "fix"
        assert config.interactive is False
        assert config.docs_path == Path("/tmp/docs")


class TestSEOOptimizationWorkflow:
    """Tests for SEOOptimizationWorkflow."""

    @pytest.fixture
    def workflow(self) -> SEOOptimizationWorkflow:
        """Create a SEOOptimizationWorkflow instance."""
        return SEOOptimizationWorkflow()

    def test_initialization(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test workflow initializes correctly."""
        assert workflow.name == "seo-optimization"
        assert workflow.stages == ["scan", "analyze", "recommend", "implement"]
        # Compare by value to handle compat vs unified ModelTier enums
        assert workflow.tier_map["scan"].value == "cheap"
        assert workflow.tier_map["analyze"].value == "capable"
        assert workflow.tier_map["recommend"].value == "premium"
        assert workflow.tier_map["implement"].value == "capable"

    def test_should_skip_stage_audit_mode(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test stage skipping in audit mode."""
        workflow._mode = "audit"
        skip, reason = workflow.should_skip_stage("recommend", None)
        assert skip is True
        assert "Audit mode" in reason

        skip, reason = workflow.should_skip_stage("implement", None)
        assert skip is True
        assert "audit" in reason

        skip, reason = workflow.should_skip_stage("scan", None)
        assert skip is False
        assert reason is None

    def test_should_skip_stage_suggest_mode(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test stage skipping in suggest mode."""
        workflow._mode = "suggest"
        skip, reason = workflow.should_skip_stage("recommend", None)
        assert skip is False

        skip, reason = workflow.should_skip_stage("implement", None)
        assert skip is True
        assert "suggest" in reason

    def test_should_skip_stage_fix_mode(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test stage skipping in fix mode."""
        workflow._mode = "fix"
        skip, reason = workflow.should_skip_stage("scan", None)
        assert skip is False

        skip, reason = workflow.should_skip_stage("recommend", None)
        assert skip is False

        skip, reason = workflow.should_skip_stage("implement", None)
        assert skip is False

    @pytest.mark.asyncio
    async def test_scan_files(self, workflow: SEOOptimizationWorkflow, tmp_path: Path) -> None:
        """Test _scan_files stage."""
        # Create test markdown files
        (tmp_path / "index.md").write_text("# Home\n")
        (tmp_path / "about.md").write_text("# About\n")
        sub = tmp_path / "guides"
        sub.mkdir()
        (sub / "guide.md").write_text("# Guide\n")

        config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=["test"],
        )
        result = await workflow._scan_files(config)
        assert result["file_count"] == 3
        assert len(result["files"]) == 3
        assert result["site_url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_scan_files_empty_directory(
        self, workflow: SEOOptimizationWorkflow, tmp_path: Path
    ) -> None:
        """Test _scan_files with empty directory."""
        config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=[],
        )
        result = await workflow._scan_files(config)
        assert result["file_count"] == 0
        assert result["files"] == []

    @pytest.mark.asyncio
    async def test_analyze_seo_with_issues(
        self, workflow: SEOOptimizationWorkflow, tmp_path: Path
    ) -> None:
        """Test _analyze_seo finds SEO issues in files."""
        # Create file without description but with H1
        (tmp_path / "page.md").write_text("# My Page\n\nSome content.\n")
        # Create file with no H1
        (tmp_path / "empty.md").write_text("No heading here\n")
        # Create file with multiple H1s
        (tmp_path / "multi.md").write_text("# First\n# Second\n# Third\n")

        config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=["test"],
        )
        scan_data = {
            "files": [
                str(tmp_path / "page.md"),
                str(tmp_path / "empty.md"),
                str(tmp_path / "multi.md"),
            ],
        }
        result = await workflow._analyze_seo(config, scan_data)
        assert result["total_issues"] > 0
        assert result["files_analyzed"] == 3
        # Check for specific issue types
        issue_types = [i["element"] for i in result["issues"]]
        assert "meta_description" in issue_types  # page.md missing description
        assert "h1_count" in issue_types  # multi.md has multiple H1s

    @pytest.mark.asyncio
    async def test_analyze_seo_unreadable_file(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test _analyze_seo handles unreadable files gracefully."""
        config = SEOOptimizationConfig(
            docs_path=Path("/tmp"),
            site_url="https://example.com",
            target_keywords=[],
        )
        scan_data = {"files": ["/nonexistent/file.md"]}
        result = await workflow._analyze_seo(config, scan_data)
        # Should not crash, just skip unreadable files
        assert result["files_analyzed"] == 1
        assert result["total_issues"] == 0

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test _generate_recommendations creates prioritized recommendations."""
        config = SEOOptimizationConfig(
            docs_path=Path("/tmp"),
            site_url="https://example.com",
            target_keywords=["AI"],
        )
        analysis = {
            "issues": [
                {
                    "file": "/tmp/page.md",
                    "element": "meta_description",
                    "severity": "critical",
                    "message": "Missing meta description",
                },
                {
                    "file": "/tmp/other.md",
                    "element": "keyword_density",
                    "severity": "warning",
                    "message": "Low keyword density",
                },
            ],
        }
        result = await workflow._generate_recommendations(config, analysis)
        assert result["total_recommendations"] >= 0
        assert "recommendations" in result
        assert "clarification_needed" in result
        # meta_description has high confidence, keyword_density has low
        total = result["total_recommendations"] + result["needs_clarification"]
        assert total == 2

    @pytest.mark.asyncio
    async def test_implement_fixes_interactive(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test _implement_fixes in interactive mode skips all fixes."""
        config = SEOOptimizationConfig(
            docs_path=Path("/tmp"),
            site_url="https://example.com",
            target_keywords=[],
            interactive=True,
        )
        recommendations = {
            "recommendations": [
                {"priority": "high", "title": "Fix title"},
                {"priority": "medium", "title": "Fix desc"},
            ],
        }
        result = await workflow._implement_fixes(config, recommendations)
        assert result["applied"] == 0
        assert result["skipped"] == 2
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_implement_fixes_non_interactive(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test _implement_fixes in non-interactive mode applies fixes."""
        config = SEOOptimizationConfig(
            docs_path=Path("/tmp"),
            site_url="https://example.com",
            target_keywords=[],
            interactive=False,
        )
        recommendations = {
            "recommendations": [
                {"priority": "high", "title": "Fix title"},
            ],
        }
        result = await workflow._implement_fixes(config, recommendations)
        assert result["applied"] == 1
        assert result["skipped"] == 0

    @pytest.mark.asyncio
    async def test_ask_initial_discovery(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test _ask_initial_discovery returns default goal."""
        goal = await workflow._ask_initial_discovery()
        assert goal == "health"

    def test_calculate_confidence_meta_description_critical(
        self, workflow: SEOOptimizationWorkflow
    ) -> None:
        """Test confidence for critical meta_description issue."""
        issue = {"element": "meta_description", "severity": "critical"}
        confidence = workflow._calculate_confidence(issue)
        # best_practice (+0.3) + critical (+0.3) = 0.6
        assert confidence == 0.6

    def test_calculate_confidence_sitemap(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test confidence for sitemap issue."""
        issue = {"element": "sitemap", "severity": "critical"}
        confidence = workflow._calculate_confidence(issue)
        # best_practice (+0.3) + critical (+0.3) + technical (+0.2) = 0.8
        assert confidence == 0.8

    def test_calculate_confidence_keyword_density(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test confidence for content-related issue is lower."""
        issue = {"element": "keyword_density", "severity": "warning"}
        confidence = workflow._calculate_confidence(issue)
        # content_fix (-0.1) = -0.1, clamped to 0.0
        assert confidence == 0.0

    def test_calculate_confidence_h1_count(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test confidence for H1 count issue."""
        issue = {"element": "h1_count", "severity": "warning"}
        confidence = workflow._calculate_confidence(issue)
        # best_practice (+0.3) = 0.3
        assert confidence == 0.3

    def test_calculate_confidence_unknown_element(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test confidence for unknown element type."""
        issue = {"element": "unknown_thing", "severity": "info"}
        confidence = workflow._calculate_confidence(issue)
        assert confidence == 0.0

    def test_calculate_confidence_clamped(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test confidence is clamped between 0.0 and 1.0."""
        # Create an issue that could theoretically push above 1.0
        issue = {"element": "sitemap", "severity": "critical"}
        confidence = workflow._calculate_confidence(issue)
        assert 0.0 <= confidence <= 1.0

    def test_format_educational_explanation_critical(
        self, workflow: SEOOptimizationWorkflow
    ) -> None:
        """Test educational explanation for critical issue."""
        issue = {"element": "meta_description", "severity": "critical"}
        explanation = workflow._format_educational_explanation(issue, 0.9)
        assert explanation["impact"] == "High - directly affects search rankings"
        assert explanation["time"] == "2-3 minutes"
        assert "click-through rate" in explanation["why"]
        assert "90%" in explanation["confidence"]

    def test_format_educational_explanation_warning(
        self, workflow: SEOOptimizationWorkflow
    ) -> None:
        """Test educational explanation for warning severity."""
        issue = {"element": "h1_count", "severity": "warning"}
        explanation = workflow._format_educational_explanation(issue, 0.5)
        assert "Medium" in explanation["impact"]
        assert "50%" in explanation["confidence"]

    def test_format_educational_explanation_info(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test educational explanation for info severity."""
        issue = {"element": "broken_link", "severity": "info"}
        explanation = workflow._format_educational_explanation(issue, 0.7)
        assert "Low" in explanation["impact"]
        assert "broken links" in explanation["why"].lower()

    def test_format_educational_explanation_unknown(
        self, workflow: SEOOptimizationWorkflow
    ) -> None:
        """Test educational explanation for unknown element/severity."""
        issue = {"element": "unknown", "severity": "unknown"}
        explanation = workflow._format_educational_explanation(issue, 0.4)
        assert "Variable impact" in explanation["impact"]
        assert "5-15 minutes" in explanation["time"]

    def test_get_reasoning_known_elements(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test _get_reasoning for all known element types."""
        known_elements = [
            "meta_description",
            "page_title",
            "h1_count",
            "sitemap",
            "robots_txt",
            "broken_link",
        ]
        for element in known_elements:
            reasoning = workflow._get_reasoning({"element": element})
            assert len(reasoning) > 20  # Should be a meaningful explanation

    def test_get_reasoning_unknown_element(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test _get_reasoning for unknown element returns default."""
        reasoning = workflow._get_reasoning({"element": "unknown_xyz"})
        assert "search engines" in reasoning.lower()

    def test_generate_clarifying_question_known_types(
        self, workflow: SEOOptimizationWorkflow
    ) -> None:
        """Test clarifying questions for known issue types."""
        known_types = ["keyword_density", "meta_description", "content_length", "heading_structure"]
        for element in known_types:
            issue = {"element": element, "file": "/tmp/test.md"}
            question = workflow._generate_clarifying_question(issue, 0.5)
            assert len(question) > 10
            assert "test.md" in question

    def test_generate_clarifying_question_unknown_type(
        self, workflow: SEOOptimizationWorkflow
    ) -> None:
        """Test clarifying question for unknown issue type."""
        issue = {"element": "unknown_type", "file": "/tmp/test.md"}
        question = workflow._generate_clarifying_question(issue, 0.6)
        assert "60%" in question
        assert "test.md" in question

    def test_create_clarification_question_empty(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test _create_clarification_question with empty list."""
        result = workflow._create_clarification_question([])
        assert result is None

    def test_create_clarification_question_few_recommendations(
        self, workflow: SEOOptimizationWorkflow
    ) -> None:
        """Test _create_clarification_question with few recommendations."""
        recs = [{"title": "Fix 1"}, {"title": "Fix 2"}, {"title": "Fix 3"}]
        result = workflow._create_clarification_question(recs)
        assert result is not None
        assert "question" in result
        assert "3 pages" in result["question"]
        assert len(result["options"]) == 3

    def test_create_clarification_question_many_recommendations(
        self, workflow: SEOOptimizationWorkflow
    ) -> None:
        """Test _create_clarification_question with many recommendations."""
        recs = [{"title": f"Fix {i}"} for i in range(10)]
        result = workflow._create_clarification_question(recs)
        assert result is not None
        assert "10 SEO issues" in result["question"]
        assert len(result["options"]) == 4

    @pytest.mark.asyncio
    async def test_run_stage_scan(self, workflow: SEOOptimizationWorkflow, tmp_path: Path) -> None:
        """Test run_stage dispatches to scan correctly."""
        from attune.workflows.base import ModelTier

        workflow._seo_config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=[],
        )
        (tmp_path / "test.md").write_text("# Test\n")
        result, in_tok, out_tok = await workflow.run_stage("scan", ModelTier.CHEAP, {})
        assert result["file_count"] == 1
        assert in_tok == 0
        assert workflow._scan_result is not None

    @pytest.mark.asyncio
    async def test_run_stage_analyze(
        self, workflow: SEOOptimizationWorkflow, tmp_path: Path
    ) -> None:
        """Test run_stage dispatches to analyze correctly."""
        from attune.workflows.base import ModelTier

        (tmp_path / "page.md").write_text("# Title\n\nContent\n")
        workflow._seo_config = SEOOptimizationConfig(
            docs_path=tmp_path,
            site_url="https://example.com",
            target_keywords=[],
        )
        workflow._scan_result = {"files": [str(tmp_path / "page.md")]}

        result, in_tok, out_tok = await workflow.run_stage("analyze", ModelTier.CAPABLE, {})
        assert "issues" in result
        assert in_tok == 1000
        assert out_tok == 500

    @pytest.mark.asyncio
    async def test_run_stage_recommend(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test run_stage dispatches to recommend correctly."""
        from attune.workflows.base import ModelTier

        workflow._seo_config = SEOOptimizationConfig(
            docs_path=Path("/tmp"),
            site_url="https://example.com",
            target_keywords=[],
        )
        workflow._analyze_result = {"issues": []}
        result, in_tok, out_tok = await workflow.run_stage("recommend", ModelTier.PREMIUM, {})
        assert "recommendations" in result
        assert in_tok == 2000

    @pytest.mark.asyncio
    async def test_run_stage_implement_fix_mode(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test run_stage dispatches to implement in fix mode."""
        from attune.workflows.base import ModelTier

        workflow._mode = "fix"
        workflow._seo_config = SEOOptimizationConfig(
            docs_path=Path("/tmp"),
            site_url="https://example.com",
            target_keywords=[],
            interactive=False,
        )
        workflow._recommend_result = {"recommendations": []}
        result, in_tok, out_tok = await workflow.run_stage("implement", ModelTier.CAPABLE, {})
        assert "applied" in result
        assert in_tok == 1500

    @pytest.mark.asyncio
    async def test_run_stage_implement_non_fix_mode(
        self, workflow: SEOOptimizationWorkflow
    ) -> None:
        """Test run_stage implement stage skipped when not in fix mode."""
        from attune.workflows.base import ModelTier

        workflow._mode = "audit"
        workflow._seo_config = SEOOptimizationConfig(
            docs_path=Path("/tmp"),
            site_url="https://example.com",
            target_keywords=[],
        )
        result, in_tok, out_tok = await workflow.run_stage("implement", ModelTier.CAPABLE, {})
        assert result["skipped"] is True
        assert in_tok == 0

    @pytest.mark.asyncio
    async def test_run_stage_unknown(self, workflow: SEOOptimizationWorkflow) -> None:
        """Test run_stage raises ValueError for unknown stage."""
        from attune.workflows.base import ModelTier

        with pytest.raises(ValueError, match="Unknown stage"):
            await workflow.run_stage("nonexistent", ModelTier.CHEAP, {})


# ============================================================================
# Module 4: research_synthesis.py
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
    """Tests for ResearchSynthesisWorkflow."""

    @pytest.fixture
    def workflow(self) -> ResearchSynthesisWorkflow:
        """Create a ResearchSynthesisWorkflow instance."""
        return ResearchSynthesisWorkflow()

    @pytest.fixture
    def workflow_low_threshold(self) -> ResearchSynthesisWorkflow:
        """Create workflow with low complexity threshold."""
        return ResearchSynthesisWorkflow(complexity_threshold=0.1)

    def test_initialization(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test workflow initializes correctly."""
        assert workflow.name == "research"
        assert workflow.stages == ["summarize", "analyze", "synthesize"]
        assert workflow.complexity_threshold == 0.7
        assert workflow._detected_complexity == 0.0
        # Compare by value to handle compat vs unified ModelTier enums
        assert workflow.tier_map["summarize"].value == "cheap"
        assert workflow.tier_map["analyze"].value == "capable"
        assert workflow.tier_map["synthesize"].value == "premium"

    def test_initialization_custom_threshold(self) -> None:
        """Test workflow with custom complexity threshold."""
        wf = ResearchSynthesisWorkflow(complexity_threshold=0.5)
        assert wf.complexity_threshold == 0.5

    def test_validate_sources_valid(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test validate_sources with sufficient sources."""
        workflow.validate_sources(["source1", "source2"])  # Should not raise

    def test_validate_sources_empty(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test validate_sources with empty list."""
        with pytest.raises(ValueError, match="at least 2"):
            workflow.validate_sources([])

    def test_validate_sources_one(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test validate_sources with only one source."""
        with pytest.raises(ValueError, match="at least 2"):
            workflow.validate_sources(["only_one"])

    def test_validate_sources_none(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test validate_sources with None."""
        with pytest.raises(ValueError, match="at least 2"):
            workflow.validate_sources(None)

    def test_should_skip_stage_low_complexity(self) -> None:
        """Test should_skip_stage downgrades tier for low complexity."""
        # Use a fresh workflow to avoid tier_map mutation from other tests
        wf = ResearchSynthesisWorkflow()
        wf._detected_complexity = 0.3  # Below default 0.7 threshold
        skip, reason = wf.should_skip_stage("synthesize", {})
        assert skip is False  # Does not skip, just downgrades
        assert wf.tier_map["synthesize"].value == "capable"

    def test_should_skip_stage_high_complexity(self) -> None:
        """Test should_skip_stage keeps premium tier for high complexity."""
        from attune.workflows.base import ModelTier

        # Use a fresh workflow and reset class-level tier_map mutation
        wf = ResearchSynthesisWorkflow()
        wf.tier_map["synthesize"] = ModelTier.PREMIUM  # Reset in case previous tests mutated it
        wf._detected_complexity = 0.9
        skip, reason = wf.should_skip_stage("synthesize", {})
        assert skip is False
        assert wf.tier_map["synthesize"].value == "premium"

    def test_should_skip_stage_non_synthesize(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test should_skip_stage does not affect non-synthesize stages."""
        skip, reason = workflow.should_skip_stage("summarize", {})
        assert skip is False
        assert reason is None

    @pytest.mark.asyncio
    async def test_run_stage_summarize(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test run_stage dispatches to summarize."""
        from attune.workflows.base import ModelTier

        mock_response = ("Summary of doc.", 50, 30)
        with patch.object(
            workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response
        ):
            input_data = {
                "sources": ["Document A content", "Document B content"],
                "question": "What patterns exist?",
            }
            result, in_tok, out_tok = await workflow.run_stage(
                "summarize", ModelTier.CHEAP, input_data
            )
            assert result["source_count"] == 2
            assert len(result["summaries"]) == 2
            assert result["question"] == "What patterns exist?"
            assert in_tok == 100  # 50 * 2 sources
            assert out_tok == 60

    @pytest.mark.asyncio
    async def test_run_stage_analyze(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test run_stage dispatches to analyze."""
        from attune.workflows.base import ModelTier

        mock_response = ("Pattern analysis result with moderate complexity" * 20, 200, 150)
        with patch.object(
            workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response
        ):
            input_data = {
                "summaries": [
                    {"source": "doc1", "summary": "Summary 1"},
                    {"source": "doc2", "summary": "Summary 2"},
                ],
                "question": "What patterns?",
            }
            result, in_tok, out_tok = await workflow.run_stage(
                "analyze", ModelTier.CAPABLE, input_data
            )
            assert len(result["patterns"]) == 1
            assert result["summary_count"] == 2
            assert result["question"] == "What patterns?"
            assert "complexity" in result
            # Complexity should be calculated from response length
            assert workflow._detected_complexity > 0

    @pytest.mark.asyncio
    async def test_run_stage_synthesize_no_xml(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test run_stage dispatches to synthesize without XML."""
        from attune.workflows.base import ModelTier

        mock_response = ("Synthesized insights.", 300, 200)
        with (
            patch.object(workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response),
            patch.object(workflow, "_is_xml_enabled", return_value=False),
            patch.object(
                workflow,
                "_parse_xml_response",
                return_value={"_parsed_response": None, "_raw": "Synthesized insights."},
            ),
        ):
            input_data = {
                "patterns": [{"pattern": "test", "sources": [], "confidence": 0.85}],
                "complexity": 0.8,
                "question": "Key insights?",
                "analysis": "Analysis text",
            }
            result, in_tok, out_tok = await workflow.run_stage(
                "synthesize", ModelTier.PREMIUM, input_data
            )
            assert result["answer"] == "Synthesized insights."
            assert result["confidence"] == 0.85
            assert result["model_tier_used"] == "premium"
            assert result["complexity_score"] == 0.8

    @pytest.mark.asyncio
    async def test_run_stage_synthesize_with_xml(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test run_stage synthesize with XML-enhanced prompts."""
        from attune.workflows.base import ModelTier

        mock_response = ("<thinking>analysis</thinking><answer>result</answer>", 300, 200)
        mock_parsed = MagicMock()
        mock_parsed.extra = {"key_insights": ["Insight 1", "Insight 2"]}

        with (
            patch.object(workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response),
            patch.object(workflow, "_is_xml_enabled", return_value=True),
            patch.object(workflow, "_render_xml_prompt", return_value="rendered xml prompt"),
            patch.object(
                workflow,
                "_parse_xml_response",
                return_value={
                    "xml_parsed": True,
                    "summary": "Parsed summary",
                    "findings": ["finding1"],
                    "checklist": ["check1"],
                    "_parsed_response": mock_parsed,
                },
            ),
        ):
            input_data = {
                "patterns": [],
                "complexity": 0.5,
                "question": "Q",
                "analysis": "A",
            }
            result, in_tok, out_tok = await workflow.run_stage(
                "synthesize", ModelTier.PREMIUM, input_data
            )
            assert result["xml_parsed"] is True
            assert result["summary"] == "Parsed summary"
            assert result["findings"] == ["finding1"]
            assert result["key_insights"] == ["Insight 1", "Insight 2"]

    @pytest.mark.asyncio
    async def test_run_stage_synthesize_xml_no_extra(
        self, workflow: ResearchSynthesisWorkflow
    ) -> None:
        """Test synthesize with XML parsed but no extra key_insights."""
        from attune.workflows.base import ModelTier

        mock_response = ("result", 300, 200)
        with (
            patch.object(workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response),
            patch.object(workflow, "_is_xml_enabled", return_value=False),
            patch.object(
                workflow,
                "_parse_xml_response",
                return_value={
                    "xml_parsed": True,
                    "summary": "S",
                    "_parsed_response": None,  # No parsed response object
                },
            ),
        ):
            input_data = {
                "patterns": [],
                "complexity": 0.5,
                "question": "Q",
                "analysis": "A",
            }
            result, in_tok, out_tok = await workflow.run_stage(
                "synthesize", ModelTier.PREMIUM, input_data
            )
            assert result["xml_parsed"] is True
            # key_insights should remain empty list (no extra data)
            assert result["key_insights"] == []

    @pytest.mark.asyncio
    async def test_run_stage_unknown(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test run_stage raises ValueError for unknown stage."""
        from attune.workflows.base import ModelTier

        with pytest.raises(ValueError, match="Unknown stage"):
            await workflow.run_stage("nonexistent", ModelTier.CHEAP, {})

    @pytest.mark.asyncio
    async def test_execute_validates_sources(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test execute raises ValueError if sources are insufficient."""
        with pytest.raises(ValueError, match="at least 2"):
            await workflow.execute(sources=["only_one"], question="Q")

    @pytest.mark.asyncio
    async def test_execute_no_sources(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test execute raises ValueError if no sources provided."""
        with pytest.raises(ValueError, match="at least 2"):
            await workflow.execute(question="Q")

    @pytest.mark.asyncio
    async def test_call_with_step_no_executor(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test _call_with_step falls back to _call_llm when no executor."""
        workflow._executor = None
        mock_response = ("response text", 100, 50)
        with patch.object(
            workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response
        ):
            content, in_tok, out_tok = await workflow._call_with_step(
                SUMMARIZE_STEP,
                "System prompt",
                "User message",
            )
            assert content == "response text"
            assert in_tok == 100
            assert out_tok == 50

    @pytest.mark.asyncio
    async def test_call_with_step_with_executor(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test _call_with_step uses executor when available."""
        workflow._executor = MagicMock()  # Non-None executor
        mock_return = ("executor response", 200, 80, 0.01)
        with patch.object(
            workflow,
            "run_step_with_executor",
            new_callable=AsyncMock,
            return_value=mock_return,
        ):
            content, in_tok, out_tok = await workflow._call_with_step(
                SUMMARIZE_STEP,
                "System prompt",
                "User message",
            )
            assert content == "executor response"
            assert in_tok == 200
            assert out_tok == 80

    @pytest.mark.asyncio
    async def test_call_with_step_with_executor_no_system(
        self, workflow: ResearchSynthesisWorkflow
    ) -> None:
        """Test _call_with_step with executor and empty system prompt."""
        workflow._executor = MagicMock()
        mock_return = ("response", 10, 5, 0.001)
        with patch.object(
            workflow,
            "run_step_with_executor",
            new_callable=AsyncMock,
            return_value=mock_return,
        ):
            content, in_tok, out_tok = await workflow._call_with_step(
                SUMMARIZE_STEP,
                "",  # Empty system prompt
                "User message",
            )
            assert content == "response"

    @pytest.mark.asyncio
    async def test_summarize_stage(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test the _summarize method directly."""
        from attune.workflows.base import ModelTier

        mock_response = ("Summary of content.", 50, 30)
        with patch.object(
            workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response
        ):
            result, in_tok, out_tok = await workflow._summarize(
                {
                    "sources": ["Doc A", "Doc B", "Doc C"],
                    "question": "Compare these documents",
                },
                ModelTier.CHEAP,
            )
            assert result["source_count"] == 3
            assert len(result["summaries"]) == 3
            for s in result["summaries"]:
                assert s["summary"] == "Summary of content."
                assert s["key_points"] == []

    @pytest.mark.asyncio
    async def test_analyze_stage(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test the _analyze method directly."""
        from attune.workflows.base import ModelTier

        # Create a response that would give moderate complexity
        response_text = "A" * 1000  # 1000 chars / 2000 = 0.5 complexity
        mock_response = (response_text, 100, 80)
        with patch.object(
            workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response
        ):
            result, in_tok, out_tok = await workflow._analyze(
                {
                    "summaries": [
                        {"source": "doc1", "summary": "Summary 1"},
                    ],
                    "question": "What patterns exist?",
                },
                ModelTier.CAPABLE,
            )
            assert result["summary_count"] == 1
            assert result["question"] == "What patterns exist?"
            assert abs(result["complexity"] - 0.5) < 0.01
            assert workflow._detected_complexity == result["complexity"]

    @pytest.mark.asyncio
    async def test_analyze_stage_high_complexity(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test analyze detects high complexity from long response."""
        from attune.workflows.base import ModelTier

        long_response = "X" * 5000
        mock_response = (long_response, 200, 150)
        with patch.object(
            workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response
        ):
            result, _, _ = await workflow._analyze(
                {"summaries": [{"source": "s", "summary": "s"}], "question": "Q"},
                ModelTier.CAPABLE,
            )
            # 5000 / 2000 = 2.5, clamped to 1.0
            assert result["complexity"] == 1.0

    @pytest.mark.asyncio
    async def test_synthesize_stage_no_xml(self, workflow: ResearchSynthesisWorkflow) -> None:
        """Test _synthesize without XML enabled."""
        from attune.workflows.base import ModelTier

        mock_response = ("Final synthesis answer.", 300, 200)
        with (
            patch.object(workflow, "_call_llm", new_callable=AsyncMock, return_value=mock_response),
            patch.object(workflow, "_is_xml_enabled", return_value=False),
            patch.object(
                workflow,
                "_parse_xml_response",
                return_value={"_parsed_response": None, "_raw": "raw"},
            ),
        ):
            result, in_tok, out_tok = await workflow._synthesize(
                {
                    "patterns": [],
                    "complexity": 0.6,
                    "question": "Key insights?",
                    "analysis": "Analysis text here",
                },
                ModelTier.PREMIUM,
            )
            assert result["answer"] == "Final synthesis answer."
            assert result["model_tier_used"] == "premium"
            assert result["complexity_score"] == 0.6
