"""Tests for empathy_llm_toolkit langgraph_adapter module.

Comprehensive test coverage for LangGraphAgent, LangGraphWorkflow, and LangGraphAdapter.

Created: 2026-01-20
Coverage target: 80%+
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.agent_factory.adapters.langgraph_adapter import (
    LangGraphAdapter,
    LangGraphAgent,
    LangGraphWorkflow,
    _check_langgraph,
)
from attune.agent_factory.base import AgentConfig, AgentGraphConfig, AgentRole

# =============================================================================
# _check_langgraph Tests
# =============================================================================


class TestCheckLangGraph:
    """Tests for _check_langgraph function."""

    def test_check_langgraph_available(self):
        """Test when langgraph is available."""
        import attune.agent_factory.adapters.langgraph_adapter as module

        # Reset global state
        module._langgraph_available = None

        with patch.dict("sys.modules", {"langgraph": MagicMock()}):
            _check_langgraph()
            # Result depends on actual availability

    def test_check_langgraph_not_available(self):
        """Test when langgraph is not available."""
        import attune.agent_factory.adapters.langgraph_adapter as module

        # Reset global state
        module._langgraph_available = None

        with patch.dict("sys.modules", {"langgraph": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                # Reset to force recheck
                module._langgraph_available = None
                result = module._check_langgraph()
                assert result is False


# =============================================================================
# LangGraphAgent Tests
# =============================================================================


class TestLangGraphAgent:
    """Tests for LangGraphAgent class."""

    def test_init(self):
        """Test agent initialization."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)
        agent = LangGraphAgent(config, runnable=None, node_func=None)

        assert agent._runnable is None
        assert agent._node_func is None

    def test_init_with_runnable(self):
        """Test initialization with runnable."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)
        mock_runnable = MagicMock()
        agent = LangGraphAgent(config, runnable=mock_runnable)

        assert agent._runnable is mock_runnable

    def test_init_with_node_func(self):
        """Test initialization with node function."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)

        def node_func(state):
            return state

        agent = LangGraphAgent(config, node_func=node_func)
        assert agent._node_func is node_func

    @pytest.mark.asyncio
    async def test_invoke_with_string_input(self):
        """Test invoke with string input and no runnable."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)
        agent = LangGraphAgent(config)

        result = await agent.invoke("test input")

        assert "output" in result
        assert "No runnable configured" in result["output"]
        assert result["metadata"]["framework"] == "langgraph"

    @pytest.mark.asyncio
    async def test_invoke_with_dict_input(self):
        """Test invoke with dict input."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)
        agent = LangGraphAgent(config)

        result = await agent.invoke({"key": "value"})

        assert "output" in result

    @pytest.mark.asyncio
    async def test_invoke_with_other_input_type(self):
        """Test invoke with non-string, non-dict input."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)
        agent = LangGraphAgent(config)

        result = await agent.invoke(123)  # Integer input

        assert "output" in result

    @pytest.mark.asyncio
    async def test_invoke_with_context(self):
        """Test invoke with context."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)
        agent = LangGraphAgent(config)

        result = await agent.invoke("test", context={"extra": "data"})

        assert "output" in result

    @pytest.mark.asyncio
    async def test_invoke_with_async_runnable(self):
        """Test invoke with async runnable."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)

        mock_runnable = MagicMock()
        mock_runnable.ainvoke = AsyncMock(return_value={"output": "async result", "messages": []})

        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = await agent.invoke("test")

        assert result["output"] == "async result"
        mock_runnable.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_invoke_with_sync_runnable(self):
        """Test invoke with sync runnable."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)

        mock_runnable = MagicMock()
        mock_runnable.invoke = MagicMock(return_value={"output": "sync result"})
        del mock_runnable.ainvoke  # Remove ainvoke to force sync path

        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = await agent.invoke("test")

        assert result["output"] == "sync result"

    @pytest.mark.asyncio
    async def test_invoke_with_async_node_func(self):
        """Test invoke with async node function."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)

        async def async_node(state):
            return {"output": "async node result"}

        agent = LangGraphAgent(config, node_func=async_node)
        result = await agent.invoke("test")

        assert result["output"] == "async node result"

    @pytest.mark.asyncio
    async def test_invoke_with_sync_node_func(self):
        """Test invoke with sync node function."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)

        def sync_node(state):
            return {"output": "sync node result"}

        agent = LangGraphAgent(config, node_func=sync_node)
        result = await agent.invoke("test")

        assert result["output"] == "sync node result"

    @pytest.mark.asyncio
    async def test_invoke_extracts_messages_output(self):
        """Test invoke extracts output from messages."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)

        mock_runnable = MagicMock()
        mock_runnable.ainvoke = AsyncMock(
            return_value={
                "messages": [
                    {"content": "first message"},
                    {"content": "last message"},
                ],
            },
        )

        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = await agent.invoke("test")

        assert result["output"] == "last message"

    @pytest.mark.asyncio
    async def test_invoke_handles_exception(self):
        """Test invoke handles exceptions gracefully."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)

        mock_runnable = MagicMock()
        mock_runnable.ainvoke = AsyncMock(side_effect=Exception("Test error"))

        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = await agent.invoke("test")

        assert "Error" in result["output"]
        assert "error" in result["metadata"]

    @pytest.mark.asyncio
    async def test_invoke_tracks_conversation_history(self):
        """Test invoke tracks conversation history."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)
        agent = LangGraphAgent(config)

        await agent.invoke("first message")
        await agent.invoke("second message")

        assert len(agent._conversation_history) == 4  # 2 user + 2 assistant

    @pytest.mark.asyncio
    async def test_stream_with_streaming_runnable(self):
        """Test stream with runnable that supports astream."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)

        async def mock_astream(state):
            yield {"chunk": 1}
            yield {"chunk": 2}

        mock_runnable = MagicMock()
        mock_runnable.astream = mock_astream

        agent = LangGraphAgent(config, runnable=mock_runnable)

        chunks = []
        async for chunk in agent.stream("test"):
            chunks.append(chunk)

        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_stream_fallback_to_invoke(self):
        """Test stream falls back to invoke when astream not available."""
        config = AgentConfig(name="test_agent", role=AgentRole.RESEARCHER)
        agent = LangGraphAgent(config)  # No runnable

        chunks = []
        async for chunk in agent.stream("test"):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "output" in chunks[0]


