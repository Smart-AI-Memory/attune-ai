"""Unit tests for plan_generator module.

Tests cover:
- AgentStep dataclass creation and field access
- ExecutionPlan dataclass creation and field access
- PlanGenerator initialization, plan generation, response collection,
  step building, agent inclusion logic, prompt building, and output formatting
- generate_plan() top-level function with all output formats and error handling

Created: 2026-02-08
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from attune.meta_workflows.models import (
    AgentCompositionRule,
    MetaWorkflowTemplate,
    TierStrategy,
)
from attune.meta_workflows.plan_generator import (
    AgentStep,
    ExecutionPlan,
    PlanGenerator,
    generate_plan,
)

# =============================================================================
# Fixtures
# =============================================================================


def _make_mock_question(question_id: str, default: str | None = None, required: bool = True):
    """Create a mock FormQuestion object.

    Args:
        question_id: The question ID
        default: Default value for the question
        required: Whether the question is required

    Returns:
        MagicMock mimicking a FormQuestion
    """
    question = MagicMock()
    question.id = question_id
    question.default = default
    question.required = required
    return question


def _make_mock_template(
    template_id: str = "test-template",
    name: str = "Test Template",
    questions: list | None = None,
    rules: list | None = None,
):
    """Create a mock MetaWorkflowTemplate.

    Args:
        template_id: Template identifier
        name: Template name
        questions: List of mock questions for the form schema
        rules: List of AgentCompositionRule objects

    Returns:
        MagicMock mimicking a MetaWorkflowTemplate
    """
    if questions is None:
        questions = [_make_mock_question("scope", default="full")]

    mock_form_schema = MagicMock()
    mock_form_schema.questions = questions

    mock_template = MagicMock(spec=MetaWorkflowTemplate)
    mock_template.template_id = template_id
    mock_template.name = name
    mock_template.form_schema = mock_form_schema

    if rules is None:
        rules = [
            AgentCompositionRule(
                role="Security Analyst",
                base_template="security_review",
                tier_strategy=TierStrategy.CAPABLE_FIRST,
                tools=["Grep", "Read"],
                success_criteria=["No critical vulnerabilities"],
                config_mapping={"scope": "scan_scope"},
                required_responses={},
            )
        ]

    mock_template.agent_composition_rules = rules
    return mock_template


# =============================================================================
# AgentStep Tests
# =============================================================================


class TestAgentStep:
    """Test AgentStep dataclass."""

    def test_creation(self):
        """Test AgentStep can be created with all fields."""
        step = AgentStep(
            order=1,
            role="Test Runner",
            tier_recommendation="sonnet",
            tools=["pytest", "coverage"],
            prompt="Run tests and report coverage.",
            success_criteria=["All tests pass", "Coverage above 80%"],
            config={"min_coverage": "80%"},
        )

        assert step.order == 1
        assert step.role == "Test Runner"
        assert step.tier_recommendation == "sonnet"
        assert step.tools == ["pytest", "coverage"]
        assert step.prompt == "Run tests and report coverage."
        assert step.success_criteria == ["All tests pass", "Coverage above 80%"]
        assert step.config == {"min_coverage": "80%"}

    def test_field_access(self):
        """Test individual field access on AgentStep."""
        step = AgentStep(
            order=3,
            role="Reviewer",
            tier_recommendation="opus",
            tools=["Read"],
            prompt="Review code.",
            success_criteria=["No issues found"],
            config={},
        )

        assert step.order == 3
        assert step.role == "Reviewer"
        assert step.tier_recommendation == "opus"
        assert step.tools == ["Read"]
        assert step.config == {}


# =============================================================================
# ExecutionPlan Tests
# =============================================================================


class TestExecutionPlan:
    """Test ExecutionPlan dataclass."""

    def test_creation(self):
        """Test ExecutionPlan can be created with all fields."""
        step = AgentStep(
            order=1,
            role="Analyst",
            tier_recommendation="sonnet",
            tools=["Grep"],
            prompt="Analyze code.",
            success_criteria=["Analysis complete"],
            config={},
        )

        plan = ExecutionPlan(
            template_id="my-template",
            template_name="My Template",
            generated_at="2026-02-08T12:00:00",
            form_responses={"scope": "full"},
            steps=[step],
            synthesis_prompt="Synthesize findings.",
        )

        assert plan.template_id == "my-template"
        assert plan.template_name == "My Template"
        assert plan.generated_at == "2026-02-08T12:00:00"
        assert plan.form_responses == {"scope": "full"}
        assert len(plan.steps) == 1
        assert plan.steps[0].role == "Analyst"
        assert plan.synthesis_prompt == "Synthesize findings."

    def test_field_access(self):
        """Test individual field access on ExecutionPlan."""
        plan = ExecutionPlan(
            template_id="t1",
            template_name="Template One",
            generated_at="2026-01-01T00:00:00",
            form_responses={},
            steps=[],
            synthesis_prompt="",
        )

        assert plan.template_id == "t1"
        assert plan.template_name == "Template One"
        assert plan.steps == []
        assert plan.form_responses == {}


# =============================================================================
# PlanGenerator Tests
# =============================================================================


class TestPlanGenerator:
    """Test PlanGenerator class."""

    def test_init_stores_template(self):
        """Test that __init__ stores the template."""
        mock_template = _make_mock_template()
        generator = PlanGenerator(mock_template)

        assert generator.template is mock_template

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_generate_returns_execution_plan(self, mock_get_template):
        """Test generate() returns an ExecutionPlan with correct structure."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Scan for vulnerabilities."
        mock_get_template.return_value = mock_base

        mock_template = _make_mock_template()
        generator = PlanGenerator(mock_template)

        plan = generator.generate(form_responses={"scope": "full"})

        assert isinstance(plan, ExecutionPlan)
        assert plan.template_id == "test-template"
        assert plan.template_name == "Test Template"
        assert plan.form_responses == {"scope": "full"}
        assert len(plan.steps) == 1
        assert plan.steps[0].role == "Security Analyst"
        assert plan.generated_at is not None
        assert plan.synthesis_prompt is not None

    def test_collect_responses_uses_provided(self):
        """Test _collect_responses uses provided responses."""
        question = _make_mock_question("scope", default="full")
        mock_template = _make_mock_template(questions=[question])
        generator = PlanGenerator(mock_template)

        responses = generator._collect_responses({"scope": "partial"}, use_defaults=True)

        assert responses["scope"] == "partial"

    def test_collect_responses_uses_defaults(self):
        """Test _collect_responses falls back to defaults when no response provided."""
        question = _make_mock_question("scope", default="full")
        mock_template = _make_mock_template(questions=[question])
        generator = PlanGenerator(mock_template)

        responses = generator._collect_responses(None, use_defaults=True)

        assert responses["scope"] == "full"

    def test_collect_responses_missing_required_raises(self):
        """Test _collect_responses raises ValueError for missing required response."""
        question = _make_mock_question("scope", default=None, required=True)
        mock_template = _make_mock_template(questions=[question])
        generator = PlanGenerator(mock_template)

        with pytest.raises(ValueError, match="Missing required response: scope"):
            generator._collect_responses(None, use_defaults=True)

    def test_collect_responses_missing_optional_no_error(self):
        """Test _collect_responses does not raise for missing optional response."""
        question = _make_mock_question("notes", default=None, required=False)
        mock_template = _make_mock_template(questions=[question])
        generator = PlanGenerator(mock_template)

        responses = generator._collect_responses(None, use_defaults=True)

        assert "notes" not in responses

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_build_steps_creates_agent_steps(self, mock_get_template):
        """Test _build_steps creates AgentStep list from composition rules."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Default instructions."
        mock_get_template.return_value = mock_base

        rule = AgentCompositionRule(
            role="Code Reviewer",
            base_template="code_review",
            tier_strategy=TierStrategy.PREMIUM_ONLY,
            tools=["Read", "Grep"],
            success_criteria=["No major issues"],
            config_mapping={"scope": "review_scope"},
            required_responses={},
        )
        mock_template = _make_mock_template(rules=[rule])
        generator = PlanGenerator(mock_template)

        steps = generator._build_steps({"scope": "full"})

        assert len(steps) == 1
        assert isinstance(steps[0], AgentStep)
        assert steps[0].order == 1
        assert steps[0].role == "Code Reviewer"
        assert steps[0].tier_recommendation == "opus"
        assert steps[0].tools == ["Read", "Grep"]
        assert steps[0].success_criteria == ["No major issues"]
        assert steps[0].config == {"review_scope": "full"}

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_build_steps_multiple_rules(self, mock_get_template):
        """Test _build_steps assigns sequential order numbers."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Instructions."
        mock_get_template.return_value = mock_base

        rule1 = AgentCompositionRule(
            role="Agent A",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["Read"],
            success_criteria=["Done"],
            config_mapping={},
            required_responses={},
        )
        rule2 = AgentCompositionRule(
            role="Agent B",
            base_template="generic",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=["Grep"],
            success_criteria=["Complete"],
            config_mapping={},
            required_responses={},
        )
        mock_template = _make_mock_template(rules=[rule1, rule2])
        generator = PlanGenerator(mock_template)

        steps = generator._build_steps({})

        assert len(steps) == 2
        assert steps[0].order == 1
        assert steps[0].role == "Agent A"
        assert steps[1].order == 2
        assert steps[1].role == "Agent B"

    def test_should_include_agent_no_requirements(self):
        """Test _should_include_agent returns True when no required_responses."""
        rule = AgentCompositionRule(
            role="Agent",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            required_responses={},
        )
        mock_template = _make_mock_template()
        generator = PlanGenerator(mock_template)

        assert generator._should_include_agent(rule, {"scope": "full"}) is True

    def test_should_include_agent_matching_response(self):
        """Test _should_include_agent returns True when response matches."""
        rule = AgentCompositionRule(
            role="Agent",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            required_responses={"include_security": "yes"},
        )
        mock_template = _make_mock_template()
        generator = PlanGenerator(mock_template)

        result = generator._should_include_agent(rule, {"include_security": "yes"})

        assert result is True

    def test_should_include_agent_mismatched_response(self):
        """Test _should_include_agent returns False when response does not match."""
        rule = AgentCompositionRule(
            role="Agent",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            required_responses={"include_security": "yes"},
        )
        mock_template = _make_mock_template()
        generator = PlanGenerator(mock_template)

        result = generator._should_include_agent(rule, {"include_security": "no"})

        assert result is False

    def test_should_include_agent_missing_response(self):
        """Test _should_include_agent returns False when required key is missing."""
        rule = AgentCompositionRule(
            role="Agent",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            required_responses={"include_security": "yes"},
        )
        mock_template = _make_mock_template()
        generator = PlanGenerator(mock_template)

        result = generator._should_include_agent(rule, {})

        assert result is False

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_build_agent_prompt_includes_role_and_criteria(self, mock_get_template):
        """Test _build_agent_prompt includes role, instructions, and criteria."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Perform a security scan."
        mock_get_template.return_value = mock_base

        rule = AgentCompositionRule(
            role="Security Analyst",
            base_template="security_review",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
            tools=["Grep", "Read"],
            success_criteria=["No critical vulnerabilities", "Report generated"],
            config_mapping={"scope": "scan_scope"},
            required_responses={},
        )
        mock_template = _make_mock_template(rules=[rule])
        generator = PlanGenerator(mock_template)

        prompt = generator._build_agent_prompt(rule, mock_base, {"scope": "full"})

        assert "Security Analyst" in prompt
        assert "Perform a security scan." in prompt
        assert "No critical vulnerabilities" in prompt
        assert "Report generated" in prompt
        assert "Grep" in prompt
        assert "Read" in prompt
        assert "scan_scope" in prompt

    def test_build_agent_prompt_no_base_template(self):
        """Test _build_agent_prompt works when base_template is None."""
        rule = AgentCompositionRule(
            role="Generic Agent",
            base_template="nonexistent",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["Read"],
            success_criteria=["Task done"],
            config_mapping={},
            required_responses={},
        )
        mock_template = _make_mock_template(rules=[rule])
        generator = PlanGenerator(mock_template)

        prompt = generator._build_agent_prompt(rule, None, {})

        assert "Generic Agent" in prompt
        assert "Task done" in prompt
        assert "Using default configuration." in prompt

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_to_markdown_returns_expected_headers(self, mock_get_template):
        """Test to_markdown returns markdown with expected section headers."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Instructions."
        mock_get_template.return_value = mock_base

        mock_template = _make_mock_template()
        generator = PlanGenerator(mock_template)
        plan = generator.generate(form_responses={"scope": "full"})

        markdown = generator.to_markdown(plan)

        assert isinstance(markdown, str)
        assert "# Execution Plan: Test Template" in markdown
        assert "## Configuration" in markdown
        assert "## Execution Steps" in markdown
        assert "## Synthesis" in markdown
        assert "**scope**: full" in markdown
        assert "Step 1: Security Analyst" in markdown

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_to_claude_code_skill_returns_expected_format(self, mock_get_template):
        """Test to_claude_code_skill returns skill-formatted output."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Analyze security."
        mock_get_template.return_value = mock_base

        mock_template = _make_mock_template()
        generator = PlanGenerator(mock_template)
        plan = generator.generate(form_responses={"scope": "full"})

        skill = generator.to_claude_code_skill(plan)

        assert isinstance(skill, str)
        assert "# Test Template" in skill
        assert "## Steps" in skill
        assert "## Synthesis" in skill
        assert "## Output" in skill
        assert "Security Analyst" in skill
        assert "subagent_type" in skill

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_build_synthesis_prompt_includes_all_roles(self, mock_get_template):
        """Test _build_synthesis_prompt references all step roles."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Instructions."
        mock_get_template.return_value = mock_base

        rule1 = AgentCompositionRule(
            role="Analyst",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["Read"],
            success_criteria=["Done"],
            config_mapping={},
            required_responses={},
        )
        rule2 = AgentCompositionRule(
            role="Reviewer",
            base_template="generic",
            tier_strategy=TierStrategy.CAPABLE_FIRST,
            tools=["Grep"],
            success_criteria=["Complete"],
            config_mapping={},
            required_responses={},
        )
        mock_template = _make_mock_template(rules=[rule1, rule2])
        generator = PlanGenerator(mock_template)

        steps = generator._build_steps({})
        synthesis = generator._build_synthesis_prompt(steps)

        assert "Analyst" in synthesis
        assert "Reviewer" in synthesis
        assert "## Summary" in synthesis
        assert "## Critical Issues" in synthesis

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_tier_to_model_mapping(self, mock_get_template):
        """Test that tier strategies map to correct model recommendations."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Instructions."
        mock_get_template.return_value = mock_base

        test_cases = [
            (TierStrategy.CHEAP_ONLY, "haiku"),
            (TierStrategy.PROGRESSIVE, "sonnet (escalate to opus if needed)"),
            (TierStrategy.CAPABLE_FIRST, "sonnet"),
            (TierStrategy.PREMIUM_ONLY, "opus"),
        ]

        for tier, expected_model in test_cases:
            rule = AgentCompositionRule(
                role="Agent",
                base_template="generic",
                tier_strategy=tier,
                tools=[],
                success_criteria=[],
                config_mapping={},
                required_responses={},
            )
            mock_template = _make_mock_template(rules=[rule])
            generator = PlanGenerator(mock_template)

            steps = generator._build_steps({})

            assert len(steps) == 1
            assert steps[0].tier_recommendation == expected_model, (
                f"Expected {expected_model} for {tier}, got {steps[0].tier_recommendation}"
            )

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_build_steps_excluded_agent(self, mock_get_template):
        """Test _build_steps excludes agents that do not match required_responses."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Instructions."
        mock_get_template.return_value = mock_base

        rule_included = AgentCompositionRule(
            role="Always Included",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["Read"],
            success_criteria=["Done"],
            config_mapping={},
            required_responses={},
        )
        rule_excluded = AgentCompositionRule(
            role="Conditionally Excluded",
            base_template="generic",
            tier_strategy=TierStrategy.PREMIUM_ONLY,
            tools=["Grep"],
            success_criteria=["Done"],
            config_mapping={},
            required_responses={"enable_premium": "yes"},
        )
        mock_template = _make_mock_template(rules=[rule_included, rule_excluded])
        generator = PlanGenerator(mock_template)

        steps = generator._build_steps({"enable_premium": "no"})

        assert len(steps) == 1
        assert steps[0].role == "Always Included"


