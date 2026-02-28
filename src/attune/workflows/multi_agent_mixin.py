"""Multi-Agent Stage Mixin for BaseWorkflow.

Allows a workflow stage to delegate to a ``DynamicTeam`` instead of
making a single LLM call.  Workflow subclasses opt in by calling
``self._run_multi_agent_stage()`` from their ``run_stage()`` implementation.

Expected attributes on the host class:
    name (str): Workflow name
    _state_store (AgentStateStore | None): Optional state store
    _multi_agent_configs (dict | None): Optional per-stage team configs

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MultiAgentStageMixin:
    """Mixin enabling workflow stages to delegate to multi-agent teams.

    When ``self._multi_agent_configs`` is ``None`` **and** no ``team_config``
    is passed to ``_run_multi_agent_stage``, the method raises ``ValueError``.
    This is an explicitly opt-in API -- it does nothing unless called.
    """

    # Expected attributes (set by BaseWorkflow.__init__)
    name: str
    _state_store: Any  # AgentStateStore | None
    _multi_agent_configs: dict[str, dict[str, Any]] | None

    async def _run_multi_agent_stage(
        self,
        stage_name: str,
        input_data: dict[str, Any],
        team_config: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int, int]:
        """Execute a stage using a DynamicTeam.

        Args:
            stage_name: Current workflow stage name.
            input_data: Input data for the stage.
            team_config: Team configuration dict.  If ``None``, looks up
                ``self._multi_agent_configs[stage_name]``.

        Returns:
            Tuple of (merged_output, total_input_tokens, total_output_tokens).

        Raises:
            ValueError: When no team config is found for the stage.

        The ``team_config`` format::

            {
                "agents": [
                    {"template_id": "security_auditor"},
                    {"template_id": "code_reviewer"},
                    {"role": "Custom Agent"},
                ],
                "strategy": "parallel",
                "quality_gates": {"min_score": 70},
            }

        """
        # Lazy imports to avoid circular dependencies
        from attune.orchestration.dynamic_team import DynamicTeam
        from attune.orchestration.team_builder import DynamicTeamBuilder

        # Resolve config
        config = team_config
        if config is None:
            configs = getattr(self, "_multi_agent_configs", None) or {}
            config = configs.get(stage_name)

        if config is None:
            raise ValueError(
                f"No multi-agent team config found for stage '{stage_name}'. "
                f"Pass team_config directly or set _multi_agent_configs['{stage_name}'].",
            )

        # Build the team
        state_store = getattr(self, "_state_store", None)
        builder = DynamicTeamBuilder(state_store=state_store)

        plan = {
            "name": f"{self.name}:{stage_name}",
            "agents": config.get("agents", []),
            "strategy": config.get("strategy", "parallel"),
            "quality_gates": config.get("quality_gates", {}),
            "phases": config.get("phases", []),
        }
        team: DynamicTeam = builder.build_from_plan(plan)

        # Execute the team
        team_result = await team.execute(input_data)

        # Merge results into a single stage output
        merged = self._merge_team_results(team_result, stage_name)

        # Estimate token counts from total cost (best-effort)
        total_cost = team_result.total_cost
        estimated_tokens = self._estimate_tokens_from_cost(total_cost)

        return merged, estimated_tokens, estimated_tokens

    def _merge_team_results(
        self,
        team_result: Any,
        stage_name: str,
    ) -> dict[str, Any]:
        """Merge individual agent results into a single stage output.

        Subclasses can override for domain-specific merging logic.

        Args:
            team_result: ``DynamicTeamResult`` from team execution.
            stage_name: Name of the workflow stage.

        Returns:
            Merged dict suitable as workflow stage output.

        """
        agent_findings = []
        for r in team_result.agent_results:
            agent_findings.append(
                {
                    "agent_id": r.agent_id,
                    "role": r.role,
                    "success": r.success,
                    "score": r.score,
                    "findings": r.findings,
                },
            )

        return {
            "stage": stage_name,
            "team_name": team_result.team_name,
            "team_success": team_result.success,
            "strategy": team_result.strategy,
            "agents": agent_findings,
            "quality_gate_results": team_result.quality_gate_results,
            "total_cost": team_result.total_cost,
            "execution_time_ms": team_result.execution_time_ms,
        }

    @staticmethod
    def _estimate_tokens_from_cost(cost: float) -> int:
        """Estimate token count from API cost (best-effort).

        Uses a rough average of $3 per 1M input tokens (Haiku-level).
        This is intentionally conservative -- the value is used for
        telemetry only, not billing.

        Args:
            cost: LLM API cost in USD.

        Returns:
            Estimated token count.

        """
        if cost <= 0:
            return 0
        # $3 per 1M tokens (rough Haiku average)
        return int(cost / 3.0 * 1_000_000)
