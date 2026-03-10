"""SDK Agent Team for parallel/sequential multi-agent execution.

Composes ``SDKAgent`` instances and evaluates quality gates,
following the same patterns as ``ReleasePrepTeam`` and ``CDSTeam``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .sdk_agent import SDKAgent
from .sdk_models import SDKAgentResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Team result
# ---------------------------------------------------------------------------


@dataclass
class SDKTeamResult:
    """Aggregated result from an SDKAgentTeam execution.

    Args:
        team_name: Human-readable team name.
        success: Whether all quality gates passed.
        agent_results: Individual results from each agent.
        quality_gate_results: Per-gate pass/fail details.
        total_cost: Sum of all agent costs.
        execution_time_ms: Wall-clock time for the full team run.

    """

    team_name: str
    success: bool = True
    agent_results: list[SDKAgentResult] = field(default_factory=list)
    quality_gate_results: dict[str, bool] = field(default_factory=dict)
    total_cost: float = 0.0
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict.

        Returns:
            Dict representation of this team result.

        """
        return {
            "team_name": self.team_name,
            "success": self.success,
            "agent_results": [r.to_dict() for r in self.agent_results],
            "quality_gate_results": self.quality_gate_results,
            "total_cost": self.total_cost,
            "execution_time_ms": self.execution_time_ms,
        }


# ---------------------------------------------------------------------------
# Quality gate definition
# ---------------------------------------------------------------------------


@dataclass
class QualityGate:
    """A named threshold that an agent result must satisfy.

    Args:
        name: Gate name (e.g. "min_security_score").
        agent_role: Role name of the agent whose result is checked.
        metric: Key in ``SDKAgentResult.findings`` to evaluate.
        threshold: Minimum acceptable value.
        required: If ``True``, gate failure fails the entire team.

    """

    name: str
    agent_role: str
    metric: str
    threshold: float
    required: bool = True


# ---------------------------------------------------------------------------
# SDK Agent Team
# ---------------------------------------------------------------------------


class SDKAgentTeam:
    """Composes SDKAgent instances for parallel or sequential execution.

    Args:
        team_name: Human-readable name for this team.
        agents: List of ``SDKAgent`` instances.
        quality_gates: Optional list of ``QualityGate`` thresholds.
        parallel: If ``True``, agents run concurrently via ``asyncio.gather``.

    """

    def __init__(
        self,
        team_name: str,
        agents: list[SDKAgent],
        quality_gates: list[QualityGate] | None = None,
        parallel: bool = True,
    ) -> None:
        """Initialize the SDK agent team.

        Args:
            team_name: Name identifying this team.
            agents: List of SDKAgent instances.
            quality_gates: Optional quality gate thresholds.
            parallel: If True, agents run concurrently.
        """
        self.team_name = team_name
        self.agents = agents
        self.quality_gates = quality_gates or []
        self.parallel = parallel

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, input_data: dict[str, Any]) -> SDKTeamResult:
        """Run all agents and evaluate quality gates.

        Args:
            input_data: Structured input forwarded to every agent.

        Returns:
            Aggregated ``SDKTeamResult``.

        """
        start = time.time()

        if self.parallel:
            results = await self._execute_parallel(input_data)
        else:
            results = await self._execute_sequential(input_data)

        execution_time = (time.time() - start) * 1000
        total_cost = sum(r.cost for r in results)

        gate_results = self._evaluate_quality_gates(results)
        all_gates_pass = all(
            passed
            for gate_name, passed in gate_results.items()
            if self._gate_is_required(gate_name)
        )

        return SDKTeamResult(
            team_name=self.team_name,
            success=all_gates_pass,
            agent_results=results,
            quality_gate_results=gate_results,
            total_cost=total_cost,
            execution_time_ms=execution_time,
        )

    async def _execute_parallel(self, input_data: dict[str, Any]) -> list[SDKAgentResult]:
        """Run agents concurrently with asyncio.gather.

        Args:
            input_data: Input forwarded to each agent.

        Returns:
            List of agent results.

        """
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, agent.process, input_data) for agent in self.agents]
        results: list[SDKAgentResult] = list(await asyncio.gather(*tasks))
        return results

    async def _execute_sequential(self, input_data: dict[str, Any]) -> list[SDKAgentResult]:
        """Run agents one-at-a-time in order.

        Args:
            input_data: Input forwarded to each agent.

        Returns:
            List of agent results.

        """
        results: list[SDKAgentResult] = []
        for agent in self.agents:
            result = agent.process(input_data)
            results.append(result)
        return results

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
            agent_result = results_by_role.get(gate.agent_role)
            if agent_result is None:
                logger.warning(
                    f"Quality gate '{gate.name}' references unknown role '{gate.agent_role}'",
                )
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
