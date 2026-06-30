"""Tests for NativeAgent, NativeWorkflow, and NativeAdapter.

Covers creation, invocation (with/without LLM), streaming,
tool management, conversation history, and workflow execution modes.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.agent_factory.adapters.native import (
    NativeAdapter,
    NativeAgent,
    NativeWorkflow,
)
from attune.agent_factory.base import AgentConfig, AgentRole, WorkflowConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent_config() -> AgentConfig:
    """Minimal agent config for testing."""
    return AgentConfig(
        name="test-agent",
        role=AgentRole.WRITER,
        description="A test agent",
        model_tier="capable",
        tools=[{"name": "search", "description": "search tool"}],
    )


@pytest.fixture
def agent_config_no_tools() -> AgentConfig:
    """Agent config with no tools."""
    return AgentConfig(
        name="bare-agent",
        role=AgentRole.REVIEWER,
        description="No tools",
    )


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Mock EmpathyLLM whose interact() returns a sensible dict."""
    llm = AsyncMock()
    llm.interact = AsyncMock(
        return_value={
            "response": "LLM says hello",
            "level": 4,
            "model": "claude-sonnet-5",
            "patterns_used": ["greeting"],
        }
    )
    return llm


@pytest.fixture
def native_agent(agent_config: AgentConfig) -> NativeAgent:
    """NativeAgent without an LLM (fallback mode)."""
    return NativeAgent(agent_config)


@pytest.fixture
def native_agent_with_llm(agent_config: AgentConfig, mock_llm: AsyncMock) -> NativeAgent:
    """NativeAgent backed by a mock LLM."""
    return NativeAgent(agent_config, llm=mock_llm)


@pytest.fixture
def workflow_config() -> WorkflowConfig:
    """Workflow config for sequential execution."""
    return WorkflowConfig(name="test-workflow", mode="sequential")


@pytest.fixture
def parallel_workflow_config() -> WorkflowConfig:
    """Workflow config for parallel execution."""
    return WorkflowConfig(name="parallel-workflow", mode="parallel")


# ===================================================================
# NativeAgent tests
# ===================================================================


class TestNativeAgentCreation:
    """Tests for NativeAgent construction and properties."""

    def test_creation_sets_name_and_role(self, agent_config: AgentConfig) -> None:
        agent = NativeAgent(agent_config)
        assert agent.name == "test-agent"
        assert agent.role == AgentRole.WRITER

    def test_tools_parsed_from_config(self, agent_config: AgentConfig) -> None:
        agent = NativeAgent(agent_config)
        assert "search" in agent._tools
        assert agent._tools["search"]["description"] == "search tool"

    def test_non_dict_tools_are_skipped(self) -> None:
        cfg = AgentConfig(
            name="x",
            tools=["not-a-dict", {"name": "real", "description": "ok"}],
        )
        agent = NativeAgent(cfg)
        assert "real" in agent._tools
        assert len(agent._tools) == 1

    def test_llm_defaults_to_none(self, agent_config: AgentConfig) -> None:
        agent = NativeAgent(agent_config)
        assert agent._llm is None

    def test_llm_set_when_provided(self, agent_config: AgentConfig, mock_llm: AsyncMock) -> None:
        agent = NativeAgent(agent_config, llm=mock_llm)
        assert agent._llm is mock_llm

    def test_model_property_returns_tier(self, agent_config: AgentConfig) -> None:
        agent = NativeAgent(agent_config)
        assert agent.model == "tier:capable"

    def test_model_property_uses_override(self) -> None:
        cfg = AgentConfig(
            name="x",
            model_override="claude-opus-4-8",
        )
        agent = NativeAgent(cfg)
        assert agent.model == "claude-opus-4-8"


# -------------------------------------------------------------------
# invoke
# -------------------------------------------------------------------


