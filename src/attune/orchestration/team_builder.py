"""Dynamic team builder.

Creates runnable ``DynamicTeam`` instances from:
- User specifications (``TeamSpecification``)
- MetaOrchestrator execution plans
- Saved configurations (``ConfigurationStore``)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .dynamic_team import DynamicTeam

from attune.agents.sdk.sdk_agent import SDKAgent
from attune.agents.sdk.sdk_models import SDKExecutionMode
from attune.agents.sdk.sdk_team import QualityGate
from attune.agents.state.store import AgentStateStore
from attune.orchestration.agent_templates import get_template

from .config_store import AgentConfiguration
from .team_store import TeamSpecification

logger = logging.getLogger(__name__)


class DynamicTeamBuilder:
    """Builds runnable ``DynamicTeam`` instances from various sources.

    Args:
        state_store: Optional persistent state store shared by agents.
        redis_client: Optional Redis client shared by agents.

    """

    def __init__(
        self,
        state_store: AgentStateStore | None = None,
        redis_client: Any | None = None,
    ) -> None:
        self.state_store = state_store
        self.redis_client = redis_client

    # ------------------------------------------------------------------
    # Build from specification
    # ------------------------------------------------------------------

    def build_from_spec(self, spec: TeamSpecification) -> DynamicTeam:
        """Build a DynamicTeam from a TeamSpecification.

        Args:
            spec: Team specification with agents, strategy, and gates.

        Returns:
            Runnable DynamicTeam instance.

        """
        from .dynamic_team import DynamicTeam

        agents = [self._instantiate_agent(agent_spec) for agent_spec in spec.agents]
        gates = self._build_quality_gates(spec.quality_gates)

        return DynamicTeam(
            team_name=spec.name,
            agents=agents,
            strategy=spec.strategy,
            quality_gates=gates,
            phases=spec.phases,
        )

    # ------------------------------------------------------------------
    # Build from MetaOrchestrator plan
    # ------------------------------------------------------------------

    def build_from_plan(self, plan: dict[str, Any]) -> DynamicTeam:
        """Build a DynamicTeam from a MetaOrchestrator execution plan.

        Args:
            plan: Dict containing ``agents``, ``strategy``, and ``quality_gates``.

        Returns:
            Runnable DynamicTeam instance.

        """
        from .dynamic_team import DynamicTeam

        agent_specs = plan.get("agents", [])
        agents = [self._instantiate_agent(spec) for spec in agent_specs]
        gates = self._build_quality_gates(plan.get("quality_gates", {}))

        return DynamicTeam(
            team_name=plan.get("name", "dynamic-team"),
            agents=agents,
            strategy=plan.get("strategy", "parallel"),
            quality_gates=gates,
            phases=plan.get("phases", []),
        )

    # ------------------------------------------------------------------
    # Build from saved configuration
    # ------------------------------------------------------------------

    def build_from_config(self, config: AgentConfiguration) -> DynamicTeam:
        """Build a DynamicTeam from a saved AgentConfiguration.

        Args:
            config: Previously-saved agent configuration.

        Returns:
            Runnable DynamicTeam instance.

        """
        from .dynamic_team import DynamicTeam

        agents = [self._instantiate_agent(spec) for spec in config.agents]
        gates = self._build_quality_gates(config.quality_gates)

        return DynamicTeam(
            team_name=config.id,
            agents=agents,
            strategy=config.strategy,
            quality_gates=gates,
        )

    # ------------------------------------------------------------------
    # Agent instantiation
    # ------------------------------------------------------------------

    def _instantiate_agent(self, agent_spec: dict[str, Any]) -> SDKAgent:
        """Create an SDKAgent from an agent specification dict.

        The spec may reference a template by ``template_id``, in which case
        the template's defaults are used for any missing fields.

        Args:
            agent_spec: Dict with ``role``, optional ``template_id``, ``tier``,
                ``system_prompt``, ``mode``.

        Returns:
            Configured SDKAgent instance.

        """
        template_id = agent_spec.get("template_id")
        template = get_template(template_id) if template_id else None

        role = agent_spec.get("role", getattr(template, "role", "Agent"))
        system_prompt = agent_spec.get(
            "system_prompt",
            getattr(template, "default_instructions", ""),
        )

        mode_str = agent_spec.get("mode", "tools_only")
        try:
            mode = SDKExecutionMode(mode_str)
        except ValueError:
            mode = SDKExecutionMode.TOOLS_ONLY

        return SDKAgent(
            agent_id=agent_spec.get("agent_id"),
            role=role,
            system_prompt=system_prompt,
            mode=mode,
            redis_client=self.redis_client,
            state_store=self.state_store,
        )

    def _build_quality_gates(self, gates_spec: dict[str, Any]) -> list[QualityGate]:
        """Build QualityGate objects from a spec dict.

        The spec format is::

            {
                "gate_name": {
                    "agent_role": "Security",
                    "metric": "score",
                    "threshold": 80.0,
                    "required": True
                }
            }

        Or a simple ``{"metric_name": threshold}`` shorthand where the
        metric is matched against all agents using their score.

        Args:
            gates_spec: Dict of gate definitions.

        Returns:
            List of QualityGate objects.

        """
        gates: list[QualityGate] = []
        for name, value in gates_spec.items():
            if isinstance(value, dict):
                gates.append(
                    QualityGate(
                        name=name,
                        agent_role=value.get("agent_role", ""),
                        metric=value.get("metric", "score"),
                        threshold=float(value.get("threshold", 0.0)),
                        required=value.get("required", True),
                    ),
                )
            else:
                # Simple shorthand: name = threshold (check all agents)
                gates.append(
                    QualityGate(
                        name=name,
                        agent_role="",
                        metric="score",
                        threshold=float(value),
                        required=True,
                    ),
                )
        return gates
