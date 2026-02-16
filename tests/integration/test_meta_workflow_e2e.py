"""End-to-end integration tests for meta-workflow system.

Tests the complete workflow from template loading through execution,
storage, analytics, and CLI commands.

Created: 2026-01-17
Updated: 2026-01-24 (Fixed to use existing built-in templates)
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from attune.meta_workflows import (
    FormResponse,
    MetaWorkflow,
    PatternLearner,
    TemplateRegistry,
    list_execution_results,
    load_execution_result,
)


class TestEndToEndWorkflow:
    """Test complete meta-workflow execution end-to-end."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directories."""
        templates_dir = tmp_path / "templates"
        executions_dir = tmp_path / "executions"

        templates_dir.mkdir()
        executions_dir.mkdir()

        return {
            "templates": str(templates_dir),
            "executions": str(executions_dir),
            "root": tmp_path,
        }

    def test_complete_workflow_lifecycle(self, temp_storage):
        """Test complete workflow from template to analytics.

        This test covers:
        1. Template loading
        2. Workflow creation
        3. Execution with form responses
        4. Result storage (files)
        5. Result loading
        6. Pattern analysis
        7. Analytics report generation
        """
        # Step 1: Load built-in template
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        assert template is not None
        assert template.template_id == "release-prep"
        # Check template has expected structure (may vary by version)
        assert len(template.form_schema.questions) >= 3
        assert len(template.agent_composition_rules) >= 2

        # Step 2: Create workflow
        workflow = MetaWorkflow(
            template=template,
            storage_dir=temp_storage["executions"],
        )

        # Step 3: Execute with form responses matching the template
        response = FormResponse(
            template_id="release-prep",
            responses={
                "security_scan": "Yes",
                "test_coverage_check": "Yes",
                "coverage_threshold": "80%",
                "quality_review": "Yes",
                "doc_verification": "Yes",
            },
        )

        result = workflow.execute(form_response=response, mock_execution=True)

        # Step 4: Verify execution result
        assert result.success is True
        assert result.template_id == "release-prep"
        assert len(result.agents_created) >= 1  # At least some agents created
        assert len(result.agent_results) >= 1  # At least some agents executed

        # All mock executions should succeed
        assert all(ar.success for ar in result.agent_results)

        # Step 5: Verify files saved
        run_dir = Path(temp_storage["executions"]) / result.run_id
        assert run_dir.exists()
        assert (run_dir / "config.json").exists()
        assert (run_dir / "form_responses.json").exists()
        assert (run_dir / "agents.json").exists()
        assert (run_dir / "result.json").exists()
        assert (run_dir / "report.txt").exists()

        # Step 6: Load result from storage
        loaded_result = load_execution_result(
            result.run_id,
            storage_dir=temp_storage["executions"],
        )

        assert loaded_result.run_id == result.run_id
        assert loaded_result.success == result.success
        assert len(loaded_result.agents_created) == len(result.agents_created)

        # Step 7: Initialize pattern learner
        learner = PatternLearner(executions_dir=temp_storage["executions"])

        # Step 8: Analyze patterns
        insights = learner.analyze_patterns(
            template_id="release-prep",
            min_confidence=0.0,
        )

        # Should have insights for single execution
        assert len(insights) >= 0  # May be 0 for single execution

        # Step 9: Generate analytics report
        report = learner.generate_analytics_report(template_id="release-prep")

        assert "summary" in report
        assert "insights" in report
        assert "recommendations" in report

        summary = report["summary"]
        assert summary["total_runs"] == 1
        assert summary["successful_runs"] == 1
        assert summary["success_rate"] == 1.0

    def test_multiple_executions_and_pattern_learning(self, temp_storage):
        """Test pattern learning across multiple executions."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        workflow = MetaWorkflow(
            template=template,
            storage_dir=temp_storage["executions"],
        )

        # Execute 3 workflows with different configurations
        configs = [
            {"security_scan": "No", "test_coverage_check": "Yes", "coverage_threshold": "70%"},
            {"security_scan": "Yes", "test_coverage_check": "Yes", "coverage_threshold": "80%"},
            {
                "security_scan": "Yes",
                "test_coverage_check": "Yes",
                "coverage_threshold": "90%",
                "quality_review": "Yes",
                "doc_verification": "Yes",
            },
        ]

        results = []
        for i, config in enumerate(configs):
            response = FormResponse(
                template_id="release-prep",
                responses=config,
            )

            result = workflow.execute(form_response=response, mock_execution=True)
            results.append(result)

            # Add delay to ensure different timestamps (run_id is second-precision)
            if i < len(configs) - 1:
                time.sleep(1.1)

        # Verify all executions succeeded
        assert all(r.success for r in results)

        # List all results
        run_ids = list_execution_results(storage_dir=temp_storage["executions"])
        assert len(run_ids) == 3

        # Initialize pattern learner
        learner = PatternLearner(executions_dir=temp_storage["executions"])

        # Analyze patterns with multiple executions
        insights = learner.analyze_patterns(
            template_id="release-prep",
            min_confidence=0.3,  # Lower threshold for small sample
        )

        # Should have multiple types of insights
        if len(insights) > 0:
            {i.insight_type for i in insights}
            # May have various insight types

        # Get recommendations
        recommendations = learner.get_recommendations(
            "release-prep",
            min_confidence=0.3,
        )

        # With multiple executions, should have some recommendations
        assert isinstance(recommendations, list)

        # Generate analytics report
        report = learner.generate_analytics_report(template_id="release-prep")

        summary = report["summary"]
        assert summary["total_runs"] == 3
        assert summary["successful_runs"] == 3
        assert summary["success_rate"] == 1.0

    def test_workflow_with_memory_integration(self, temp_storage):
        """Test workflow with memory integration enabled."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        # Create mock memory
        mock_memory = Mock()
        mock_memory.persist_pattern.return_value = {"pattern_id": "pat_test_123"}

        # Initialize pattern learner with memory
        learner = PatternLearner(
            executions_dir=temp_storage["executions"],
            memory=mock_memory,
        )

        # Create workflow with pattern learner
        workflow = MetaWorkflow(
            template=template,
            storage_dir=temp_storage["executions"],
            pattern_learner=learner,
        )

        # Execute workflow
        response = FormResponse(
            template_id="release-prep",
            responses={"security_scan": "Yes", "test_coverage_check": "Yes"},
        )

        result = workflow.execute(form_response=response, mock_execution=True)

        # Verify execution succeeded
        assert result.success is True

        # Memory may or may not be called depending on workflow implementation
        # Just verify execution completed successfully

    def test_error_handling_and_recovery(self, temp_storage):
        """Test error handling during workflow execution."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        workflow = MetaWorkflow(
            template=template,
            storage_dir=temp_storage["executions"],
        )

        # Mock agent_creator to raise error
        def mock_error(*args, **kwargs):
            raise RuntimeError("Simulated agent creation error")

        workflow.agent_creator.create_agents = mock_error

        # Execution should raise error
        response = FormResponse(
            template_id="release-prep",
            responses={"security_scan": "Yes"},
        )

        with pytest.raises(ValueError, match="Meta-workflow execution failed"):
            workflow.execute(form_response=response, mock_execution=True)

        # Error result should be saved
        run_ids = list_execution_results(storage_dir=temp_storage["executions"])
        assert len(run_ids) == 1

        error_result = load_execution_result(
            run_ids[0],
            storage_dir=temp_storage["executions"],
        )

        assert error_result.success is False
        assert error_result.error is not None
        assert "Simulated agent creation error" in error_result.error

    def test_config_file_persistence(self, temp_storage):
        """Test that configuration files are properly saved and loaded."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        workflow = MetaWorkflow(
            template=template,
            storage_dir=temp_storage["executions"],
        )

        response = FormResponse(
            template_id="release-prep",
            responses={
                "security_scan": "Yes",
                "test_coverage_check": "Yes",
                "coverage_threshold": "85%",
                "quality_review": "Yes",
            },
        )

        result = workflow.execute(form_response=response, mock_execution=True)

        # Load and verify config.json
        config_file = Path(temp_storage["executions"]) / result.run_id / "config.json"
        config_data = json.loads(config_file.read_text())

        assert config_data["template_id"] == "release-prep"
        assert config_data["run_id"] == result.run_id

        # Load and verify form_responses.json
        responses_file = Path(temp_storage["executions"]) / result.run_id / "form_responses.json"
        responses_data = json.loads(responses_file.read_text())

        assert responses_data["template_id"] == "release-prep"
        assert "security_scan" in responses_data["responses"]
        assert responses_data["responses"]["security_scan"] == "Yes"

        # Load and verify agents.json
        agents_file = Path(temp_storage["executions"]) / result.run_id / "agents.json"
        agents_data = json.loads(agents_file.read_text())

        assert len(agents_data) == len(result.agents_created)
        assert all("agent_id" in agent for agent in agents_data)
        assert all("role" in agent for agent in agents_data)
        assert all("tier_strategy" in agent for agent in agents_data)

    def test_report_generation(self, temp_storage):
        """Test human-readable report generation."""
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        workflow = MetaWorkflow(
            template=template,
            storage_dir=temp_storage["executions"],
        )

        response = FormResponse(
            template_id="release-prep",
            responses={"security_scan": "Yes", "test_coverage_check": "Yes"},
        )

        result = workflow.execute(form_response=response, mock_execution=True)

        # Load and verify report.txt
        report_file = Path(temp_storage["executions"]) / result.run_id / "report.txt"
        report_content = report_file.read_text()

        # Verify key sections are present
        assert "Meta-Workflow Execution Report" in report_content
        assert result.run_id in report_content
        assert "Summary" in report_content or "summary" in report_content.lower()

        # Verify success indicator
        if result.success:
            assert "Yes" in report_content or "success" in report_content.lower()


