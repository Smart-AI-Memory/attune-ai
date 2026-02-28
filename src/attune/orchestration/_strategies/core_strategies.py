"""Core execution strategies for agent composition.

This module contains the 6 foundational strategies for composing agents:
1. Sequential (A → B → C)
2. Parallel (A || B || C)
3. Debate (A ⇄ B ⇄ C → Synthesis)
4. Teaching (Junior → Expert validation)
5. Refinement (Draft → Review → Polish)
6. Adaptive (Classifier → Specialist)

Security:
    - All agent outputs validated before passing to next agent
    - No eval() or exec() usage
    - Timeout enforcement at strategy level

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from .base import ExecutionStrategy
from .data_classes import AgentResult, StrategyResult

if TYPE_CHECKING:
    from ..agent_templates import AgentTemplate

logger = logging.getLogger(__name__)


class SequentialStrategy(ExecutionStrategy):
    """Sequential composition (A → B → C).

    Executes agents one after another, passing results forward.
    Each agent receives output from previous agent in context.

    Use when:
        - Tasks must be done in order
        - Each step depends on previous results
        - Pipeline processing needed

    Example:
        Coverage Analyzer → Test Generator → Quality Validator

    """

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute agents sequentially.

        Args:
            agents: List of agents to execute in order
            context: Initial context

        Returns:
            StrategyResult with sequential execution results

        """
        if not agents:
            raise ValueError("agents list cannot be empty")

        logger.info(f"Sequential execution of {len(agents)} agents")

        results: list[AgentResult] = []
        current_context = context.copy()
        total_duration = 0.0

        for agent in agents:
            try:
                result = await self._execute_agent(agent, current_context)
                results.append(result)
                total_duration += result.duration_seconds

                # Pass output to next agent's context
                if result.success:
                    current_context[f"{agent.id}_output"] = result.output
                else:
                    logger.error(f"Agent {agent.id} failed: {result.error}")
                    # Continue or stop based on error handling policy
                    # For now: continue to next agent

            except Exception as e:
                logger.exception(f"Error executing agent {agent.id}: {e}")
                results.append(
                    AgentResult(
                        agent_id=agent.id,
                        success=False,
                        output={},
                        error=str(e),
                    ),
                )

        return StrategyResult(
            success=all(r.success for r in results),
            outputs=results,
            aggregated_output=self._aggregate_results(results),
            total_duration=total_duration,
            errors=[r.error for r in results if not r.success],
        )