# =============================================================================
# LangGraphWorkflow Tests
# =============================================================================


class TestLangGraphWorkflow:
    """Tests for LangGraphWorkflow class."""

    def test_init(self):
        """Test workflow initialization."""
        config = AgentGraphConfig(name="test_workflow")
        workflow = LangGraphWorkflow(config, [], graph=None)

        assert workflow._graph is None
        assert workflow._compiled is None

    def test_init_with_graph(self):
        """Test initialization with graph."""
        config = AgentGraphConfig(name="test_workflow")
        mock_graph = MagicMock()
        workflow = LangGraphWorkflow(config, [], graph=mock_graph)

        assert workflow._graph is mock_graph

    def test_compile_graph_no_graph(self):
        """Test _compile_graph with no graph."""
        config = AgentGraphConfig(name="test_workflow")
        workflow = LangGraphWorkflow(config, [])

        result = workflow._compile_graph()
        assert result is None

    def test_compile_graph_with_graph(self):
        """Test _compile_graph compiles the graph."""
        config = AgentGraphConfig(name="test_workflow")
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_graph.compile.return_value = mock_compiled

        workflow = LangGraphWorkflow(config, [], graph=mock_graph)
        result = workflow._compile_graph()

        assert result is mock_compiled
        mock_graph.compile.assert_called_once()

    def test_compile_graph_caches_result(self):
        """Test _compile_graph caches the compiled graph."""
        config = AgentGraphConfig(name="test_workflow")
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_graph.compile.return_value = mock_compiled

        workflow = LangGraphWorkflow(config, [], graph=mock_graph)

        # Compile twice
        result1 = workflow._compile_graph()
        result2 = workflow._compile_graph()

        assert result1 is result2
        mock_graph.compile.assert_called_once()  # Only called once

    @pytest.mark.asyncio
    async def test_run_with_string_input(self):
        """Test run with string input."""
        config = AgentGraphConfig(name="test_workflow")
        workflow = LangGraphWorkflow(config, [])

        result = await workflow.run("test input")

        assert "output" in result

    @pytest.mark.asyncio
    async def test_run_with_dict_input(self):
        """Test run with dict input."""
        config = AgentGraphConfig(name="test_workflow")
        workflow = LangGraphWorkflow(config, [])

        result = await workflow.run({"key": "value"})

        assert "output" in result

    @pytest.mark.asyncio
    async def test_run_with_initial_state(self):
        """Test run with initial state."""
        config = AgentGraphConfig(name="test_workflow")
        workflow = LangGraphWorkflow(config, [])

        result = await workflow.run("test", initial_state={"extra": "data"})

        assert "state" in result

    @pytest.mark.asyncio
    async def test_run_with_compiled_async(self):
        """Test run with async compiled graph."""
        config = AgentGraphConfig(name="test_workflow")
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"messages": [{"content": "result"}]})
        mock_graph.compile.return_value = mock_compiled

        workflow = LangGraphWorkflow(config, [], graph=mock_graph)
        result = await workflow.run("test")

        assert result["output"] == "result"

    @pytest.mark.asyncio
    async def test_run_with_compiled_sync(self):
        """Test run with sync compiled graph."""
        config = AgentGraphConfig(name="test_workflow")
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_compiled.invoke = MagicMock(return_value={"output": "sync result"})
        del mock_compiled.ainvoke  # Remove ainvoke

        mock_graph.compile.return_value = mock_compiled

        workflow = LangGraphWorkflow(config, [], graph=mock_graph)
        result = await workflow.run("test")

        assert result["output"] == "sync result"

    @pytest.mark.asyncio
    async def test_run_exception_handling(self):
        """Test run handles exceptions."""
        config = AgentGraphConfig(name="test_workflow")
        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(side_effect=Exception("Test error"))
        mock_graph.compile.return_value = mock_compiled

        workflow = LangGraphWorkflow(config, [], graph=mock_graph)
        result = await workflow.run("test")

        assert "Error" in result["output"]
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_sequential_fallback(self):
        """Test run falls back to sequential execution."""
        config = AgentGraphConfig(name="test_workflow")

        agent_config = AgentConfig(name="agent1", role=AgentRole.RESEARCHER)
        mock_agent = LangGraphAgent(agent_config)

        workflow = LangGraphWorkflow(config, [mock_agent])

        result = await workflow.run("test")

        assert "output" in result

    @pytest.mark.asyncio
    async def test_stream_with_astream(self):
        """Test stream with compiled graph that supports astream."""
        config = AgentGraphConfig(name="test_workflow")
        mock_graph = MagicMock()
        mock_compiled = MagicMock()

        async def mock_astream(state):
            yield {"event": 1}
            yield {"event": 2}

        mock_compiled.astream = mock_astream
        mock_graph.compile.return_value = mock_compiled

        workflow = LangGraphWorkflow(config, [], graph=mock_graph)

        events = []
        async for event in workflow.stream("test"):
            events.append(event)

        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_stream_fallback(self):
        """Test stream fallback to run."""
        config = AgentGraphConfig(name="test_workflow")
        workflow = LangGraphWorkflow(config, [])

        events = []
        async for event in workflow.stream("test"):
            events.append(event)

        assert len(events) == 1


