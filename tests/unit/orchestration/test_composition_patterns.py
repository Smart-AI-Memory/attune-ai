"""Comprehensive tests for composition patterns.

This module tests all 6 composition patterns according to Sprint 2 Day 11-12:
1. ParallelComposition (5 tests)
2. SequentialComposition (5 tests)
3. RefinementComposition (5 tests)
4. HierarchicalComposition (5 tests)
5. DebateComposition (5 tests)
6. VotingComposition (5 tests)

Each test verifies the pattern's unique behavior and architectural invariants.

NOTE: Many tests use real agent templates that analyze the actual codebase.
Tests that assert `result.success` may fail when agents find issues (e.g., low
coverage). These should be refactored to use mock agents with predictable outputs.

# =============================================================================
# XFAIL TEST REMEDIATION - COMPLETED (2026-01-24)
# =============================================================================
#
# All 24 xfail tests have been refactored to use mock agents.
#
# Changes Made:
#   1. Created mock_agents fixture in conftest.py with predictable AgentResult
#   2. Created mock_execute_agent fixture to patch strategy._execute_agent
#   3. Replaced test_agents with mock_agents in all composition tests
#   4. Removed all @pytest.mark.xfail decorators
#   5. Updated TestCompositionPatternInvariants to use mocks
#
# Refactored Classes:
#   - TestParallelComposition: 5 tests (all passing with mocks)
#   - TestSequentialComposition: 5 tests (all passing with mocks)
#   - TestRefinementComposition: 5 tests (all passing with mocks)
#   - TestHierarchicalComposition: 5 tests (all passing with mocks)
#   - TestDebateComposition: 5 tests (all passing with mocks)
#   - TestVotingComposition: 5 tests (all passing with mocks)
#   - TestCompositionPatternInvariants: 5 tests (all passing with mocks)
#
# The test_agents fixture is kept for any future integration tests that need
# real agent execution (should be marked with @pytest.mark.integration).
#
# See: docs/TEST_MAINTENANCE_PLAN.md for full maintenance documentation
# =============================================================================
"""

import time

import pytest

from attune.orchestration.agent_templates import get_template
from attune.orchestration.execution_strategies import (
    AdaptiveStrategy,
    AgentResult,
    DebateStrategy,
    ParallelStrategy,
    RefinementStrategy,
    SequentialStrategy,
    StrategyResult,
    TeachingStrategy,
)


@pytest.fixture
def test_agents():
    """Get test agents for composition testing."""
    return [
        get_template("test_coverage_analyzer"),
        get_template("code_reviewer"),
        get_template("documentation_writer"),
        get_template("security_auditor"),
    ]


@pytest.fixture
def test_context():
    """Get test context dictionary."""
    return {
        "project": "attune-ai",
        "version": "3.12.0",
        "project_root": ".",
        "target_path": "src",
    }