class ParallelStrategy(ExecutionStrategy):
    """Parallel composition (A || B || C).

    Executes all agents simultaneously, aggregates results.
    Each agent receives same initial context.

    Use when:
        - Independent validations needed
        - Multi-perspective review desired
        - Time optimization important

    Example:
        Security Audit || Performance Check || Code Quality || Docs Check

    """

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute agents in parallel.

        Args:
            agents: List of agents to execute concurrently
            context: Initial context for all agents

        Returns:
            StrategyResult with parallel execution results

        """
        if not agents:
            raise ValueError("agents list cannot be empty")

        logger.info(f"Parallel execution of {len(agents)} agents")

        # Execute all agents concurrently
        tasks = [self._execute_agent(agent, context) for agent in agents]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.exception(f"Error in parallel execution: {e}")
            raise

        # Process results (handle exceptions)
        processed_results: list[AgentResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agents[i].id} raised exception: {result}")
                processed_results.append(
                    AgentResult(
                        agent_id=agents[i].id,
                        success=False,
                        output={},
                        error=str(result),
                    ),
                )
            else:
                # Type checker doesn't know we already filtered out exceptions
                assert isinstance(result, AgentResult)
                processed_results.append(result)

        total_duration = max((r.duration_seconds for r in processed_results), default=0.0)

        return StrategyResult(
            success=all(r.success for r in processed_results),
            outputs=processed_results,
            aggregated_output=self._aggregate_results(processed_results),
            total_duration=total_duration,
            errors=[r.error for r in processed_results if not r.success],
        )


class DebateStrategy(ExecutionStrategy):
    """Debate/Consensus composition (A ⇄ B ⇄ C → Synthesis).

    Agents provide independent opinions, then a synthesizer
    aggregates and resolves conflicts.

    Use when:
        - Multiple expert opinions needed
        - Architecture decisions require debate
        - Tradeoff analysis needed

    Example:
        Architect(scale) || Architect(cost) || Architect(simplicity) → Synthesizer

    """

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute debate pattern.

        Args:
            agents: List of agents to debate (recommend 2-4)
            context: Initial context

        Returns:
            StrategyResult with synthesized consensus

        """
        if not agents:
            raise ValueError("agents list cannot be empty")

        if len(agents) < 2:
            logger.warning("Debate pattern works best with 2+ agents")

        logger.info(f"Debate execution with {len(agents)} agents")

        # Phase 1: Parallel execution for independent opinions
        parallel_strategy = ParallelStrategy()
        phase1_result = await parallel_strategy.execute(agents, context)

        # Phase 2: Synthesis (simplified - no actual synthesizer agent)
        # In production: would use dedicated synthesizer agent
        synthesis = {
            "debate_participants": [r.agent_id for r in phase1_result.outputs],
            "opinions": [r.output for r in phase1_result.outputs],
            "consensus": self._synthesize_opinions(phase1_result.outputs),
        }

        return StrategyResult(
            success=phase1_result.success,
            outputs=phase1_result.outputs,
            aggregated_output=synthesis,
            total_duration=phase1_result.total_duration,
            errors=phase1_result.errors,
        )

    def _synthesize_opinions(self, results: list[AgentResult]) -> dict[str, Any]:
        """Synthesize multiple agent opinions into consensus.

        Args:
            results: Agent results to synthesize

        Returns:
            Synthesized consensus

        """
        # Simplified synthesis: majority vote on success
        success_votes = sum(1 for r in results if r.success)
        consensus_reached = success_votes > len(results) / 2

        return {
            "consensus_reached": consensus_reached,
            "success_votes": success_votes,
            "total_votes": len(results),
            "avg_confidence": (
                sum(r.confidence for r in results) / len(results) if results else 0.0
            ),
        }


class TeachingStrategy(ExecutionStrategy):
    """Teaching/Validation (Junior → Expert Review).

    Junior agent attempts task (cheap tier), expert validates.
    If validation fails, expert takes over.

    Use when:
        - Cost-effective generation desired
        - Quality assurance critical
        - Simple tasks with review needed

    Example:
        Junior Writer(CHEAP) → Quality Gate → (pass ? done : Expert Review(CAPABLE))

    """

    def __init__(self, quality_threshold: float = 0.7):
        """Initialize teaching strategy.

        Args:
            quality_threshold: Minimum confidence for junior to pass (0-1)

        """
        self.quality_threshold = quality_threshold

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute teaching pattern.

        Args:
            agents: [junior_agent, expert_agent] (exactly 2)
            context: Initial context

        Returns:
            StrategyResult with teaching outcome

        """
        if len(agents) != 2:
            raise ValueError("Teaching strategy requires exactly 2 agents")

        junior, expert = agents
        logger.info(f"Teaching: {junior.id} → {expert.id} validation")

        results: list[AgentResult] = []
        total_duration = 0.0

        # Phase 1: Junior attempt
        junior_result = await self._execute_agent(junior, context)
        results.append(junior_result)
        total_duration += junior_result.duration_seconds

        # Phase 2: Quality gate
        if junior_result.success and junior_result.confidence >= self.quality_threshold:
            logger.info(f"Junior passed quality gate (confidence={junior_result.confidence:.2f})")
            aggregated = {"outcome": "junior_success", "junior_output": junior_result.output}
        else:
            logger.info(
                f"Junior failed quality gate, expert taking over "
                f"(confidence={junior_result.confidence:.2f})",
            )

            # Phase 3: Expert takeover
            expert_context = context.copy()
            expert_context["junior_attempt"] = junior_result.output
            expert_result = await self._execute_agent(expert, expert_context)
            results.append(expert_result)
            total_duration += expert_result.duration_seconds

            aggregated = {
                "outcome": "expert_takeover",
                "junior_output": junior_result.output,
                "expert_output": expert_result.output,
            }

        return StrategyResult(
            success=all(r.success for r in results),
            outputs=results,
            aggregated_output=aggregated,
            total_duration=total_duration,
            errors=[r.error for r in results if not r.success],
        )


class RefinementStrategy(ExecutionStrategy):
    """Progressive Refinement (Draft → Review → Polish).

    Iterative improvement through multiple quality levels.
    Each agent refines output from previous stage.

    Use when:
        - Iterative improvement needed
        - Quality ladder desired
        - Multi-stage refinement beneficial

    Example:
        Drafter(CHEAP) → Reviewer(CAPABLE) → Polisher(PREMIUM)

    """

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute refinement pattern.

        Args:
            agents: [drafter, reviewer, polisher] (3+ agents)
            context: Initial context

        Returns:
            StrategyResult with refined output

        """
        if len(agents) < 2:
            raise ValueError("Refinement strategy requires at least 2 agents")

        logger.info(f"Refinement with {len(agents)} stages")

        results: list[AgentResult] = []
        current_context = context.copy()
        total_duration = 0.0

        for i, agent in enumerate(agents):
            stage_name = f"stage_{i + 1}"
            logger.info(f"Refinement {stage_name}: {agent.id}")

            result = await self._execute_agent(agent, current_context)
            results.append(result)
            total_duration += result.duration_seconds

            if result.success:
                # Pass refined output to next stage
                current_context[f"{stage_name}_output"] = result.output
                current_context["previous_output"] = result.output
            else:
                logger.error(f"Refinement stage {i + 1} failed: {result.error}")
                break  # Stop refinement on failure

        # Final output is from last successful stage
        final_output = results[-1].output if results[-1].success else {}

        return StrategyResult(
            success=all(r.success for r in results),
            outputs=results,
            aggregated_output={
                "refinement_stages": len(results),
                "final_output": final_output,
                "stage_outputs": [r.output for r in results],
            },
            total_duration=total_duration,
            errors=[r.error for r in results if not r.success],
        )


