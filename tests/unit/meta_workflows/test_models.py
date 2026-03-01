"""Unit tests for meta-workflow data models.

Tests cover:
- Form question conversion to AskUserQuestion format
- Form schema batching
- Form response storage and retrieval
- Agent composition rule matching logic
- Agent config mapping from form responses
- Template JSON serialization/deserialization
- Result data structures

Created: 2026-01-17
"""

import json
from datetime import datetime

import pytest

from attune.meta_workflows.models import (
    AgentCompositionRule,
    AgentExecutionResult,
    AgentSpec,
    FormQuestion,
    FormResponse,
    FormSchema,
    MetaWorkflowResult,
    MetaWorkflowTemplate,
    PatternInsight,
    QuestionType,
    TierStrategy,
)

# =============================================================================
# FormQuestion Tests
# =============================================================================


class TestFormQuestion:
    """Test FormQuestion model."""

    def test_single_select_to_ask_user_format(self):
        """Test conversion to AskUserQuestion format for single-select."""
        question = FormQuestion(
            id="test_q",
            text="Pick one option",
            type=QuestionType.SINGLE_SELECT,
            options=["Option A", "Option B", "Option C"],
            help_text="Choose wisely",
        )

        result = question.to_ask_user_format()

        assert result["question_id"] == "test_q"
        assert result["question"] == "Pick one option"
        assert result["type"] == "single_select"
        assert result["options"] == ["Option A", "Option B", "Option C"]
        assert result["help_text"] == "Choose wisely"

    def test_multi_select_to_ask_user_format(self):
        """Test conversion to AskUserQuestion format for multi-select."""
        question = FormQuestion(
            id="multi_q",
            text="Select multiple",
            type=QuestionType.MULTI_SELECT,
            options=["Option 1", "Option 2"],
        )

        result = question.to_ask_user_format()

        assert result["question_id"] == "multi_q"
        assert result["type"] == "multi_select"
        assert len(result["options"]) == 2

    def test_boolean_converted_to_yes_no(self):
        """Test boolean questions convert to Yes/No options."""
        question = FormQuestion(id="bool_q", text="Agree?", type=QuestionType.BOOLEAN)

        result = question.to_ask_user_format()

        assert result["type"] == "single_select"
        assert result["options"] == ["Yes", "No"]

    def test_text_input_format(self):
        """Test text input question format."""
        question = FormQuestion(
            id="text_q",
            text="Enter your name",
            type=QuestionType.TEXT_INPUT,
            default="John Doe",
        )

        result = question.to_ask_user_format()

        assert result["question_id"] == "text_q"
        assert result["type"] == "text_input"
        assert result["default"] == "John Doe"


# =============================================================================
# FormSchema Tests
# =============================================================================


class TestFormSchema:
    """Test FormSchema model."""

    def test_batch_questions_by_four(self):
        """Test questions are batched correctly (4 per batch)."""
        questions = [
            FormQuestion(id=f"q{i}", text=f"Question {i}", type=QuestionType.TEXT_INPUT)
            for i in range(10)
        ]
        schema = FormSchema(questions=questions, title="Test Form", description="Test")

        batches = schema.get_question_batches(batch_size=4)

        assert len(batches) == 3  # 4 + 4 + 2
        assert len(batches[0]) == 4
        assert len(batches[1]) == 4
        assert len(batches[2]) == 2

    def test_batch_with_exact_multiple(self):
        """Test batching when question count is exact multiple."""
        questions = [
            FormQuestion(id=f"q{i}", text=f"Q{i}", type=QuestionType.BOOLEAN) for i in range(8)
        ]
        schema = FormSchema(questions=questions, title="Test", description="Test")

        batches = schema.get_question_batches(batch_size=4)

        assert len(batches) == 2
        assert all(len(batch) == 4 for batch in batches)

    def test_empty_questions_list(self):
        """Test schema with no questions."""
        schema = FormSchema(questions=[], title="Empty", description="No questions")

        batches = schema.get_question_batches()

        assert len(batches) == 0


# =============================================================================
# FormResponse Tests
# =============================================================================


class TestFormResponse:
    """Test FormResponse model."""

    def test_get_existing_response(self):
        """Test retrieving existing response."""
        response = FormResponse(template_id="test", responses={"q1": "Answer 1", "q2": "Answer 2"})

        assert response.get("q1") == "Answer 1"
        assert response.get("q2") == "Answer 2"

    def test_get_nonexistent_response_returns_default(self):
        """Test get with default for missing question."""
        response = FormResponse(template_id="test", responses={"q1": "Answer"})

        assert response.get("q_missing", default="default_value") == "default_value"

    def test_automatic_timestamp_and_id_generation(self):
        """Test that timestamp and response_id are auto-generated."""
        response = FormResponse(template_id="test", responses={})

        assert response.timestamp is not None
        assert response.response_id.startswith("resp-")
        assert len(response.response_id) > 10


# =============================================================================
# AgentCompositionRule Tests
# =============================================================================


