"""Unit tests for MetaWorkflow orchestrator.

Tests cover:
- Workflow initialization
- Mock agent execution
- Result storage and retrieval
- Report generation
- Error handling

Created: 2026-01-17
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from attune.meta_workflows.models import FormResponse
from attune.meta_workflows.template_registry import TemplateRegistry
from attune.meta_workflows.workflow import (
    MetaWorkflow,
    list_execution_results,
    load_execution_result,
)


class TestMetaWorkflowInitialization:
    """Test MetaWorkflow initialization."""

    def test_init_with_template(self):
        """Test initialization with direct template."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        workflow = MetaWorkflow(template=template)

        assert workflow.template == template
        assert workflow.template.template_id == "release-prep"

    def test_init_with_template_id(self):
        """Test initialization with template_id (loads template)."""
        with patch("attune.meta_workflows.workflow.TemplateRegistry") as mock_registry:
            mock_template = Mock()
            mock_template.template_id = "test_template"
            mock_registry.return_value.load_template.return_value = mock_template

            workflow = MetaWorkflow(template_id="test_template")

            assert workflow.template == mock_template
            mock_registry.return_value.load_template.assert_called_once_with("test_template")

    def test_init_with_neither_raises_error(self):
        """Test initialization without template or template_id raises error."""
        with pytest.raises(ValueError, match="Must provide either template or template_id"):
            MetaWorkflow()

    def test_init_with_invalid_template_id_raises_error(self):
        """Test initialization with non-existent template_id raises error."""
        with patch("attune.meta_workflows.workflow.TemplateRegistry") as mock_registry:
            mock_registry.return_value.load_template.return_value = None

            with pytest.raises(ValueError, match="Template not found"):
                MetaWorkflow(template_id="nonexistent")

    def test_init_with_custom_storage_dir(self, tmp_path):
        """Test initialization with custom storage directory."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        storage_dir = tmp_path / "custom_storage"
        workflow = MetaWorkflow(template=template, storage_dir=str(storage_dir))

        assert workflow.storage_dir == storage_dir
        assert storage_dir.exists()  # Should be created


class TestMetaWorkflowExecution:
    """Test meta-workflow execution."""

    def test_execute_with_provided_response(self, tmp_path):
        """Test execution with pre-provided form response."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        response = FormResponse(
            template_id="release-prep",
            responses={
                "security_scan": "Yes",
                "test_coverage_required": "80%",
                "quality_checks": ["Linting (ruff)"],
                "coverage_threshold": "80%",
                "publish_to": "Skip publishing",
                "create_git_tag": "No",
                "update_changelog": "No",
            },
        )

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))
        result = workflow.execute(form_response=response, mock_execution=True)

        assert result.success is True
        assert result.template_id == "release-prep"
        assert len(result.agents_created) > 0
        assert len(result.agent_results) == len(result.agents_created)
        assert result.total_cost > 0
        assert result.total_duration > 0

    def test_execute_mock_agents(self, tmp_path):
        """Test mock agent execution."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        response = FormResponse(
            template_id="release-prep",
            responses={
                "security_scan": "Yes",
                "coverage_threshold": "80%",
                "publish_to": "Skip publishing",
                "create_git_tag": "No",
                "update_changelog": "No",
            },
        )

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))
        result = workflow.execute(form_response=response, mock_execution=True)

        # All mock executions should succeed
        assert all(agent_result.success for agent_result in result.agent_results)

        # Check mock result structure
        for agent_result in result.agent_results:
            assert agent_result.agent_id is not None
            assert agent_result.role is not None
            assert agent_result.cost > 0
            assert agent_result.duration > 0
            assert agent_result.tier_used in ["cheap", "capable", "premium"]
            assert isinstance(agent_result.output, dict)


class TestResultStorage:
    """Test result storage and retrieval."""

    def test_result_saved_to_disk(self, tmp_path):
        """Test that result is saved to disk."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        response = FormResponse(
            template_id="release-prep",
            responses={"security_scan": "No", "coverage_threshold": "80%"},
        )

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))
        result = workflow.execute(form_response=response, mock_execution=True)

        # Check files exist
        run_dir = tmp_path / result.run_id
        assert run_dir.exists()
        assert (run_dir / "config.json").exists()
        assert (run_dir / "form_responses.json").exists()
        assert (run_dir / "agents.json").exists()
        assert (run_dir / "result.json").exists()
        assert (run_dir / "report.txt").exists()

    def test_config_file_content(self, tmp_path):
        """Test config file contains correct data."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        response = FormResponse(template_id="release-prep", responses={"coverage_threshold": "80%"})

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))
        result = workflow.execute(form_response=response, mock_execution=True)

        config_file = tmp_path / result.run_id / "config.json"
        config_data = json.loads(config_file.read_text())

        assert config_data["template_id"] == "release-prep"
        assert config_data["template_name"] == "Release Preparation"
        assert config_data["run_id"] == result.run_id

    def test_report_generation(self, tmp_path):
        """Test human-readable report is generated."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        response = FormResponse(
            template_id="release-prep",
            responses={"security_scan": "Yes", "coverage_threshold": "80%"},
        )

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))
        result = workflow.execute(form_response=response, mock_execution=True)

        report_file = tmp_path / result.run_id / "report.txt"
        report = report_file.read_text()

        # Check report contains key information
        assert "Meta-Workflow Execution Report" in report
        assert result.run_id in report
        assert "Release Preparation" in report
        assert "Summary" in report
        assert "Form Responses" in report
        assert "Agents Created" in report
        assert "Execution Results" in report
        assert "Cost Breakdown" in report