class AdaptiveStrategy(ExecutionStrategy):
    """Adaptive Routing (Classifier → Specialist).

    Classifier assesses task complexity, routes to appropriate specialist.
    Right-sizing: match agent tier to task needs.

    Use when:
        - Variable task complexity
        - Cost optimization desired
        - Right-sizing important

    Example:
        Classifier(CHEAP) → route(simple|moderate|complex) → Specialist(tier)

    """

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute adaptive routing pattern.

        Args:
            agents: [classifier, *specialists] (2+ agents)
            context: Initial context

        Returns:
            StrategyResult with routed execution

        """
        if len(agents) < 2:
            raise ValueError("Adaptive strategy requires at least 2 agents")

        classifier = agents[0]
        specialists = agents[1:]

        logger.info(f"Adaptive: {classifier.id} → {len(specialists)} specialists")

        results: list[AgentResult] = []
        total_duration = 0.0

        # Phase 1: Classification
        classifier_result = await self._execute_agent(classifier, context)
        results.append(classifier_result)
        total_duration += classifier_result.duration_seconds

        if not classifier_result.success:
            logger.error("Classifier failed, defaulting to first specialist")
            selected_specialist = specialists[0]
        # Phase 2: Route to specialist based on classification
        # Simplified: select based on confidence score
        elif classifier_result.confidence > 0.8:
            # High confidence → simple task → cheap specialist
            selected_specialist = min(
                specialists,
                key=lambda s: {
                    "CHEAP": 0,
                    "CAPABLE": 1,
                    "PREMIUM": 2,
                }.get(s.tier_preference, 1),
            )
        else:
            # Low confidence → complex task → premium specialist
            selected_specialist = max(
                specialists,
                key=lambda s: {
                    "CHEAP": 0,
                    "CAPABLE": 1,
                    "PREMIUM": 2,
                }.get(s.tier_preference, 1),
            )

        logger.info(f"Routed to specialist: {selected_specialist.id}")

        # Phase 3: Execute selected specialist
        specialist_context = context.copy()
        specialist_context["classification"] = classifier_result.output
        specialist_result = await self._execute_agent(selected_specialist, specialist_context)
        results.append(specialist_result)
        total_duration += specialist_result.duration_seconds

        return StrategyResult(
            success=all(r.success for r in results),
            outputs=results,
            aggregated_output={
                "classification": classifier_result.output,
                "selected_specialist": selected_specialist.id,
                "specialist_output": specialist_result.output,
            },
            total_duration=total_duration,
            errors=[r.error for r in results if not r.success],
        )