class TestAgentCompositionRule:
    """Test agent composition rules."""

    def test_should_create_with_matching_single_response(self):
        """Test agent is created when single-select condition matches."""
        rule = AgentCompositionRule(
            role="test_agent",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["pytest"],
            required_responses={"has_tests": "Yes"},
        )

        response = FormResponse(template_id="test", responses={"has_tests": "Yes"})

        assert rule.should_create(response) is True

    def test_should_not_create_with_non_matching_response(self):
        """Test agent is not created when condition doesn't match."""
        rule = AgentCompositionRule(
            role="test_agent",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["pytest"],
            required_responses={"has_tests": "Yes"},
        )

        response = FormResponse(template_id="test", responses={"has_tests": "No"})

        assert rule.should_create(response) is False

    def test_multi_select_matching_single_required_value(self):
        """Test multi-select responses with single required value."""
        rule = AgentCompositionRule(
            role="linter",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["ruff"],
            required_responses={"quality_checks": "Linting (ruff)"},
        )

        response = FormResponse(
            template_id="test",
            responses={"quality_checks": ["Type checking (mypy)", "Linting (ruff)"]},
        )

        assert rule.should_create(response) is True

    def test_multi_select_not_matching(self):
        """Test multi-select when required value not in selections."""
        rule = AgentCompositionRule(
            role="linter",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["ruff"],
            required_responses={"quality_checks": "Linting (ruff)"},
        )

        response = FormResponse(
            template_id="test",
            responses={"quality_checks": ["Type checking (mypy)"]},
        )

        assert rule.should_create(response) is False

    def test_multiple_required_responses_all_match(self):
        """Test multiple conditions all match."""
        rule = AgentCompositionRule(
            role="publisher",
            base_template="generic",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=["twine"],
            required_responses={
                "publish_to": ["PyPI (production)", "TestPyPI (staging)"],
                "has_tests": "Yes",
            },
        )

        response = FormResponse(
            template_id="test",
            responses={"publish_to": "PyPI (production)", "has_tests": "Yes"},
        )

        assert rule.should_create(response) is True

    def test_multiple_required_responses_one_fails(self):
        """Test multiple conditions where one doesn't match."""
        rule = AgentCompositionRule(
            role="publisher",
            base_template="generic",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=["twine"],
            required_responses={
                "publish_to": ["PyPI (production)", "TestPyPI (staging)"],
                "has_tests": "Yes",
            },
        )

        response = FormResponse(
            template_id="test",
            responses={"publish_to": "Skip publishing", "has_tests": "Yes"},
        )

        assert rule.should_create(response) is False

    def test_create_agent_config_from_responses(self):
        """Test agent config is populated from form responses."""
        rule = AgentCompositionRule(
            role="version_manager",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=["git"],
            config_mapping={"version_bump": "bump_type", "package_name": "name"},
        )

        response = FormResponse(
            template_id="test",
            responses={"version_bump": "minor", "package_name": "test-pkg"},
        )

        config = rule.create_agent_config(response)

        assert config["bump_type"] == "minor"
        assert config["name"] == "test-pkg"

    def test_create_agent_config_with_missing_values(self):
        """Test config mapping skips missing values."""
        rule = AgentCompositionRule(
            role="test_agent",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            tools=[],
            config_mapping={"missing_key": "config_key", "present_key": "other_key"},
        )

        response = FormResponse(template_id="test", responses={"present_key": "value"})

        config = rule.create_agent_config(response)

        assert "other_key" in config
        assert config["other_key"] == "value"
        assert "config_key" not in config


# =============================================================================
# AgentSpec Tests
# =============================================================================


