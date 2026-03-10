"""Workflow composition into DynamicTeam instances.

Provides a high-level API for composing multiple ``BaseWorkflow`` subclasses
into a single ``DynamicTeam`` that can be executed with any strategy
(parallel, sequential, two_phase, delegation).

Example::

    composer = WorkflowComposer()
    team = composer.compose(
        team_name="comprehensive-review",
        workflows=[
            {"workflow": SecurityAuditWorkflow, "kwargs": {"path": "src/"}},
            {"workflow": CodeReviewWorkflow, "kwargs": {"diff": "..."}},
        ],
        strategy="parallel",
        quality_gates={"min_score": 70},
    )
    result = await team.execute({"target": "src/"})

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import Any

from attune.agents.sdk.sdk_team import QualityGate
from attune.orchestration.dynamic_team import DynamicTeam

from .workflow_agent_adapter import WorkflowAgentAdapter

logger = logging.getLogger(__name__)


class WorkflowComposer:
    """Composes ``BaseWorkflow`` subclasses into a ``DynamicTeam``.

    Each workflow is wrapped via ``WorkflowAgentAdapter`` so that the
    ``DynamicTeam`` executor can call ``adapter.process(input_data)``
    uniformly for both SDK agents and workflows.

    Args:
        state_store: Optional ``AgentStateStore`` shared by all adapters.

    """

    def __init__(self, state_store: Any | None = None) -> None:
        """Initialize WorkflowComposer with optional shared state.

        Args:
            state_store: Optional AgentStateStore shared by all adapters.

        """
        self.state_store = state_store

    def compose(
        self,
        team_name: str,
        workflows: list[dict[str, Any]],
        strategy: str = "parallel",
        quality_gates: dict[str, Any] | None = None,
        phases: list[dict[str, Any]] | None = None,
    ) -> DynamicTeam:
        """Compose workflows into a runnable ``DynamicTeam``.

        Args:
            team_name: Human-readable name for the composed team.
            workflows: List of workflow specifications. Each dict must have:
                - ``workflow``: A ``BaseWorkflow`` subclass (type).
                - ``kwargs`` (optional): Dict of keyword arguments for the
                  workflow constructor.
                - ``role`` (optional): Human-readable role name.
                - ``agent_id`` (optional): Unique agent identifier.
            strategy: Execution strategy (``parallel``, ``sequential``,
                ``two_phase``, ``delegation``).
            quality_gates: Optional gate specs. Format::

                {"gate_name": threshold} or
                {"gate_name": {"agent_role": "...", "metric": "...", "threshold": N}}

            phases: Optional phase definitions for ``two_phase`` strategy.

        Returns:
            Runnable ``DynamicTeam`` instance.

        Raises:
            ValueError: If ``workflows`` is empty.

        """
        if not workflows:
            raise ValueError("At least one workflow is required")

        adapters = [self._build_adapter(spec) for spec in workflows]
        gates = self._build_quality_gates(quality_gates or {})

        return DynamicTeam(
            team_name=team_name,
            agents=adapters,  # type: ignore[arg-type]
            strategy=strategy,
            quality_gates=gates,
            phases=phases or [],
        )

    def compose_with_simplification(
        self,
        team_name: str,
        workflow_class: type,
        workflow_kwargs: dict[str, Any] | None = None,
        simplify_kwargs: dict[str, Any] | None = None,
        quality_gates: dict[str, Any] | None = None,
    ) -> DynamicTeam:
        """Compose a workflow with a trailing simplification step.

        Convenience method that chains any code-generating workflow
        with ``SimplifyCodeWorkflow`` in sequential order. This
        implements the Boris Cherny pattern::

            generate/refactor → simplify → verify

        Args:
            team_name: Human-readable name for the composed team.
            workflow_class: The primary workflow class (e.g.,
                ``RefactorPlanWorkflow``).
            workflow_kwargs: Kwargs for the primary workflow constructor.
            simplify_kwargs: Kwargs for ``SimplifyCodeWorkflow``
                constructor. Defaults to ``{"min_complexity": 5}``.
            quality_gates: Optional quality gate specs.

        Returns:
            Runnable ``DynamicTeam`` with sequential strategy.

        Example::

            composer = WorkflowComposer()
            team = composer.compose_with_simplification(
                team_name="refactor-and-simplify",
                workflow_class=RefactorPlanWorkflow,
                workflow_kwargs={"path": "src/"},
            )
            result = await team.execute({"target": "src/"})

        """
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        workflows = [
            {
                "workflow": workflow_class,
                "kwargs": workflow_kwargs or {},
                "role": "Primary Workflow",
            },
            {
                "workflow": SimplifyCodeWorkflow,
                "kwargs": simplify_kwargs or {"min_complexity": 5},
                "role": "Code Simplifier",
            },
        ]

        return self.compose(
            team_name=team_name,
            workflows=workflows,
            strategy="sequential",
            quality_gates=quality_gates,
        )

    def _build_adapter(self, spec: dict[str, Any]) -> WorkflowAgentAdapter:
        """Build a ``WorkflowAgentAdapter`` from a workflow spec.

        Args:
            spec: Dict with ``workflow`` (type), optional ``kwargs``,
                ``role``, ``agent_id``.

        Returns:
            Configured ``WorkflowAgentAdapter``.

        """
        return WorkflowAgentAdapter(
            workflow_class=spec["workflow"],
            workflow_kwargs=spec.get("kwargs"),
            agent_id=spec.get("agent_id"),
            role=spec.get("role"),
            state_store=self.state_store,
        )

    def _build_quality_gates(self, gates_spec: dict[str, Any]) -> list[QualityGate]:
        """Build ``QualityGate`` objects from a spec dict.

        Uses the same format as ``DynamicTeamBuilder._build_quality_gates()``.

        Args:
            gates_spec: Dict of gate definitions.

        Returns:
            List of ``QualityGate`` objects.

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
