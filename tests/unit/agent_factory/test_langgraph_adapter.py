"""Tests for attune.agent_factory.adapters.langgraph_adapter.

Covers all previously-uncovered branches in:
- _check_langgraph()
- LangGraphAgent.invoke() and stream()
- LangGraphWorkflow._compile_graph(), run(), _run_sequential(), stream()
- LangGraphAdapter: init, framework_name, is_available, _get_llm, create_agent,
  create_workflow, create_tool
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.agent_factory.adapters.langgraph_adapter import (
    LangGraphAdapter,
    LangGraphAgent,
    LangGraphWorkflow,
    _check_langgraph,
)
from attune.agent_factory.base import AgentConfig, AgentRole, WorkflowConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent_config(name="test-agent", role=AgentRole.COORDINATOR, api_key="sk-test"):
    return AgentConfig(name=name, role=role)


def _workflow_config(mode="sequential"):
    return WorkflowConfig(name="test-wf", mode=mode)


def _make_agent(name="agent1"):
    """Make a mock LangGraphAgent."""
    config = _agent_config(name=name)
    agent = LangGraphAgent(config, runnable=None, node_func=None)
    return agent


# ---------------------------------------------------------------------------
# _check_langgraph
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckLanggraph:
    def test_returns_true_when_langgraph_installed(self):
        """_check_langgraph returns True when langgraph importable."""
        import attune.agent_factory.adapters.langgraph_adapter as mod

        # Reset cache
        mod._langgraph_available = None
        with patch.dict("sys.modules", {"langgraph": MagicMock()}):
            result = _check_langgraph()
        assert result is True

    def test_returns_false_when_langgraph_missing(self):
        """_check_langgraph returns False when langgraph not importable."""
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = None
        with patch.dict("sys.modules", {"langgraph": None}):
            result = _check_langgraph()
        assert result is False
        mod._langgraph_available = None  # reset for other tests

    def test_caches_result(self):
        """_check_langgraph does not re-import if already cached."""
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = True
        result = _check_langgraph()
        assert result is True


# ---------------------------------------------------------------------------
# LangGraphAgent.invoke
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLangGraphAgentInvoke:
    def test_string_input_builds_messages_state(self):
        """Line 64: string input → messages dict."""
        config = _agent_config()
        agent = LangGraphAgent(config)
        result = asyncio.run(agent.invoke("hello"))
        assert "output" in result

    def test_dict_input_copied(self):
        """Line 66: dict input → copied as state."""
        config = _agent_config()
        agent = LangGraphAgent(config)
        result = asyncio.run(agent.invoke({"custom_key": "value"}))
        assert "output" in result

    def test_other_input_type(self):
        """Line 68: non-str, non-dict input → fallback state."""
        config = _agent_config()
        agent = LangGraphAgent(config)
        result = asyncio.run(agent.invoke(42))
        assert "output" in result

    def test_context_merged_into_state(self):
        """Line 72: context merged into state."""
        config = _agent_config()
        agent = LangGraphAgent(config)
        result = asyncio.run(agent.invoke("task", context={"extra": "ctx"}))
        assert "output" in result

    def test_runnable_with_ainvoke(self):
        """Line 77: runnable with ainvoke is awaited."""
        config = _agent_config()
        mock_runnable = MagicMock()
        mock_runnable.ainvoke = AsyncMock(return_value={"output": "from-ainvoke"})
        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = asyncio.run(agent.invoke("hello"))
        assert result["output"] == "from-ainvoke"

    def test_runnable_with_invoke_only(self):
        """Line 79: runnable without ainvoke uses sync invoke."""
        config = _agent_config()
        mock_runnable = MagicMock(spec=[])  # no ainvoke attr
        mock_runnable.invoke = MagicMock(return_value={"output": "from-invoke"})
        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = asyncio.run(agent.invoke("hello"))
        assert result["output"] == "from-invoke"

    def test_async_node_func(self):
        """Line 82: async node_func is awaited."""
        config = _agent_config()

        async def my_node(state):
            return {"output": "async-node", "messages": []}

        agent = LangGraphAgent(config, node_func=my_node)
        result = asyncio.run(agent.invoke("hello"))
        assert result["output"] == "async-node"

    def test_sync_node_func(self):
        """Line 84: sync node_func called directly."""
        config = _agent_config()

        def my_node(state):
            return {"output": "sync-node"}

        agent = LangGraphAgent(config, node_func=my_node)
        result = asyncio.run(agent.invoke("hello"))
        assert result["output"] == "sync-node"

    def test_no_runnable_or_node_func(self):
        """Line 87: no runnable or node_func → default output."""
        config = _agent_config()
        agent = LangGraphAgent(config)
        result = asyncio.run(agent.invoke("hello"))
        assert "No runnable configured" in result["output"]

    def test_result_dict_with_messages(self):
        """Lines 91-92: result dict with messages → last message content."""
        config = _agent_config()
        mock_runnable = MagicMock()
        mock_runnable.ainvoke = AsyncMock(
            return_value={
                "messages": [
                    {"role": "assistant", "content": "final answer"},
                ]
            }
        )
        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = asyncio.run(agent.invoke("hello"))
        assert result["output"] == "final answer"

    def test_result_dict_messages_non_content(self):
        """Line 92: message without 'content' → str(message)."""
        config = _agent_config()
        mock_runnable = MagicMock()
        mock_runnable.ainvoke = AsyncMock(
            return_value={"messages": [{"role": "assistant"}]}  # no 'content'
        )
        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = asyncio.run(agent.invoke("hello"))
        assert "output" in result

    def test_result_not_dict(self):
        """Line 96: non-dict result → str(result)."""
        config = _agent_config()
        mock_runnable = MagicMock()
        mock_runnable.ainvoke = AsyncMock(return_value="plain string result")
        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = asyncio.run(agent.invoke("hello"))
        assert result["output"] == "plain string result"

    def test_exception_returns_error_dict(self):
        """Line 107-108: exception in runnable → error dict."""
        config = _agent_config()
        mock_runnable = MagicMock()
        mock_runnable.ainvoke = AsyncMock(side_effect=RuntimeError("api failure"))
        agent = LangGraphAgent(config, runnable=mock_runnable)
        result = asyncio.run(agent.invoke("hello"))
        assert "Error" in result["output"]
        assert "error" in result["metadata"]


# ---------------------------------------------------------------------------
# LangGraphAgent.stream
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLangGraphAgentStream:
    def test_stream_with_astream_runnable(self):
        """Lines 118-119: runnable with astream → yields chunks."""

        async def _run():
            config = _agent_config()

            async def fake_astream(state):
                for chunk in ["chunk1", "chunk2"]:
                    yield chunk

            mock_runnable = MagicMock()
            mock_runnable.astream = fake_astream
            agent = LangGraphAgent(config, runnable=mock_runnable)
            chunks = []
            async for c in agent.stream("hello"):
                chunks.append(c)
            return chunks

        chunks = asyncio.run(_run())
        assert chunks == ["chunk1", "chunk2"]

    def test_stream_fallback_to_invoke(self):
        """Lines 120-122: no astream → falls back to invoke."""

        async def _run():
            config = _agent_config()
            mock_runnable = MagicMock(spec=[])  # no astream
            mock_runnable.invoke = MagicMock(return_value={"output": "fallback"})
            agent = LangGraphAgent(config, runnable=mock_runnable)
            chunks = []
            async for c in agent.stream("hello"):
                chunks.append(c)
            return chunks

        chunks = asyncio.run(_run())
        assert len(chunks) == 1
        assert chunks[0]["output"] == "fallback"

    def test_stream_no_runnable_fallback(self):
        """No runnable at all → falls back to invoke."""

        async def _run():
            config = _agent_config()
            agent = LangGraphAgent(config)
            chunks = []
            async for c in agent.stream("hello"):
                chunks.append(c)
            return chunks

        chunks = asyncio.run(_run())
        assert len(chunks) == 1


# ---------------------------------------------------------------------------
# LangGraphWorkflow._compile_graph
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLangGraphWorkflowCompileGraph:
    def test_compile_graph_when_graph_provided(self):
        """Lines 143-144: graph present → compile() called."""
        config = _workflow_config()
        mock_graph = MagicMock()
        mock_graph.compile.return_value = MagicMock()
        wf = LangGraphWorkflow(config, [], graph=mock_graph)
        compiled = wf._compile_graph()
        assert compiled is not None
        mock_graph.compile.assert_called_once()

    def test_compile_graph_cached(self):
        """compile() only called once (cached)."""
        config = _workflow_config()
        mock_graph = MagicMock()
        mock_graph.compile.return_value = MagicMock()
        wf = LangGraphWorkflow(config, [], graph=mock_graph)
        wf._compile_graph()
        wf._compile_graph()
        mock_graph.compile.assert_called_once()

    def test_compile_graph_no_graph_returns_none(self):
        """No graph → returns None."""
        config = _workflow_config()
        wf = LangGraphWorkflow(config, [], graph=None)
        result = wf._compile_graph()
        assert result is None


# ---------------------------------------------------------------------------
# LangGraphWorkflow.run
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLangGraphWorkflowRun:
    def test_run_with_compiled_ainvoke(self):
        """Lines 164-165: compiled with ainvoke → awaited."""
        config = _workflow_config()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"output": "compiled-result"})
        mock_graph = MagicMock()
        mock_graph.compile.return_value = mock_compiled
        wf = LangGraphWorkflow(config, [], graph=mock_graph)
        result = asyncio.run(wf.run("hello"))
        assert result["output"] == "compiled-result"

    def test_run_with_compiled_sync_invoke(self):
        """Line 167: compiled without ainvoke → sync invoke."""
        config = _workflow_config()
        mock_compiled = MagicMock(spec=["invoke"])
        mock_compiled.invoke = MagicMock(return_value={"output": "sync-result"})
        mock_graph = MagicMock()
        mock_graph.compile.return_value = mock_compiled
        wf = LangGraphWorkflow(config, [], graph=mock_graph)
        result = asyncio.run(wf.run("hello"))
        assert result["output"] == "sync-result"

    def test_run_with_initial_state(self):
        """Lines 157-158: initial_state merged into state."""
        config = _workflow_config()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"output": "ok"})
        mock_graph = MagicMock()
        mock_graph.compile.return_value = mock_compiled
        wf = LangGraphWorkflow(config, [], graph=mock_graph)
        result = asyncio.run(wf.run("hello", initial_state={"extra": "data"}))
        assert "output" in result

    def test_run_dict_input(self):
        """Line 155: dict input → copied directly."""
        config = _workflow_config()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"output": "dict-input"})
        mock_graph = MagicMock()
        mock_graph.compile.return_value = mock_compiled
        wf = LangGraphWorkflow(config, [], graph=mock_graph)
        result = asyncio.run(wf.run({"input": "dict-data"}))
        assert "output" in result

    def test_run_result_with_messages(self):
        """Lines 174-175: result dict with messages → last message content."""
        config = _workflow_config()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value={"messages": [{"content": "msg-output"}]})
        mock_graph = MagicMock()
        mock_graph.compile.return_value = mock_compiled
        wf = LangGraphWorkflow(config, [], graph=mock_graph)
        result = asyncio.run(wf.run("hello"))
        assert result["output"] == "msg-output"

    def test_run_fallback_sequential_when_no_graph(self):
        """Lines 169-170: no compiled graph → _run_sequential fallback."""
        config = _workflow_config()
        wf = LangGraphWorkflow(config, [], graph=None)

        # No agents → sequential returns empty output
        result = asyncio.run(wf.run("hello"))
        assert "output" in result

    def test_run_exception_returns_error(self):
        """Lines 184-185: exception → error dict."""
        config = _workflow_config()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(side_effect=RuntimeError("graph error"))
        mock_graph = MagicMock()
        mock_graph.compile.return_value = mock_compiled
        wf = LangGraphWorkflow(config, [], graph=mock_graph)
        result = asyncio.run(wf.run("hello"))
        assert "Error" in result["output"]
        assert "error" in result

    def test_run_non_dict_result(self):
        """Line 180: non-dict result → str(result)."""
        config = _workflow_config()
        mock_compiled = MagicMock()
        mock_compiled.ainvoke = AsyncMock(return_value="plain string")
        mock_graph = MagicMock()
        mock_graph.compile.return_value = mock_compiled
        wf = LangGraphWorkflow(config, [], graph=mock_graph)
        result = asyncio.run(wf.run("hello"))
        assert result["output"] == "plain string"


# ---------------------------------------------------------------------------
# LangGraphWorkflow._run_sequential
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLangGraphWorkflowRunSequential:
    def test_run_sequential_chains_agents(self):
        """Lines 190-193: agents chained sequentially."""
        config = _workflow_config()
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value={"output": "agent-out"})
        wf = LangGraphWorkflow(config, [], graph=None)
        wf.agents = {"a1": mock_agent}
        result = asyncio.run(wf._run_sequential("hello"))
        assert result["output"] == "agent-out"

    def test_run_sequential_no_agents(self):
        """Empty agents → output is original input."""
        config = _workflow_config()
        wf = LangGraphWorkflow(config, [], graph=None)
        wf.agents = {}
        result = asyncio.run(wf._run_sequential("input"))
        assert result["output"] == "input"


# ---------------------------------------------------------------------------
# LangGraphWorkflow.stream
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLangGraphWorkflowStream:
    def test_stream_with_astream_compiled(self):
        """Lines 204-206: compiled with astream → yields events."""

        async def _run():
            config = _workflow_config()

            async def fake_astream(state):
                yield {"event": "one"}
                yield {"event": "two"}

            mock_compiled = MagicMock()
            mock_compiled.astream = fake_astream
            mock_graph = MagicMock()
            mock_graph.compile.return_value = mock_compiled
            wf = LangGraphWorkflow(config, [], graph=mock_graph)
            events = []
            async for e in wf.stream("hello"):
                events.append(e)
            return events

        events = asyncio.run(_run())
        assert len(events) == 2

    def test_stream_fallback_when_no_astream(self):
        """Lines 207-209: no astream → falls back to run()."""

        async def _run():
            config = _workflow_config()
            mock_compiled = MagicMock(spec=["invoke"])
            mock_compiled.invoke = MagicMock(return_value={"output": "stream-fallback"})
            mock_graph = MagicMock()
            mock_graph.compile.return_value = mock_compiled
            wf = LangGraphWorkflow(config, [], graph=mock_graph)
            events = []
            async for e in wf.stream("hello"):
                events.append(e)
            return events

        events = asyncio.run(_run())
        assert len(events) == 1

    def test_stream_dict_input(self):
        """Line 202: dict input copied."""

        async def _run():
            config = _workflow_config()
            mock_compiled = MagicMock(spec=["invoke"])
            mock_compiled.invoke = MagicMock(return_value={"output": "dict-stream"})
            mock_graph = MagicMock()
            mock_graph.compile.return_value = mock_compiled
            wf = LangGraphWorkflow(config, [], graph=mock_graph)
            events = []
            async for e in wf.stream({"messages": []}):
                events.append(e)
            return events

        events = asyncio.run(_run())
        assert len(events) == 1


# ---------------------------------------------------------------------------
# LangGraphAdapter
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLangGraphAdapterInit:
    def test_default_anthropic_provider(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            adapter = LangGraphAdapter()
        assert adapter.provider == "anthropic"
        assert adapter.api_key == "sk-test"

    def test_openai_provider(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-openai"}):
            adapter = LangGraphAdapter(provider="openai")
        assert adapter.provider == "openai"
        assert adapter.api_key == "sk-openai"

    def test_explicit_api_key(self):
        adapter = LangGraphAdapter(api_key="my-key")
        assert adapter.api_key == "my-key"

    def test_framework_name(self):
        adapter = LangGraphAdapter()
        assert adapter.framework_name == "langgraph"

    def test_is_available_true(self):
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = True
        adapter = LangGraphAdapter()
        assert adapter.is_available() is True

    def test_is_available_false(self):
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = None
        with patch.dict("sys.modules", {"langgraph": None}):
            adapter = LangGraphAdapter()
            result = adapter.is_available()
        assert result is False
        mod._langgraph_available = None


@pytest.mark.unit
class TestLangGraphAdapterGetLLM:
    def test_anthropic_returns_chat_anthropic(self):
        """Lines 244-256: Anthropic provider creates ChatAnthropic."""
        mock_chat = MagicMock()
        with patch("langchain_anthropic.ChatAnthropic", return_value=mock_chat):
            adapter = LangGraphAdapter(provider="anthropic", api_key="sk-test")
            config = _agent_config()
            result = adapter._get_llm(config)
        assert result is mock_chat

    def test_anthropic_no_api_key_raises(self):
        """Line 249-250: no API key → ValueError."""
        adapter = LangGraphAdapter(provider="anthropic", api_key=None)
        with patch.dict("os.environ", {}, clear=True):
            adapter.api_key = None
            config = _agent_config()
            with pytest.raises(ValueError, match="API key required"):
                adapter._get_llm(config)

    def test_anthropic_omits_temperature_for_opus_4_8(self):
        """Opus 4.7+ reject temperature/top_p/top_k → not passed to ChatAnthropic."""
        with patch("langchain_anthropic.ChatAnthropic") as mock_chat:
            adapter = LangGraphAdapter(provider="anthropic", api_key="sk-test")
            config = AgentConfig(
                name="t", role=AgentRole.COORDINATOR, model_override="claude-opus-4-8"
            )
            adapter._get_llm(config)
        kwargs = mock_chat.call_args.kwargs
        assert "temperature" not in kwargs
        assert "top_p" not in kwargs
        assert "top_k" not in kwargs
        assert kwargs["model"] == "claude-opus-4-8"

    def test_anthropic_strips_temperature_for_sonnet_5(self):
        """Claude 5 family rejects temperature → stripped."""
        with patch("langchain_anthropic.ChatAnthropic") as mock_chat:
            adapter = LangGraphAdapter(provider="anthropic", api_key="sk-test")
            config = AgentConfig(
                name="t", role=AgentRole.COORDINATOR, model_override="claude-sonnet-5"
            )
            adapter._get_llm(config)
        kwargs = mock_chat.call_args.kwargs
        assert "temperature" not in kwargs

    def test_anthropic_keeps_temperature_for_sonnet_4_5(self):
        """Sonnet 4.5 still accepts temperature → passed through."""
        with patch("langchain_anthropic.ChatAnthropic") as mock_chat:
            adapter = LangGraphAdapter(provider="anthropic", api_key="sk-test")
            config = AgentConfig(
                name="t", role=AgentRole.COORDINATOR, model_override="claude-sonnet-4-5"
            )
            adapter._get_llm(config)
        kwargs = mock_chat.call_args.kwargs
        assert "temperature" in kwargs

    def test_anthropic_keeps_temperature_for_opus_4_6(self):
        """Opus 4.6 still accepts temperature → passed through."""
        with patch("langchain_anthropic.ChatAnthropic") as mock_chat:
            adapter = LangGraphAdapter(provider="anthropic", api_key="sk-test")
            config = AgentConfig(
                name="t", role=AgentRole.COORDINATOR, model_override="claude-opus-4-6"
            )
            adapter._get_llm(config)
        kwargs = mock_chat.call_args.kwargs
        assert "temperature" in kwargs

    def test_openai_returns_chat_openai(self):
        """Lines 257-265: OpenAI provider creates ChatOpenAI."""
        mock_chat = MagicMock()
        mock_openai_module = MagicMock()
        mock_openai_module.ChatOpenAI = MagicMock(return_value=mock_chat)
        with patch.dict("sys.modules", {"langchain_openai": mock_openai_module}):
            adapter = LangGraphAdapter(provider="openai", api_key="sk-openai")
            # Use model_override to skip the model router (which only supports anthropic)
            config = AgentConfig(name="test", role=AgentRole.COORDINATOR, model_override="gpt-4o")
            result = adapter._get_llm(config)
        assert result is mock_chat

    def test_unsupported_provider_raises(self):
        """Line 266: unsupported provider → ValueError."""
        adapter = LangGraphAdapter(provider="cohere", api_key="key")
        # model_override skips the model router so we reach the provider check
        config = AgentConfig(name="test", role=AgentRole.COORDINATOR, model_override="cohere-cmd")
        with pytest.raises(ValueError):
            adapter._get_llm(config)


@pytest.mark.unit
class TestLangGraphAdapterCreateAgent:
    def test_not_available_raises_import_error(self):
        """Lines 270-271: not available → ImportError."""
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = False
        adapter = LangGraphAdapter(api_key="sk-test")
        with pytest.raises(ImportError):
            adapter.create_agent(_agent_config())
        mod._langgraph_available = None

    def test_creates_langgraph_agent(self):
        """Lines 273-289: creates agent with chain runnable."""
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = True

        mock_llm = MagicMock()
        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        mock_chat_prompt = MagicMock()
        mock_chat_prompt.from_messages = MagicMock(return_value=mock_prompt)
        mock_messages_placeholder = MagicMock()

        with (
            patch.object(LangGraphAdapter, "_get_llm", return_value=mock_llm),
            patch.dict(
                "sys.modules",
                {
                    "langchain_core": MagicMock(),
                    "langchain_core.prompts": MagicMock(
                        ChatPromptTemplate=mock_chat_prompt,
                        MessagesPlaceholder=mock_messages_placeholder,
                    ),
                },
            ),
        ):
            adapter = LangGraphAdapter(api_key="sk-test")
            agent = adapter.create_agent(_agent_config())
        assert isinstance(agent, LangGraphAgent)


@pytest.mark.unit
class TestLangGraphAdapterCreateWorkflow:
    def test_not_available_raises_import_error(self):
        """Lines 293-294: not available → ImportError."""
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = False
        adapter = LangGraphAdapter()
        with pytest.raises(ImportError):
            adapter.create_workflow(_workflow_config(), [])
        mod._langgraph_available = None

    def _make_graph_mocks(self):
        """Build mock StateGraph and END."""
        mock_graph = MagicMock()
        mock_end = "END"
        mock_state_graph_class = MagicMock(return_value=mock_graph)
        mock_langgraph_graph = MagicMock(
            StateGraph=mock_state_graph_class,
            END=mock_end,
        )
        return mock_langgraph_graph, mock_graph

    def _run_create_workflow(self, mode, agents, mock_lg_graph):
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = True
        config = _workflow_config(mode=mode)

        with patch.dict(
            "sys.modules",
            {
                "langgraph": MagicMock(),
                "langgraph.graph": mock_lg_graph,
                "typing_extensions": MagicMock(TypedDict=dict),
            },
        ):
            adapter = LangGraphAdapter()
            wf = adapter.create_workflow(config, agents)
        mod._langgraph_available = None
        return wf

    def test_sequential_mode(self):
        """Lines 325-330: sequential mode builds linear chain."""
        mock_lg_graph, mock_graph = self._make_graph_mocks()
        agents = [_make_agent("a1"), _make_agent("a2")]
        wf = self._run_create_workflow("sequential", agents, mock_lg_graph)
        assert isinstance(wf, LangGraphWorkflow)

    def test_parallel_mode(self):
        """Lines 332-337: parallel mode fans out to END."""
        mock_lg_graph, mock_graph = self._make_graph_mocks()
        agents = [_make_agent("a1"), _make_agent("a2")]
        wf = self._run_create_workflow("parallel", agents, mock_lg_graph)
        assert isinstance(wf, LangGraphWorkflow)

    def test_default_mode(self):
        """Lines 339-344: unknown mode → default sequential."""
        mock_lg_graph, mock_graph = self._make_graph_mocks()
        agents = [_make_agent("a1"), _make_agent("a2")]
        wf = self._run_create_workflow("unknown", agents, mock_lg_graph)
        assert isinstance(wf, LangGraphWorkflow)

    def test_agent_node_function_is_callable(self):
        """Lines 315-318: agent_node inner function body — invoke the captured node."""
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = True
        config = _workflow_config(mode="sequential")

        mock_graph = MagicMock()
        captured_nodes: dict = {}

        def capture_add_node(name, func):
            captured_nodes[name] = func

        mock_graph.add_node.side_effect = capture_add_node
        mock_state_graph_class = MagicMock(return_value=mock_graph)
        mock_lg_graph = MagicMock(StateGraph=mock_state_graph_class, END="END")

        agent = _make_agent("node-agent")
        agent.invoke = AsyncMock(return_value={"output": "agent-result"})

        with patch.dict(
            "sys.modules",
            {
                "langgraph": MagicMock(),
                "langgraph.graph": mock_lg_graph,
                "typing_extensions": MagicMock(TypedDict=dict),
            },
        ):
            adapter = LangGraphAdapter()
            adapter.create_workflow(config, [agent])

        mod._langgraph_available = None

        # Invoke the captured agent_node function (lines 315-318)
        node_func = captured_nodes["node-agent"]
        state = {"messages": [{"role": "user", "content": "hi"}]}
        result = asyncio.run(node_func(state))
        assert result["current_agent"] == "node-agent"
        assert len(result["messages"]) > 0


@pytest.mark.unit
class TestLangGraphAdapterCreateTool:
    def test_not_available_returns_dict(self):
        """Lines 356-357: not available → returns plain dict."""
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = False

        def my_func():
            pass

        adapter = LangGraphAdapter()
        result = adapter.create_tool("my_tool", "desc", my_func)
        assert result["name"] == "my_tool"
        mod._langgraph_available = None

    def test_available_returns_structured_tool(self):
        """Lines 359-361: available → returns StructuredTool."""
        import attune.agent_factory.adapters.langgraph_adapter as mod

        mod._langgraph_available = True
        mock_tool = MagicMock()
        mock_structured = MagicMock()
        mock_structured.from_function = MagicMock(return_value=mock_tool)

        def my_func():
            pass

        with patch.dict(
            "sys.modules",
            {
                "langchain_core": MagicMock(),
                "langchain_core.tools": MagicMock(StructuredTool=mock_structured),
            },
        ):
            adapter = LangGraphAdapter()
            result = adapter.create_tool("my_tool", "desc", my_func)
        assert result is mock_tool
        mod._langgraph_available = None
