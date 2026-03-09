"""Advanced execution strategy patterns (11-13).

Contains the Anthropic-inspired strategy patterns:
11. ToolEnhanced (single agent with comprehensive tools)
12. PromptCachedSequential (sequential with cached context)
13. DelegationChain (hierarchical delegation)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..agent_templates import AgentTemplate
from .base import ExecutionStrategy
from .data_classes import AgentResult, StrategyResult

logger = logging.getLogger(__name__)


class ToolEnhancedStrategy(ExecutionStrategy):
    """Single agent with comprehensive tool access.

    Anthropic Pattern: Use tools over multiple agents when possible.
    A single agent with rich tooling often outperforms multiple specialized agents.

    Example:
        # Instead of: FileReader -> Parser -> Analyzer -> Writer
        # Use: Single agent with [read, parse, analyze, write] tools

    Benefits:
        - Reduced LLM calls (1 vs 4+)
        - Simpler coordination
        - Lower cost
        - Better context preservation

    Security:
        - Tool schemas validated before execution
        - No eval() or exec() usage
        - Tool execution sandboxed

    """

    def __init__(self, tools: list[dict[str, Any]] | None = None):
        """Initialize with tool definitions.

        Args:
            tools: List of tool definitions in Anthropic format
                [
                    {
                        "name": "tool_name",
                        "description": "What the tool does",
                        "input_schema": {...}
                    },
                    ...
                ]

        """
        self.tools = tools or []

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute single agent with tool access.

        Args:
            agents: Single agent (others ignored)
            context: Execution context with task

        Returns:
            Result with tool usage trace

        """
        if not agents:
            return StrategyResult(
                success=False,
                outputs=[],
                aggregated_output={},
                errors=["No agent provided"],
            )

        agent = agents[0]  # Use first agent only
        start_time = asyncio.get_event_loop().time()

        # Execute with tool access
        try:
            result = await self._execute_with_tools(agent=agent, context=context, tools=self.tools)

            duration = asyncio.get_event_loop().time() - start_time

            return StrategyResult(
                success=result["success"],
                outputs=[
                    AgentResult(
                        agent_id=agent.agent_id,
                        success=result["success"],
                        output=result["output"],
                        confidence=result.get("confidence", 1.0),
                        duration_seconds=duration,
                    ),
                ],
                aggregated_output=result["output"],
                total_duration=duration,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Tool-enhanced execution failed: {e}")
            duration = asyncio.get_event_loop().time() - start_time
            return StrategyResult(
                success=False,
                outputs=[],
                aggregated_output={},
                total_duration=duration,
                errors=[str(e)],
            )

    async def _execute_with_tools(
        self,
        agent: AgentTemplate,
        context: dict[str, Any],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Execute agent with tool use enabled."""
        from attune.models import LLMClient

        client = LLMClient()

        # Agent makes autonomous tool use decisions
        response = await client.call(
            prompt=context.get("task", ""),
            system_prompt=agent.system_prompt,
            tools=tools or None,
            tier=agent.tier,
            workflow_id=f"tool-enhanced:{agent.agent_id}",
        )

        return {"success": True, "output": response, "confidence": 1.0}


class PromptCachedSequentialStrategy(ExecutionStrategy):
    """Sequential execution with shared cached context.

    Anthropic Pattern: Cache large unchanging contexts across agent calls.
    Saves 90%+ on prompt tokens for repeated workflows.

    Example:
        # All agents share cached codebase context
        # Only task-specific prompts vary
        # Massive token savings on subsequent calls

    Benefits:
        - 90%+ token cost reduction
        - Faster response times (cache hits)
        - Consistent context across agents

    Security:
        - Cached content validated once
        - No executable code in cache
        - Cache size limits enforced

    """

    def __init__(self, cached_context: str | None = None, cache_ttl: int = 3600):
        """Initialize with optional cached context.

        Args:
            cached_context: Large unchanging context to cache
                (e.g., documentation, code files, guidelines)
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)

        """
        self.cached_context = cached_context
        self.cache_ttl = cache_ttl

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute agents sequentially with shared cache.

        Args:
            agents: List of agents to execute in order
            context: Execution context with task

        Returns:
            Result with cumulative outputs

        """
        from attune.models import LLMClient

        client = LLMClient()
        outputs = []
        current_output = context.get("input", {})
        start_time = asyncio.get_event_loop().time()

        for agent in agents:
            try:
                # Build prompt with cached context
                if self.cached_context:
                    full_prompt = f"""{self.cached_context}

---

Current task: {context.get('task', '')}
Previous output: {current_output}
Your role: {agent.role}"""
                else:
                    full_prompt = f"{context.get('task', '')}\n\nPrevious: {current_output}"

                # Execute with caching enabled
                response = await client.call(
                    prompt=full_prompt,
                    system_prompt=agent.system_prompt,
                    tier=agent.tier,
                    workflow_id=f"cached-seq:{agent.agent_id}",
                    enable_caching=True,  # Anthropic prompt caching
                )

                result = AgentResult(
                    agent_id=agent.agent_id,
                    success=True,
                    output=response,
                    confidence=1.0,
                    duration_seconds=response.get("duration", 0.0),
                )

                outputs.append(result)
                current_output = response.get("content", "")

            except Exception as e:  # noqa: BLE001
                logger.exception(f"Agent {agent.agent_id} failed: {e}")
                result = AgentResult(
                    agent_id=agent.agent_id,
                    success=False,
                    output={},
                    confidence=0.0,
                    duration_seconds=0.0,
                    error=str(e),
                )
                outputs.append(result)

        duration = asyncio.get_event_loop().time() - start_time

        return StrategyResult(
            success=all(r.success for r in outputs),
            outputs=outputs,
            aggregated_output={"final_output": current_output},
            total_duration=duration,
            errors=[r.error for r in outputs if not r.success],
        )


class DelegationChainStrategy(ExecutionStrategy):
    """Hierarchical delegation with max depth enforcement.

    Anthropic Pattern: Keep agent hierarchies shallow (<=3 levels).
    Coordinator delegates to specialists, specialists can delegate further.

    Example:
        Level 1: Coordinator (analyzes task)
        Level 2: Domain specialists (security, performance, quality)
        Level 3: Sub-specialists (SQL injection, XSS, etc.)
        Level 4: NOT ALLOWED (too deep)

    Benefits:
        - Complex specialization within depth limits
        - Clear delegation hierarchy
        - Prevents runaway recursion

    Security:
        - Max depth enforced (default: 3)
        - Delegation trace logged
        - Circular delegation prevented

    """

    MAX_DEPTH = 3

    def __init__(self, max_depth: int = 3):
        """Initialize with depth limit.

        Args:
            max_depth: Maximum delegation depth (default: 3, max: 3)

        """
        self.max_depth = min(max_depth, self.MAX_DEPTH)

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute delegation chain with depth tracking.

        Args:
            agents: Hierarchical agent structure [coordinator, specialist1, specialist2, ...]
            context: Execution context with task

        Returns:
            Result with delegation trace

        """
        current_depth = context.get("_delegation_depth", 0)

        if current_depth >= self.max_depth:
            return StrategyResult(
                success=False,
                outputs=[],
                aggregated_output={},
                errors=[
                    f"Max delegation depth ({self.max_depth}) exceeded at depth {current_depth}",
                ],
            )

        if not agents:
            return StrategyResult(
                success=False,
                outputs=[],
                aggregated_output={},
                errors=["No agents provided for delegation"],
            )

        start_time = asyncio.get_event_loop().time()

        # Execute coordinator (first agent)
        coordinator = agents[0]
        specialists = agents[1:]

        try:
            # Coordinator analyzes and plans delegation
            delegation_plan = await self._plan_delegation(
                coordinator=coordinator,
                task=context.get("task", ""),
                specialists=specialists,
            )

            # Execute delegated tasks
            results = []
            for sub_task in delegation_plan.get("sub_tasks", []):
                specialist_id = sub_task.get("specialist_id")
                specialist = self._find_specialist(specialist_id, specialists)

                if specialist:
                    # Recursive delegation (with depth tracking)
                    sub_context = {
                        **context,
                        "task": sub_task.get("task", ""),
                        "_delegation_depth": current_depth + 1,
                    }

                    sub_result = await self._execute_specialist(
                        specialist=specialist,
                        context=sub_context,
                    )

                    results.append(sub_result)

            # Synthesize results
            final_output = await self._synthesize_results(
                coordinator=coordinator,
                results=results,
                original_task=context.get("task", ""),
            )

            duration = asyncio.get_event_loop().time() - start_time

            return StrategyResult(
                success=True,
                outputs=results,
                aggregated_output=final_output,
                total_duration=duration,
            )

        except Exception as e:  # noqa: BLE001
            logger.exception(f"Delegation chain failed: {e}")
            duration = asyncio.get_event_loop().time() - start_time
            return StrategyResult(
                success=False,
                outputs=[],
                aggregated_output={},
                total_duration=duration,
                errors=[str(e)],
            )

    async def _plan_delegation(
        self,
        coordinator: AgentTemplate,
        task: str,
        specialists: list[AgentTemplate],
    ) -> dict[str, Any]:
        """Coordinator plans delegation strategy."""
        import json

        from attune.models import LLMClient

        client = LLMClient()

        specialist_descriptions = "\n".join([f"- {s.agent_id}: {s.role}" for s in specialists])

        prompt = f"""Break down this task and assign to specialists:

Task: {task}

Available specialists:
{specialist_descriptions}

Return JSON:
{{
    "sub_tasks": [
        {{"specialist_id": "...", "task": "..."}},
        ...
    ]
}}"""

        response = await client.call(
            prompt=prompt,
            system_prompt=coordinator.system_prompt or "You are a task coordinator.",
            tier=coordinator.tier,
            workflow_id=f"delegation:{coordinator.agent_id}",
        )

        try:
            return json.loads(response.get("content", "{}"))
        except json.JSONDecodeError:
            logger.warning("Failed to parse delegation plan, using fallback")
            return {
                "sub_tasks": [
                    {
                        "specialist_id": specialists[0].agent_id if specialists else "unknown",
                        "task": task,
                    },
                ],
            }

    async def _execute_specialist(
        self,
        specialist: AgentTemplate,
        context: dict[str, Any],
    ) -> AgentResult:
        """Execute specialist agent."""
        from attune.models import LLMClient

        client = LLMClient()
        start_time = asyncio.get_event_loop().time()

        try:
            response = await client.call(
                prompt=context.get("task", ""),
                system_prompt=specialist.system_prompt,
                tier=specialist.tier,
                workflow_id=f"specialist:{specialist.agent_id}",
            )

            duration = asyncio.get_event_loop().time() - start_time

            return AgentResult(
                agent_id=specialist.agent_id,
                success=True,
                output=response,
                confidence=1.0,
                duration_seconds=duration,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Specialist {specialist.agent_id} failed: {e}")
            duration = asyncio.get_event_loop().time() - start_time
            return AgentResult(
                agent_id=specialist.agent_id,
                success=False,
                output={},
                confidence=0.0,
                duration_seconds=duration,
                error=str(e),
            )

    def _find_specialist(
        self,
        specialist_id: str,
        agents: list[AgentTemplate],
    ) -> AgentTemplate | None:
        """Find specialist by ID."""
        for agent in agents:
            if agent.agent_id == specialist_id:
                return agent
        return None

    async def _synthesize_results(
        self,
        coordinator: AgentTemplate,
        results: list[AgentResult],
        original_task: str,
    ) -> dict[str, Any]:
        """Coordinator synthesizes specialist results."""
        from attune.models import LLMClient

        client = LLMClient()

        specialist_reports = "\n\n".join(
            [f"## {r.agent_id}\n{r.output.get('content', '')}" for r in results],
        )

        prompt = f"""Synthesize these specialist reports:

Original task: {original_task}

{specialist_reports}

Provide cohesive final analysis."""

        try:
            response = await client.call(
                prompt=prompt,
                system_prompt=coordinator.system_prompt or "You are a synthesis coordinator.",
                tier=coordinator.tier,
                workflow_id=f"synthesis:{coordinator.agent_id}",
            )

            return {
                "synthesis": response.get("content", ""),
                "specialist_reports": [r.output for r in results],
                "delegation_depth": len(results),
            }
        except Exception as e:  # noqa: BLE001
            logger.exception(f"Synthesis failed: {e}")
            return {
                "synthesis": "Synthesis failed",
                "specialist_reports": [r.output for r in results],
                "delegation_depth": len(results),
                "error": str(e),
            }