class TestResultLoading:
    """Test loading saved results."""

    def test_load_execution_result(self, tmp_path):
        """Test loading a saved execution result."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        response = FormResponse(template_id="release-prep", responses={"coverage_threshold": "80%"})

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))
        original_result = workflow.execute(form_response=response, mock_execution=True)

        # Load the result
        loaded_result = load_execution_result(original_result.run_id, storage_dir=str(tmp_path))

        assert loaded_result.run_id == original_result.run_id
        assert loaded_result.template_id == original_result.template_id
        assert loaded_result.success == original_result.success
        assert loaded_result.total_cost == original_result.total_cost
        assert len(loaded_result.agents_created) == len(original_result.agents_created)

    def test_load_nonexistent_result_raises_error(self, tmp_path):
        """Test loading non-existent result raises error."""
        with pytest.raises(FileNotFoundError, match="Result not found"):
            load_execution_result("nonexistent-run-id", storage_dir=str(tmp_path))

    def test_list_execution_results(self, tmp_path):
        """Test listing all execution results."""
        import time

        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        response = FormResponse(template_id="release-prep", responses={"coverage_threshold": "80%"})

        # Create multiple executions
        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))

        result1 = workflow.execute(form_response=response, mock_execution=True)
        time.sleep(1.1)  # Ensure different timestamp
        result2 = workflow.execute(form_response=response, mock_execution=True)

        # List results
        results = list_execution_results(storage_dir=str(tmp_path))

        assert len(results) == 2
        assert result1.run_id in results
        assert result2.run_id in results

        # Should be sorted (newest first)
        assert results[0] >= results[1]  # Lexicographic comparison

    def test_list_empty_directory(self, tmp_path):
        """Test listing results from empty directory."""
        results = list_execution_results(storage_dir=str(tmp_path))
        assert len(results) == 0


class TestErrorHandling:
    """Test error handling in workflow execution."""

    def test_execution_error_creates_error_result(self, tmp_path):
        """Test that execution errors are captured in result."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        response = FormResponse(template_id="release-prep", responses={"coverage_threshold": "80%"})

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))

        # Mock agent_creator to raise error
        def mock_error(*args, **kwargs):
            raise RuntimeError("Test error")

        workflow.agent_creator.create_agents = mock_error

        # Execution should raise error
        with pytest.raises(ValueError, match="Meta-workflow execution failed"):
            workflow.execute(form_response=response, mock_execution=True)

        # But error result should be saved
        results = list_execution_results(storage_dir=str(tmp_path))
        assert len(results) == 1

        error_result = load_execution_result(results[0], storage_dir=str(tmp_path))
        assert error_result.success is False
        assert error_result.error is not None
        assert "Test error" in error_result.error


