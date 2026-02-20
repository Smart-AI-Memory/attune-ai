"""Tests for socratic/llm_analyzer.py module.

Tests the LLM-powered goal analysis including:
- Data classes (LLMAnalysisResult, LLMQuestionResult, LLMAgentRecommendation)
- LLMGoalAnalyzer with mocked LLM calls
- JSON parsing from LLM responses
- Fallback analysis logic
- Form generation from LLM questions

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.socratic.forms import FieldType
from attune.socratic.llm_analyzer import (
    GOAL_ANALYSIS_PROMPT,
    LLMAgentRecommendation,
    LLMAnalysisResult,
    LLMGoalAnalyzer,
    LLMQuestionResult,
    MockLLMExecutor,
    llm_questions_to_form,
)
from attune.socratic.session import SocraticSession

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def analyzer():
    """Create LLMGoalAnalyzer without API key."""
    return LLMGoalAnalyzer(api_key=None)


@pytest.fixture
def analyzer_with_key():
    """Create LLMGoalAnalyzer with fake API key."""
    return LLMGoalAnalyzer(api_key="test-api-key")


@pytest.fixture
def mock_session():
    """Create a mock SocraticSession."""
    session = SocraticSession(session_id="test-session")
    session.goal = "Automate code reviews for Python"
    session.question_rounds = [{"answers": {"language": "python"}}]

    # Mock requirements
    requirements = MagicMock()
    requirements.must_have = ["security"]
    requirements.technical_constraints = ["python"]
    requirements.quality_attributes = ["performance"]
    requirements.preferences = {}
    requirements.domain_specific = {}
    session.requirements = requirements

    # Mock goal_analysis
    goal_analysis = MagicMock()
    goal_analysis.domain = "code_review"
    goal_analysis.ambiguities = ["Which testing framework?"]
    session.goal_analysis = goal_analysis

    return session


@pytest.fixture
def sample_llm_response():
    """Sample LLM analysis response."""
    return json.dumps(
        {
            "intent": "Automate code reviews",
            "domain": "code_review",
            "confidence": 0.85,
            "ambiguities": ["Which languages?"],
            "assumptions": ["Python codebase"],
            "constraints": ["Fast execution"],
            "keywords": ["code", "review", "python"],
            "suggested_agents": ["code_quality_reviewer", "security_reviewer"],
            "suggested_questions": [
                {
                    "id": "q1",
                    "question": "Which languages?",
                    "type": "multi_select",
                    "options": ["Python", "JavaScript"],
                }
            ],
        }
    )


@pytest.fixture
def sample_question_response():
    """Sample LLM question generation response."""
    return json.dumps(
        {
            "questions": [
                {
                    "id": "q1",
                    "question": "What testing framework?",
                    "type": "single_select",
                    "options": ["pytest", "unittest"],
                    "category": "technical",
                    "priority": 5,
                }
            ],
            "confidence_after_answers": 0.9,
            "ready_to_generate": True,
            "reasoning": "All key information gathered",
        }
    )


@pytest.fixture
def sample_agent_response():
    """Sample LLM agent recommendation response."""
    return json.dumps(
        {
            "agents": [
                {
                    "template_id": "code_quality_reviewer",
                    "priority": 1,
                    "customizations": {"focus_areas": ["style"]},
                    "reasoning": "Needed for quality",
                }
            ],
            "workflow_stages": [
                {"name": "Analysis", "agents": ["code_quality_reviewer"], "parallel": False}
            ],
            "estimated_cost_tier": "cheap",
            "estimated_duration": "fast",
        }
    )


# =============================================================================
# LLM ANALYSIS RESULT TESTS
# =============================================================================


@pytest.mark.unit
class TestLLMAnalysisResult:
    """Tests for LLMAnalysisResult dataclass."""

    def test_create_result(self):
        """Test creating an analysis result."""
        result = LLMAnalysisResult(
            intent="Test intent",
            domain="code_review",
            confidence=0.9,
            ambiguities=["Question 1"],
            assumptions=["Assumption 1"],
            constraints=["Constraint 1"],
            keywords=["keyword1"],
            suggested_agents=["reviewer"],
            suggested_questions=[],
        )

        assert result.intent == "Test intent"
        assert result.domain == "code_review"
        assert result.confidence == 0.9

    def test_primary_domain_property(self):
        """Test primary_domain property (alias for domain)."""
        result = LLMAnalysisResult(
            intent="",
            domain="security",
            confidence=0.8,
            ambiguities=[],
            assumptions=[],
            constraints=[],
            keywords=[],
            suggested_agents=[],
            suggested_questions=[],
        )

        assert result.primary_domain == "security"
        assert result.primary_domain == result.domain

    def test_optional_fields_have_defaults(self):
        """Test optional fields have default values."""
        result = LLMAnalysisResult(
            intent="",
            domain="general",
            confidence=0.5,
            ambiguities=[],
            assumptions=[],
            constraints=[],
            keywords=[],
            suggested_agents=[],
            suggested_questions=[],
        )

        assert result.raw_response == ""
        assert result.secondary_domains == []
        assert result.detected_requirements == []


# =============================================================================
# LLM QUESTION RESULT TESTS
# =============================================================================


@pytest.mark.unit
class TestLLMQuestionResult:
    """Tests for LLMQuestionResult dataclass."""

    def test_create_result(self):
        """Test creating a question result."""
        result = LLMQuestionResult(
            questions=[{"id": "q1", "question": "Test?"}],
            confidence_after_answers=0.85,
            ready_to_generate=True,
            reasoning="All requirements gathered",
        )

        assert len(result.questions) == 1
        assert result.confidence_after_answers == 0.85
        assert result.ready_to_generate is True
        assert "requirements" in result.reasoning


# =============================================================================
# LLM AGENT RECOMMENDATION TESTS
# =============================================================================


@pytest.mark.unit
class TestLLMAgentRecommendation:
    """Tests for LLMAgentRecommendation dataclass."""

    def test_create_recommendation(self):
        """Test creating an agent recommendation."""
        result = LLMAgentRecommendation(
            agents=[{"template_id": "reviewer", "priority": 1}],
            workflow_stages=[{"name": "Review", "agents": ["reviewer"]}],
            estimated_cost_tier="cheap",
            estimated_duration="fast",
        )

        assert len(result.agents) == 1
        assert result.agents[0]["template_id"] == "reviewer"
        assert result.estimated_cost_tier == "cheap"
        assert result.estimated_duration == "fast"


# =============================================================================
# LLM GOAL ANALYZER INITIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
class TestLLMGoalAnalyzerInit:
    """Tests for LLMGoalAnalyzer initialization."""

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict("os.environ", {}, clear=True):
            analyzer = LLMGoalAnalyzer(api_key=None)

            assert analyzer.api_key is None
            assert analyzer._client is None
            assert analyzer._executor is None

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        analyzer = LLMGoalAnalyzer(api_key="test-key")

        assert analyzer.api_key == "test-key"
        assert analyzer.provider == "anthropic"
        assert analyzer.model_tier == "capable"

    def test_init_with_env_api_key(self):
        """Test initialization picks up API key from environment."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env-key"}):
            analyzer = LLMGoalAnalyzer(api_key=None)

            assert analyzer.api_key == "env-key"

    def test_init_custom_model_tier(self):
        """Test initialization with custom model tier."""
        analyzer = LLMGoalAnalyzer(model_tier="premium")

        assert analyzer.model_tier == "premium"

    def test_models_constant(self):
        """Test MODELS constant contains expected tiers."""
        assert "cheap" in LLMGoalAnalyzer.MODELS
        assert "capable" in LLMGoalAnalyzer.MODELS
        assert "premium" in LLMGoalAnalyzer.MODELS