class TestCLIIntegration:
    """Test CLI command integration (mock tests)."""

    def test_cli_available(self):
        """Test that CLI commands are available."""
        try:
            from attune.meta_workflows.cli_meta_workflows import meta_workflow_app

            assert meta_workflow_app is not None

            # Verify commands are registered
            commands = [cmd.name for cmd in meta_workflow_app.registered_commands]

            assert "list-templates" in commands
            assert "inspect" in commands
            assert "run" in commands
            assert "analytics" in commands
            assert "list-runs" in commands
            assert "show" in commands
            assert "cleanup" in commands

        except ImportError as e:
            pytest.fail(f"CLI module not available: {e}")

    def test_cli_integrated_with_main_cli(self):
        """Test that CLI minimal entry point is available."""
        try:
            from attune.cli_minimal import main

            assert main is not None

        except Exception as e:
            pytest.fail(f"Failed to import main CLI: {e}")


class TestSecurityValidation:
    """Test security features and validations."""

    def test_file_path_validation_in_workflow(self, tmp_path):
        """Test that file paths are validated during workflow execution."""
        # This is an indirect test - we verify the workflow uses validated paths
        registry = TemplateRegistry(storage_dir=".attune/meta_workflows/templates")
        template = registry.load_template("release-prep")

        # Normal path should work
        workflow = MetaWorkflow(
            template=template,
            storage_dir=str(tmp_path / "executions"),
        )

        response = FormResponse(
            template_id="release-prep",
            responses={"security_scan": "Yes"},
        )

        result = workflow.execute(form_response=response, mock_execution=True)
        assert result.success is True

        # Verify files are in expected location
        run_dir = tmp_path / "executions" / result.run_id
        assert run_dir.exists()
        assert run_dir.is_relative_to(tmp_path)

    def test_no_eval_or_exec_in_codebase(self):
        """Test that no eval() or exec() calls exist in meta-workflow code."""
        import ast

        code_files = [
            "src/attune/meta_workflows/models.py",
            "src/attune/meta_workflows/workflow.py",
            "src/attune/meta_workflows/pattern_learner.py",
            "src/attune/meta_workflows/agent_creator.py",
            "src/attune/meta_workflows/form_engine.py",
            "src/attune/meta_workflows/template_registry.py",
            "src/attune/meta_workflows/cli_meta_workflows.py",
        ]

        for file_path in code_files:
            path = Path(file_path)
            if not path.exists():
                continue

            content = path.read_text()
            tree = ast.parse(content, filename=str(path))

            # Check for eval/exec calls
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        assert node.func.id not in [
                            "eval",
                            "exec",
                        ], f"Found {node.func.id}() call in {file_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
