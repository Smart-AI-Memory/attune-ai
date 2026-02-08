"""Tests for Smart Router and Wizard Classification

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

from pathlib import Path

import pytest

# Check if workflow_chains.yaml exists for chain executor tests
CHAIN_CONFIG_EXISTS = Path(".attune/workflow_chains.yaml").exists()

from attune.routing import (  # noqa: E402
    ChainExecutor,
    HaikuClassifier,
    RoutingDecision,
    SmartRouter,
    WorkflowInfo,
    WorkflowRegistry,
)


class TestWorkflowRegistry:
    """Tests for WorkflowRegistry."""

    def test_default_workflows_loaded(self):
        """Test that default wizards are loaded."""
        registry = WorkflowRegistry()
        wizards = registry.list_all()

        assert len(wizards) >= 10
        assert registry.get("security-audit") is not None
        assert registry.get("code-review") is not None
        assert registry.get("bug-predict") is not None

    def test_get_wizard(self):
        """Test getting a specific wizard."""
        registry = WorkflowRegistry()
        wizard = registry.get("security-audit")

        assert wizard is not None
        assert wizard.name == "security-audit"
        assert wizard.primary_domain == "security"
        assert "vulnerability" in wizard.keywords

    def test_register_custom_wizard(self):
        """Test registering a custom wizard."""
        registry = WorkflowRegistry()

        custom = WorkflowInfo(
            name="custom-wizard",
            description="A custom wizard for testing",
            keywords=["custom", "test"],
            primary_domain="testing",
        )

        registry.register(custom)

        assert registry.get("custom-wizard") is not None
        assert registry.get("custom-wizard").primary_domain == "testing"

    def test_find_by_domain(self):
        """Test finding wizards by domain."""
        registry = WorkflowRegistry()
        security_wizards = registry.find_by_domain("security")

        assert len(security_wizards) >= 1
        assert all(w.primary_domain == "security" for w in security_wizards)

    def test_find_by_keyword(self):
        """Test finding wizards by keyword."""
        registry = WorkflowRegistry()
        vuln_wizards = registry.find_by_keyword("vulnerability")

        assert len(vuln_wizards) >= 1
        # Security and dependency wizards should match
        names = [w.name for w in vuln_wizards]
        assert "security-audit" in names

    def test_get_descriptions_for_classification(self):
        """Test getting descriptions for LLM classification."""
        registry = WorkflowRegistry()
        descriptions = registry.get_descriptions_for_classification()

        assert "security-audit" in descriptions
        assert "domain: security" in descriptions["security-audit"]

    def test_unregister_wizard(self):
        """Test removing a wizard."""
        registry = WorkflowRegistry()

        # Add then remove
        registry.register(
            WorkflowInfo(
                name="temp-wizard",
                description="Temporary",
                keywords=["temp"],
            ),
        )

        assert registry.get("temp-wizard") is not None
        registry.unregister("temp-wizard")
        assert registry.get("temp-wizard") is None


class TestHaikuClassifier:
    """Tests for HaikuClassifier (keyword fallback)."""

    def test_keyword_classify_security(self):
        """Test keyword classification for security requests."""
        classifier = HaikuClassifier()
        result = classifier.classify_sync("Check for SQL injection vulnerabilities")

        assert result.primary_workflow == "security-audit"
        assert result.confidence > 0

    def test_keyword_classify_performance(self):
        """Test keyword classification for performance requests."""
        classifier = HaikuClassifier()
        result = classifier.classify_sync("Optimize slow database queries")

        assert result.primary_workflow == "perf-audit"

    def test_keyword_classify_testing(self):
        """Test keyword classification for testing requests."""
        classifier = HaikuClassifier()
        result = classifier.classify_sync("Generate unit tests for the auth module")

        assert result.primary_workflow == "test-gen"

    def test_keyword_classify_bugs(self):
        """Test keyword classification for bug requests."""
        classifier = HaikuClassifier()
        result = classifier.classify_sync("Find the null reference error causing crashes")

        assert result.primary_workflow == "bug-predict"

    def test_keyword_classify_with_secondary(self):
        """Test that secondary wizards are suggested."""
        classifier = HaikuClassifier()
        # Request that matches multiple domains
        result = classifier.classify_sync("Fix the security vulnerability bug")

        assert result.primary_workflow in ["security-audit", "bug-predict"]
        # Should have secondary suggestions
        assert len(result.secondary_workflows) >= 0

    def test_default_to_code_review(self):
        """Test defaulting to code-review for unclear requests."""
        classifier = HaikuClassifier()
        result = classifier.classify_sync("Can you help with my code?")

        # Should default to code-review with low confidence
        assert result.primary_workflow == "code-review"
        assert result.confidence < 0.5


class TestSmartRouter:
    """Tests for SmartRouter."""

    def test_route_sync(self):
        """Test synchronous routing."""
        router = SmartRouter()
        decision = router.route_sync("Fix security issues in auth.py")

        assert isinstance(decision, RoutingDecision)
        assert decision.primary_workflow == "security-audit"
        assert decision.classification_method == "keyword"

    def test_route_sync_with_context(self):
        """Test routing with context."""
        router = SmartRouter()
        decision = router.route_sync(
            "Review this code",
            context={"file": "auth.py", "language": "python"},
        )

        assert decision.context.get("file") == "auth.py"

    def test_suggest_for_file_python(self):
        """Test file-based suggestions for Python files."""
        router = SmartRouter()
        suggestions = router.suggest_for_file("src/auth.py")

        assert "security-audit" in suggestions
        assert "code-review" in suggestions

    def test_suggest_for_file_package_json(self):
        """Test file-based suggestions for package.json."""
        router = SmartRouter()
        suggestions = router.suggest_for_file("package.json")

        assert "dependency-check" in suggestions

    def test_suggest_for_error_security(self):
        """Test error-based suggestions for security errors."""
        router = SmartRouter()
        suggestions = router.suggest_for_error("SecurityError: Permission denied")

        assert "security-audit" in suggestions

    def test_suggest_for_error_null(self):
        """Test error-based suggestions for null errors."""
        router = SmartRouter()
        suggestions = router.suggest_for_error("NullReferenceException")

        assert "bug-predict" in suggestions

    def test_list_workflows(self):
        """Test listing all wizards."""
        router = SmartRouter()
        wizards = router.list_workflows()

        assert len(wizards) >= 10
        assert all(isinstance(w, WorkflowInfo) for w in wizards)

    def test_get_workflow_info(self):
        """Test getting specific wizard info."""
        router = SmartRouter()
        info = router.get_workflow_info("security-audit")

        assert info is not None
        assert info.name == "security-audit"

    def test_routing_decision_structure(self):
        """Test that routing decision has expected structure."""
        router = SmartRouter()
        decision = router.route_sync("Test request")

        assert hasattr(decision, "primary_workflow")
        assert hasattr(decision, "secondary_workflows")
        assert hasattr(decision, "confidence")
        assert hasattr(decision, "reasoning")
        assert hasattr(decision, "suggested_chain")
        assert hasattr(decision, "context")


@pytest.mark.skipif(not CHAIN_CONFIG_EXISTS, reason=".attune/workflow_chains.yaml not found")
class TestChainExecutor:
    """Tests for ChainExecutor."""

    def test_load_config(self):
        """Test loading chain configuration."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")
        templates = executor.list_templates()

        assert len(templates) >= 1

    def test_get_triggered_chains(self):
        """Test getting triggered chains based on results."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")

        result = {"high_severity_count": 5}
        triggers = executor.get_triggered_chains("security-audit", result)

        assert len(triggers) >= 1
        assert any(t.next_workflow == "bug-predict" for t in triggers)

    def test_condition_evaluation_greater_than(self):
        """Test condition evaluation with greater than."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")

        result = {"count": 10}
        assert executor._evaluate_condition("count > 5", result) is True
        assert executor._evaluate_condition("count > 15", result) is False

    def test_condition_evaluation_equals(self):
        """Test condition evaluation with equals."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")

        result = {"status": "critical"}
        assert executor._evaluate_condition("status == 'critical'", result) is True
        assert executor._evaluate_condition("status == 'low'", result) is False

    def test_condition_evaluation_boolean(self):
        """Test condition evaluation with booleans."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")

        result = {"has_issues": True}
        assert executor._evaluate_condition("has_issues == true", result) is True
        assert executor._evaluate_condition("has_issues == false", result) is False

    def test_should_trigger_chain(self):
        """Test should_trigger_chain helper."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")

        should, triggers = executor.should_trigger_chain(
            "bug-predict",
            {"high_risk_count": 10},
        )

        assert should is True
        assert len(triggers) >= 1

    def test_get_chain_config(self):
        """Test getting chain config for a wizard."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")
        config = executor.get_chain_config("security-audit")

        assert config is not None
        assert config.auto_chain is True
        assert len(config.triggers) >= 1

    def test_get_template(self):
        """Test getting a chain template."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")
        template = executor.get_template("full-security-review")

        assert template is not None
        assert "security-audit" in template

    def test_create_execution(self):
        """Test creating a chain execution."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")

        triggers = executor.get_triggered_chains(
            "security-audit",
            {"high_severity_count": 5},
        )

        execution = executor.create_execution("security-audit", triggers)

        assert execution.initial_workflow == "security-audit"
        assert len(execution.steps) >= 2  # Initial + triggered

    def test_approve_step(self):
        """Test approving a chain step."""
        executor = ChainExecutor(".attune/workflow_chains.yaml")
        execution = executor.create_execution("test", [])

        # Add a step that needs approval
        from attune.routing import ChainStep

        execution.steps.append(
            ChainStep(
                workflow_name="next-wizard",
                triggered_by="test",
                approval_required=True,
            ),
        )

        assert execution.steps[1].approved is None
        executor.approve_step(execution, 1)
        assert execution.steps[1].approved is True