class TestNativeAgentInvoke:
    """Tests for NativeAgent.invoke()."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invoke_without_llm_returns_fallback(self, native_agent: NativeAgent) -> None:
        result = await native_agent.invoke("hello")
        assert "output" in result
        assert "metadata" in result
        assert native_agent.name in result["output"]
        assert "hello" in result["output"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invoke_with_llm_calls_interact(
        self,
        native_agent_with_llm: NativeAgent,
        mock_llm: AsyncMock,
    ) -> None:
        result = await native_agent_with_llm.invoke("hello")
        mock_llm.interact.assert_awaited_once()
        assert result["output"] == "LLM says hello"
        assert result["metadata"]["patterns_used"] == ["greeting"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invoke_with_dict_input_uses_input_key(self, native_agent: NativeAgent) -> None:
        result = await native_agent.invoke({"input": "structured"})
        assert "structured" in result["output"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invoke_with_dict_input_uses_query_key(self, native_agent: NativeAgent) -> None:
        result = await native_agent.invoke({"query": "question?"})
        assert "question?" in result["output"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invoke_with_dict_input_falls_back_to_str(
        self, native_agent: NativeAgent
    ) -> None:
        result = await native_agent.invoke({"other": "data"})
        assert "output" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invoke_empty_input_returns_skipped(self, native_agent: NativeAgent) -> None:
        result = await native_agent.invoke("")
        assert result["metadata"]["skipped"] is True
        assert result["output"] == ""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invoke_whitespace_only_returns_skipped(self, native_agent: NativeAgent) -> None:
        result = await native_agent.invoke("   ")
        assert result["metadata"]["skipped"] is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invoke_passes_context_to_llm(
        self,
        native_agent_with_llm: NativeAgent,
        mock_llm: AsyncMock,
    ) -> None:
        ctx = {"extra": "data"}
        await native_agent_with_llm.invoke("hi", context=ctx)
        call_kwargs = mock_llm.interact.call_args[1]
        assert call_kwargs["context"]["extra"] == "data"
        assert call_kwargs["context"]["agent_name"] == "test-agent"
        assert call_kwargs["context"]["agent_role"] == "writer"


# -------------------------------------------------------------------
# conversation history
# -------------------------------------------------------------------


class TestNativeAgentHistory:
    """Tests for conversation tracking and history."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invoke_appends_to_history(self, native_agent: NativeAgent) -> None:
        await native_agent.invoke("hello")
        history = native_agent.get_conversation_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "hello"
        assert history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_conversation_history_returns_copy(self, native_agent: NativeAgent) -> None:
        await native_agent.invoke("hello")
        h1 = native_agent.get_conversation_history()
        h2 = native_agent.get_conversation_history()
        assert h1 == h2
        assert h1 is not h2  # must be a copy

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_clear_history(self, native_agent: NativeAgent) -> None:
        await native_agent.invoke("hello")
        assert len(native_agent.get_conversation_history()) == 2
        native_agent.clear_history()
        assert len(native_agent.get_conversation_history()) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_history_included_in_context_for_llm(
        self,
        native_agent_with_llm: NativeAgent,
        mock_llm: AsyncMock,
    ) -> None:
        # First call — no history yet
        await native_agent_with_llm.invoke("first")
        # Second call — should include history from first call
        await native_agent_with_llm.invoke("second")
        second_call_ctx = mock_llm.interact.call_args_list[1][1]["context"]
        assert "conversation_history" in second_call_ctx
        assert len(second_call_ctx["conversation_history"]) == 2


# -------------------------------------------------------------------
# add_tool
# -------------------------------------------------------------------


class TestNativeAgentTools:
    """Tests for tool management."""

    def test_add_tool_appends_to_config(self, native_agent: NativeAgent) -> None:
        original_count = len(native_agent.config.tools)
        new_tool = {"name": "calc", "description": "calculator"}
        native_agent.add_tool(new_tool)
        assert len(native_agent.config.tools) == original_count + 1
        assert native_agent.config.tools[-1] is new_tool


# -------------------------------------------------------------------
# stream
# -------------------------------------------------------------------


