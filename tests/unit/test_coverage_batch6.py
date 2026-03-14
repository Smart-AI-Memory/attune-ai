"""Comprehensive tests for low-coverage workflow modules (Batch 6).

Covers:
1. manage_documentation.py - Documentation management crew workflow
2. orchestrated_release_prep.py - Orchestrated release preparation (extra coverage)
3. research_synthesis.py - Research synthesis workflow

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
                },
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
                },
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
                },
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
                },
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
                },
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
        self,
        crew: ManageDocumentationCrew,
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
        self,
        crew: ManageDocumentationCrew,
        tmp_path: Path,
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
# Module 3: research_synthesis.py
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
