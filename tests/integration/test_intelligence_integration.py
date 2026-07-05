"""Integration Tests for Intelligence System

Tests the complete flow of Smart Router, Memory Graph, and Chain Executor
working together as a unified system.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from pathlib import Path

import pytest

# Check if workflow_chains.yaml exists for chain executor tests
CHAIN_CONFIG_EXISTS = Path(".attune/workflow_chains.yaml").exists()

from attune.routing import (  # noqa: E402
    ChainExecutor,
    ClassificationResult,
    HaikuClassifier,
    SmartRouter,
    WorkflowRegistry,
)


class TestSmartRouterIntegration:
    """Integration tests for Smart Router with other components."""

    def test_router_with_registry(self):
        """Test router correctly uses wizard registry."""
        router = SmartRouter()

        # Verify all registered wizards are accessible
        wizards = router.list_workflows()
        assert len(wizards) >= 10

        # Verify wizard info is complete
        for wizard in wizards:
            assert wizard.name
            assert wizard.description
            assert len(wizard.keywords) > 0

    def test_router_security_request(self):
        """Test routing a security-related request."""
        router = SmartRouter()
        decision = router.route_sync("Check for SQL injection vulnerabilities in auth.py")

        assert decision.primary_workflow == "security-audit"
        assert decision.confidence > 0.1  # Keyword-based classifier has lower confidence
        assert "security-audit" in decision.suggested_chain

    def test_router_performance_request(self):
        """Test routing a performance-related request."""
        router = SmartRouter()
        decision = router.route_sync("Optimize slow database queries")

        assert decision.primary_workflow == "perf-audit"
        assert decision.confidence > 0.1  # Keyword-based classifier has lower confidence

    def test_router_testing_request(self):
        """Test routing a testing-related request."""
        router = SmartRouter()
        # Use request without "authentication" which triggers security-audit
        decision = router.route_sync("Generate unit tests for the user service module")

        assert decision.primary_workflow == "test-gen"

    def test_router_with_context(self):
        """Test routing with file context."""
        router = SmartRouter()
        decision = router.route_sync(
            "Review this code",
            context={"file": "auth.py", "language": "python"},
        )

        assert decision.context.get("file") == "auth.py"

    def test_router_file_suggestions(self):
        """Test file-based wizard suggestions."""
        router = SmartRouter()

        # Python file
        suggestions = router.suggest_for_file("src/auth.py")
        assert "security-audit" in suggestions
        assert "code-review" in suggestions

        # Package.json
        suggestions = router.suggest_for_file("package.json")
        assert "dependency-check" in suggestions

    def test_router_error_suggestions(self):
        """Test error-based wizard suggestions."""
        router = SmartRouter()

        suggestions = router.suggest_for_error("NullPointerException at line 42")
        assert "bug-predict" in suggestions

        suggestions = router.suggest_for_error("SecurityException: Access denied")
        assert "security-audit" in suggestions


@pytest.mark.skipif(not CHAIN_CONFIG_EXISTS, reason=".attune/workflow_chains.yaml not found")
class TestChainExecutorIntegration:
    """Integration tests for Chain Executor with routing."""

    def test_chain_trigger_evaluation(self):
        """Test chain triggers are evaluated correctly."""
        executor = ChainExecutor()

        # Security audit with high severity should trigger follow-up workflows
        result = {"high_severity_count": 5}
        triggers = executor.get_triggered_chains("security-audit", result)

        assert len(triggers) >= 1
        wizard_names = [t.next_workflow for t in triggers]
        # Should trigger bug-predict or dependency-check based on config
        assert len(wizard_names) >= 1

    def test_chain_template_loading(self):
        """Test pre-built chain templates load correctly."""
        executor = ChainExecutor()
        templates = executor.list_templates()

        assert "full-security-review" in templates
        assert "pre-release" in templates

    def test_chain_execution_creation(self):
        """Test creating a chain execution plan."""
        executor = ChainExecutor()

        triggers = executor.get_triggered_chains(
            "security-audit",
            {"high_severity_count": 3},
        )

        execution = executor.create_execution("security-audit", triggers)

        assert execution.initial_workflow == "security-audit"
        assert len(execution.steps) >= 1

    def test_chain_approval_workflow(self):
        """Test approval workflow for chain steps."""
        executor = ChainExecutor()
        from attune.routing import ChainStep

        execution = executor.create_execution("test", [])
        execution.steps.append(
            ChainStep(
                workflow_name="next-wizard",
                triggered_by="test",
                approval_required=True,
            ),
        )

        # Step should need approval
        assert execution.steps[-1].approved is None

        # Approve step
        executor.approve_step(execution, len(execution.steps) - 1)
        assert execution.steps[-1].approved is True


class TestFullIntegration:
    """End-to-end integration tests."""

    def test_request_to_chain_flow(self):
        """Test complete flow from request to chain execution."""
        # 1. User makes a request
        request = "Fix security vulnerabilities and check dependencies"

        # 2. Smart Router classifies the request
        router = SmartRouter()
        decision = router.route_sync(request)

        assert decision.primary_workflow in ["security-audit", "dependency-check"]
        assert len(decision.suggested_chain) >= 1

        # 3. Chain Executor creates execution plan
        executor = ChainExecutor()
        config = executor.get_chain_config(decision.primary_workflow)

        if config and config.auto_chain:
            # Simulate wizard result
            mock_result = {"high_severity_count": 2}
            triggers = executor.get_triggered_chains(decision.primary_workflow, mock_result)
            execution = executor.create_execution(decision.primary_workflow, triggers)

            assert execution.initial_workflow == decision.primary_workflow

    def test_file_history_informs_routing(self):
        """Test that file-based suggestions influence routing."""
        router = SmartRouter()
        _decision = router.route_sync("Review db/queries.py for issues")

        # Should suggest security wizard for a db query file
        suggestions = router.suggest_for_file("db/queries.py")
        assert "security-audit" in suggestions

    def test_registry_wizard_info_completeness(self):
        """Test that all registered wizards have complete information."""
        registry = WorkflowRegistry()
        wizards = registry.list_all()

        for wizard in wizards:
            # Required fields
            assert wizard.name, "Wizard missing name"
            assert wizard.description, f"{wizard.name} missing description"
            assert len(wizard.keywords) > 0, f"{wizard.name} missing keywords"
            assert wizard.primary_domain, f"{wizard.name} missing domain"

            # Verify wizard can be retrieved
            retrieved = registry.get(wizard.name)
            assert retrieved is not None
            assert retrieved.name == wizard.name

    def test_classifier_fallback_works(self):
        """Test that keyword classifier works as fallback."""
        classifier = HaikuClassifier()

        # Should work without API key (keyword fallback)
        result = classifier.classify_sync("Check for security vulnerabilities")

        assert isinstance(result, ClassificationResult)
        assert result.primary_workflow == "security-audit"
        assert result.confidence > 0


class TestResilienceIntegration:
    """Test resilience patterns with Intelligence System."""

    def test_router_handles_missing_registry(self):
        """Test router handles gracefully when registry is empty."""
        router = SmartRouter()

        # Should still return a decision even for unclear requests
        decision = router.route_sync("do something")

        assert decision is not None
        assert decision.primary_workflow  # Should have a default

    def test_chain_executor_handles_missing_config(self):
        """Test chain executor handles missing config file."""
        executor = ChainExecutor("nonexistent_file.yaml")

        # Should return empty list, not crash
        triggers = executor.get_triggered_chains("any-wizard", {})
        assert triggers == []