# =============================================================================
# GET CLIENT TESTS
# =============================================================================


@pytest.mark.unit
class TestGetClient:
    """Tests for _get_client method."""

    def test_get_client_without_api_key(self, analyzer, monkeypatch):
        """Test _get_client returns None without API key."""
        # Ensure no API key from environment
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Create a fresh analyzer without API key
        from src.attune.socratic.llm_analyzer import LLMGoalAnalyzer

        analyzer_no_key = LLMGoalAnalyzer(api_key=None)
        client = analyzer_no_key._get_client()
        assert client is None

    def test_get_client_with_api_key_no_anthropic(self, analyzer_with_key):
        """Test _get_client handles missing anthropic package."""
        with patch.dict("sys.modules", {"anthropic": None}):
            with patch("importlib.import_module", side_effect=ImportError):
                # This shouldn't raise, just return None
                analyzer_with_key._get_client()
                # May or may not be None depending on if anthropic is installed

    def test_get_client_caches_client(self, analyzer_with_key):
        """Test _get_client returns cached client."""
        mock_client = MagicMock()
        analyzer_with_key._client = mock_client

        result = analyzer_with_key._get_client()
        assert result is mock_client


# =============================================================================
# JSON PARSING TESTS
# =============================================================================


@pytest.mark.unit
class TestParseJsonResponse:
    """Tests for _parse_json_response method."""

    def test_parse_valid_json(self, analyzer):
        """Test parsing valid JSON."""
        content = '{"key": "value", "number": 42}'
        result = analyzer._parse_json_response(content)

        assert result["key"] == "value"
        assert result["number"] == 42

    def test_parse_json_in_code_block(self, analyzer):
        """Test parsing JSON from markdown code block."""
        content = """Here's the response:
```json
{"key": "value"}
```
That's the JSON."""
        result = analyzer._parse_json_response(content)

        assert result["key"] == "value"

    def test_parse_json_in_code_block_no_lang(self, analyzer):
        """Test parsing JSON from code block without language."""
        content = """```
{"key": "value"}
```"""
        result = analyzer._parse_json_response(content)

        assert result["key"] == "value"

    def test_parse_json_object_in_text(self, analyzer):
        """Test parsing JSON object embedded in text."""
        content = 'Here is the result: {"key": "value"} and more text'
        result = analyzer._parse_json_response(content)

        assert result["key"] == "value"

    def test_parse_invalid_json_returns_empty(self, analyzer):
        """Test parsing invalid JSON returns empty dict."""
        content = "This is not JSON at all"
        result = analyzer._parse_json_response(content)

        assert result == {}

    def test_parse_nested_json(self, analyzer):
        """Test parsing nested JSON structure."""
        content = json.dumps(
            {
                "outer": {"inner": [1, 2, 3]},
                "list": [{"a": 1}, {"b": 2}],
            }
        )
        result = analyzer._parse_json_response(content)

        assert result["outer"]["inner"] == [1, 2, 3]
        assert len(result["list"]) == 2