class TestAgentExecution:
    """Test agent execution logic."""

    def test_mock_execution_cost_by_tier(self, tmp_path):
        """Test mock execution assigns correct costs by tier."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        # Get full quality response to create all agents
        response = FormResponse(
            template_id="release-prep",
            responses={
                "security_scan": "Yes",
                "test_coverage_required": "90%",
                "quality_checks": [
                    "Type checking (mypy)",
                    "Linting (ruff)",
                    "Security scan (bandit)",
                ],
                "coverage_threshold": "80%",
                "publish_to": "PyPI (production)",
                "create_git_tag": "Yes",
                "update_changelog": "Yes",
            },
        )

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))
        result = workflow.execute(form_response=response, mock_execution=True)

        # Check that costs vary by tier
        cheap_costs = [r.cost for r in result.agent_results if r.tier_used == "cheap"]
        capable_costs = [r.cost for r in result.agent_results if r.tier_used == "capable"]

        if cheap_costs:
            assert all(cost == 0.05 for cost in cheap_costs)
        if capable_costs:
            assert all(cost >= 0.15 for cost in capable_costs)

    def test_all_agents_executed(self, tmp_path):
        """Test that all created agents are executed."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        response = FormResponse(
            template_id="release-prep",
            responses={"security_scan": "Yes", "coverage_threshold": "80%"},
        )

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))
        result = workflow.execute(form_response=response, mock_execution=True)

        # Number of results should equal number of agents
        assert len(result.agent_results) == len(result.agents_created)

        # All agent IDs should match
        agent_ids = {agent.agent_id for agent in result.agents_created}
        result_agent_ids = {result.agent_id for result in result.agent_results}
        assert agent_ids == result_agent_ids


# ===========================================================================
# Coverage gap tests
# ===========================================================================