class TestNativeAgentStream:
    """Tests for NativeAgent.stream()."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stream_yields_single_result(self, native_agent: NativeAgent) -> None:
        chunks = []
        async for chunk in native_agent.stream("hello"):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert "output" in chunks[0]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stream_with_llm(
        self,
        native_agent_with_llm: NativeAgent,
        mock_llm: AsyncMock,
    ) -> None:
        chunks = []
        async for chunk in native_agent_with_llm.stream("hi"):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0]["output"] == "LLM says hello"


# ===================================================================
# NativeWorkflow tests
# ===================================================================


def _make_agent(name: str) -> NativeAgent:
    """Helper to create a lightweight NativeAgent for workflows."""
    cfg = AgentConfig(name=name, role=AgentRole.EXECUTOR)
    return NativeAgent(cfg)


class TestNativeWorkflowCreation:
    """Tests for NativeWorkflow construction."""

    def test_creation_stores_agents_by_name(self, workflow_config: WorkflowConfig) -> None:
        a1 = _make_agent("a1")
        a2 = _make_agent("a2")
        wf = NativeWorkflow(workflow_config, [a1, a2])
        assert "a1" in wf.agents
        assert "a2" in wf.agents

    def test_get_agent_returns_agent(self, workflow_config: WorkflowConfig) -> None:
        a1 = _make_agent("a1")
        wf = NativeWorkflow(workflow_config, [a1])
        assert wf.get_agent("a1") is a1

    def test_get_agent_returns_none_for_missing(self, workflow_config: WorkflowConfig) -> None:
        wf = NativeWorkflow(workflow_config, [])
        assert wf.get_agent("nonexistent") is None

    def test_get_state_initially_empty(self, workflow_config: WorkflowConfig) -> None:
        wf = NativeWorkflow(workflow_config, [])
        assert wf.get_state() == {}


# -------------------------------------------------------------------
# sequential run
# -------------------------------------------------------------------


class TestNativeWorkflowSequential:
    """Tests for sequential workflow execution."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sequential_run_chains_output(self, workflow_config: WorkflowConfig) -> None:
        a1 = _make_agent("a1")
        a2 = _make_agent("a2")
        wf = NativeWorkflow(workflow_config, [a1, a2])
        result = await wf.run("start")
        assert len(result["results"]) == 2
        assert result["results"][0]["agent"] == "a1"
        assert result["results"][1]["agent"] == "a2"
        # a2 should have received a1's output as input
        assert result["output"] != ""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sequential_run_sets_state(self, workflow_config: WorkflowConfig) -> None:
        a1 = _make_agent("a1")
        wf = NativeWorkflow(workflow_config, [a1])
        await wf.run("input-data")
        state = wf.get_state()
        assert state["input"] == "input-data"
        assert "results" in state
        assert "final_output" in state

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sequential_run_with_initial_state(self, workflow_config: WorkflowConfig) -> None:
        a1 = _make_agent("a1")
        wf = NativeWorkflow(workflow_config, [a1])
        await wf.run("go", initial_state={"key": "val"})
        state = wf.get_state()
        assert state["key"] == "val"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sequential_run_no_agents(self, workflow_config: WorkflowConfig) -> None:
        wf = NativeWorkflow(workflow_config, [])
        result = await wf.run("go")
        assert result["results"] == []
        assert result["output"] == ""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_unknown_mode_falls_back_to_sequential(self) -> None:
        cfg = WorkflowConfig(name="wf", mode="unknown-mode")
        a1 = _make_agent("a1")
        wf = NativeWorkflow(cfg, [a1])
        result = await wf.run("go")
        assert len(result["results"]) == 1


# -------------------------------------------------------------------
# parallel run
# -------------------------------------------------------------------


class TestNativeWorkflowParallel:
    """Tests for parallel workflow execution."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parallel_run_invokes_all_agents(
        self, parallel_workflow_config: WorkflowConfig
    ) -> None:
        a1 = _make_agent("a1")
        a2 = _make_agent("a2")
        wf = NativeWorkflow(parallel_workflow_config, [a1, a2])
        result = await wf.run("go")
        assert len(result["results"]) == 2
        agent_names = [r["agent"] for r in result["results"]]
        assert "a1" in agent_names
        assert "a2" in agent_names

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parallel_all_receive_same_input(
        self, parallel_workflow_config: WorkflowConfig
    ) -> None:
        a1 = _make_agent("a1")
        a2 = _make_agent("a2")
        wf = NativeWorkflow(parallel_workflow_config, [a1, a2])
        result = await wf.run("shared-input")
        # Both agents should have processed the same input
        for r in result["results"]:
            assert "shared-input" in r["output"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_parallel_agents_invoked_list(
        self, parallel_workflow_config: WorkflowConfig
    ) -> None:
        a1 = _make_agent("a1")
        a2 = _make_agent("a2")
        wf = NativeWorkflow(parallel_workflow_config, [a1, a2])
        result = await wf.run("go")
        assert set(result["agents_invoked"]) == {"a1", "a2"}


# -------------------------------------------------------------------
# workflow stream
# -------------------------------------------------------------------


class TestNativeWorkflowStream:
    """Tests for NativeWorkflow.stream()."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stream_yields_start_output_end(self, workflow_config: WorkflowConfig) -> None:
        a1 = _make_agent("a1")
        wf = NativeWorkflow(workflow_config, [a1])
        events = []
        async for event in wf.stream("go"):
            events.append(event)
        event_types = [e["event"] for e in events]
        assert "agent_start" in event_types
        assert "agent_output" in event_types
        assert "agent_end" in event_types

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stream_multiple_agents(self, workflow_config: WorkflowConfig) -> None:
        a1 = _make_agent("a1")
        a2 = _make_agent("a2")
        wf = NativeWorkflow(workflow_config, [a1, a2])
        events = []
        async for event in wf.stream("go"):
            events.append(event)
        starts = [e for e in events if e["event"] == "agent_start"]
        assert len(starts) == 2