class TestAgentSpec:
    """Test AgentSpec model."""

    def test_agent_spec_creation(self):
        """Test basic agent spec creation."""
        spec = AgentSpec(
            role="test_runner",
            base_template="test_coverage_analyzer",
            tier_strategy=TierStrategy.PROGRESSIVE,
            tools=["pytest", "coverage"],
            config={"min_coverage": "80%"},
            success_criteria=["All tests pass"],
        )

        assert spec.role == "test_runner"
        assert spec.tier_strategy == TierStrategy.PROGRESSIVE
        assert spec.agent_id.startswith("agent-")

    def test_agent_id_unique(self):
        """Test that agent IDs are unique."""
        spec1 = AgentSpec(
            role="agent1",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        spec2 = AgentSpec(
            role="agent2",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )

        assert spec1.agent_id != spec2.agent_id


# =============================================================================
# MetaWorkflowTemplate Tests
# =============================================================================


class TestMetaWorkflowTemplate:
    """Test template serialization."""

    def test_template_to_json(self):
        """Test template can be serialized to JSON."""
        template = MetaWorkflowTemplate(
            template_id="test_template",
            name="Test Template",
            description="Test description",
            form_schema=FormSchema(
                questions=[FormQuestion(id="q1", text="Question 1", type=QuestionType.BOOLEAN)],
                title="Test Form",
                description="Test",
            ),
            agent_composition_rules=[
                AgentCompositionRule(
                    role="test_agent",
                    base_template="generic",
                    tier_strategy=TierStrategy.PROGRESSIVE,
                    tools=["pytest"],
                ),
            ],
        )

        json_str = template.to_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["template_id"] == "test_template"
        assert data["name"] == "Test Template"
        assert len(data["form_schema"]["questions"]) == 1
        assert len(data["agent_composition_rules"]) == 1

    def test_template_round_trip_json(self):
        """Test template can be serialized and deserialized."""
        template = MetaWorkflowTemplate(
            template_id="test_template",
            name="Test Template",
            description="Test description",
            version="1.0.0",
            tags=["test", "demo"],
            author="test_author",
            form_schema=FormSchema(
                questions=[
                    FormQuestion(id="q1", text="Question 1", type=QuestionType.BOOLEAN),
                    FormQuestion(
                        id="q2",
                        text="Question 2",
                        type=QuestionType.SINGLE_SELECT,
                        options=["A", "B"],
                    ),
                ],
                title="Test Form",
                description="Test",
            ),
            agent_composition_rules=[
                AgentCompositionRule(
                    role="test_agent",
                    base_template="generic",
                    tier_strategy=TierStrategy.PROGRESSIVE,
                    tools=["pytest"],
                    required_responses={"q1": "Yes"},
                    config_mapping={"q2": "option"},
                    success_criteria=["Tests pass"],
                ),
            ],
            estimated_cost_range=(0.10, 0.50),
            estimated_duration_minutes=10,
        )

        # Serialize
        json_str = template.to_json()

        # Deserialize
        restored = MetaWorkflowTemplate.from_json(json_str)

        assert restored.template_id == template.template_id
        assert restored.name == template.name
        assert restored.version == template.version
        assert restored.tags == template.tags
        assert restored.author == template.author
        assert len(restored.form_schema.questions) == 2
        assert len(restored.agent_composition_rules) == 1
        assert restored.estimated_cost_range == template.estimated_cost_range
        assert restored.estimated_duration_minutes == template.estimated_duration_minutes

    def test_template_from_json_invalid(self):
        """Test template deserialization with invalid JSON."""
        invalid_json = "{ invalid json }"

        with pytest.raises(ValueError, match="Invalid JSON"):
            MetaWorkflowTemplate.from_json(invalid_json)


# =============================================================================
# MetaWorkflowResult Tests
# =============================================================================


class TestMetaWorkflowResult:
    """Test workflow result data structure."""

    def test_result_to_dict(self):
        """Test result can be converted to dictionary."""
        form_response = FormResponse(template_id="test", responses={"q1": "Answer"})

        agent_spec = AgentSpec(
            role="test_agent",
            base_template="generic",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )

        agent_result = AgentExecutionResult(
            agent_id=agent_spec.agent_id,
            role="test_agent",
            success=True,
            cost=0.05,
            duration=2.0,
            tier_used="cheap",
            output="Success",
        )

        result = MetaWorkflowResult(
            run_id="test-run-123",
            template_id="test_template",
            timestamp=datetime.now().isoformat(),
            form_responses=form_response,
            agents_created=[agent_spec],
            agent_results=[agent_result],
            total_cost=0.05,
            total_duration=2.0,
            success=True,
        )

        result_dict = result.to_dict()

        assert result_dict["run_id"] == "test-run-123"
        assert result_dict["template_id"] == "test_template"
        assert len(result_dict["agents_created"]) == 1
        assert len(result_dict["agent_results"]) == 1
        assert result_dict["total_cost"] == 0.05

    def test_result_round_trip_dict(self):
        """Test result can be converted to dict and back."""
        form_response = FormResponse(template_id="test", responses={"q1": "Answer"})

        result = MetaWorkflowResult(
            run_id="test-run-123",
            template_id="test_template",
            timestamp=datetime.now().isoformat(),
            form_responses=form_response,
            total_cost=0.10,
            total_duration=5.0,
            success=True,
        )

        # To dict
        result_dict = result.to_dict()

        # From dict
        restored = MetaWorkflowResult.from_dict(result_dict)

        assert restored.run_id == result.run_id
        assert restored.template_id == result.template_id
        assert restored.total_cost == result.total_cost
        assert restored.success == result.success


# =============================================================================
# PatternInsight Tests
# =============================================================================


class TestPatternInsight:
    """Test pattern insight model."""

    def test_insight_to_dict(self):
        """Test insight can be converted to dictionary."""
        insight = PatternInsight(
            insight_type="cost_optimization",
            description="Agent X succeeds 95% at cheap tier",
            confidence=0.95,
            data={"agent": "test_runner", "tier": "cheap", "success_rate": 0.95},
            sample_size=20,
        )

        insight_dict = insight.to_dict()

        assert insight_dict["insight_type"] == "cost_optimization"
        assert insight_dict["confidence"] == 0.95
        assert insight_dict["sample_size"] == 20
