"""Runtime + adapter-method tests for the LangChain adapter.

Complements test_langchain_adapter.py (which covers _get_llm sampling
normalization) by exercising the agent/workflow runtime methods
(invoke/stream/run) against mock runnables — no real LangChain needed —
plus the adapter availability/tool/prompt methods, mocking LangChain at
sys.modules for the import-gated paths.

Async methods are driven via asyncio.run so the suite is independent of
the --asyncio-mode plugin setting.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import attune.agent_factory.adapters.langchain_adapter as mod
from attune.agent_factory.adapters.langchain_adapter import (
    LangChainAdapter,
    LangChainAgent,
    LangChainWorkflow,
    _check_langchain,
)
from attune.agent_factory.base import (
    AgentCapability,
    AgentConfig,
    AgentRole,
    WorkflowConfig,
)


def _run(coro):
    return asyncio.run(coro)


async def _collect(agen):
    return [x async for x in agen]


def _cfg(role=AgentRole.COORDINATOR, **kw):
    return AgentConfig(name=kw.pop("name", "agent"), role=role, **kw)


class _SyncRunnable:
    """A runnable exposing only sync invoke (no ainvoke/astream)."""

    def __init__(self, result):
        self._result = result

    def invoke(self, _input):
        return self._result


class TestAgentInvoke:
    def test_no_runnable_returns_placeholder(self):
        agent = LangChainAgent(_cfg(), chain=None)
        out = _run(agent.invoke("hi"))
        assert out["output"] == "No LangChain runnable configured"

    def test_ainvoke_dict_result(self):
        runnable = MagicMock()
        runnable.ainvoke = AsyncMock(return_value={"output": "answer"})
        agent = LangChainAgent(_cfg(), agent_executor=runnable)

        out = _run(agent.invoke("question"))

        assert out["output"] == "answer"
        assert out["metadata"]["framework"] == "langchain"
        # Conversation tracked.
        assert agent._conversation_history[-1]["content"] == "answer"

    def test_sync_fallback_non_dict_result(self):
        agent = LangChainAgent(_cfg(), chain=_SyncRunnable("plain text"))
        out = _run(agent.invoke("q"))
        assert out["output"] == "plain text"

    def test_dict_input_with_context_and_memory(self):
        runnable = MagicMock()
        runnable.ainvoke = AsyncMock(return_value={"answer": "via-answer-key"})
        agent = LangChainAgent(_cfg(memory_enabled=True), chain=runnable)
        agent._conversation_history.append({"role": "user", "content": "earlier"})

        out = _run(agent.invoke({"input": "q"}, context={"k": "v"}))

        assert out["output"] == "via-answer-key"
        # chat_history (memory) + context were threaded into the call.
        call_arg = runnable.ainvoke.call_args.args[0]
        assert call_arg["context"] == {"k": "v"}
        assert "chat_history" in call_arg

    def test_exception_returns_error(self):
        runnable = MagicMock()
        runnable.ainvoke = AsyncMock(side_effect=RuntimeError("kaboom"))
        agent = LangChainAgent(_cfg(), chain=runnable)
        out = _run(agent.invoke("q"))
        assert "Error:" in out["output"]
        assert out["metadata"]["error"] == "kaboom"


class TestAgentStream:
    def test_no_runnable_yields_placeholder(self):
        agent = LangChainAgent(_cfg(), chain=None)
        chunks = _run(_collect(agent.stream("hi")))
        assert chunks[0]["output"] == "No LangChain runnable configured"

    def test_astream_yields_chunks(self):
        async def _astream(_input):
            yield {"chunk": "a"}
            yield "raw-string"

        runnable = MagicMock()
        runnable.astream = _astream
        agent = LangChainAgent(_cfg(), chain=runnable)

        chunks = _run(_collect(agent.stream("q")))
        assert {"chunk": "a"} in chunks
        assert {"chunk": "raw-string"} in chunks

    def test_dict_input_is_passed_through(self):
        async def _astream(_input):
            yield {"c": 1}

        runnable = MagicMock()
        runnable.astream = _astream
        agent = LangChainAgent(_cfg(), chain=runnable)
        chunks = _run(_collect(agent.stream({"input": "q"})))
        assert {"c": 1} in chunks

    def test_no_astream_falls_back_to_invoke(self):
        agent = LangChainAgent(_cfg(), chain=_SyncRunnable({"output": "done"}))
        chunks = _run(_collect(agent.stream("q")))
        assert chunks[-1]["output"] == "done"

    def test_astream_error_yields_error(self):
        async def _astream(_input):
            raise RuntimeError("stream boom")
            yield  # pragma: no cover

        runnable = MagicMock()
        runnable.astream = _astream
        agent = LangChainAgent(_cfg(), chain=runnable)
        chunks = _run(_collect(agent.stream("q")))
        assert chunks[-1]["error"] == "stream boom"


def _agent_with(output):
    a = MagicMock()
    a.name = "ag"
    a.invoke = AsyncMock(return_value={"output": output})

    async def _astream(_input):
        yield {"text": output}

    a.stream = _astream
    return a


class TestWorkflowRun:
    def test_chain_ainvoke(self):
        chain = MagicMock()
        chain.ainvoke = AsyncMock(return_value={"output": "chained"})
        wf = LangChainWorkflow(WorkflowConfig(name="w"), [], chain=chain)
        out = _run(wf.run("in"))
        assert out["output"] == "chained"

    def test_chain_sync_and_non_dict(self):
        wf = LangChainWorkflow(WorkflowConfig(name="w"), [], chain=_SyncRunnable("flat"))
        out = _run(wf.run("in"))
        assert out["output"] == "flat"

    def test_chain_exception(self):
        chain = MagicMock()
        chain.ainvoke = AsyncMock(side_effect=RuntimeError("chain boom"))
        wf = LangChainWorkflow(WorkflowConfig(name="w"), [], chain=chain)
        out = _run(wf.run("in"))
        assert "Error:" in out["output"]

    def test_no_chain_sequential_agents(self):
        a1, a2 = _agent_with("r1"), _agent_with("r2")
        a1.name, a2.name = "a1", "a2"
        wf = LangChainWorkflow(WorkflowConfig(name="w"), [a1, a2])
        out = _run(wf.run("in"))
        assert out["output"] == "r2"
        assert len(out["results"]) == 2


class TestWorkflowStream:
    def test_emits_agent_events(self):
        a = _agent_with("x")
        wf = LangChainWorkflow(WorkflowConfig(name="w"), [a])
        events = _run(_collect(wf.stream("in")))
        kinds = [e["event"] for e in events]
        assert kinds == ["agent_start", "chunk", "agent_end"]


class TestAdapterBasics:
    def test_init_uses_env_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-anthropic")
        assert LangChainAdapter(provider="anthropic").api_key == "env-anthropic"

    def test_framework_name(self):
        assert LangChainAdapter().framework_name == "langchain"

    def test_is_available_reflects_check(self):
        adapter = LangChainAdapter()
        with patch.object(mod, "_check_langchain", return_value=True):
            assert adapter.is_available() is True
        with patch.object(mod, "_check_langchain", return_value=False):
            assert adapter.is_available() is False

    def test_default_system_prompt_known_and_unknown_role(self):
        adapter = LangChainAdapter()
        known = adapter._default_system_prompt(_cfg(role=AgentRole.RESEARCHER, description="extra"))
        assert "researcher" in known.lower()
        assert "extra" in known  # description appended
        unknown = adapter._default_system_prompt(_cfg(role=AgentRole.ARCHITECT))
        assert "architect" in unknown.lower()


class TestCheckLangchain:
    def test_true_when_importable(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", None)
        with patch.dict(sys.modules, {"langchain": MagicMock()}):
            assert _check_langchain() is True

    def test_false_when_missing(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", None)
        with patch.dict(sys.modules, {"langchain": None}):
            assert _check_langchain() is False


class TestGetLLM:
    def test_not_available_raises_import_error(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", False)
        with pytest.raises(ImportError):
            LangChainAdapter(provider="anthropic", api_key="k")._get_llm(_cfg())

    def test_anthropic_missing_key_raises(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", True)
        # Make the missing-key contract hermetic: LangChainAdapter falls back
        # to os.getenv("ANTHROPIC_API_KEY"), so a developer with the key set in
        # their shell would otherwise take the happy path and DID NOT RAISE.
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        adapter = LangChainAdapter(provider="anthropic", api_key=None)
        with patch("langchain_anthropic.ChatAnthropic"), pytest.raises(ValueError):
            adapter._get_llm(_cfg(model_override="claude-sonnet-5"))

    def test_openai_branch(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", True)
        adapter = LangChainAdapter(provider="openai", api_key="k")
        fake_openai = MagicMock()
        with patch.dict(sys.modules, {"langchain_openai": fake_openai}):
            adapter._get_llm(_cfg(model_override="gpt-4o"))
        assert fake_openai.ChatOpenAI.call_args.kwargs["model"] == "gpt-4o"

    def test_unsupported_provider_raises(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", True)
        adapter = LangChainAdapter(provider="cohere", api_key="k")
        with pytest.raises(ValueError, match="Unsupported provider"):
            adapter._get_llm(_cfg(model_override="x"))


class TestToolMethods:
    def test_create_tool_unavailable_uses_base(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", False)
        result = LangChainAdapter().create_tool("t", "desc", lambda x: x)
        assert result["name"] == "t"  # base adapter returns a dict

    def test_create_tool_available_uses_structured_tool(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", True)
        fake_mod = MagicMock()
        with patch.dict(sys.modules, {"langchain_core.tools": fake_mod}):
            LangChainAdapter().create_tool("t", "desc", lambda x: x)
        fake_mod.StructuredTool.from_function.assert_called_once()

    def test_convert_tool_unavailable_returns_none(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", False)
        assert LangChainAdapter()._convert_tool({"name": "t"}) is None

    @staticmethod
    def _fake_tools_module():
        # BaseTool must be a real type for isinstance() in _convert_tool.
        fake = MagicMock()
        fake.BaseTool = type("BaseTool", (), {})
        return fake

    def test_convert_tool_dict_creates_tool(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", True)
        adapter = LangChainAdapter()
        with (
            patch.object(adapter, "create_tool", return_value="LC_TOOL") as mock_ct,
            patch.dict(sys.modules, {"langchain_core.tools": self._fake_tools_module()}),
        ):
            result = adapter._convert_tool({"name": "t", "description": "d", "func": lambda x: x})
        assert result == "LC_TOOL"
        mock_ct.assert_called_once()

    def test_convert_tool_unknown_returns_none(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", True)
        with patch.dict(sys.modules, {"langchain_core.tools": self._fake_tools_module()}):
            # An int is neither a BaseTool nor a dict.
            assert LangChainAdapter()._convert_tool(42) is None

    def test_convert_tool_basetool_passthrough(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", True)
        fake = self._fake_tools_module()
        tool = fake.BaseTool()  # an instance of the fake BaseTool type
        with patch.dict(sys.modules, {"langchain_core.tools": fake}):
            assert LangChainAdapter()._convert_tool(tool) is tool


class TestCreateAgent:
    def test_unavailable_raises(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", False)
        with pytest.raises(ImportError):
            LangChainAdapter().create_agent(_cfg())

    def test_simple_chain_path(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", True)
        adapter = LangChainAdapter(provider="anthropic", api_key="k")
        fake_prompts = MagicMock()
        mods = {
            "langchain.agents": MagicMock(),
            "langchain.agents.agent": MagicMock(),
            "langchain_core.prompts": fake_prompts,
        }
        with (
            patch.object(adapter, "_get_llm", return_value=MagicMock()),
            patch.dict(sys.modules, mods),
        ):
            agent = adapter.create_agent(_cfg(name="a", system_prompt="sys"))
        assert isinstance(agent, LangChainAgent)

    def test_langgraph_fallback_path(self, monkeypatch):
        # langchain.agents import fails -> falls back to langgraph.prebuilt.
        monkeypatch.setattr(mod, "_langchain_available", True)
        adapter = LangChainAdapter(provider="anthropic", api_key="k")
        mods = {
            "langchain.agents": None,  # ImportError on `from langchain.agents import ...`
            "langgraph.prebuilt": MagicMock(),
            "langchain_core.prompts": MagicMock(),
        }
        with (
            patch.object(adapter, "_get_llm", return_value=MagicMock()),
            patch.dict(sys.modules, mods),
        ):
            agent = adapter.create_agent(_cfg(name="a"))
        assert isinstance(agent, LangChainAgent)

    def test_tool_calling_agent_path(self, monkeypatch):
        monkeypatch.setattr(mod, "_langchain_available", True)
        adapter = LangChainAdapter(provider="anthropic", api_key="k")
        mods = {
            "langchain.agents": MagicMock(),
            "langchain.agents.agent": MagicMock(),
            "langchain_core.prompts": MagicMock(),
        }
        cfg = _cfg(
            name="a",
            capabilities=[AgentCapability.TOOL_USE],
            tools=[{"name": "t", "description": "d", "func": lambda x: x}],
        )
        with (
            patch.object(adapter, "_get_llm", return_value=MagicMock()),
            patch.object(adapter, "_convert_tool", return_value=MagicMock()),
            patch.dict(sys.modules, mods),
        ):
            agent = adapter.create_agent(cfg)
        assert isinstance(agent, LangChainAgent)


class TestCreateWorkflow:
    def test_returns_langchain_workflow(self):
        wf = LangChainAdapter().create_workflow(WorkflowConfig(name="w"), [])
        assert isinstance(wf, LangChainWorkflow)
