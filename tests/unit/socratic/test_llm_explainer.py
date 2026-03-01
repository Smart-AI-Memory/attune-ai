"""Tests for socratic/llm_explainer.py.

Tests LLMExplanationGenerator with mocked Anthropic client.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from attune.socratic.blueprint import (
    AgentRole,
    StageSpec,
    WorkflowBlueprint,
)
from attune.socratic.llm_explainer import LLMExplanationGenerator


def _make_blueprint() -> WorkflowBlueprint:
    """Create a minimal WorkflowBlueprint for testing.

    Note: LLMExplanationGenerator.generate() accesses a.name,
    a.role.value, and a.description on blueprint.agents items.
    AgentBlueprint doesn't expose these directly, so we use
    SimpleNamespace agents that match what the code accesses.
    """
    agent = SimpleNamespace(
        name="Code Analyzer",
        role=AgentRole.ANALYZER,
        description="Analyzes code quality",
    )
    stage = StageSpec(
        id="analysis",
        name="Analysis",
        description="Run analysis",
        agent_ids=["analyzer"],
    )
    return WorkflowBlueprint(
        name="Test Workflow",
        description="A test workflow",
        domain="testing",
        agents=[agent],
        stages=[stage],
    )


class TestInit:
    """Tests for LLMExplanationGenerator.__init__."""

    def test_explicit_api_key(self):
        """Test that an explicit API key is stored."""
        gen = LLMExplanationGenerator(api_key="sk-test-key")
        assert gen.api_key == "sk-test-key"

    def test_env_api_key(self):
        """Test that API key falls back to env var."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-env-key"}):
            gen = LLMExplanationGenerator()
            assert gen.api_key == "sk-env-key"

    def test_no_api_key(self):
        """Test that missing key results in None."""
        with patch.dict("os.environ", {}, clear=True):
            gen = LLMExplanationGenerator()
            assert gen.api_key is None


class TestGetClient:
    """Tests for LLMExplanationGenerator._get_client()."""

    def test_creates_client_with_key(self):
        """Test that _get_client creates an Anthropic client when key is set."""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        gen = LLMExplanationGenerator(api_key="sk-test")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            client = gen._get_client()
            assert client is mock_client

    def test_caches_client(self):
        """Test that _get_client returns the same client on second call."""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        gen = LLMExplanationGenerator(api_key="sk-test")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            client1 = gen._get_client()
            client2 = gen._get_client()
            assert client1 is client2
            mock_anthropic.Anthropic.assert_called_once()

    def test_no_key_returns_none(self):
        """Test that _get_client returns None when no API key."""
        with patch.dict("os.environ", {}, clear=True):
            gen = LLMExplanationGenerator()
            assert gen._get_client() is None

    def test_import_error_returns_none(self):
        """Test that _get_client returns None when anthropic not installed."""
        gen = LLMExplanationGenerator(api_key="sk-test")
        with patch.dict("sys.modules", {"anthropic": None}):
            result = gen._get_client()
            assert result is None


class TestGenerate:
    """Tests for LLMExplanationGenerator.generate()."""

    def test_llm_success_path(self):
        """Test generate() calls LLM and returns response text."""
        gen = LLMExplanationGenerator(api_key="sk-test")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="# Workflow Explanation\n...")]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        gen._client = mock_client

        blueprint = _make_blueprint()
        result = gen.generate(blueprint)
        assert result == "# Workflow Explanation\n..."
        mock_client.messages.create.assert_called_once()

    def test_no_client_fallback(self):
        """Test generate() falls back to rule-based explainer without client."""
        mock_explainer = MagicMock()
        mock_explanation = MagicMock()
        mock_explanation.to_markdown.return_value = "# Fallback explanation"
        mock_explainer.return_value.explain_workflow.return_value = mock_explanation

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("attune.socratic.explainer.WorkflowExplainer", mock_explainer),
        ):
            gen = LLMExplanationGenerator()
            blueprint = _make_blueprint()
            result = gen.generate(blueprint)
            assert result == "# Fallback explanation"

    def test_api_error_fallback(self):
        """Test generate() falls back on API error."""
        mock_explainer = MagicMock()
        mock_explanation = MagicMock()
        mock_explanation.to_markdown.return_value = "# Error fallback"
        mock_explainer.return_value.explain_workflow.return_value = mock_explanation

        gen = LLMExplanationGenerator(api_key="sk-test")
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API error")
        gen._client = mock_client

        with patch("attune.socratic.explainer.WorkflowExplainer", mock_explainer):
            blueprint = _make_blueprint()
            result = gen.generate(blueprint)
            assert result == "# Error fallback"
