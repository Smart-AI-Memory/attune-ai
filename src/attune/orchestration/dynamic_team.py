"""Dynamic team executor.

Supports multiple execution strategies: parallel, sequential,
two-phase, and delegation.  Mirrors the patterns from
``ReleasePrepTeam`` (parallel ``asyncio.gather``) and
``CDSTeam`` (two-phase gather-then-reason).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from attune.agents.sdk.sdk_agent import SDKAgent
from attune.agents.sdk.sdk_models import SDKAgentResult
from attune.agents.sdk.sdk_team import QualityGate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class DynamicTeamResult:
    """Aggregated result from a DynamicTeam execution.

    Args:
        team_name: Human-readable team name.
        strategy: Strategy used for execution.
        success: Whether all required quality gates passed.
        agent_results: Individual per-agent results.
        quality_gate_results: Per-gate pass/fail.
        total_cost: Sum of all agent costs.
        execution_time_ms: Wall-clock time for the full team run.
        phase_results: Optional per-phase results for multi-phase strategies.

    """

    team_name: str
    strategy: str
    success: bool = True
    agent_results: list[SDKAgentResult] = field(default_factory=list)
    quality_gate_results: dict[str, bool] = field(default_factory=dict)
    total_cost: float = 0.0
    execution_time_ms: float = 0.0
    phase_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict.

        Returns:
            Dict representation.

        """
        return {
            "team_name": self.team_name,
            "strategy": self.strategy,
            "success": self.success,
            "agent_results": [r.to_dict() for r in self.agent_results],
            "quality_gate_results": self.quality_gate_results,
            "total_cost": self.total_cost,
            "execution_time_ms": self.execution_time_ms,
            "phase_results": self.phase_results,
        }


# ---------------------------------------------------------------------------
# DynamicTeam
# ---------------------------------------------------------------------------


