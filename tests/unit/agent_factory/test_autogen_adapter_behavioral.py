"""Behavioral tests for AutoGenAdapter, AutoGenAgent, and AutoGenWorkflow.

Tests the public API surface without requiring the pyautogen package.
The optional ``autogen`` dependency is injected into ``sys.modules`` as a
MagicMock so adapter creation logic can be exercised in isolation.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

import attune.agent_factory.adapters.autogen_adapter as mod
from attune.agent_factory.adapters.autogen_adapter import (
    AutoGenAdapter,
    AutoGenAgent,
    AutoGenWorkflow,
    _check_autogen,
)
from attune.agent_factory.base import (
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
        role=AgentRole.COORDINATOR,
        description="Test agent",
        model_tier="capable",
        temperature=0.5,
        max_tokens=1024,
    )


@pytest.fixture()
def workflow_config():
    """Create a basic workflow config."""
    return AgentGraphConfig(name="test-workflow", description="Test workflow")


@pytest.fixture()
def fake_autogen(monkeypatch):
    """Inject a fake ``autogen`` module and force availability True.

    Yields the fake module so tests can assert on the constructors AutoGen
    would have been asked to build.
    """
    fake = MagicMock(name="autogen")
    monkeypatch.setitem(sys.modules, "autogen", fake)
    monkeypatch.setattr(mod, "_autogen_available", True)
    yield fake


# ---------------------------------------------------------------------------
# AutoGenAgent — invoke
# ---------------------------------------------------------------------------


class TestAutoGenAgentInvoke:
    """Test AutoGenAgent.invoke() across input shapes and outcomes."""

    @pytest.mark.asyncio()
    async def test_invoke_no_agent_returns_placeholder(self, agent_config):
        """Given no underlying agent, invoke returns a 'no agent' message."""
        agent = AutoGenAgent(agent_config)
        result = await agent.invoke("hello")

        assert result["output"] == "No AutoGen agent configured"
        assert result["metadata"] == {}

    @pytest.mark.asyncio()
    async def test_invoke_str_input_with_generate_reply(self, agent_config):
        """Given a string input and an agent with generate_reply, the reply is returned."""
        ag = MagicMock()
        ag.generate_reply.return_value = "the reply"

        agent = AutoGenAgent(agent_config, autogen_agent=ag)
        result = await agent.invoke("a question")

        assert result["output"] == "the reply"
        assert result["metadata"]["framework"] == "autogen"
        ag.generate_reply.assert_called_once_with(
            messages=[{"role": "user", "content": "a question"}],
        )

    @pytest.mark.asyncio()
    async def test_invoke_dict_input_uses_input_key(self, agent_config):
        """Given dict input with 'input', that value becomes the message."""
        ag = MagicMock()
        ag.generate_reply.return_value = "ok"

        agent = AutoGenAgent(agent_config, autogen_agent=ag)
        await agent.invoke({"input": "from-input-key"})

        ag.generate_reply.assert_called_once_with(
            messages=[{"role": "user", "content": "from-input-key"}],
        )

    @pytest.mark.asyncio()
    async def test_invoke_dict_input_uses_message_key(self, agent_config):
        """Given dict input with only 'message', that value becomes the message."""
        ag = MagicMock()
        ag.generate_reply.return_value = "ok"

        agent = AutoGenAgent(agent_config, autogen_agent=ag)
        await agent.invoke({"message": "from-message-key"})

        ag.generate_reply.assert_called_once_with(
            messages=[{"role": "user", "content": "from-message-key"}],
        )

    @pytest.mark.asyncio()
    async def test_invoke_dict_input_falls_back_to_str(self, agent_config):
        """Given dict input lacking input/message keys, falls back to str(dict)."""
        ag = MagicMock()
        ag.generate_reply.return_value = "ok"

        agent = AutoGenAgent(agent_config, autogen_agent=ag)
        await agent.invoke({"other": 1})

        sent = ag.generate_reply.call_args.kwargs["messages"][0]["content"]
        assert "other" in sent

    @pytest.mark.asyncio()
    async def test_invoke_agent_without_generate_reply(self, agent_config):
        """Given an agent missing generate_reply, a received-echo is returned."""
        ag = object()  # has no generate_reply attribute

        agent = AutoGenAgent(agent_config, autogen_agent=ag)
        result = await agent.invoke("ping")

        assert result["output"] == "[test-agent] Received: ping"

    @pytest.mark.asyncio()
    async def test_invoke_non_str_reply_is_stringified(self, agent_config):
        """Given a non-string reply, the output is str()-coerced."""
        ag = MagicMock()
        ag.generate_reply.return_value = {"k": "v"}

        agent = AutoGenAgent(agent_config, autogen_agent=ag)
        result = await agent.invoke("q")

        assert result["output"] == str({"k": "v"})

    @pytest.mark.asyncio()
    async def test_invoke_records_conversation_history(self, agent_config):
        """Given a successful invoke, user + assistant turns are recorded."""
        ag = MagicMock()
        ag.generate_reply.return_value = "answer"

        agent = AutoGenAgent(agent_config, autogen_agent=ag)
        await agent.invoke("hi")

        assert len(agent._conversation_history) == 2
        assert agent._conversation_history[0] == {"role": "user", "content": "hi"}
        assert agent._conversation_history[1] == {"role": "assistant", "content": "answer"}

    @pytest.mark.asyncio()
    async def test_invoke_handles_error(self, agent_config):
        """Given generate_reply raising, invoke returns an error dict."""
        ag = MagicMock()
        ag.generate_reply.side_effect = RuntimeError("boom")

        agent = AutoGenAgent(agent_config, autogen_agent=ag)
        result = await agent.invoke("q")

        assert "Error" in result["output"]
        assert result["metadata"]["error"] == "boom"


# ---------------------------------------------------------------------------
# AutoGenAgent — stream / accessor
# ---------------------------------------------------------------------------


class TestAutoGenAgentStreamAndAccessor:
    """Test AutoGenAgent.stream() and get_autogen_agent()."""

    @pytest.mark.asyncio()
    async def test_stream_yields_single_invoke_result(self, agent_config):
        """Given a stream call, exactly one chunk matching invoke is yielded."""
        ag = MagicMock()
        ag.generate_reply.return_value = "streamed"

        agent = AutoGenAgent(agent_config, autogen_agent=ag)
        chunks = [c async for c in agent.stream("x")]

        assert len(chunks) == 1
        assert chunks[0]["output"] == "streamed"

    def test_get_autogen_agent_returns_underlying(self, agent_config):
        """get_autogen_agent() returns the wrapped instance (or None)."""
        sentinel = object()
        assert AutoGenAgent(agent_config, autogen_agent=sentinel).get_autogen_agent() is sentinel
        assert AutoGenAgent(agent_config).get_autogen_agent() is None


# ---------------------------------------------------------------------------
# AutoGenWorkflow — run
# ---------------------------------------------------------------------------


class TestAutoGenWorkflowRun:
    """Test AutoGenWorkflow.run() across manager/no-manager paths."""

    @pytest.mark.asyncio()
    async def test_run_without_manager_falls_back_to_sequential(
        self, workflow_config, agent_config
    ):
        """Given no manager, run threads input through agents sequentially."""
        a1 = AutoGenAgent(agent_config)
        a1.invoke = MagicMock(return_value=_coro({"output": "step1"}))
        wf = AutoGenWorkflow(workflow_config, [a1])

        result = await wf.run("start")

        assert result["output"] == "step1"
        assert result["results"][0]["output"] == "step1"

    @pytest.mark.asyncio()
    async def test_run_sequential_non_str_final_is_stringified(self, workflow_config, agent_config):
        """Given a final non-string output, the sequential result is str-coerced."""
        a1 = AutoGenAgent(agent_config)
        a1.invoke = MagicMock(return_value=_coro({"output": {"k": 1}}))
        wf = AutoGenWorkflow(workflow_config, [a1])

        result = await wf.run("start")

        assert result["output"] == str({"k": 1})

    @pytest.mark.asyncio()
    async def test_run_with_manager_returns_last_message_content(
        self, workflow_config, agent_config
    ):
        """Given a manager and chat history, output is the last message content."""
        ag = MagicMock()
        first = AutoGenAgent(agent_config, autogen_agent=ag)
        manager = MagicMock()
        manager.chat_messages = {"a": [{"content": "first"}, {"content": "last"}]}

        wf = AutoGenWorkflow(workflow_config, [first], manager=manager)
        result = await wf.run("go")

        assert result["output"] == "last"
        assert result["metadata"]["framework"] == "autogen"
        ag.initiate_chat.assert_called_once()

    @pytest.mark.asyncio()
    async def test_run_with_manager_dict_input(self, workflow_config, agent_config):
        """Given dict input with 'input', the message is extracted for initiate_chat."""
        ag = MagicMock()
        first = AutoGenAgent(agent_config, autogen_agent=ag)
        manager = MagicMock()
        manager.chat_messages = {"a": [{"content": "done"}]}

        wf = AutoGenWorkflow(workflow_config, [first], manager=manager)
        await wf.run({"input": "hello-dict"})

        assert ag.initiate_chat.call_args.kwargs["message"] == "hello-dict"

    @pytest.mark.asyncio()
    async def test_run_with_manager_no_messages_returns_chat_completed(
        self, workflow_config, agent_config
    ):
        """Given truthy-but-empty chat history, output is 'Chat completed'."""
        ag = MagicMock()
        first = AutoGenAgent(agent_config, autogen_agent=ag)
        manager = MagicMock()
        manager.chat_messages = {"a": []}  # truthy dict, yields no messages

        wf = AutoGenWorkflow(workflow_config, [first], manager=manager)
        result = await wf.run("go")

        assert result["output"] == "Chat completed"

    @pytest.mark.asyncio()
    async def test_run_with_manager_falsy_history_returns_no_response(
        self, workflow_config, agent_config
    ):
        """Given falsy chat history, output is 'No response'."""
        ag = MagicMock()
        first = AutoGenAgent(agent_config, autogen_agent=ag)
        manager = MagicMock()
        manager.chat_messages = {}  # falsy

        wf = AutoGenWorkflow(workflow_config, [first], manager=manager)
        result = await wf.run("go")

        assert result["output"] == "No response"

    @pytest.mark.asyncio()
    async def test_run_with_manager_no_underlying_agent(self, workflow_config, agent_config):
        """Given a manager but a first agent without an underlying agent, no chat fires."""
        first = AutoGenAgent(agent_config)  # get_autogen_agent() -> None
        manager = MagicMock()

        wf = AutoGenWorkflow(workflow_config, [first], manager=manager)
        result = await wf.run("go")

        # sync_chat returns {"messages": []} -> no messages -> Chat completed
        assert result["output"] == "Chat completed"

    @pytest.mark.asyncio()
    async def test_run_with_manager_handles_error(self, workflow_config, agent_config):
        """Given initiate_chat raising, run returns an error dict."""
        ag = MagicMock()
        ag.initiate_chat.side_effect = RuntimeError("chat broke")
        first = AutoGenAgent(agent_config, autogen_agent=ag)
        manager = MagicMock()

        wf = AutoGenWorkflow(workflow_config, [first], manager=manager)
        result = await wf.run("go")

        assert "Error" in result["output"]
        assert result["error"] == "chat broke"

    @pytest.mark.asyncio()
    async def test_stream_yields_run_result(self, workflow_config, agent_config):
        """Given a stream call, exactly one chunk matching run is yielded."""
        a1 = AutoGenAgent(agent_config)
        a1.invoke = MagicMock(return_value=_coro({"output": "seq"}))
        wf = AutoGenWorkflow(workflow_config, [a1])

        chunks = [c async for c in wf.stream("x")]

        assert len(chunks) == 1
        assert chunks[0]["output"] == "seq"


# ---------------------------------------------------------------------------
# AutoGenAdapter — properties / config
# ---------------------------------------------------------------------------


class TestAutoGenAdapterProperties:
    """Test adapter construction, properties, and LLM config building."""

    def test_framework_name(self):
        """framework_name is 'autogen'."""
        assert AutoGenAdapter().framework_name == "autogen"

    def test_default_provider_is_anthropic(self, monkeypatch):
        """Default provider is anthropic, key read from ANTHROPIC_API_KEY."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")
        adapter = AutoGenAdapter()
        assert adapter.provider == "anthropic"
        assert adapter.api_key == "sk-anthropic"

    def test_openai_provider_reads_openai_key(self, monkeypatch):
        """provider='openai' reads OPENAI_API_KEY from env."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        adapter = AutoGenAdapter(provider="openai")
        assert adapter.api_key == "sk-openai"

    def test_explicit_api_key_wins(self):
        """An explicit api_key overrides the env lookup."""
        adapter = AutoGenAdapter(api_key="explicit")
        assert adapter.api_key == "explicit"

    def test_is_available_delegates_to_check(self, monkeypatch):
        """is_available() reflects _check_autogen()."""
        monkeypatch.setattr(mod, "_autogen_available", True)
        assert AutoGenAdapter().is_available() is True
        monkeypatch.setattr(mod, "_autogen_available", False)
        assert AutoGenAdapter().is_available() is False

    def test_get_llm_config_anthropic(self, agent_config):
        """The anthropic branch tags the config_list with api_type=anthropic."""
        adapter = AutoGenAdapter(provider="anthropic", api_key="sk-a")
        cfg = adapter._get_llm_config(agent_config)

        entry = cfg["config_list"][0]
        assert entry["api_type"] == "anthropic"
        assert entry["api_key"] == "sk-a"
        assert cfg["temperature"] == agent_config.temperature
        assert cfg["max_tokens"] == agent_config.max_tokens

    def test_get_llm_config_openai(self):
        """The openai branch omits api_type."""
        adapter = AutoGenAdapter(provider="openai", api_key="sk-o")
        cfg = adapter._get_llm_config(
            AgentConfig(name="o", model_override="gpt-4o"),
        )

        entry = cfg["config_list"][0]
        assert "api_type" not in entry
        assert entry["api_key"] == "sk-o"
        assert entry["model"] == "gpt-4o"

    def test_get_llm_config_uses_model_override(self):
        """model_override is used verbatim as the config model id."""
        adapter = AutoGenAdapter(provider="anthropic", api_key="sk-a")
        cfg = adapter._get_llm_config(
            AgentConfig(name="m", model_override="claude-custom-id"),
        )
        assert cfg["config_list"][0]["model"] == "claude-custom-id"


# ---------------------------------------------------------------------------
# AutoGenAdapter — create_agent / create_workflow / create_tool
# ---------------------------------------------------------------------------


class TestAutoGenAdapterCreateAgent:
    """Test agent and workflow creation with a mocked autogen module."""

    def test_create_agent_raises_when_unavailable(self, agent_config, monkeypatch):
        """Given autogen not installed, create_agent raises ImportError."""
        monkeypatch.setattr(mod, "_autogen_available", False)
        with pytest.raises(ImportError, match="not installed"):
            AutoGenAdapter().create_agent(agent_config)

    def test_create_agent_assistant_for_non_executor(self, agent_config, fake_autogen):
        """A non-executor role builds an AssistantAgent."""
        adapter = AutoGenAdapter(api_key="sk-a")
        agent = adapter.create_agent(agent_config)

        assert isinstance(agent, AutoGenAgent)
        fake_autogen.AssistantAgent.assert_called_once()
        fake_autogen.UserProxyAgent.assert_not_called()

    def test_create_agent_userproxy_for_executor(self, fake_autogen):
        """An EXECUTOR role builds a UserProxyAgent for code execution."""
        adapter = AutoGenAdapter(api_key="sk-a")
        cfg = AgentConfig(name="exec", role=AgentRole.EXECUTOR)
        adapter.create_agent(cfg)

        fake_autogen.UserProxyAgent.assert_called_once()
        fake_autogen.AssistantAgent.assert_not_called()

    def test_create_workflow_raises_when_unavailable(self, workflow_config, monkeypatch):
        """Given autogen not installed, create_workflow raises ImportError."""
        monkeypatch.setattr(mod, "_autogen_available", False)
        with pytest.raises(ImportError, match="not installed"):
            AutoGenAdapter().create_workflow(workflow_config, [])

    def test_create_workflow_default_when_no_underlying_agents(
        self, workflow_config, agent_config, fake_autogen
    ):
        """Given agents with no underlying autogen agent, a default workflow is returned."""
        adapter = AutoGenAdapter(api_key="sk-a")
        agent = AutoGenAgent(agent_config)  # no underlying agent

        wf = adapter.create_workflow(workflow_config, [agent])

        assert isinstance(wf, AutoGenWorkflow)
        fake_autogen.GroupChat.assert_not_called()

    def test_create_workflow_conversation_mode(self, agent_config, fake_autogen):
        """conversation mode builds a free-form GroupChat (no round_robin)."""
        adapter = AutoGenAdapter(api_key="sk-a")
        agent = AutoGenAgent(agent_config, autogen_agent=MagicMock())
        cfg = AgentGraphConfig(name="w", mode="conversation", max_iterations=5)

        adapter.create_workflow(cfg, [agent])

        fake_autogen.GroupChat.assert_called_once()
        assert "speaker_selection_method" not in fake_autogen.GroupChat.call_args.kwargs
        fake_autogen.GroupChatManager.assert_called_once()

    def test_create_workflow_sequential_mode_uses_round_robin(self, agent_config, fake_autogen):
        """A non-conversation mode builds a round-robin GroupChat."""
        adapter = AutoGenAdapter(api_key="sk-a")
        agent = AutoGenAgent(agent_config, autogen_agent=MagicMock())
        cfg = AgentGraphConfig(name="w", mode="sequential", max_iterations=3)

        adapter.create_workflow(cfg, [agent])

        kwargs = fake_autogen.GroupChat.call_args.kwargs
        assert kwargs["speaker_selection_method"] == "round_robin"

    def test_create_tool_returns_dict(self):
        """create_tool returns a registration dict for AutoGen."""

        def fn():
            pass

        tool = AutoGenAdapter().create_tool("t", "desc", fn, {"a": "str"})
        assert tool == {"name": "t", "description": "desc", "func": fn, "args_schema": {"a": "str"}}


# ---------------------------------------------------------------------------
# _default_system_message / _check_autogen
# ---------------------------------------------------------------------------


class TestDefaultSystemMessageAndCheck:
    """Test the role-message map and the lazy availability check."""

    def test_default_system_message_known_role(self):
        """A known role maps to its tailored system message."""
        msg = AutoGenAdapter()._default_system_message(
            AgentConfig(name="c", role=AgentRole.RESEARCHER),
        )
        assert "research" in msg.lower()

    def test_default_system_message_unknown_role_fallback(self):
        """An unmapped role falls back to a generic helpful message."""
        msg = AutoGenAdapter()._default_system_message(
            AgentConfig(name="s", role=AgentRole.SUMMARIZER),
        )
        assert "summarizer" in msg.lower()

    def test_check_autogen_returns_bool(self, monkeypatch):
        """_check_autogen() resolves to a boolean and caches the result."""
        monkeypatch.setattr(mod, "_autogen_available", None)
        result = _check_autogen()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _coro(value):
    """Return an awaitable resolving to ``value`` (for mocking async invoke)."""
    return value
