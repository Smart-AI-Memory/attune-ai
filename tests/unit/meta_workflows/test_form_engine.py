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


# ---------------------------------------------------------------------------
# _ask_batch coverage (lines 145-166)
# ---------------------------------------------------------------------------


class TestAskBatch:
    def test_callback_invoked_returns_result(self):
        """Lines 148-153: callback present → returned dict."""
        engine = SocraticFormEngine(
            ask_user_callback=lambda qs: {"q1": "yes"},
        )
        result = engine._ask_batch([{"question_id": "q1", "header": "Q1", "question": "?"}], "tmpl")
        assert result == {"q1": "yes"}

    def test_callback_raises_with_defaults_fallback(self):
        """Lines 154-158: callback raises + use_defaults_when_no_callback=True → defaults."""

        def bad_callback(qs):
            raise ValueError("network down")

        engine = SocraticFormEngine(
            ask_user_callback=bad_callback,
            use_defaults_when_no_callback=True,
        )
        result = engine._ask_batch([{"question_id": "q1", "default": "x"}], "tmpl")
        assert result == {"q1": "x"}

    def test_callback_raises_no_defaults_reraises(self):
        """Line 159: callback raises + use_defaults_when_no_callback=False → RuntimeError."""
        import pytest

        def bad_callback(qs):
            raise ValueError("net down")

        engine = SocraticFormEngine(
            ask_user_callback=bad_callback,
            use_defaults_when_no_callback=False,
        )
        with pytest.raises(RuntimeError, match="callback failed"):
            engine._ask_batch([{"question_id": "q1"}], "tmpl")

    def test_no_callback_uses_defaults(self):
        """Lines 162-164: no callback + use_defaults=True → defaults."""
        engine = SocraticFormEngine(use_defaults_when_no_callback=True)
        result = engine._ask_batch([{"question_id": "q1", "default": "auto"}], "tmpl")
        assert result == {"q1": "auto"}

    def test_no_callback_no_defaults_raises(self):
        """Lines 166-169: no callback + use_defaults=False → RuntimeError."""
        import pytest

        engine = SocraticFormEngine(use_defaults_when_no_callback=False)
        with pytest.raises(RuntimeError, match="No AskUserQuestion callback"):
            engine._ask_batch([{"question_id": "q1"}], "tmpl")


# ---------------------------------------------------------------------------
# _get_defaults_from_questions coverage (lines 181-206)
# ---------------------------------------------------------------------------


class TestGetDefaultsFromQuestions:
    def test_explicit_default_is_used(self):
        """Lines 187-190: q['default'] takes precedence."""
        engine = SocraticFormEngine()
        result = engine._get_defaults_from_questions(
            [{"question_id": "q1", "default": "MY_DEFAULT", "options": [{"label": "ignored"}]}]
        )
        assert result == {"q1": "MY_DEFAULT"}

    def test_first_option_dict_used_when_no_default(self):
        """Lines 197-198: first option is dict → use its label."""
        engine = SocraticFormEngine()
        result = engine._get_defaults_from_questions(
            [{"question_id": "q1", "options": [{"label": "yes"}, {"label": "no"}]}]
        )
        assert result == {"q1": "yes"}

    def test_first_option_string_used_when_no_default(self):
        """Lines 199-200: first option is non-dict → str() conversion."""
        engine = SocraticFormEngine()
        result = engine._get_defaults_from_questions(
            [{"question_id": "q1", "options": ["alpha", "beta"]}]
        )
        assert result == {"q1": "alpha"}

    def test_no_options_no_default_yields_empty_string(self):
        """Lines 201-202: no options and no default → empty string."""
        engine = SocraticFormEngine()
        result = engine._get_defaults_from_questions([{"question_id": "q1"}])
        assert result == {"q1": ""}

    def test_falls_back_to_header_then_question_when_no_id(self):
        """Line 184: prefer question_id, then header, then question."""
        engine = SocraticFormEngine()
        result = engine._get_defaults_from_questions([{"header": "MyHeader", "default": "v"}])
        assert result == {"MyHeader": "v"}
        result2 = engine._get_defaults_from_questions([{"question": "Q text?", "default": "v"}])
        assert result2 == {"Q text?": "v"}


# ---------------------------------------------------------------------------
# set_callback (lines 215-216)
# ---------------------------------------------------------------------------


class TestSetCallback:
    def test_set_callback_assigns(self):
        """Line 215: callback is stored on instance."""
        engine = SocraticFormEngine()

        def cb(qs):
            return {}

        engine.set_callback(cb)
        assert engine._ask_user_callback is cb

    def test_set_callback_clears_with_none(self):
        """Line 215: passing None clears the callback."""
        engine = SocraticFormEngine(ask_user_callback=lambda qs: {})
        engine.set_callback(None)
        assert engine._ask_user_callback is None


# ---------------------------------------------------------------------------
# create_header_from_question — coverage gaps at lines 296, 298, 300
# ---------------------------------------------------------------------------


class TestCreateHeaderEdgeCases:
    def test_name_keyword(self):
        """Line 295-296: 'name' in text → 'Name'."""
        q = FormQuestion(id="x", text="What is the project name?", type=QuestionType.TEXT_INPUT)
        assert create_header_from_question(q) == "Name"

    def test_changelog_keyword(self):
        """Line 297-298: 'changelog' in text → 'Changelog'."""
        q = FormQuestion(id="x", text="Update the changelog?", type=QuestionType.BOOLEAN)
        assert create_header_from_question(q) == "Changelog"

    def test_git_keyword(self):
        """Line 299-300: 'git' in text → 'Git'."""
        q = FormQuestion(id="x", text="Configure git settings?", type=QuestionType.BOOLEAN)
        assert create_header_from_question(q) == "Git"