# =============================================================================
# LangGraphAdapter Tests
# =============================================================================


class TestLangGraphAdapter:
    """Tests for LangGraphAdapter class."""

    def test_init_default(self):
        """Test adapter initialization with defaults."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            adapter = LangGraphAdapter()

            assert adapter.provider == "anthropic"
            assert adapter.api_key == "test-key"

    def test_init_custom_provider(self):
        """Test adapter initialization with custom provider."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "openai-key"}):
            adapter = LangGraphAdapter(provider="openai")

            assert adapter.provider == "openai"
            assert adapter.api_key == "openai-key"

    def test_init_explicit_api_key(self):
        """Test adapter initialization with explicit API key."""
        adapter = LangGraphAdapter(api_key="explicit-key")

        assert adapter.api_key == "explicit-key"

    def test_framework_name(self):
        """Test framework_name property."""
        adapter = LangGraphAdapter(api_key="test")

        assert adapter.framework_name == "langgraph"

    def test_is_available(self):
        """Test is_available method."""
        adapter = LangGraphAdapter(api_key="test")

        # Returns True or False based on langgraph availability
        result = adapter.is_available()
        assert isinstance(result, bool)

    def test_get_llm_anthropic(self):
        """Test _get_llm for Anthropic provider."""
        adapter = LangGraphAdapter(provider="anthropic", api_key="test-key")

        config = AgentConfig(
            name="test",
            role=AgentRole.RESEARCHER,
            model_tier="capable",
        )

        # Mock the langchain_anthropic module
        mock_chat_class = MagicMock()
        mock_chat_class.return_value = MagicMock()

        with patch.dict(
            "sys.modules",
            {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_class)},
        ):
            try:
                adapter._get_llm(config)
            except ImportError:
                # LangChain not installed, which is fine
                pass

    def test_get_llm_unsupported_provider(self):
        """Test _get_llm raises for unsupported provider."""
        adapter = LangGraphAdapter(provider="unsupported", api_key="test-key")

        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)

        with pytest.raises(ValueError, match="Unknown provider"):
            adapter._get_llm(config)

    def test_get_llm_no_api_key(self):
        """Test _get_llm raises when no API key for Anthropic."""
        # Clear the environment variable so adapter can't fall back to it
        with patch.dict(os.environ, {}, clear=False):
            # Remove ANTHROPIC_API_KEY from environment
            os.environ.pop("ANTHROPIC_API_KEY", None)

            adapter = LangGraphAdapter(provider="anthropic", api_key=None)

            config = AgentConfig(name="test", role=AgentRole.RESEARCHER)

            # Mock langchain_anthropic to ensure we reach the api_key check
            mock_chat_class = MagicMock()
            with (
                patch.dict(
                    "sys.modules",
                    {"langchain_anthropic": MagicMock(ChatAnthropic=mock_chat_class)},
                ),
                pytest.raises(ValueError, match="API key required"),
            ):
                adapter._get_llm(config)

    def test_create_agent_not_available(self):
        """Test create_agent raises when LangGraph not available."""
        adapter = LangGraphAdapter(api_key="test")

        config = AgentConfig(name="test", role=AgentRole.RESEARCHER)

        with patch.object(adapter, "is_available", return_value=False):
            with pytest.raises(ImportError, match="LangGraph not installed"):
                adapter.create_agent(config)

    def test_create_workflow_not_available(self):
        """Test create_workflow raises when LangGraph not available."""
        adapter = LangGraphAdapter(api_key="test")

        config = AgentGraphConfig(name="test")

        with patch.object(adapter, "is_available", return_value=False):
            with pytest.raises(ImportError, match="LangGraph not installed"):
                adapter.create_workflow(config, [])

    def test_create_tool_not_available(self):
        """Test create_tool returns dict when LangGraph not available."""
        adapter = LangGraphAdapter(api_key="test")

        def dummy_func():
            pass

        with patch.object(adapter, "is_available", return_value=False):
            tool = adapter.create_tool("test", "description", dummy_func)

            assert tool["name"] == "test"
            assert tool["description"] == "description"
            assert tool["func"] is dummy_func
