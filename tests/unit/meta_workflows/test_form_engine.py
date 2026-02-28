"""Unit tests for Socratic form engine.

Tests cover:
- Question format conversion
- Batch processing
- Response collection and caching
- Header generation

Created: 2026-01-17
"""

from unittest.mock import Mock

from attune.meta_workflows.form_engine import (
    SocraticFormEngine,
    convert_ask_user_response_to_form_response,
    create_header_from_question,
)
from attune.meta_workflows.models import FormQuestion, FormSchema, QuestionType


class TestSocraticFormEngine:
    """Test SocraticFormEngine."""

    def test_ask_questions_with_empty_schema(self):
        """Test asking questions with empty schema returns empty response."""
        engine = SocraticFormEngine()
        schema = FormSchema(questions=[], title="Empty", description="No questions")

        response = engine.ask_questions(schema, "test_template")

        assert response.template_id == "test_template"
        assert len(response.responses) == 0

    def test_ask_questions_batches_correctly(self):
        """Test questions are batched correctly (4 per batch)."""
        engine = SocraticFormEngine()

        # Create 10 questions
        questions = [
            FormQuestion(id=f"q{i}", text=f"Question {i}", type=QuestionType.TEXT_INPUT)
            for i in range(10)
        ]
        schema = FormSchema(questions=questions, title="Test", description="Test")

        # Mock _ask_batch to return responses
        def mock_ask_batch(questions, template_id):
            return {q["question_id"]: f"answer_{q['question_id']}" for q in questions}

        engine._ask_batch = Mock(side_effect=mock_ask_batch)

        response = engine.ask_questions(schema, "test_template")

        # Should have called _ask_batch 3 times (4 + 4 + 2)
        assert engine._ask_batch.call_count == 3

        # Should have all 10 responses
        assert len(response.responses) == 10
        assert all(f"q{i}" in response.responses for i in range(10))

    def test_ask_questions_caches_response(self):
        """Test responses are cached by response_id."""
        engine = SocraticFormEngine()

        questions = [FormQuestion(id="q1", text="Question 1", type=QuestionType.BOOLEAN)]
        schema = FormSchema(questions=questions, title="Test", description="Test")

        engine._ask_batch = Mock(return_value={"q1": "Yes"})

        response = engine.ask_questions(schema, "test_template")

        # Response should be cached
        cached = engine.get_cached_response(response.response_id)
        assert cached is not None
        assert cached.response_id == response.response_id
        assert cached.get("q1") == "Yes"

    def test_clear_cache(self):
        """Test cache clearing."""
        engine = SocraticFormEngine()

        questions = [FormQuestion(id="q1", text="Question 1", type=QuestionType.BOOLEAN)]
        schema = FormSchema(questions=questions, title="Test", description="Test")

        engine._ask_batch = Mock(return_value={"q1": "Yes"})

        response = engine.ask_questions(schema, "test_template")
        response_id = response.response_id

        # Cache should have response
        assert engine.get_cached_response(response_id) is not None

        # Clear cache
        engine.clear_cache()

        # Cache should be empty
        assert engine.get_cached_response(response_id) is None

    def test_convert_batch_to_ask_user_format(self):
        """Test batch conversion to AskUserQuestion format."""
        engine = SocraticFormEngine()

        questions = [
            FormQuestion(
                id="q1",
                text="Question 1",
                type=QuestionType.SINGLE_SELECT,
                options=["A", "B"],
            ),
            FormQuestion(id="q2", text="Question 2", type=QuestionType.BOOLEAN),
        ]

        result = engine._convert_batch_to_ask_user_format(questions)

        assert len(result) == 2
        assert result[0]["question_id"] == "q1"
        assert result[0]["type"] == "single_select"
        assert result[1]["question_id"] == "q2"
        assert result[1]["type"] == "single_select"  # Boolean converted
        assert result[1]["options"] == ["Yes", "No"]


class TestConvertAskUserResponseToFormResponse:
    """Test conversion from AskUserQuestion result to FormResponse."""

    def test_basic_conversion(self):
        """Test basic conversion."""
        ask_user_result = {"q1": "Answer 1", "q2": "Answer 2"}

        response = convert_ask_user_response_to_form_response(ask_user_result, "test_template")

        assert response.template_id == "test_template"
        assert response.get("q1") == "Answer 1"
        assert response.get("q2") == "Answer 2"

    def test_multi_select_conversion(self):
        """Test conversion with multi-select answers."""
        ask_user_result = {
            "q1": "Single answer",
            "q2": ["Option A", "Option B", "Option C"],
        }

        response = convert_ask_user_response_to_form_response(ask_user_result, "test_template")

        assert response.get("q1") == "Single answer"
        assert isinstance(response.get("q2"), list)
        assert len(response.get("q2")) == 3


class TestCreateHeaderFromQuestion:
    """Test header generation for questions."""

    def test_test_related_question(self):
        """Test header for test-related questions."""
        question = FormQuestion(
            id="has_tests",
            text="Do you have tests?",
            type=QuestionType.BOOLEAN,
        )

        header = create_header_from_question(question)

        assert header == "Tests"

    def test_coverage_related_question(self):
        """Test header for coverage-related questions."""
        question = FormQuestion(
            id="coverage_threshold",
            text="What coverage do you require?",
            type=QuestionType.SINGLE_SELECT,
            options=["70%", "80%", "90%"],
        )

        header = create_header_from_question(question)

        assert header == "Coverage"

    def test_version_related_question(self):
        """Test header for version-related questions."""
        question = FormQuestion(
            id="version_bump",
            text="How should we bump the version?",
            type=QuestionType.SINGLE_SELECT,
            options=["patch", "minor", "major"],
        )

        header = create_header_from_question(question)

        assert header == "Version"

    def test_fallback_to_question_id(self):
        """Test fallback to question ID for unknown patterns."""
        question = FormQuestion(
            id="custom_question_id",
            text="Some unrecognized question text",
            type=QuestionType.TEXT_INPUT,
        )

        header = create_header_from_question(question)

        # Should use question ID (title-cased, truncated to 12 chars)
        assert header == "Custom_Quest"
        assert len(header) <= 12

    def test_publish_related_question(self):
        """Test header for publishing-related questions."""
        question = FormQuestion(
            id="publish_to",
            text="Where should we publish?",
            type=QuestionType.SINGLE_SELECT,
            options=["PyPI", "TestPyPI"],
        )

        header = create_header_from_question(question)

        assert header == "Publishing"

    def test_quality_related_question(self):
        """Test header for quality-related questions."""
        question = FormQuestion(
            id="quality_checks",
            text="What quality checks should we run?",
            type=QuestionType.MULTI_SELECT,
            options=["Linting", "Type checking"],
        )

        header = create_header_from_question(question)

        assert header == "Quality"

    def test_security_related_question(self):
        """Test header for security-related questions."""
        question = FormQuestion(
            id="security_scan",
            text="Run security scan?",
            type=QuestionType.BOOLEAN,
        )

        header = create_header_from_question(question)

        assert header == "Security"