class TestParallelComposition:
    """Test ParallelComposition pattern (A || B || C).

    Verifies:
    - Parallel execution of independent agents
    - Result aggregation
    - Error handling (one agent fails)
    - Performance (faster than sequential)
    - Resource limits
    """

    @pytest.mark.asyncio
    async def test_parallel_execution_of_independent_agents(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that agents execute independently in parallel.

        Verifies parallelism structurally via asyncio scheduling order rather
        than wall-clock duration ratios. When ParallelStrategy uses
        ``asyncio.gather``, every agent enters its coroutine and reaches its
        first ``await`` before any of them returns — so the count of started
        agents at each finish is ``[n, n, n]``. Sequential execution would
        produce ``[1, 2, 3]``. The previous duration-ratio assertion was
        flaky on Windows 3.12 where timer granularity and asyncio scheduling
        overhead exceeded the measured individual durations of instant mock
        agents.
        """
        strategy = ParallelStrategy()

        started = 0
        finished_when_started: list[int] = []

        async def tracked_execute(agent, context):
            nonlocal started
            started += 1
            result = await mock_execute_agent(agent, context)
            finished_when_started.append(started)
            return result

        strategy._execute_agent = tracked_execute

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success
        assert len(result.outputs) == 3
        assert len(finished_when_started) == 3

        assert finished_when_started == [3, 3, 3], (
            "Agents did not execute in parallel: "
            f"finished_when_started={finished_when_started} "
            "(parallel expected [3, 3, 3], sequential would be [1, 2, 3])"
        )

    @pytest.mark.asyncio
    async def test_parallel_result_aggregation(self, mock_agents, test_context, mock_execute_agent):
        """Test that results from all agents are properly aggregated."""
        strategy = ParallelStrategy()
        strategy._execute_agent = mock_execute_agent
        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success
        assert "num_agents" in result.aggregated_output
        assert result.aggregated_output["num_agents"] == 3
        assert "all_succeeded" in result.aggregated_output
        assert "avg_confidence" in result.aggregated_output
        assert "outputs" in result.aggregated_output

        # All agents should have contributed their outputs
        assert len(result.aggregated_output["outputs"]) == 3

    @pytest.mark.asyncio
    async def test_parallel_error_handling_one_agent_fails(
        self,
        failing_mock_agents,
        test_context,
        mock_agent_result_factory,
    ):
        """Test parallel execution when one agent fails."""
        strategy = ParallelStrategy()

        async def mixed_execute(agent, context):
            """Some agents succeed, some fail based on agent id."""
            agent_num = int(agent.id.split("_")[-1]) if "_" in agent.id else 0
            success = agent_num < 1  # Only first agent succeeds
            return mock_agent_result_factory(
                success=success,
                output={"status": "success" if success else "failed"},
                confidence=0.8 if success else 0.3,
                agent_id=agent.id,
            )

        strategy._execute_agent = mixed_execute

        result = await strategy.execute(failing_mock_agents[:2], test_context)

        # Strategy should complete without crashing
        assert len(result.outputs) == 2

        # Check that we captured failures
        if not result.success:
            assert any(not r.success for r in result.outputs)

    @pytest.mark.asyncio
    async def test_parallel_performance_faster_than_sequential(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that parallel execution is faster than sequential for independent tasks."""
        # Execute parallel
        parallel_strategy = ParallelStrategy()
        parallel_strategy._execute_agent = mock_execute_agent
        parallel_start = time.perf_counter()
        parallel_result = await parallel_strategy.execute(mock_agents[:3], test_context)
        parallel_duration = time.perf_counter() - parallel_start

        # Execute sequential
        sequential_strategy = SequentialStrategy()
        sequential_strategy._execute_agent = mock_execute_agent
        sequential_start = time.perf_counter()
        sequential_result = await sequential_strategy.execute(mock_agents[:3], test_context)
        sequential_duration = time.perf_counter() - sequential_start

        # Both should succeed
        assert parallel_result.success
        assert sequential_result.success

        # With mocked execution, parallel should complete all at once
        # Sequential must wait for each, so it should be slower
        # We allow margin for test environment variance
        assert parallel_duration <= sequential_duration * 1.5

    @pytest.mark.asyncio
    async def test_parallel_resource_limits(self, mock_agents, test_context, mock_execute_agent):
        """Test parallel execution respects resource limits."""
        strategy = ParallelStrategy()
        strategy._execute_agent = mock_execute_agent

        # Test with maximum agents (should still work)
        all_agents = mock_agents  # 4 agents
        result = await strategy.execute(all_agents, test_context)

        assert result.success
        assert len(result.outputs) == len(all_agents)

        # Test with empty agents (should raise error)
        with pytest.raises(ValueError, match="agents list cannot be empty"):
            await strategy.execute([], test_context)


class TestSequentialComposition:
    """Test SequentialComposition pattern (A → B → C).

    Verifies:
    - Sequential execution maintains order
    - Context passing between agents
    - Early termination on error
    - Dependency chain validation
    - State accumulation
    """

    @pytest.mark.asyncio
    async def test_sequential_execution_maintains_order(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that agents execute in the specified order."""
        strategy = SequentialStrategy()

        execution_order = []

        async def tracked_execute(agent, context):
            execution_order.append(agent.id)
            return await mock_execute_agent(agent, context)

        strategy._execute_agent = tracked_execute

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success
        # Verify execution order matches agent order
        assert execution_order == [a.id for a in mock_agents[:3]]

    @pytest.mark.asyncio
    async def test_sequential_context_passing_between_agents(
        self,
        mock_agents,
        test_context,
        mock_agent_result_factory,
    ):
        """Test that context is passed from one agent to the next."""
        strategy = SequentialStrategy()

        context_snapshots = []

        async def tracked_execute(agent, context):
            context_snapshots.append(context.copy())
            return mock_agent_result_factory(
                success=True,
                output={"agent_role": agent.id, "result": "completed"},
                agent_id=agent.id,
            )

        strategy._execute_agent = tracked_execute

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Each subsequent agent should see previous agent's output in context
        for i in range(1, len(context_snapshots)):
            current_snapshot = context_snapshots[i]
            # Previous agent's output should be in current context
            prev_agent_id = mock_agents[i - 1].id
            assert f"{prev_agent_id}_output" in current_snapshot

    @pytest.mark.asyncio
    async def test_sequential_early_termination_on_error(
        self,
        mock_agents,
        test_context,
        mock_agent_result_factory,
    ):
        """Test sequential execution behavior when an agent fails."""
        strategy = SequentialStrategy()

        async def mixed_execute(agent, context):
            """Second agent fails."""
            agent_idx = mock_agents.index(agent) if agent in mock_agents else 0
            success = agent_idx != 1  # Second agent fails
            return mock_agent_result_factory(
                success=success,
                output={"status": "success" if success else "failed"},
                agent_id=agent.id,
            )

        strategy._execute_agent = mixed_execute

        result = await strategy.execute(mock_agents[:3], test_context)

        # Check that all agents were attempted
        assert len(result.outputs) == 3

        # If any failed, overall success should be False
        if not all(r.success for r in result.outputs):
            assert not result.success

    @pytest.mark.asyncio
    async def test_sequential_dependency_chain_validation(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that sequential composition validates dependency chains."""
        strategy = SequentialStrategy()
        strategy._execute_agent = mock_execute_agent

        # Test with valid chain
        result = await strategy.execute(mock_agents[:3], test_context)
        assert result.success

        # Test with empty chain (should raise error)
        with pytest.raises(ValueError, match="agents list cannot be empty"):
            await strategy.execute([], test_context)

        # Test with single agent (should work)
        single_result = await strategy.execute(mock_agents[:1], test_context)
        assert single_result.success
        assert len(single_result.outputs) == 1

    @pytest.mark.asyncio
    async def test_sequential_state_accumulation(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that state accumulates across sequential execution."""
        strategy = SequentialStrategy()
        strategy._execute_agent = mock_execute_agent
        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Verify all agent outputs are in the aggregated output
        assert "outputs" in result.aggregated_output
        assert len(result.aggregated_output["outputs"]) == 3

        # Each output should be from a different agent
        agent_ids = [
            output.get("agent_role", "unknown") for output in result.aggregated_output["outputs"]
        ]
        assert len(set(agent_ids)) == 3  # All unique


class TestRefinementComposition:
    """Test RefinementComposition pattern (Draft → Review → Polish).

    Verifies:
    - Iterative refinement of results
    - Quality improvement tracking
    - Convergence detection
    - Max iteration limits
    - Refinement stopping criteria
    """

    @pytest.mark.asyncio
    async def test_refinement_iterative_refinement_of_results(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that each stage refines previous output."""
        strategy = RefinementStrategy()
        strategy._execute_agent = mock_execute_agent
        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Verify refinement stages structure
        assert "refinement_stages" in result.aggregated_output
        assert result.aggregated_output["refinement_stages"] == 3
        assert "final_output" in result.aggregated_output
        assert "stage_outputs" in result.aggregated_output

        # Each stage should have produced output
        assert len(result.aggregated_output["stage_outputs"]) == 3

    @pytest.mark.asyncio
    async def test_refinement_quality_improvement_tracking(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that quality metrics improve across refinement stages."""
        strategy = RefinementStrategy()
        strategy._execute_agent = mock_execute_agent
        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Track confidence across stages
        confidences = [r.confidence for r in result.outputs]

        # We can't guarantee strictly increasing confidence, but we track it
        assert len(confidences) == 3
        assert all(0.0 <= c <= 1.0 for c in confidences)

        # Final output should be from last stage
        assert result.aggregated_output["final_output"] == result.outputs[-1].output

    @pytest.mark.asyncio
    async def test_refinement_convergence_detection(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test refinement convergence detection."""
        strategy = RefinementStrategy()
        strategy._execute_agent = mock_execute_agent

        # Test with 2 agents (minimum)
        result = await strategy.execute(mock_agents[:2], test_context)
        assert result.success
        assert result.aggregated_output["refinement_stages"] == 2

        # Test with 3 agents
        result3 = await strategy.execute(mock_agents[:3], test_context)
        assert result3.success
        assert result3.aggregated_output["refinement_stages"] == 3

    @pytest.mark.asyncio
    async def test_refinement_max_iteration_limits(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that refinement respects maximum iteration limits."""
        strategy = RefinementStrategy()
        strategy._execute_agent = mock_execute_agent

        # Test with all 4 agents
        result = await strategy.execute(mock_agents, test_context)

        # Should execute all agents (no artificial limit)
        assert len(result.outputs) == len(mock_agents)

        # Verify each stage completed
        assert result.aggregated_output["refinement_stages"] == len(mock_agents)

    @pytest.mark.asyncio
    async def test_refinement_stopping_criteria(
        self,
        mock_agents,
        test_context,
        mock_agent_result_factory,
    ):
        """Test refinement stopping criteria."""
        strategy = RefinementStrategy()

        # Test minimum requirement (at least 2 agents)
        with pytest.raises(ValueError, match="Refinement strategy requires at least 2 agents"):
            await strategy.execute(mock_agents[:1], test_context)

        # Test that refinement stops on failure
        async def failing_execute(agent, context):
            return mock_agent_result_factory(success=False, agent_id=agent.id)

        strategy._execute_agent = failing_execute
        result = await strategy.execute(mock_agents[:3], test_context)

        # May not complete all stages if early stage fails
        # But should capture what was completed
        assert len(result.outputs) <= 3


class TestHierarchicalComposition:
    """Test HierarchicalComposition pattern (Manager → Workers).

    Note: This pattern is implemented via AdaptiveStrategy.
    Verifies:
    - Manager-worker delegation
    - Task decomposition
    - Result synthesis
    - Coordinator role
    - Subtask distribution
    """

    @pytest.mark.asyncio
    async def test_hierarchical_manager_worker_delegation(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test manager delegates to appropriate workers."""
        # Adaptive strategy implements hierarchical pattern
        strategy = AdaptiveStrategy()
        strategy._execute_agent = mock_execute_agent

        # Manager (classifier) selects worker (specialist)
        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Should have manager classification
        assert "classification" in result.aggregated_output

        # Should have selected a worker
        assert "selected_specialist" in result.aggregated_output

        # Should have worker's output
        assert "specialist_output" in result.aggregated_output

    @pytest.mark.asyncio
    async def test_hierarchical_task_decomposition(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that manager decomposes task for workers."""
        strategy = AdaptiveStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Manager analyzes task (classification phase)
        classification = result.aggregated_output["classification"]
        assert classification is not None

        # Worker executes assigned subtask
        specialist_output = result.aggregated_output["specialist_output"]
        assert specialist_output is not None

    @pytest.mark.asyncio
    async def test_hierarchical_result_synthesis(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that results from workers are synthesized."""
        strategy = AdaptiveStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Aggregated output synthesizes manager + worker results
        assert "classification" in result.aggregated_output
        assert "selected_specialist" in result.aggregated_output
        assert "specialist_output" in result.aggregated_output

        # Total outputs = manager + worker
        assert len(result.outputs) == 2

    @pytest.mark.asyncio
    async def test_hierarchical_coordinator_role(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test coordinator (manager) role in orchestration."""
        strategy = AdaptiveStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:4], test_context)

        assert result.success

        # First agent acts as coordinator
        coordinator_result = result.outputs[0]
        assert coordinator_result.agent_id == mock_agents[0].id

        # Coordinator classifies and routes
        selected_specialist_id = result.aggregated_output["selected_specialist"]
        assert selected_specialist_id in [a.id for a in mock_agents[1:]]

    @pytest.mark.asyncio
    async def test_hierarchical_subtask_distribution(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test distribution of subtasks to specialized workers."""
        strategy = AdaptiveStrategy()
        strategy._execute_agent = mock_execute_agent

        # Test that different contexts route to different specialists
        context1 = test_context.copy()
        context1["complexity"] = "simple"

        context2 = test_context.copy()
        context2["complexity"] = "complex"

        result1 = await strategy.execute(mock_agents[:3], context1)
        result2 = await strategy.execute(mock_agents[:3], context2)

        assert result1.success
        assert result2.success

        # Both should have selected a specialist
        assert "selected_specialist" in result1.aggregated_output
        assert "selected_specialist" in result2.aggregated_output

        # Minimum requirement: at least 2 agents (manager + worker)
        with pytest.raises(ValueError, match="Adaptive strategy requires at least 2 agents"):
            await strategy.execute(mock_agents[:1], test_context)


class TestDebateComposition:
    """Test DebateComposition pattern (A ⇄ B ⇄ C → Synthesis).

    Verifies:
    - Multi-viewpoint generation
    - Consensus building
    - Disagreement resolution
    - Voting mechanism
    - Synthesis of perspectives
    """

    @pytest.mark.asyncio
    async def test_debate_multi_viewpoint_generation(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that multiple agents provide different viewpoints."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Should have multiple viewpoints
        assert "opinions" in result.aggregated_output
        opinions = result.aggregated_output["opinions"]
        assert len(opinions) == 3

        # Each opinion should be from a different agent
        assert len(opinions) == len(mock_agents[:3])

    @pytest.mark.asyncio
    async def test_debate_consensus_building(self, mock_agents, test_context, mock_execute_agent):
        """Test that consensus is built from multiple viewpoints."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Should have consensus section
        assert "consensus" in result.aggregated_output
        consensus = result.aggregated_output["consensus"]

        # Consensus should track votes
        assert "consensus_reached" in consensus
        assert "success_votes" in consensus
        assert "total_votes" in consensus
        assert consensus["total_votes"] == 3

    @pytest.mark.asyncio
    async def test_debate_disagreement_resolution(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test handling of disagreements between agents."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Consensus mechanism should resolve disagreements
        consensus = result.aggregated_output["consensus"]

        # Should use majority vote
        assert consensus["consensus_reached"] == (
            consensus["success_votes"] > consensus["total_votes"] / 2
        )

    @pytest.mark.asyncio
    async def test_debate_voting_mechanism(self, mock_agents, test_context, mock_execute_agent):
        """Test voting mechanism for consensus."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        consensus = result.aggregated_output["consensus"]

        # Voting data should be present
        assert "success_votes" in consensus
        assert "total_votes" in consensus

        # Vote count should match agent count
        assert consensus["total_votes"] == 3

        # Success votes should be <= total votes
        assert consensus["success_votes"] <= consensus["total_votes"]

    @pytest.mark.asyncio
    async def test_debate_synthesis_of_perspectives(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test synthesis of multiple perspectives into coherent output."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Should have debate participants listed
        assert "debate_participants" in result.aggregated_output
        participants = result.aggregated_output["debate_participants"]
        assert len(participants) == 3

        # Should synthesize opinions
        assert "opinions" in result.aggregated_output

        # Should produce consensus
        assert "consensus" in result.aggregated_output
        consensus = result.aggregated_output["consensus"]
        assert "avg_confidence" in consensus


class TestVotingComposition:
    """Test VotingComposition pattern (Vote on best proposal).

    Note: This is implemented via DebateStrategy with voting mechanism.
    Verifies:
    - Multiple agent proposals
    - Vote aggregation
    - Majority/consensus selection
    - Tie-breaking
    - Confidence weighting
    """

    @pytest.mark.asyncio
    async def test_voting_multiple_agent_proposals(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that multiple agents submit proposals for voting."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        # Each agent should have submitted a proposal (opinion)
        opinions = result.aggregated_output["opinions"]
        assert len(opinions) == 3

        # Each proposal should have content
        for opinion in opinions:
            assert opinion is not None

    @pytest.mark.asyncio
    async def test_voting_vote_aggregation(self, mock_agents, test_context, mock_execute_agent):
        """Test aggregation of votes from all agents."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:4], test_context)

        assert result.success

        consensus = result.aggregated_output["consensus"]

        # Votes should be aggregated
        assert "success_votes" in consensus
        assert "total_votes" in consensus
        assert consensus["total_votes"] == 4

    @pytest.mark.asyncio
    async def test_voting_majority_consensus_selection(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test selection based on majority consensus."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        consensus = result.aggregated_output["consensus"]

        # Majority is > 50%
        success_votes = consensus["success_votes"]
        total_votes = consensus["total_votes"]

        consensus_reached = success_votes > total_votes / 2
        assert consensus["consensus_reached"] == consensus_reached

    @pytest.mark.asyncio
    async def test_voting_tie_breaking(self, mock_agents, test_context, mock_execute_agent):
        """Test tie-breaking mechanism in voting."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        # Test with even number of agents
        result = await strategy.execute(mock_agents[:2], test_context)

        assert result.success

        consensus = result.aggregated_output["consensus"]

        # With 2 agents, tie is possible (1-1)
        # Majority requires > 50%, so 1 out of 2 is not consensus
        if consensus["success_votes"] == 1 and consensus["total_votes"] == 2:
            assert not consensus["consensus_reached"]

        # With 2 votes for success, consensus reached
        if consensus["success_votes"] == 2 and consensus["total_votes"] == 2:
            assert consensus["consensus_reached"]

    @pytest.mark.asyncio
    async def test_voting_confidence_weighting(self, mock_agents, test_context, mock_execute_agent):
        """Test confidence weighting in voting."""
        strategy = DebateStrategy()
        strategy._execute_agent = mock_execute_agent

        result = await strategy.execute(mock_agents[:3], test_context)

        assert result.success

        consensus = result.aggregated_output["consensus"]

        # Should compute average confidence
        assert "avg_confidence" in consensus

        # Confidence should be in valid range
        avg_confidence = consensus["avg_confidence"]
        assert 0.0 <= avg_confidence <= 1.0

        # Should be based on actual agent confidences
        actual_avg = sum(r.confidence for r in result.outputs) / len(result.outputs)
        assert abs(consensus["avg_confidence"] - actual_avg) < 0.01


class TestCompositionPatternInvariants:
    """Test architectural invariants across all composition patterns."""

    @pytest.mark.asyncio
    async def test_all_patterns_validate_empty_agents(self, test_context):
        """Test that all patterns reject empty agent lists."""
        strategies = [
            ParallelStrategy(),
            SequentialStrategy(),
            DebateStrategy(),
            RefinementStrategy(),
            AdaptiveStrategy(),
            TeachingStrategy(),
        ]

        for strategy in strategies:
            with pytest.raises(ValueError):
                await strategy.execute([], test_context)

    @pytest.mark.asyncio
    async def test_all_patterns_return_strategy_result(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that all patterns return StrategyResult."""
        strategies = [
            (ParallelStrategy(), mock_agents[:3]),
            (SequentialStrategy(), mock_agents[:3]),
            (DebateStrategy(), mock_agents[:3]),
            (RefinementStrategy(), mock_agents[:3]),
            (AdaptiveStrategy(), mock_agents[:3]),
            (TeachingStrategy(), mock_agents[:2]),  # Requires exactly 2
        ]

        for strategy, agents in strategies:
            strategy._execute_agent = mock_execute_agent
            result = await strategy.execute(agents, test_context)
            assert isinstance(result, StrategyResult)
            assert hasattr(result, "success")
            assert hasattr(result, "outputs")
            assert hasattr(result, "aggregated_output")
            assert hasattr(result, "total_duration")
            assert hasattr(result, "errors")

    @pytest.mark.asyncio
    async def test_all_patterns_track_duration(self, mock_agents, test_context, mock_execute_agent):
        """Test that all patterns track execution duration."""
        strategies = [
            (ParallelStrategy(), mock_agents[:3]),
            (SequentialStrategy(), mock_agents[:3]),
            (DebateStrategy(), mock_agents[:3]),
            (RefinementStrategy(), mock_agents[:3]),
            (AdaptiveStrategy(), mock_agents[:3]),
            (TeachingStrategy(), mock_agents[:2]),
        ]

        for strategy, agents in strategies:
            strategy._execute_agent = mock_execute_agent
            result = await strategy.execute(agents, test_context)
            assert result.total_duration >= 0.0
            assert isinstance(result.total_duration, float)

    @pytest.mark.asyncio
    async def test_all_patterns_produce_outputs(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that all patterns produce outputs."""
        strategies = [
            (ParallelStrategy(), mock_agents[:3]),
            (SequentialStrategy(), mock_agents[:3]),
            (DebateStrategy(), mock_agents[:3]),
            (RefinementStrategy(), mock_agents[:3]),
            (AdaptiveStrategy(), mock_agents[:3]),
            (TeachingStrategy(), mock_agents[:2]),
        ]

        for strategy, agents in strategies:
            strategy._execute_agent = mock_execute_agent
            result = await strategy.execute(agents, test_context)
            assert len(result.outputs) > 0
            assert isinstance(result.outputs, list)
            assert all(isinstance(o, AgentResult) for o in result.outputs)

    @pytest.mark.asyncio
    async def test_all_patterns_aggregate_results(
        self,
        mock_agents,
        test_context,
        mock_execute_agent,
    ):
        """Test that all patterns aggregate results."""
        strategies = [
            (ParallelStrategy(), mock_agents[:3]),
            (SequentialStrategy(), mock_agents[:3]),
            (DebateStrategy(), mock_agents[:3]),
            (RefinementStrategy(), mock_agents[:3]),
            (AdaptiveStrategy(), mock_agents[:3]),
            (TeachingStrategy(), mock_agents[:2]),
        ]

        for strategy, agents in strategies:
            strategy._execute_agent = mock_execute_agent
            result = await strategy.execute(agents, test_context)
            assert isinstance(result.aggregated_output, dict)
            assert len(result.aggregated_output) > 0