class DynamicTeam:
    """Executes a dynamically-composed agent team.

    Supports strategies:
    - **parallel**: All agents run concurrently via ``asyncio.gather``.
    - **sequential**: Agents run one-at-a-time in order.
    - **two_phase**: Agents split into gatherer and reasoner phases.
    - **delegation**: First agent delegates to subsequent agents.

    Args:
        team_name: Human-readable name.
        agents: List of SDKAgent instances.
        strategy: Execution strategy name.
        quality_gates: Optional quality gate thresholds.
        phases: Optional phase definitions for two_phase strategy.

    """

    def __init__(
        self,
        team_name: str,
        agents: list[SDKAgent],
        strategy: str = "parallel",
        quality_gates: list[QualityGate] | None = None,
        phases: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize DynamicTeam with agents and execution strategy.

        Args:
            team_name: Human-readable name for the team.
            agents: List of SDK agents to execute.
            strategy: Execution strategy (parallel, sequential, two_phase).
            quality_gates: Optional quality gate thresholds.
            phases: Optional phase definitions for two_phase strategy.

        """
        self.team_name = team_name
        self.agents = agents
        self.strategy = strategy
        self.quality_gates = quality_gates or []
        self.phases = phases or []

    # ------------------------------------------------------------------
    # Main execution entry
    # ------------------------------------------------------------------

    async def execute(self, input_data: dict[str, Any]) -> DynamicTeamResult:
        """Execute the team using the configured strategy.

        Args:
            input_data: Structured input forwarded to agents.

        Returns:
            Aggregated DynamicTeamResult.

        """
        start = time.time()

        strategy_map = {
            "parallel": self._execute_parallel,
            "sequential": self._execute_sequential,
            "two_phase": self._execute_two_phase,
            "delegation": self._execute_delegation,
        }

        executor = strategy_map.get(self.strategy, self._execute_parallel)
        results, phase_results = await executor(input_data)

        execution_time = (time.time() - start) * 1000
        total_cost = sum(r.cost for r in results)

        gate_results = self._evaluate_quality_gates(results)
        all_required_pass = all(
            passed
            for gate_name, passed in gate_results.items()
            if self._gate_is_required(gate_name)
        )

        return DynamicTeamResult(
            team_name=self.team_name,
            strategy=self.strategy,
            success=all_required_pass,
            agent_results=results,
            quality_gate_results=gate_results,
            total_cost=total_cost,
            execution_time_ms=execution_time,
            phase_results=phase_results,
        )

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    async def _execute_parallel(
        self,
        input_data: dict[str, Any],
    ) -> tuple[list[SDKAgentResult], list[dict[str, Any]]]:
        """Run all agents concurrently.

        Args:
            input_data: Input forwarded to each agent.

        Returns:
            Tuple of (results, phase_results).

        """
        loop = asyncio.get_running_loop()
        tasks = [loop.run_in_executor(None, agent.process, input_data) for agent in self.agents]
        results: list[SDKAgentResult] = list(await asyncio.gather(*tasks))
        return results, []

    async def _execute_sequential(
        self,
        input_data: dict[str, Any],
    ) -> tuple[list[SDKAgentResult], list[dict[str, Any]]]:
        """Run agents one-at-a-time.

        Args:
            input_data: Input forwarded to each agent.

        Returns:
            Tuple of (results, phase_results).

        """
        results: list[SDKAgentResult] = []
        for agent in self.agents:
            result = agent.process(input_data)
            results.append(result)
        return results, []

    async def _execute_two_phase(
        self,
        input_data: dict[str, Any],
    ) -> tuple[list[SDKAgentResult], list[dict[str, Any]]]:
        """Execute in two phases: gather then reason.

        Phase 1 agents run in parallel. Their findings are merged
        into the input for Phase 2 agents.

        Args:
            input_data: Input forwarded to agents.

        Returns:
            Tuple of (all_results, phase_results).

        """
        if len(self.phases) >= 2:
            phase1_indices = self.phases[0].get("agent_indices", [])
            phase2_indices = self.phases[1].get("agent_indices", [])
        else:
            # Default split: first half gathers, second half reasons
            mid = max(1, len(self.agents) // 2)
            phase1_indices = list(range(mid))
            phase2_indices = list(range(mid, len(self.agents)))

        # Phase 1: Gather (parallel)
        phase1_agents = [self.agents[i] for i in phase1_indices if i < len(self.agents)]
        loop = asyncio.get_running_loop()
        phase1_tasks = [loop.run_in_executor(None, a.process, input_data) for a in phase1_agents]
        phase1_results: list[SDKAgentResult] = list(await asyncio.gather(*phase1_tasks))

        # Merge Phase 1 findings into input for Phase 2
        enriched_input = dict(input_data)
        enriched_input["phase1_findings"] = [r.findings for r in phase1_results]

        # Phase 2: Reason (sequential to allow chaining)
        phase2_agents = [self.agents[i] for i in phase2_indices if i < len(self.agents)]
        phase2_results: list[SDKAgentResult] = []
        for agent in phase2_agents:
            result = agent.process(enriched_input)
            phase2_results.append(result)

        all_results = phase1_results + phase2_results
        phase_summaries = [
            {"phase": 1, "strategy": "parallel", "agent_count": len(phase1_results)},
            {"phase": 2, "strategy": "sequential", "agent_count": len(phase2_results)},
        ]

        return all_results, phase_summaries

    async def _execute_delegation(
        self,
        input_data: dict[str, Any],
    ) -> tuple[list[SDKAgentResult], list[dict[str, Any]]]:
        """First agent delegates to subsequent agents.

        The first agent acts as a coordinator whose findings are
        forwarded to the remaining agents as additional context.

        Args:
            input_data: Input for the coordinator.

        Returns:
            Tuple of (all_results, phase_results).

        """
        if not self.agents:
            return [], []

        # Coordinator runs first
        coordinator = self.agents[0]
        coordinator_result = coordinator.process(input_data)

        # Delegate to remaining agents with coordinator's findings
        delegate_input = dict(input_data)
        delegate_input["coordinator_findings"] = coordinator_result.findings

        delegate_results: list[SDKAgentResult] = []
        if len(self.agents) > 1:
            loop = asyncio.get_running_loop()
            tasks = [
                loop.run_in_executor(None, agent.process, delegate_input)
                for agent in self.agents[1:]
            ]
            delegate_results = list(await asyncio.gather(*tasks))

        all_results = [coordinator_result] + delegate_results
        return all_results, []

    # ------------------------------------------------------------------
    # Quality gates
    # ------------------------------------------------------------------

    def _evaluate_quality_gates(self, results: list[SDKAgentResult]) -> dict[str, bool]:
        """Evaluate quality gates against agent results.

        Args:
            results: Agent results to check.

        Returns:
            Dict mapping gate name to pass/fail boolean.

        """
        gate_results: dict[str, bool] = {}
        results_by_role = {r.role: r for r in results}

        for gate in self.quality_gates:
            if not gate.agent_role:
                # Gate applies to all agents
                all_pass = all(
                    r.findings.get(gate.metric, r.score) >= gate.threshold for r in results
                )
                gate_results[gate.name] = all_pass
                continue

            agent_result = results_by_role.get(gate.agent_role)
            if agent_result is None:
                gate_results[gate.name] = False
                continue

            value = agent_result.findings.get(gate.metric, agent_result.score)
            gate_results[gate.name] = value >= gate.threshold

        return gate_results

    def _gate_is_required(self, gate_name: str) -> bool:
        """Check if a gate is marked as required.

        Args:
            gate_name: Name of the quality gate.

        Returns:
            True if the gate is required or unknown.

        """
        for gate in self.quality_gates:
            if gate.name == gate_name:
                return gate.required
        return True
