"""Pytest fixtures for orchestration tests.

Provides mock agents for testing composition patterns without real agent execution.
"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from attune.orchestration.execution_strategies import AgentResult


@pytest.fixture
def mock_agent_result_factory():
    """Factory for creating mock agent results with custom values.

    Usage:
        result = mock_agent_result_factory(success=True, confidence=0.9)
    """

    def _factory(
        success: bool = True,
        output: dict | None = None,
        confidence: float = 0.85,
        agent_id: str = "mock_agent",
        duration_seconds: float = 0.1,
    ) -> AgentResult:
        return AgentResult(
            success=success,
            output=output or {"analysis": "Mock analysis", "score": 0.85},
            confidence=confidence,
            agent_id=agent_id,
            duration_seconds=duration_seconds,
        )

    return _factory


@pytest.fixture
def mock_agent_result(mock_agent_result_factory):
    """Create a default successful mock agent result."""
    return mock_agent_result_factory()


@pytest.fixture
def mock_agents(mock_agent_result_factory):
    """Create mock agents that return predictable results.

    Returns 4 mock agents suitable for testing composition patterns:
    - test_coverage_analyzer (mock)
    - code_reviewer (mock)
    - documentation_writer (mock)
    - security_auditor (mock)

    Each agent returns a successful result with 0.85 confidence.

    Usage:
        async def test_parallel_execution(self, mock_agents, test_context):
            strategy = ParallelStrategy()
            result = await strategy.execute(mock_agents[:3], test_context)
            assert result.success  # Now predictable!
    """
    agent_configs = [
        ("test_coverage_analyzer", {"coverage": 85.0, "files_analyzed": 100}),
        ("code_reviewer", {"issues_found": 3, "severity": "low"}),
        ("documentation_writer", {"docs_generated": 5, "completeness": 0.9}),
        ("security_auditor", {"vulnerabilities": 0, "passed": True}),
    ]

    agents = []
    for agent_id, output in agent_configs:
        agent = Mock()
        agent.id = agent_id
        agent.role = agent_id.replace("_", " ").title()
        agent.description = f"Mock {agent_id} for testing"
        agent.capabilities = ["analysis"]

        # Create the result this agent will return
        result = mock_agent_result_factory(
            success=True,
            output=output,
            confidence=0.85,
            agent_id=agent_id,
            duration_seconds=0.1,
        )

        # Make execute return the result
        agent.execute = AsyncMock(return_value=result)
        agents.append(agent)

    return agents


@pytest.fixture
def failing_mock_agents(mock_agent_result_factory):
    """Create mock agents where some fail.

    Returns 4 agents: first 2 succeed, last 2 fail.
    Useful for testing error handling in composition patterns.
    """
    agents = []

    for i in range(4):
        agent = Mock()
        agent.id = f"agent_{i}"
        agent.role = f"Agent {i}"
        agent.capabilities = ["analysis"]

        success = i < 2  # First 2 succeed, last 2 fail
        result = mock_agent_result_factory(
            success=success,
            output={"status": "success" if success else "failed"},
            confidence=0.8 if success else 0.3,
            agent_id=f"agent_{i}",
        )

        agent.execute = AsyncMock(return_value=result)
        agents.append(agent)

    return agents


@pytest.fixture
def mock_execute_agent(monkeypatch, mock_agent_result_factory):
    """Fixture that provides a mock _execute_agent function.

    Patches ExecutionStrategy._execute_agent at the class level in addition
    to returning the standalone callable. The class-level patch is required
    for composing strategies (DebateStrategy creates an inner ParallelStrategy;
    the inner instance has no instance-level shadow and would otherwise fall
    through to the real _execute_agent and call subprocess pytest via
    RealCoverageAnalyzer).

    Usage:
        async def test_something(self, mock_execute_agent):
            strategy = ParallelStrategy()
            strategy._execute_agent = mock_execute_agent
            result = await strategy.execute(agents, context)
    """

    async def _mock_execute(agent, context):
        """Mock agent execution that returns predictable results."""
        # Small delay to simulate async execution
        await asyncio.sleep(0.01)
        return mock_agent_result_factory(
            success=True,
            output={"agent_role": agent.id, "analysis": f"Mock analysis from {agent.id}"},
            confidence=0.85,
            agent_id=agent.id,
            duration_seconds=0.01,
        )

    async def _mock_execute_method(self, agent, context):
        return await _mock_execute(agent, context)

    from attune.orchestration._strategies.base import ExecutionStrategy

    monkeypatch.setattr(ExecutionStrategy, "_execute_agent", _mock_execute_method)

    return _mock_execute


@pytest.fixture
def patch_strategy_execution(mock_execute_agent):
    """Context manager to patch strategy execution with mocks.

    Usage:
        async def test_something(self, patch_strategy_execution, mock_agents, test_context):
            strategy = ParallelStrategy()
            with patch_strategy_execution(strategy):
                result = await strategy.execute(mock_agents[:3], test_context)
            assert result.success
    """

    @asynccontextmanager
    async def _patcher(strategy):
        original = strategy._execute_agent
        strategy._execute_agent = mock_execute_agent
        try:
            yield strategy
        finally:
            strategy._execute_agent = original

    return _patcher