class TestExecuteFormCollection:
    """Cover lines 164-168: form_response None without use_defaults → ask_questions."""

    def test_no_form_response_interactive(self):
        """Lines 167-171: ask_questions called when no form_response + not use_defaults."""
        from attune.meta_workflows.models import (
            FormResponse,
            FormSchema,
            MetaWorkflowTemplate,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        wf = MetaWorkflow(template=template)

        # Mock form engine and downstream pieces
        fake_response = FormResponse(template_id="t1", responses={})
        with (
            patch.object(wf.form_engine, "ask_questions", return_value=fake_response) as mock_ask,
            patch.object(wf.agent_creator, "create_agents", return_value=[]),
        ):
            result = wf.execute(mock_execution=True, use_defaults=False)
        mock_ask.assert_called_once()
        assert result.success is True


class TestExecuteRealAgentsPath:
    """Cover line 187: execute_agents_real path."""

    def test_real_execution_calls_execute_agents_real(self):
        from attune.meta_workflows.models import (
            FormResponse,
            FormSchema,
            MetaWorkflowTemplate,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        wf = MetaWorkflow(template=template)

        fr = FormResponse(template_id="t1", responses={})
        with (
            patch.object(wf.agent_creator, "create_agents", return_value=[]),
            patch(
                "attune.meta_workflows.workflow.execute_agents_real",
                return_value=[],
            ) as mock_real,
        ):
            wf.execute(form_response=fr, mock_execution=False)
        mock_real.assert_called_once()


class TestExecutePatternLearnerStorage:
    """Cover lines 213-217: pattern_learner storage."""

    def test_pattern_learner_stores_execution(self):
        from attune.meta_workflows.models import (
            FormResponse,
            FormSchema,
            MetaWorkflowTemplate,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        learner = MagicMock()
        learner.store_execution_in_memory.return_value = "pattern-123"
        wf = MetaWorkflow(template=template, pattern_learner=learner)

        fr = FormResponse(template_id="t1", responses={})
        with patch.object(wf.agent_creator, "create_agents", return_value=[]):
            result = wf.execute(form_response=fr, mock_execution=True)

        learner.store_execution_in_memory.assert_called_once()
        assert result.success is True

    def test_pattern_learner_returns_no_id(self):
        """Line 216 branch: pattern_id falsy → no log."""
        from attune.meta_workflows.models import (
            FormResponse,
            FormSchema,
            MetaWorkflowTemplate,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        learner = MagicMock()
        learner.store_execution_in_memory.return_value = None
        wf = MetaWorkflow(template=template, pattern_learner=learner)

        fr = FormResponse(template_id="t1", responses={})
        with patch.object(wf.agent_creator, "create_agents", return_value=[]):
            result = wf.execute(form_response=fr, mock_execution=True)
        assert result.success is True


class TestExecuteErrorPath:
    """Cover lines 244-245: save error result exception."""

    def test_error_path_save_failure_logged(self):
        import pytest

        from attune.meta_workflows.models import (
            FormResponse,
            FormSchema,
            MetaWorkflowTemplate,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        wf = MetaWorkflow(template=template)

        fr = FormResponse(template_id="t1", responses={})
        # First _save_execution call (success path) won't be reached;
        # create_agents raises → enter except block → _save_execution
        # for error result also raises.
        call_idx = [0]

        def fake_save(result):
            call_idx[0] += 1
            raise RuntimeError("disk full")

        with (
            patch.object(
                wf.agent_creator,
                "create_agents",
                side_effect=RuntimeError("creation failed"),
            ),
            patch.object(wf, "_save_execution", side_effect=fake_save),
            pytest.raises(ValueError, match="Meta-workflow execution failed"),
        ):
            wf.execute(form_response=fr, mock_execution=True)


class TestMockExecutionAllTiers:
    """Cover lines 278-280: PREMIUM_ONLY tier branch."""

    def test_premium_only_tier_path(self):
        from attune.meta_workflows.models import (
            AgentSpec,
            FormSchema,
            MetaWorkflowTemplate,
            TierStrategy,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        wf = MetaWorkflow(template=template)

        agent = AgentSpec(
            role="r",
            base_template="bt",
            tier_strategy=TierStrategy.PREMIUM_ONLY,
        )
        results = wf._execute_agents_mock([agent])
        assert len(results) == 1
        assert results[0].tier_used == "premium"

    def test_capable_first_tier_path(self):
        """Cover the CAPABLE_FIRST branch (line 273)."""
        from attune.meta_workflows.models import (
            AgentSpec,
            FormSchema,
            MetaWorkflowTemplate,
            TierStrategy,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        wf = MetaWorkflow(template=template)
        agent = AgentSpec(
            role="r",
            base_template="bt",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
        )
        results = wf._execute_agents_mock([agent])
        assert results[0].tier_used == "capable"


class TestDelegateMethods:
    """Cover lines 408, 422, 437: delegate methods."""

    def _make_wf(self):
        from attune.meta_workflows.models import FormSchema, MetaWorkflowTemplate
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        return MetaWorkflow(template=template)

    def test_get_generic_instructions_delegates(self):
        wf = self._make_wf()
        result = wf._get_generic_instructions("analyst")
        assert "analyst" in result.lower()

    def test_build_agent_prompt_delegates(self):
        from attune.meta_workflows.models import AgentSpec, TierStrategy

        wf = self._make_wf()
        spec = AgentSpec(
            role="reviewer",
            base_template="bt",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        with patch(
            "attune.meta_workflows.workflow.build_agent_prompt",
            return_value="PROMPT",
        ):
            assert wf._build_agent_prompt(spec) == "PROMPT"

    def test_evaluate_success_criteria_delegates(self):
        from attune.meta_workflows.models import AgentExecutionResult, AgentSpec, TierStrategy

        wf = self._make_wf()
        result = AgentExecutionResult(
            agent_id="a",
            role="r",
            success=True,
            cost=0.0,
            duration=0.0,
            tier_used="cheap",
            output={},
        )
        spec = AgentSpec(
            role="r",
            base_template="bt",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        with patch(
            "attune.meta_workflows.workflow.evaluate_success_criteria",
            return_value=True,
        ):
            assert wf._evaluate_success_criteria(result, spec) is True


class TestHelperFunctions:
    """Cover lines 461, 488, 493."""

    def test_load_execution_result_default_dir(self, tmp_path, monkeypatch):
        from pathlib import Path

        """Line 461: storage_dir None uses ~/.attune/meta_workflows/executions."""
        import pytest

        from attune.meta_workflows.workflow import load_execution_result

        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        # No file → FileNotFoundError
        with pytest.raises(FileNotFoundError):
            load_execution_result("nonexistent")

    def test_list_execution_results_default_dir(self, tmp_path, monkeypatch):
        from pathlib import Path

        """Line 488: storage_dir None uses default."""
        from attune.meta_workflows.workflow import list_execution_results

        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        # Default dir doesn't exist → empty list
        assert list_execution_results() == []

    def test_list_execution_results_path_does_not_exist(self, tmp_path):
        """Line 493: storage_path doesn't exist → []."""
        from attune.meta_workflows.workflow import list_execution_results

        result = list_execution_results(str(tmp_path / "nonexistent"))
        assert result == []


class TestExecuteUseDefaults:
    """Cover line 165: use_defaults=True path."""

    def test_use_defaults_true_logs_default_values(self):
        from attune.meta_workflows.models import (
            FormResponse,
            FormSchema,
            MetaWorkflowTemplate,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        wf = MetaWorkflow(template=template)

        fake_response = FormResponse(template_id="t1", responses={})
        with (
            patch.object(wf.form_engine, "ask_questions", return_value=fake_response),
            patch.object(wf.agent_creator, "create_agents", return_value=[]),
        ):
            result = wf.execute(mock_execution=True, use_defaults=True)
        assert result.success is True


class TestMockExecutionRemainingTiers:
    """Cover lines 266-268, 270-272 (CHEAP_ONLY, PROGRESSIVE)."""

    def test_cheap_only_tier(self):
        from attune.meta_workflows.models import (
            AgentSpec,
            FormSchema,
            MetaWorkflowTemplate,
            TierStrategy,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        wf = MetaWorkflow(template=template)
        agent = AgentSpec(
            role="r",
            base_template="bt",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        results = wf._execute_agents_mock([agent])
        assert results[0].tier_used == "cheap"

    def test_progressive_tier(self):
        from attune.meta_workflows.models import (
            AgentSpec,
            FormSchema,
            MetaWorkflowTemplate,
            TierStrategy,
        )
        from attune.meta_workflows.workflow import MetaWorkflow

        schema = FormSchema(questions=[], title="t", description="d")
        template = MetaWorkflowTemplate(
            template_id="t1",
            name="Test",
            description="d",
            form_schema=schema,
            agent_composition_rules=[],
        )
        wf = MetaWorkflow(template=template)
        agent = AgentSpec(
            role="r",
            base_template="bt",
            tier_strategy=TierStrategy.PROGRESSIVE,
        )
        results = wf._execute_agents_mock([agent])
        assert results[0].tier_used == "capable"


class TestLoadExecutionResultInvalid:
    """Cover lines 473-474: invalid JSON → ValueError."""

    def test_invalid_json_raises_value_error(self, tmp_path):
        import pytest

        from attune.meta_workflows.workflow import load_execution_result

        # Create directory with bad result.json
        run_dir = tmp_path / "run-1"
        run_dir.mkdir()
        (run_dir / "result.json").write_text("not-json{")

        with pytest.raises(ValueError, match="Invalid result file"):
            load_execution_result("run-1", storage_dir=str(tmp_path))


class TestListExecutionResultsSkipsInvalid:
    """Cover branch 498->497: iterdir entries without result.json or non-dir → skipped."""

    def test_skips_files_and_dirs_without_result(self, tmp_path):
        from attune.meta_workflows.workflow import list_execution_results

        # Loose file (not a dir) — should be skipped
        (tmp_path / "loose.txt").write_text("x")
        # Directory without result.json — should be skipped
        empty_dir = tmp_path / "empty-run"
        empty_dir.mkdir()
        # Directory with result.json — should be included
        good_dir = tmp_path / "good-run"
        good_dir.mkdir()
        (good_dir / "result.json").write_text("{}")

        result = list_execution_results(str(tmp_path))
        assert "good-run" in result
        assert "empty-run" not in result