# =============================================================================
# generate_plan() Function Tests
# =============================================================================


class TestGeneratePlan:
    """Test the top-level generate_plan() function.

    The generate_plan() function uses a lazy import:
        from attune.meta_workflows.registry import get_template as get_workflow_template

    To mock this, we inject a mock module into sys.modules before calling
    the function, so the lazy import resolves to our mock.
    """

    def _patch_registry(self, return_value):
        """Create a context manager that mocks the registry lazy import.

        Args:
            return_value: What get_template should return

        Returns:
            Patch context manager for the registry module
        """
        mock_registry_module = MagicMock()
        mock_registry_module.get_template.return_value = return_value
        return patch.dict(
            "sys.modules",
            {"attune.meta_workflows.registry": mock_registry_module},
        )

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_generate_plan_markdown(self, mock_get_agent_template):
        """Test generate_plan returns markdown output."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Instructions."
        mock_get_agent_template.return_value = mock_base

        mock_workflow_template = _make_mock_template()

        with self._patch_registry(mock_workflow_template):
            result = generate_plan(
                "test-template",
                form_responses={"scope": "full"},
                output_format="markdown",
            )

        assert isinstance(result, str)
        assert "# Execution Plan: Test Template" in result
        assert "## Configuration" in result

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_generate_plan_json(self, mock_get_agent_template):
        """Test generate_plan returns valid JSON output."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Instructions."
        mock_get_agent_template.return_value = mock_base

        mock_workflow_template = _make_mock_template()

        with self._patch_registry(mock_workflow_template):
            result = generate_plan(
                "test-template",
                form_responses={"scope": "full"},
                output_format="json",
            )

        parsed = json.loads(result)
        assert parsed["template_id"] == "test-template"
        assert parsed["template_name"] == "Test Template"
        assert "steps" in parsed
        assert "synthesis_prompt" in parsed
        assert isinstance(parsed["steps"], list)

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_generate_plan_skill(self, mock_get_agent_template):
        """Test generate_plan returns skill-formatted output."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Instructions."
        mock_get_agent_template.return_value = mock_base

        mock_workflow_template = _make_mock_template()

        with self._patch_registry(mock_workflow_template):
            result = generate_plan(
                "test-template",
                form_responses={"scope": "full"},
                output_format="skill",
            )

        assert isinstance(result, str)
        assert "# Test Template" in result
        assert "## Steps" in result

    def test_generate_plan_unknown_template(self):
        """Test generate_plan raises ValueError for unknown template."""
        with self._patch_registry(None):
            with pytest.raises(ValueError, match="Template not found"):
                generate_plan("nonexistent-template")

    @patch("attune.meta_workflows.plan_generator.get_template")
    def test_generate_plan_unknown_format(self, mock_get_agent_template):
        """Test generate_plan raises ValueError for unknown output format."""
        mock_base = MagicMock()
        mock_base.default_instructions = "Instructions."
        mock_get_agent_template.return_value = mock_base

        mock_workflow_template = _make_mock_template()

        with self._patch_registry(mock_workflow_template):
            with pytest.raises(ValueError, match="Unknown format"):
                generate_plan(
                    "test-template",
                    form_responses={"scope": "full"},
                    output_format="xml",
                )