# =============================================================================
# ANALYZE GOAL TESTS
# =============================================================================


@pytest.mark.unit
class TestAnalyzeGoal:
    """Tests for analyze_goal method."""

    @pytest.mark.asyncio
    async def test_analyze_goal_with_mock_llm(self, analyzer, sample_llm_response):
        """Test analyze_goal with mocked LLM response."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = sample_llm_response

            result = await analyzer.analyze_goal("Automate code reviews")

            assert result.intent == "Automate code reviews"
            assert result.domain == "code_review"
            assert result.confidence == 0.85
            assert "Which languages?" in result.ambiguities

    @pytest.mark.asyncio
    async def test_analyze_goal_uses_fallback_on_error(self, analyzer):
        """Test analyze_goal falls back on LLM error."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("LLM error")

            result = await analyzer.analyze_goal("Check security vulnerabilities")

            # Should use fallback analysis
            assert result.domain in ["security", "code_review", "general"]
            assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_analyze_goal_prompt_formatting(self, analyzer):
        """Test goal is properly formatted in prompt."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "{}"

            await analyzer.analyze_goal("Test goal")

            # Verify prompt was called with goal
            args = mock_call.call_args
            assert "Test goal" in args[0][0]


# =============================================================================
# GENERATE QUESTIONS TESTS
# =============================================================================


@pytest.mark.unit
class TestGenerateQuestions:
    """Tests for generate_questions method."""

    @pytest.mark.asyncio
    async def test_generate_questions_success(
        self, analyzer, mock_session, sample_question_response
    ):
        """Test successful question generation."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = sample_question_response

            result = await analyzer.generate_questions(mock_session)

            assert len(result.questions) == 1
            assert result.confidence_after_answers == 0.9
            assert result.ready_to_generate is True

    @pytest.mark.asyncio
    async def test_generate_questions_on_error(self, analyzer, mock_session):
        """Test question generation handles errors."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("LLM error")

            result = await analyzer.generate_questions(mock_session)

            assert result.questions == []
            assert result.ready_to_generate is False
            assert "Fallback" in result.reasoning


# =============================================================================
# RECOMMEND AGENTS TESTS
# =============================================================================


@pytest.mark.unit
class TestRecommendAgents:
    """Tests for recommend_agents method."""

    @pytest.mark.asyncio
    async def test_recommend_agents_success(self, analyzer, mock_session, sample_agent_response):
        """Test successful agent recommendation."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = sample_agent_response

            result = await analyzer.recommend_agents(mock_session)

            assert len(result.agents) == 1
            assert result.agents[0]["template_id"] == "code_quality_reviewer"
            assert result.estimated_cost_tier == "cheap"

    @pytest.mark.asyncio
    async def test_recommend_agents_fallback(self, analyzer, mock_session):
        """Test agent recommendation falls back on error."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("LLM error")

            result = await analyzer.recommend_agents(mock_session)

            # Should return fallback recommendation
            assert len(result.agents) > 0
            assert result.estimated_cost_tier == "moderate"


# =============================================================================
# FALLBACK ANALYSIS TESTS
# =============================================================================


@pytest.mark.unit
class TestFallbackAnalysis:
    """Tests for _fallback_analysis method."""

    def test_fallback_security_domain(self, analyzer):
        """Test fallback detects security domain."""
        result = analyzer._fallback_analysis("Check for security vulnerabilities")

        assert result.domain in ["security", "code_review"]
        assert (
            "security_reviewer" in result.suggested_agents
            or "code_quality_reviewer" in result.suggested_agents
        )

    def test_fallback_testing_domain(self, analyzer):
        """Test fallback detects testing domain."""
        result = analyzer._fallback_analysis("Generate unit tests")

        assert result.domain in ["testing", "general"]

    def test_fallback_returns_valid_result(self, analyzer):
        """Test fallback returns valid LLMAnalysisResult."""
        result = analyzer._fallback_analysis("Some goal")

        assert isinstance(result, LLMAnalysisResult)
        assert result.intent != ""
        assert result.domain != ""
        assert 0 <= result.confidence <= 1


# =============================================================================
# FALLBACK AGENT RECOMMENDATION TESTS
# =============================================================================


@pytest.mark.unit
class TestFallbackAgentRecommendation:
    """Tests for _fallback_agent_recommendation method."""

    def test_fallback_security_domain(self, mock_session):
        """Test fallback for security domain."""
        mock_session.goal_analysis.domain = "security"
        analyzer = LLMGoalAnalyzer()

        result = analyzer._fallback_agent_recommendation(mock_session)

        assert any(a["template_id"] == "security_reviewer" for a in result.agents)

    def test_fallback_code_review_domain(self, mock_session):
        """Test fallback for code_review domain."""
        mock_session.goal_analysis.domain = "code_review"
        analyzer = LLMGoalAnalyzer()

        result = analyzer._fallback_agent_recommendation(mock_session)

        assert any(a["template_id"] == "code_quality_reviewer" for a in result.agents)

    def test_fallback_testing_domain(self, mock_session):
        """Test fallback for testing domain."""
        mock_session.goal_analysis.domain = "testing"
        analyzer = LLMGoalAnalyzer()

        result = analyzer._fallback_agent_recommendation(mock_session)

        assert any(a["template_id"] == "test_generator" for a in result.agents)

    def test_fallback_unknown_domain(self, mock_session):
        """Test fallback for unknown domain defaults to code_review."""
        mock_session.goal_analysis.domain = "unknown_domain"
        analyzer = LLMGoalAnalyzer()

        result = analyzer._fallback_agent_recommendation(mock_session)

        # Should use code_review as default
        assert len(result.agents) > 0

    def test_fallback_no_goal_analysis(self):
        """Test fallback when session has no goal_analysis."""
        session = MagicMock()
        session.goal_analysis = None
        analyzer = LLMGoalAnalyzer()

        result = analyzer._fallback_agent_recommendation(session)

        assert len(result.agents) > 0
        assert result.estimated_cost_tier == "moderate"


# =============================================================================
# MOCK LLM EXECUTOR TESTS
# =============================================================================


@pytest.mark.unit
class TestMockLLMExecutor:
    """Tests for MockLLMExecutor."""

    @pytest.mark.asyncio
    async def test_run_returns_mock_response(self):
        """Test run returns mock response."""
        executor = MockLLMExecutor()
        result = await executor.run(prompt="test")

        assert result.content == "{}"


# =============================================================================
# LLM QUESTIONS TO FORM TESTS
# =============================================================================


@pytest.mark.unit
class TestLlmQuestionsToForm:
    """Tests for llm_questions_to_form function."""

    def test_convert_single_select(self, mock_session):
        """Test converting single select question."""
        questions = [
            {
                "id": "q1",
                "question": "Which framework?",
                "type": "single_select",
                "options": ["pytest", "unittest"],
            }
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.id == "llm_round_1"
        assert len(form.fields) == 1
        assert form.fields[0].field_type == FieldType.SINGLE_SELECT
        assert len(form.fields[0].options) == 2

    def test_convert_multi_select(self, mock_session):
        """Test converting multi select question."""
        questions = [
            {
                "id": "q1",
                "question": "Which languages?",
                "type": "multi_select",
                "options": ["Python", "JavaScript"],
            }
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].field_type == FieldType.MULTI_SELECT

    def test_convert_text(self, mock_session):
        """Test converting text question."""
        questions = [
            {
                "id": "q1",
                "question": "Any additional notes?",
                "type": "text",
            }
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].field_type == FieldType.TEXT

    def test_convert_text_area(self, mock_session):
        """Test converting text_area question."""
        questions = [
            {
                "id": "q1",
                "question": "Describe your needs",
                "type": "text_area",
            }
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].field_type == FieldType.TEXT_AREA

    def test_convert_boolean(self, mock_session):
        """Test converting boolean question."""
        questions = [
            {
                "id": "q1",
                "question": "Enable feature?",
                "type": "boolean",
            }
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].field_type == FieldType.BOOLEAN

    def test_convert_unknown_type_defaults_to_text(self, mock_session):
        """Test unknown type defaults to text."""
        questions = [
            {
                "id": "q1",
                "question": "Question?",
                "type": "unknown_type",
            }
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].field_type == FieldType.TEXT

    def test_options_string_format(self, mock_session):
        """Test options in string format are converted."""
        questions = [
            {
                "id": "q1",
                "question": "Choose one",
                "type": "single_select",
                "options": ["Option A", "Option B"],
            }
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].options[0].value == "option_a"
        assert form.fields[0].options[0].label == "Option A"

    def test_options_dict_format(self, mock_session):
        """Test options in dict format are converted."""
        questions = [
            {
                "id": "q1",
                "question": "Choose one",
                "type": "single_select",
                "options": [
                    {"value": "a", "label": "Option A", "description": "Desc A"},
                    {"value": "b", "label": "Option B"},
                ],
            }
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].options[0].value == "a"
        assert form.fields[0].options[0].description == "Desc A"

    def test_form_progress_calculation(self, mock_session):
        """Test progress is calculated based on round."""
        form1 = llm_questions_to_form([], round_number=1, session=mock_session)
        form2 = llm_questions_to_form([], round_number=2, session=mock_session)
        form5 = llm_questions_to_form([], round_number=5, session=mock_session)

        # Use pytest.approx for floating point comparisons
        assert form1.progress == pytest.approx(0.45)  # 0.3 + 1 * 0.15
        assert form2.progress == pytest.approx(0.6)  # 0.3 + 2 * 0.15
        assert form5.progress == pytest.approx(0.9)  # capped at 0.9

    def test_fields_sorted_by_priority(self, mock_session):
        """Test fields are sorted by priority (descending)."""
        questions = [
            {"id": "q1", "question": "Low priority", "type": "text", "priority": 1},
            {"id": "q2", "question": "High priority", "type": "text", "priority": 5},
            {"id": "q3", "question": "Medium priority", "type": "text", "priority": 3},
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        # Higher priority should come first
        assert form.fields[0].id == "q2"  # priority 5
        assert form.fields[1].id == "q3"  # priority 3
        assert form.fields[2].id == "q1"  # priority 1

    def test_form_title_and_description(self, mock_session):
        """Test form title and description are set."""
        form = llm_questions_to_form([], round_number=3, session=mock_session)

        assert "Questions" in form.title
        assert "Round 3" in form.description

    def test_question_with_required_flag(self, mock_session):
        """Test required flag is respected."""
        questions = [
            {"id": "q1", "question": "Required?", "type": "text", "required": True},
            {"id": "q2", "question": "Optional?", "type": "text", "required": False},
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].validation.required is True
        assert form.fields[1].validation.required is False

    def test_question_category(self, mock_session):
        """Test category is preserved."""
        questions = [
            {"id": "q1", "question": "Tech?", "type": "text", "category": "technical"},
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].category == "technical"

    def test_auto_generated_id(self, mock_session):
        """Test ID is auto-generated if missing."""
        questions = [
            {"question": "Question without ID", "type": "text"},
        ]

        form = llm_questions_to_form(questions, round_number=1, session=mock_session)

        assert form.fields[0].id == "q_0"


# =============================================================================
# PROMPT CONSTANT TESTS
# =============================================================================


@pytest.mark.unit
class TestPromptConstants:
    """Tests for prompt constants."""

    def test_goal_analysis_prompt_contains_placeholders(self):
        """Test GOAL_ANALYSIS_PROMPT has required placeholder."""
        assert "{goal}" in GOAL_ANALYSIS_PROMPT

    def test_goal_analysis_prompt_requests_json(self):
        """Test prompt asks for JSON response."""
        assert "JSON" in GOAL_ANALYSIS_PROMPT
        assert "domain" in GOAL_ANALYSIS_PROMPT
        assert "ambiguities" in GOAL_ANALYSIS_PROMPT


# =============================================================================
# CALL LLM TESTS
# =============================================================================


@pytest.mark.unit
class TestCallLlm:
    """Tests for _call_llm method."""

    @pytest.mark.asyncio
    async def test_call_llm_uses_executor_fallback(self, analyzer):
        """Test _call_llm uses executor when no API key."""
        mock_executor = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = '{"test": true}'
        mock_executor.run.return_value = mock_response

        with (
            patch.object(analyzer, "_get_client", return_value=None),
            patch.object(analyzer, "_get_executor", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = mock_executor

            result = await analyzer._call_llm("prompt", "system")

            assert '{"test": true}' in result

    @pytest.mark.asyncio
    async def test_call_llm_handles_response_without_content(self, analyzer):
        """Test handling response without content attribute."""
        mock_executor = AsyncMock()
        mock_executor.run.return_value = "string response"

        with (
            patch.object(analyzer, "_get_client", return_value=None),
            patch.object(analyzer, "_get_executor", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = mock_executor

            result = await analyzer._call_llm("prompt", "system")

            assert result == "string response"
