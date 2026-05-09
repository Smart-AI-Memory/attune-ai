"""Tests for attune.orchestration._strategies.advanced_strategies.

Covers previously-uncovered branches in:
- ToolEnhancedStrategy.execute() (lines 84-116)
- PromptCachedSequentialStrategy.execute() (lines 187-248)
- DelegationChainStrategy.execute() and helpers (lines 317-523)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.orchestration._strategies.advanced_strategies import (
    DelegationChainStrategy,
    PromptCachedSequentialStrategy,
    ToolEnhancedStrategy,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent(agent_id="a1", role="analyzer", tier="cheap", system_prompt="You are an AI."):
    """Mock agent with all attributes used by the strategies."""
    a = MagicMock()
    a.agent_id = agent_id
    a.role = role
    a.tier = tier
    a.system_prompt = system_prompt
    return a


def _llm_response(content="result", duration=0.1):
    return {"content": content, "duration": duration, "success": True}


# ---------------------------------------------------------------------------
# ToolEnhancedStrategy
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestToolEnhancedStrategy:
    @pytest.mark.asyncio
    async def test_no_agents_returns_failure(self):
        strategy = ToolEnhancedStrategy(tools=[])
        result = await strategy.execute([], {"task": "do something"})
        assert result.success is False
        assert "No agent provided" in result.errors[0]

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        strategy = ToolEnhancedStrategy(tools=[{"name": "read_file"}])
        agent = _agent()
        mock_response = _llm_response("analysis complete")

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(return_value=mock_response)

            result = await strategy.execute([agent], {"task": "analyze this"})

        assert result.success is True
        assert len(result.outputs) == 1
        assert result.outputs[0].agent_id == "a1"

    @pytest.mark.asyncio
    async def test_exception_returns_failure_result(self):
        strategy = ToolEnhancedStrategy(tools=[])
        agent = _agent()

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

            result = await strategy.execute([agent], {"task": "analyze"})

        assert result.success is False
        assert "LLM unavailable" in result.errors[0]

    @pytest.mark.asyncio
    async def test_only_first_agent_used(self):
        strategy = ToolEnhancedStrategy(tools=[])
        agent1 = _agent("a1")
        agent2 = _agent("a2")
        mock_response = _llm_response()

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(return_value=mock_response)

            result = await strategy.execute([agent1, agent2], {"task": "x"})

        # Only 1 output — from first agent
        assert len(result.outputs) == 1
        assert result.outputs[0].agent_id == "a1"


# ---------------------------------------------------------------------------
# PromptCachedSequentialStrategy
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptCachedSequentialStrategy:
    @pytest.mark.asyncio
    async def test_empty_agents_returns_success_with_no_outputs(self):
        strategy = PromptCachedSequentialStrategy()
        with patch("attune.models.LLMClient", create=True) as MockLLM:
            MockLLM.return_value = MagicMock()
            result = await strategy.execute([], {"task": "x"})
        # No agents → loop skipped, success=True (all() over empty)
        assert result.success is True
        assert result.outputs == []

    @pytest.mark.asyncio
    async def test_sequential_with_cached_context(self):
        strategy = PromptCachedSequentialStrategy(cached_context="LARGE DOCS HERE")
        agents = [_agent("a1"), _agent("a2")]
        mock_response = _llm_response("output")

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(return_value=mock_response)

            result = await strategy.execute(agents, {"task": "review", "input": {}})

        assert result.success is True
        assert len(result.outputs) == 2

    @pytest.mark.asyncio
    async def test_sequential_without_cached_context(self):
        strategy = PromptCachedSequentialStrategy(cached_context=None)
        agents = [_agent("a1")]
        mock_response = _llm_response("done")

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(return_value=mock_response)

            result = await strategy.execute(agents, {"task": "analyze", "input": {}})

        assert result.success is True

    @pytest.mark.asyncio
    async def test_agent_failure_recorded_in_outputs(self):
        strategy = PromptCachedSequentialStrategy()
        agents = [_agent("a1"), _agent("a2")]

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(side_effect=RuntimeError("API error"))

            result = await strategy.execute(agents, {"task": "x", "input": {}})

        assert result.success is False
        assert all(not r.success for r in result.outputs)
        assert len(result.errors) == 2

    @pytest.mark.asyncio
    async def test_final_output_contains_last_agent_content(self):
        strategy = PromptCachedSequentialStrategy()
        agents = [_agent("a1"), _agent("a2")]
        responses = [_llm_response("first"), _llm_response("second")]

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(side_effect=responses)

            result = await strategy.execute(agents, {"task": "x", "input": {}})

        assert result.aggregated_output["final_output"] == "second"


# ---------------------------------------------------------------------------
# DelegationChainStrategy
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDelegationChainStrategy:
    @pytest.mark.asyncio
    async def test_max_depth_exceeded_returns_failure(self):
        strategy = DelegationChainStrategy(max_depth=2)
        agents = [_agent("coord"), _agent("spec")]

        result = await strategy.execute(agents, {"task": "x", "_delegation_depth": 3})

        assert result.success is False
        assert "Max delegation depth" in result.errors[0]

    @pytest.mark.asyncio
    async def test_no_agents_returns_failure(self):
        strategy = DelegationChainStrategy()
        result = await strategy.execute([], {"task": "x"})
        assert result.success is False
        assert "No agents provided" in result.errors[0]

    @pytest.mark.asyncio
    async def test_successful_delegation_with_specialist(self):
        strategy = DelegationChainStrategy(max_depth=3)
        coordinator = _agent("coord", "coordinator")
        specialist = _agent("spec1", "security")
        agents = [coordinator, specialist]

        plan_response = {
            "content": '{"sub_tasks": [{"specialist_id": "spec1", "task": "check security"}]}'
        }
        specialist_response = _llm_response("security ok")
        synthesis_response = _llm_response("all good")

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(
                side_effect=[plan_response, specialist_response, synthesis_response]
            )

            result = await strategy.execute(agents, {"task": "audit codebase"})

        assert result.success is True

    @pytest.mark.asyncio
    async def test_delegation_with_invalid_json_plan_uses_fallback(self):
        strategy = DelegationChainStrategy(max_depth=3)
        coordinator = _agent("coord")
        specialist = _agent("spec1")
        agents = [coordinator, specialist]

        # Plan response returns non-JSON → fallback used
        plan_response = {"content": "NOT JSON AT ALL"}
        specialist_response = _llm_response("done")
        synthesis_response = _llm_response("synthesized")

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(
                side_effect=[plan_response, specialist_response, synthesis_response]
            )

            result = await strategy.execute(agents, {"task": "do work"})

        # Fallback assigns to first specialist
        assert result.success is True

    @pytest.mark.asyncio
    async def test_delegation_unknown_specialist_skipped(self):
        strategy = DelegationChainStrategy(max_depth=3)
        coordinator = _agent("coord")
        # No specialists provided
        agents = [coordinator]

        # Plan references a specialist that doesn't exist
        plan_response = {"content": '{"sub_tasks": [{"specialist_id": "ghost", "task": "haunt"}]}'}
        synthesis_response = _llm_response("synthesized")

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(side_effect=[plan_response, synthesis_response])

            result = await strategy.execute(agents, {"task": "x"})

        assert result.success is True
        assert result.outputs == []  # No specialist found → no results

    @pytest.mark.asyncio
    async def test_delegation_exception_returns_failure(self):
        strategy = DelegationChainStrategy(max_depth=3)
        coordinator = _agent("coord")
        specialist = _agent("spec1")

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(side_effect=RuntimeError("LLM down"))

            result = await strategy.execute([coordinator, specialist], {"task": "x"})

        assert result.success is False
        assert "LLM down" in result.errors[0]

    @pytest.mark.asyncio
    async def test_specialist_exception_returns_failed_agent_result(self):
        strategy = DelegationChainStrategy(max_depth=3)
        coordinator = _agent("coord")
        specialist = _agent("spec1")

        plan_response = {"content": '{"sub_tasks": [{"specialist_id": "spec1", "task": "work"}]}'}
        synthesis_response = _llm_response("ok")

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            # plan succeeds, specialist fails, synthesis succeeds
            mock_client.call = AsyncMock(
                side_effect=[plan_response, RuntimeError("spec failed"), synthesis_response]
            )

            result = await strategy.execute([coordinator, specialist], {"task": "x"})

        # The whole chain succeeds (error in specialist is captured in AgentResult)
        specialist_results = [r for r in result.outputs if not r.success]
        assert len(specialist_results) == 1

    @pytest.mark.asyncio
    async def test_synthesis_exception_returns_error_dict(self):
        strategy = DelegationChainStrategy(max_depth=3)
        coordinator = _agent("coord")
        specialist = _agent("spec1")

        plan_response = {"content": '{"sub_tasks": [{"specialist_id": "spec1", "task": "work"}]}'}
        specialist_response = _llm_response("ok")

        with patch("attune.models.LLMClient", create=True) as MockLLM:
            mock_client = MockLLM.return_value
            mock_client.call = AsyncMock(
                side_effect=[plan_response, specialist_response, RuntimeError("synthesis broke")]
            )

            result = await strategy.execute([coordinator, specialist], {"task": "x"})

        assert result.aggregated_output.get("synthesis") == "Synthesis failed"

    def test_find_specialist_returns_none_for_unknown_id(self):
        strategy = DelegationChainStrategy()
        agents = [_agent("a1"), _agent("a2")]
        result = strategy._find_specialist("ghost", agents)
        assert result is None

    def test_find_specialist_returns_matching_agent(self):
        strategy = DelegationChainStrategy()
        a2 = _agent("a2")
        result = strategy._find_specialist("a2", [_agent("a1"), a2])
        assert result is a2
