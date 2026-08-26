"""Behavioral tests for HaystackAdapter, HaystackAgent, and HaystackWorkflow.

Tests the public API surface without requiring the haystack package.
All Haystack imports are mocked to allow testing adapter logic in isolation.
"""

from unittest.mock import MagicMock

import pytest

from attune.agent_factory.adapters.haystack_adapter import (
    HaystackAdapter,
    HaystackAgent,
    HaystackWorkflow,
    _check_haystack,
)
from attune.agent_factory.base import (
    AgentCapability,
    AgentConfig,
    AgentGraphConfig,
    AgentRole,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def agent_config():
    """Create a basic agent config for testing."""
    return AgentConfig(
        name="test-agent",
        role=AgentRole.CUSTOM,
        description="Test agent",
        model_tier="capable",
        temperature=0.5,
        max_tokens=1024,
    )


@pytest.fixture()
def rag_config():
    """Create a RAG agent config with retrieval capability."""
    return AgentConfig(
        name="rag-agent",
        role=AgentRole.RETRIEVER,
        description="RAG agent",
        capabilities=[AgentCapability.RETRIEVAL],
    )


@pytest.fixture()
def workflow_config():
    """Create a basic workflow config."""
    return AgentGraphConfig(
        name="test-workflow",
        description="Test workflow",
    )


@pytest.fixture()
def mock_pipeline():
    """Create a mock Haystack pipeline."""
    pipeline = MagicMock()
    pipeline.run.return_value = {
        "replies": ["This is the answer"],
    }
    return pipeline


@pytest.fixture()
def mock_generator():
    """Create a mock Haystack generator."""
    gen = MagicMock()
    gen.run.return_value = {"replies": ["Generated response"]}
    return gen


# ---------------------------------------------------------------------------
# HaystackAdapter — framework_name / is_available
# ---------------------------------------------------------------------------


class TestHaystackAdapterProperties:
    """Test adapter property accessors."""

    def test_framework_name_returns_haystack(self):
        """Given a HaystackAdapter, framework_name is 'haystack'."""
        adapter = HaystackAdapter()
        assert adapter.framework_name == "haystack"

    def test_default_provider_is_anthropic(self):
        """Given no provider arg, default is 'anthropic'."""
        adapter = HaystackAdapter()
        assert adapter.provider == "anthropic"

    def test_custom_provider(self):
        """Given provider='openai', adapter stores it."""
        adapter = HaystackAdapter(provider="openai")
        assert adapter.provider == "openai"

    def test_is_available_delegates_to_check(self):
        """is_available() returns the result of _check_haystack()."""
        import attune.agent_factory.adapters.haystack_adapter as mod

        original = mod._haystack_available
        try:
            mod._haystack_available = True
            adapter = HaystackAdapter()
            assert adapter.is_available() is True

            mod._haystack_available = False
            assert adapter.is_available() is False
        finally:
            mod._haystack_available = original


# ---------------------------------------------------------------------------
# HaystackAgent — invoke
# ---------------------------------------------------------------------------


class TestHaystackAgentInvoke:
    """Test HaystackAgent.invoke() with various inputs."""

    @pytest.mark.asyncio()
    async def test_invoke_with_pipeline_replies(self, agent_config, mock_pipeline):
        """Given a pipeline that returns replies, output is the first reply."""
        agent = HaystackAgent(agent_config, pipeline=mock_pipeline)
        result = await agent.invoke("What is AI?")

        assert result["output"] == "This is the answer"
        assert result["metadata"]["framework"] == "haystack"
        mock_pipeline.run.assert_called_once()

    @pytest.mark.asyncio()
    async def test_invoke_with_pipeline_answers(self, agent_config):
        """Given a pipeline that returns answers, output is answer.data."""
        mock_answer = MagicMock()
        mock_answer.data = "Answer from docs"
        pipeline = MagicMock()
        pipeline.run.return_value = {"answers": [mock_answer]}

        agent = HaystackAgent(agent_config, pipeline=pipeline)
        result = await agent.invoke("question")

        assert result["output"] == "Answer from docs"

    @pytest.mark.asyncio()
    async def test_invoke_with_pipeline_empty_answers(self, agent_config):
        """Given a pipeline with empty answers list, output is fallback."""
        pipeline = MagicMock()
        pipeline.run.return_value = {"answers": []}

        agent = HaystackAgent(agent_config, pipeline=pipeline)
        result = await agent.invoke("question")

        assert result["output"] == "No answer found"

    @pytest.mark.asyncio()
    async def test_invoke_with_generator(self, agent_config, mock_generator):
        """Given only a generator, invoke uses it directly."""
        agent = HaystackAgent(agent_config, generator=mock_generator)
        result = await agent.invoke("Generate something")

        assert result["output"] == "Generated response"
        mock_generator.run.assert_called_once_with(
            prompt="Generate something",
        )

    @pytest.mark.asyncio()
    async def test_invoke_no_pipeline_no_generator(self, agent_config):
        """Given no pipeline or generator, output indicates no config."""
        agent = HaystackAgent(agent_config)
        result = await agent.invoke("hello")

        assert "No pipeline configured" in result["output"]

    @pytest.mark.asyncio()
    async def test_invoke_with_dict_input(self, agent_config, mock_pipeline):
        """Given dict input with 'query' key, extracts the query string."""
        agent = HaystackAgent(agent_config, pipeline=mock_pipeline)
        await agent.invoke({"query": "test query"})

        call_args = mock_pipeline.run.call_args[0][0]
        assert call_args["query"] == "test query"

    @pytest.mark.asyncio()
    async def test_invoke_records_conversation_history(self, agent_config, mock_pipeline):
        """Given a successful invoke, conversation history is updated."""
        agent = HaystackAgent(agent_config, pipeline=mock_pipeline)
        await agent.invoke("hello")

        assert len(agent._conversation_history) == 2
        assert agent._conversation_history[0]["role"] == "user"
        assert agent._conversation_history[1]["role"] == "assistant"

    @pytest.mark.asyncio()
    async def test_invoke_handles_pipeline_error(self, agent_config):
        """Given a pipeline that raises, invoke returns error dict."""
        pipeline = MagicMock()
        pipeline.run.side_effect = RuntimeError("Pipeline broke")

        agent = HaystackAgent(agent_config, pipeline=pipeline)
        result = await agent.invoke("boom")

        assert "Error" in result["output"]
        assert "Pipeline broke" in result["metadata"]["error"]


# ---------------------------------------------------------------------------
# HaystackAgent — stream
# ---------------------------------------------------------------------------


class TestHaystackAgentStream:
    """Test HaystackAgent.stream() yields invoke result."""

    @pytest.mark.asyncio()
    async def test_stream_yields_single_result(self, agent_config, mock_pipeline):
        """Given a stream call, yields exactly one result matching invoke."""
        agent = HaystackAgent(agent_config, pipeline=mock_pipeline)
        results = []
        async for chunk in agent.stream("test"):
            results.append(chunk)

        assert len(results) == 1
        assert results[0]["output"] == "This is the answer"


# ---------------------------------------------------------------------------
# HaystackWorkflow — run
# ---------------------------------------------------------------------------


class TestHaystackWorkflowRun:
    """Test HaystackWorkflow.run() with various configs."""

    @pytest.mark.asyncio()
    async def test_run_with_pipeline_replies(self, workflow_config, mock_pipeline, agent_config):
        """Given a workflow with a pipeline, run returns first reply."""
        agent = HaystackAgent(agent_config)
        wf = HaystackWorkflow(
            workflow_config,
            [agent],
            pipeline=mock_pipeline,
        )
        result = await wf.run("What?")

        assert result["output"] == "This is the answer"
        assert result["metadata"]["framework"] == "haystack"

    @pytest.mark.asyncio()
    async def test_run_falls_back_to_sequential(self, workflow_config, agent_config, mock_pipeline):
        """Given no pipeline, workflow falls back to sequential agents."""
        agent = HaystackAgent(agent_config, pipeline=mock_pipeline)
        wf = HaystackWorkflow(workflow_config, [agent], pipeline=None)
        result = await wf.run("input")

        assert "output" in result

    @pytest.mark.asyncio()
    async def test_run_with_dict_input(self, workflow_config, agent_config, mock_pipeline):
        """Given dict input, extracts query key."""
        agent = HaystackAgent(agent_config)
        wf = HaystackWorkflow(
            workflow_config,
            [agent],
            pipeline=mock_pipeline,
        )
        result = await wf.run({"query": "test"})

        assert "output" in result

    @pytest.mark.asyncio()
    async def test_run_handles_pipeline_error(self, workflow_config, agent_config):
        """Given a pipeline that raises, run returns error dict."""
        pipeline = MagicMock()
        pipeline.run.side_effect = RuntimeError("Workflow failed")

        agent = HaystackAgent(agent_config)
        wf = HaystackWorkflow(
            workflow_config,
            [agent],
            pipeline=pipeline,
        )
        result = await wf.run("boom")

        assert "Error" in result["output"]
        assert "error" in result

    @pytest.mark.asyncio()
    async def test_stream_yields_run_result(self, workflow_config, agent_config, mock_pipeline):
        """Given a stream call, yields exactly one result."""
        agent = HaystackAgent(agent_config)
        wf = HaystackWorkflow(
            workflow_config,
            [agent],
            pipeline=mock_pipeline,
        )
        results = []
        async for chunk in wf.stream("test"):
            results.append(chunk)

        assert len(results) == 1


# ---------------------------------------------------------------------------
# HaystackAdapter — create_agent / create_tool
# ---------------------------------------------------------------------------


class TestHaystackAdapterCreateAgent:
    """Test adapter agent and tool creation."""

    def test_create_agent_raises_when_unavailable(self, agent_config):
        """Given haystack not installed, create_agent raises ImportError."""
        import attune.agent_factory.adapters.haystack_adapter as mod

        original = mod._haystack_available
        try:
            mod._haystack_available = False
            adapter = HaystackAdapter()
            with pytest.raises(ImportError, match="not installed"):
                adapter.create_agent(agent_config)
        finally:
            mod._haystack_available = original

    def test_create_workflow_raises_when_unavailable(self, workflow_config, agent_config):
        """Given haystack not installed, create_workflow raises ImportError."""
        import attune.agent_factory.adapters.haystack_adapter as mod

        original = mod._haystack_available
        try:
            mod._haystack_available = False
            adapter = HaystackAdapter()
            with pytest.raises(ImportError, match="not installed"):
                adapter.create_workflow(workflow_config, [])
        finally:
            mod._haystack_available = original

    def test_create_tool_returns_dict(self):
        """Given a function, create_tool returns a tool dict."""
        adapter = HaystackAdapter()

        def my_func():
            pass

        tool = adapter.create_tool(
            "my_tool",
            "A tool",
            my_func,
            {"arg1": "str"},
        )
        assert tool["name"] == "my_tool"
        assert tool["description"] == "A tool"
        assert tool["func"] is my_func
        assert tool["args_schema"] == {"arg1": "str"}

    def test_create_document_store_raises_when_unavailable(self):
        """Given haystack not installed, create_document_store raises."""
        import attune.agent_factory.adapters.haystack_adapter as mod

        original = mod._haystack_available
        try:
            mod._haystack_available = False
            adapter = HaystackAdapter()
            with pytest.raises(ImportError, match="not installed"):
                adapter.create_document_store()
        finally:
            mod._haystack_available = original

    def test_create_document_store_unsupported_type(self):
        """Given unsupported store type, raises ValueError."""
        import attune.agent_factory.adapters.haystack_adapter as mod

        original = mod._haystack_available
        try:
            mod._haystack_available = True
            adapter = HaystackAdapter()
            with pytest.raises(ValueError, match="Unsupported store type"):
                adapter.create_document_store("postgres")
        finally:
            mod._haystack_available = original

    def test_get_generator_unsupported_provider(self, agent_config):
        """Given unsupported provider, _get_generator raises ValueError."""
        import attune.agent_factory.adapters.haystack_adapter as mod

        original = mod._haystack_available
        try:
            mod._haystack_available = True
            adapter = HaystackAdapter(provider="unsupported")
            with pytest.raises(
                ValueError,
                match="(?i)(unsupported|unknown).*provider",
            ):
                adapter._get_generator(agent_config)
        finally:
            mod._haystack_available = original


# ---------------------------------------------------------------------------
# _check_haystack
# ---------------------------------------------------------------------------


class TestCheckHaystack:
    """Test the lazy haystack availability check."""

    def test_returns_bool(self):
        """_check_haystack() returns a boolean."""
        import attune.agent_factory.adapters.haystack_adapter as mod

        original = mod._haystack_available
        try:
            mod._haystack_available = None  # Reset to force re-check
            result = _check_haystack()
            assert isinstance(result, bool)
        finally:
            mod._haystack_available = original
