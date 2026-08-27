"""Comprehensive tests for coverage batch 9.

Tests for:
- attune.meta_workflows.workflow (Meta workflow execution)
- attune.meta_workflows.cli_commands.workflow_commands (CLI commands for workflows)

All external dependencies (Redis, LLM, Anthropic, etc.) are mocked.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

try:
    # Import from typer (the library that raises) rather than click.exceptions
    # — typer 0.26 vendored click and `typer.Exit` is no longer the same class
    # as `click.exceptions.Exit`. See the CLAUDE.md lesson on typer.Exit.
    from typer import Exit as ClickExit
except ImportError:
    ClickExit = SystemExit  # type: ignore[assignment,misc]


try:
    from attune.meta_workflows.models import (
        AgentExecutionResult,
        AgentSpec,
        FormResponse,
        FormSchema,
        MetaWorkflowResult,
        MetaWorkflowTemplate,
        TierStrategy,
    )
    from attune.meta_workflows.workflow import (
        MetaWorkflow,
        list_execution_results,
        load_execution_result,
    )

    HAS_META_WORKFLOW = True
except ImportError:
    HAS_META_WORKFLOW = False


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    """Create a temporary storage directory for experiments."""
    storage = tmp_path / "experiments.json"
    return storage


@pytest.fixture
def sample_variant_control() -> dict[str, Any]:
    """Sample control variant data dict."""
    return {
        "variant_id": "exp1_control",
        "name": "Control",
        "description": "Control group",
        "config": {"agents": ["analyzer"]},
        "is_control": True,
        "traffic_percentage": 50.0,
        "impressions": 100,
        "conversions": 30,
        "total_success_score": 25.0,
    }


@pytest.fixture
def sample_variant_treatment() -> dict[str, Any]:
    """Sample treatment variant data dict."""
    return {
        "variant_id": "exp1_treatment_0",
        "name": "Treatment 1",
        "description": "Treatment group",
        "config": {"agents": ["analyzer", "reviewer"]},
        "is_control": False,
        "traffic_percentage": 50.0,
        "impressions": 100,
        "conversions": 45,
        "total_success_score": 40.0,
    }


# ============================================================================
# META-WORKFLOW MODULE
# ============================================================================


@pytest.mark.skipif(not HAS_META_WORKFLOW, reason="meta_workflows not available")
class TestMetaWorkflow:
    """Tests for MetaWorkflow orchestration."""

    def _make_template(self) -> MetaWorkflowTemplate:
        """Create a minimal template for testing."""
        return MetaWorkflowTemplate(
            template_id="test-template",
            name="Test Template",
            description="A test template",
            form_schema=FormSchema(
                title="Test Form",
                description="Test form schema",
                questions=[],
            ),
            agent_composition_rules=[],
            version="1.0.0",
        )

    def test_init_with_template(self, tmp_path: Path) -> None:
        """Test initialization with a template object."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))
        assert wf.template.template_id == "test-template"

    def test_init_requires_template_or_id(self) -> None:
        """Test initialization raises ValueError without template or ID."""
        with pytest.raises(ValueError, match="Must provide either"):
            MetaWorkflow()

    @patch("attune.meta_workflows.workflow.TemplateRegistry")
    def test_init_with_template_id(
        self,
        mock_registry_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test initialization with template_id loads from registry."""
        mock_registry = mock_registry_cls.return_value
        template = self._make_template()
        mock_registry.load_template.return_value = template

        wf = MetaWorkflow(template_id="test-template", storage_dir=str(tmp_path / "exec"))
        assert wf.template.template_id == "test-template"

    @patch("attune.meta_workflows.workflow.TemplateRegistry")
    def test_init_with_template_id_not_found(
        self,
        mock_registry_cls: MagicMock,
    ) -> None:
        """Test initialization with unknown template_id raises ValueError."""
        mock_registry = mock_registry_cls.return_value
        mock_registry.load_template.return_value = None

        with pytest.raises(ValueError, match="Template not found"):
            MetaWorkflow(template_id="nonexistent")

    def test_execute_mock(self, tmp_path: Path) -> None:
        """Test mock execution of a meta-workflow."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        mock_response = FormResponse(
            template_id="test-template",
            responses={"q1": "answer1"},
        )
        mock_agents = [
            AgentSpec(
                role="Analyzer",
                base_template="code-analyzer",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
        ]

        with patch.object(wf.form_engine, "ask_questions", return_value=mock_response):
            with patch.object(wf.agent_creator, "create_agents", return_value=mock_agents):
                result = wf.execute(mock_execution=True, use_defaults=True)

        assert result.success is True
        assert len(result.agent_results) == 1
        assert result.total_cost > 0

    def test_execute_with_provided_form_response(self, tmp_path: Path) -> None:
        """Test execution with pre-collected form responses."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        form_response = FormResponse(
            template_id="test-template",
            responses={"q1": "val"},
        )
        mock_agents = [
            AgentSpec(
                role="Reviewer",
                base_template="code-reviewer",
                tier_strategy=TierStrategy.PROGRESSIVE,
            ),
        ]

        with patch.object(wf.agent_creator, "create_agents", return_value=mock_agents):
            result = wf.execute(form_response=form_response, mock_execution=True)

        assert result.success is True

    def test_execute_with_pattern_learner(self, tmp_path: Path) -> None:
        """Test execution with pattern learner stores in memory."""
        template = self._make_template()
        mock_learner = MagicMock()
        mock_learner.store_execution_in_memory.return_value = "pattern_123"

        wf = MetaWorkflow(
            template=template,
            storage_dir=str(tmp_path / "exec"),
            pattern_learner=mock_learner,
        )

        form_response = FormResponse(template_id="test-template", responses={})
        with patch.object(wf.agent_creator, "create_agents", return_value=[]):
            result = wf.execute(form_response=form_response, mock_execution=True)

        assert result.success is True
        mock_learner.store_execution_in_memory.assert_called_once()

    def test_execute_error_handling(self, tmp_path: Path) -> None:
        """Test execution error handling creates error result."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        with (
            patch.object(
                wf.form_engine,
                "ask_questions",
                side_effect=RuntimeError("form engine error"),
            ),
            pytest.raises(ValueError, match="Meta-workflow execution failed"),
        ):
            wf.execute(use_defaults=True)

    def test_execute_agents_mock_tier_strategies(self, tmp_path: Path) -> None:
        """Test mock execution handles all tier strategies."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        agents = [
            AgentSpec(role="Cheap", base_template="t", tier_strategy=TierStrategy.CHEAP_ONLY),
            AgentSpec(role="Prog", base_template="t", tier_strategy=TierStrategy.PROGRESSIVE),
            AgentSpec(role="Capable", base_template="t", tier_strategy=TierStrategy.CAPABLE_FIRST),
            AgentSpec(role="Premium", base_template="t", tier_strategy=TierStrategy.PREMIUM_ONLY),
        ]

        results = wf._execute_agents_mock(agents)
        assert len(results) == 4
        assert results[0].tier_used == "cheap"
        assert results[1].tier_used == "capable"
        assert results[2].tier_used == "capable"
        assert results[3].tier_used == "premium"
        assert all(r.success for r in results)

    def test_get_generic_instructions_roles(self, tmp_path: Path) -> None:
        """Test generic instructions generation for various roles."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        analyst_instr = wf._get_generic_instructions("Code Analyst")
        assert "analyst" in analyst_instr.lower()

        reviewer_instr = wf._get_generic_instructions("Code Reviewer")
        assert "reviewer" in reviewer_instr.lower()

        generator_instr = wf._get_generic_instructions("Test Generator")
        assert "generator" in generator_instr.lower() or "content" in generator_instr.lower()

        validator_instr = wf._get_generic_instructions("Schema Validator")
        assert "validator" in validator_instr.lower()

        synthesizer_instr = wf._get_generic_instructions("Result Synthesizer")
        assert "synthesizer" in synthesizer_instr.lower()

        test_instr = wf._get_generic_instructions("Test Runner")
        assert "test" in test_instr.lower()

        # "Doc Specialist" matches "doc" branch (avoids "writer" branch matching first)
        doc_instr = wf._get_generic_instructions("Doc Specialist")
        assert "documentation" in doc_instr.lower()

        # "Content Writer" matches "writer" in the generator branch
        writer_instr = wf._get_generic_instructions("Content Writer")
        assert "content" in writer_instr.lower() or "generator" in writer_instr.lower()

        generic_instr = wf._get_generic_instructions("Custom Agent")
        assert "Custom Agent" in generic_instr

    @patch("attune.meta_workflows.prompt_builder.get_template")
    def test_build_agent_prompt_with_template(
        self,
        mock_get_template: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test prompt building with existing template."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        mock_tmpl = MagicMock()
        mock_tmpl.default_instructions = "You are a test agent."
        mock_get_template.return_value = mock_tmpl

        agent = AgentSpec(
            role="Analyzer",
            base_template="code-analyzer",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            config={"focus": "security"},
            success_criteria=["all issues found"],
            tools=["grep", "ast"],
        )

        prompt = wf._build_agent_prompt(agent)
        assert "Analyzer" in prompt
        assert "You are a test agent." in prompt
        assert "security" in prompt
        assert "all issues found" in prompt
        assert "grep" in prompt

    @patch("attune.meta_workflows.prompt_builder.get_template")
    def test_build_agent_prompt_template_not_found(
        self,
        mock_get_template: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test prompt building falls back to generic when template not found."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        mock_get_template.return_value = None

        agent = AgentSpec(
            role="Reviewer",
            base_template="missing-template",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )

        prompt = wf._build_agent_prompt(agent)
        assert "Reviewer" in prompt

    def test_evaluate_success_criteria_basic(self, tmp_path: Path) -> None:
        """Test success criteria evaluation."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result_success = AgentExecutionResult(
            agent_id="a1",
            role="Test",
            success=True,
            cost=0.01,
            duration=1.0,
            tier_used="cheap",
            output={"message": "done"},
        )
        agent = AgentSpec(
            role="Test",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        assert wf._evaluate_success_criteria(result_success, agent) is True

    def test_evaluate_success_criteria_failed_result(self, tmp_path: Path) -> None:
        """Test success criteria evaluation with failed result."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result_fail = AgentExecutionResult(
            agent_id="a1",
            role="Test",
            success=False,
            cost=0.0,
            duration=0.5,
            tier_used="cheap",
            output={"error": "failed"},
        )
        agent = AgentSpec(
            role="Test",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        assert wf._evaluate_success_criteria(result_fail, agent) is False

    def test_evaluate_success_criteria_with_criteria(self, tmp_path: Path) -> None:
        """Test success criteria evaluation with explicit criteria."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result = AgentExecutionResult(
            agent_id="a1",
            role="Test",
            success=True,
            cost=0.01,
            duration=1.0,
            tier_used="cheap",
            output={"message": "done"},
        )
        agent = AgentSpec(
            role="Test",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            success_criteria=["tests pass", "no regressions"],
        )
        assert wf._evaluate_success_criteria(result, agent) is True

    def test_generate_report(self, tmp_path: Path) -> None:
        """Test report generation."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result = MetaWorkflowResult(
            run_id="test-run-001",
            template_id="test-template",
            timestamp=datetime.now().isoformat(),
            form_responses=FormResponse(
                template_id="test-template",
                responses={"q1": "answer"},
            ),
            agents_created=[
                AgentSpec(
                    role="Analyzer",
                    base_template="t",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    tools=["grep"],
                    config={"focus": "perf"},
                    success_criteria=["done"],
                ),
            ],
            agent_results=[
                AgentExecutionResult(
                    agent_id="a1",
                    role="Analyzer",
                    success=True,
                    cost=0.05,
                    duration=2.0,
                    tier_used="cheap",
                    output={"message": "ok"},
                ),
            ],
            total_cost=0.05,
            total_duration=2.0,
            success=True,
        )

        report = wf._generate_report(result)
        assert "Meta-Workflow Execution Report" in report
        assert "test-run-001" in report
        assert "$0.05" in report
        assert "Analyzer" in report

    def test_generate_report_with_error(self, tmp_path: Path) -> None:
        """Test report generation for failed execution."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result = MetaWorkflowResult(
            run_id="error-run",
            template_id="test-template",
            timestamp=datetime.now().isoformat(),
            form_responses=FormResponse(template_id="test-template", responses={}),
            agent_results=[
                AgentExecutionResult(
                    agent_id="a1",
                    role="Broken",
                    success=False,
                    cost=0.0,
                    duration=0.1,
                    tier_used="cheap",
                    output={},
                    error="Something went wrong",
                ),
            ],
            success=False,
            error="Execution failed",
        )

        report = wf._generate_report(result)
        assert "Execution failed" in report
        assert "Something went wrong" in report


@pytest.mark.skipif(not HAS_META_WORKFLOW, reason="meta_workflows not available")
class TestMetaWorkflowHelpers:
    """Tests for helper functions in meta_workflows.workflow module."""

    def test_load_execution_result(self, tmp_path: Path) -> None:
        """Test loading a saved execution result."""
        run_id = "test-load-run"
        run_dir = tmp_path / run_id
        run_dir.mkdir(parents=True)

        result_data = MetaWorkflowResult(
            run_id=run_id,
            template_id="test-template",
            timestamp=datetime.now().isoformat(),
            form_responses=FormResponse(
                template_id="test-template",
                responses={},
            ),
            success=True,
        )
        (run_dir / "result.json").write_text(result_data.to_json(), encoding="utf-8")

        loaded = load_execution_result(run_id, storage_dir=str(tmp_path))
        assert loaded.run_id == run_id
        assert loaded.success is True

    def test_load_execution_result_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent result raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Result not found"):
            load_execution_result("nonexistent", storage_dir=str(tmp_path))

    def test_load_execution_result_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON result raises ValueError."""
        run_dir = tmp_path / "bad-run"
        run_dir.mkdir()
        (run_dir / "result.json").write_text("not valid json", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid result file"):
            load_execution_result("bad-run", storage_dir=str(tmp_path))

    def test_list_execution_results(self, tmp_path: Path) -> None:
        """Test listing execution results."""
        # Create some execution directories
        for name in ["run-a", "run-b", "run-c"]:
            d = tmp_path / name
            d.mkdir()
            (d / "result.json").write_text("{}", encoding="utf-8")

        # Create a directory without result.json (should be excluded)
        (tmp_path / "not-a-run").mkdir()

        results = list_execution_results(storage_dir=str(tmp_path))
        assert len(results) == 3
        # Sorted in reverse
        assert results == sorted(results, reverse=True)

    def test_list_execution_results_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test listing from nonexistent directory returns empty list."""
        results = list_execution_results(storage_dir=str(tmp_path / "nonexistent"))
        assert results == []


# ============================================================================
# CLI WORKFLOW COMMANDS MODULE
# ============================================================================


@pytest.mark.skipif(not HAS_META_WORKFLOW, reason="meta_workflows not available")
class TestCLIWorkflowCommands:
    """Tests for CLI workflow commands.

    These tests mock all external dependencies (typer, rich, workflow execution).
    """

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_template_not_found(
        self,
        mock_registry_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow with template not found."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        mock_registry = mock_registry_cls.return_value
        mock_registry.load_template.return_value = None

        with pytest.raises(ClickExit):
            rw(
                template_id="nonexistent",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=False,
            )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_template_not_found_json_output(
        self,
        mock_registry_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow with template not found in JSON mode."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        mock_registry = mock_registry_cls.return_value
        mock_registry.load_template.return_value = None

        with pytest.raises(ClickExit):
            rw(
                template_id="nonexistent",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=True,
            )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_success_json(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow success with JSON output."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test Template"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-123"
        mock_result.timestamp = "2026-01-01T00:00:00"
        mock_result.success = True
        mock_result.error = None
        mock_result.total_cost = 0.10
        mock_result.total_duration = 5.0
        mock_result.agents_created = []
        mock_result.form_responses.template_id = "test"
        mock_result.form_responses.responses = {}
        mock_result.form_responses.timestamp = "2026-01-01T00:00:00"
        mock_result.form_responses.response_id = "resp-1"
        mock_result.agent_results = []

        mock_workflow_cls.return_value.execute.return_value = mock_result

        # Capture print output
        with patch("builtins.print") as mock_print:
            rw(
                template_id="test-template",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=True,
            )

        mock_print.assert_called()
        # The first call should be the JSON output
        call_args = mock_print.call_args_list[0][0][0]
        output = json.loads(call_args)
        assert output["run_id"] == "run-123"
        assert output["success"] is True

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_success_normal_output(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow success with normal console output."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test Template"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-456"
        mock_result.success = True
        mock_result.error = None
        mock_result.total_cost = 0.05
        mock_result.total_duration = 2.0
        mock_result.agents_created = [MagicMock()]
        mock_result.agent_results = [
            MagicMock(role="Analyzer", success=True, tier_used="cheap", cost=0.05),
        ]
        mock_result.form_responses = MagicMock()

        mock_workflow_cls.return_value.execute.return_value = mock_result

        rw(
            template_id="test-template",
            mock=True,
            use_memory=False,
            use_defaults=False,
            user_id="test",
            json_output=False,
        )

        # Verify console.print was called (output displayed)
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_with_error_result(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow displays error in result."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-err"
        mock_result.success = False
        mock_result.error = "Something broke"
        mock_result.total_cost = 0.0
        mock_result.total_duration = 0.1
        mock_result.agents_created = []
        mock_result.agent_results = []
        mock_result.form_responses = MagicMock()

        mock_workflow_cls.return_value.execute.return_value = mock_result

        rw(
            template_id="test-template",
            mock=True,
            use_memory=False,
            use_defaults=True,
            user_id="test",
            json_output=False,
        )

        # Should have printed error info
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_detect_intent_with_matches(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test detect_intent with matching results."""
        from attune.meta_workflows.cli_commands.workflow_commands import detect_intent as di

        mock_match = MagicMock()
        mock_match.template_id = "release-prep"
        mock_match.template_name = "Release Prep"
        mock_match.confidence = 0.85
        mock_match.matched_keywords = ["release", "prepare"]
        mock_match.description = "Prepare for release"

        mock_detector_cls.return_value.detect.return_value = [mock_match]

        di(request="prepare for release", threshold=0.3)

        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_detect_intent_no_matches(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test detect_intent with no matches."""
        from attune.meta_workflows.cli_commands.workflow_commands import detect_intent as di

        mock_detector_cls.return_value.detect.return_value = []

        di(request="something unrelated", threshold=0.3)

        # Should print "no matches" message
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_no_matches(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test natural_language_run with no matching templates."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_detector_cls.return_value.detect.return_value = []

        nlr(request="do something random", auto_run=False, mock=True, use_defaults=True)

        # Should show "couldn't identify" message
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.run_workflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_auto_high_confidence(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
        mock_run_workflow: MagicMock,
    ) -> None:
        """Test natural_language_run auto-runs on high confidence."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_match = MagicMock()
        mock_match.template_id = "release-prep"
        mock_match.template_name = "Release Preparation"
        mock_match.confidence = 0.85
        mock_match.description = "Prepare for release"
        mock_match.matched_keywords = ["release"]

        mock_detector_cls.return_value.detect.return_value = [mock_match]

        nlr(request="prepare for release", auto_run=True, mock=True, use_defaults=True)

        mock_run_workflow.assert_called_once()

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_shows_suggestions(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test natural_language_run shows suggestions when not auto-running."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_match1 = MagicMock()
        mock_match1.template_id = "release-prep"
        mock_match1.template_name = "Release Prep"
        mock_match1.confidence = 0.7
        mock_match1.description = "Release"
        mock_match1.matched_keywords = ["release"]

        mock_match2 = MagicMock()
        mock_match2.template_id = "test-boost"
        mock_match2.template_name = "Test Boost"
        mock_match2.confidence = 0.4
        mock_match2.description = "Tests"
        mock_match2.matched_keywords = ["test"]

        mock_detector_cls.return_value.detect.return_value = [mock_match1, mock_match2]

        nlr(request="prepare for release", auto_run=False, mock=True, use_defaults=True)

        # Should display suggestions
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_auto_low_confidence(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test natural_language_run does not auto-run on low confidence."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_match = MagicMock()
        mock_match.template_id = "test-boost"
        mock_match.template_name = "Test Boost"
        mock_match.confidence = 0.3  # Below 0.6 threshold
        mock_match.description = "Boost tests"
        mock_match.matched_keywords = ["test"]

        mock_detector_cls.return_value.detect.return_value = [mock_match]

        nlr(request="maybe test something", auto_run=True, mock=True, use_defaults=True)

        # Should show suggestions, NOT auto-run
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_detect_intent_error_handling(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test detect_intent handles errors gracefully."""
        from attune.meta_workflows.cli_commands.workflow_commands import detect_intent as di

        mock_detector_cls.return_value.detect.side_effect = RuntimeError("detection failed")

        with pytest.raises(ClickExit):
            di(request="test", threshold=0.3)

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_error_handling(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test natural_language_run handles errors gracefully."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_detector_cls.return_value.detect.side_effect = RuntimeError("detection error")

        with pytest.raises(ClickExit):
            nlr(request="test", auto_run=False, mock=True, use_defaults=True)

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_execution_error_json(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow handles execution error with JSON output."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template
        mock_workflow_cls.return_value.execute.side_effect = RuntimeError("execution failed")

        with pytest.raises(ClickExit):
            rw(
                template_id="test",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=True,
            )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_execution_error_normal(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow handles execution error with normal output."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template
        mock_workflow_cls.return_value.execute.side_effect = RuntimeError("execution failed")

        with pytest.raises(ClickExit):
            rw(
                template_id="test",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=False,
            )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.PatternLearner")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_with_memory_enabled(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_pattern_learner_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow with memory integration enabled."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-mem"
        mock_result.success = True
        mock_result.error = None
        mock_result.total_cost = 0.0
        mock_result.total_duration = 1.0
        mock_result.agents_created = []
        mock_result.agent_results = []
        mock_result.form_responses = MagicMock()

        mock_workflow_cls.return_value.execute.return_value = mock_result

        # Mock the UnifiedMemory import
        with patch(
            "attune.meta_workflows.cli_commands.workflow_commands.UnifiedMemory",
            create=True,
        ):
            # We need to mock the import inside the function
            with patch.dict("sys.modules", {"attune.memory.unified": MagicMock()}):
                rw(
                    template_id="test",
                    mock=True,
                    use_memory=True,
                    use_defaults=True,
                    user_id="test_user",
                    json_output=False,
                )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_with_memory_init_failure(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow continues when memory initialization fails."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-mem-fail"
        mock_result.success = True
        mock_result.error = None
        mock_result.total_cost = 0.0
        mock_result.total_duration = 1.0
        mock_result.agents_created = []
        mock_result.agent_results = []
        mock_result.form_responses = MagicMock()

        mock_workflow_cls.return_value.execute.return_value = mock_result

        # Mock UnifiedMemory to raise on init
        mock_unified = MagicMock()
        mock_unified.side_effect = RuntimeError("Redis not available")

        with patch.dict(
            "sys.modules",
            {"attune.memory.unified": MagicMock(UnifiedMemory=mock_unified)},
        ):
            rw(
                template_id="test",
                mock=True,
                use_memory=True,
                use_defaults=True,
                user_id="test_user",
                json_output=False,
            )

        # Should continue without memory
        mock_workflow_cls.return_value.execute.assert_called_once()