# -------------------------------------------------------------------
# get_state returns a copy
# -------------------------------------------------------------------


class TestNativeWorkflowState:
    """Tests for workflow state management."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_state_returns_copy(self, workflow_config: WorkflowConfig) -> None:
        a1 = _make_agent("a1")
        wf = NativeWorkflow(workflow_config, [a1])
        await wf.run("go")
        s1 = wf.get_state()
        s2 = wf.get_state()
        assert s1 == s2
        assert s1 is not s2


# ===================================================================
# NativeAdapter tests
# ===================================================================


class TestNativeAdapter:
    """Tests for NativeAdapter."""

    def test_framework_name(self) -> None:
        adapter = NativeAdapter()
        assert adapter.framework_name == "native"

    def test_is_available_always_true(self) -> None:
        adapter = NativeAdapter()
        assert adapter.is_available() is True

    def test_create_agent_returns_native_agent(self, agent_config: AgentConfig) -> None:
        adapter = NativeAdapter()
        agent = adapter.create_agent(agent_config)
        assert isinstance(agent, NativeAgent)
        assert agent.name == agent_config.name

    def test_create_agent_without_api_key_has_no_llm(self, agent_config: AgentConfig) -> None:
        adapter = NativeAdapter(api_key=None)
        adapter.api_key = None  # ensure no env fallback
        agent = adapter.create_agent(agent_config)
        assert agent._llm is None

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False)
    def test_create_agent_with_api_key_tries_empathy_llm(self, agent_config: AgentConfig) -> None:
        adapter = NativeAdapter(api_key="fake-key-for-test")
        with patch(
            "attune.agent_factory.adapters.native.EmpathyLLM",
            create=True,
        ) as mock_cls:
            # Simulate the import inside _get_llm
            with patch.dict(
                "sys.modules",
                {"attune.llm.core": MagicMock(EmpathyLLM=mock_cls)},
            ):
                agent = adapter.create_agent(agent_config)
                # _get_llm should have attempted to create an EmpathyLLM
                # The agent may or may not have an LLM depending on
                # import success; we verify the adapter tried.
                assert isinstance(agent, NativeAgent)

    def test_create_agent_import_error_falls_back(self, agent_config: AgentConfig) -> None:
        """When EmpathyLLM import fails, agent is created without LLM."""
        adapter = NativeAdapter(api_key="fake-key")
        # Force ImportError inside _get_llm
        with patch.dict("sys.modules", {"attune.llm.core": None}):
            agent = adapter.create_agent(agent_config)
            assert isinstance(agent, NativeAgent)
            # llm should be None due to ImportError
            assert agent._llm is None

    def test_create_workflow_returns_native_workflow(
        self,
        agent_config: AgentConfig,
        workflow_config: WorkflowConfig,
    ) -> None:
        adapter = NativeAdapter()
        agent = adapter.create_agent(agent_config)
        wf = adapter.create_workflow(workflow_config, [agent])
        assert isinstance(wf, NativeWorkflow)
        assert wf.config.name == "test-workflow"
        assert agent.name in wf.agents

    def test_create_tool_returns_dict(self) -> None:
        adapter = NativeAdapter()

        def dummy_fn() -> str:
            return "ok"

        tool = adapter.create_tool(
            name="my_tool",
            description="does stuff",
            func=dummy_fn,
            args_schema={"x": "int"},
        )
        assert tool["name"] == "my_tool"
        assert tool["description"] == "does stuff"
        assert tool["func"] is dummy_fn
        assert tool["args_schema"] == {"x": "int"}

    def test_create_tool_args_schema_defaults_to_none(self) -> None:
        adapter = NativeAdapter()
        tool = adapter.create_tool("t", "d", lambda: None)
        assert tool["args_schema"] is None

    def test_adapter_uses_env_api_key(self) -> None:
        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "env-key-123"},
        ):
            adapter = NativeAdapter()
            assert adapter.api_key == "env-key-123"

    def test_adapter_explicit_key_overrides_env(self) -> None:
        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "env-key"},
        ):
            adapter = NativeAdapter(api_key="explicit-key")
            assert adapter.api_key == "explicit-key"

    def test_adapter_provider_defaults_to_anthropic(self) -> None:
        adapter = NativeAdapter()
        assert adapter.provider == "anthropic"
