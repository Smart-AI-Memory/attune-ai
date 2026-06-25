"""Claude-driven access to agent-team orchestration (Phase 2).

The 14 builtin agent templates are *listable* via the catalog but were
not *runnable* through a shipped surface. This module gives the
Claude-driven ``agent`` skill a clean two-step bridge, mirroring the
wizard driver:

1. ``describe_team_for_task(task)`` — deterministic, no LLM. Composes a
   team plan from the templates (which agents, what strategy, estimated
   cost/duration) so the model can preview it for the user and confirm.
2. ``run_team_for_task(task, ...)`` — composes AND executes the team.
   This is the LLM-heavy step; only call it after the user confirms.

See ``docs/specs/interactive-orchestration-access`` (Phase 2).
"""

from __future__ import annotations

from typing import Any


def describe_team_for_task(
    task: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose (but do not run) an agent team for a task.

    Deterministic / no LLM — safe to call for a preview.

    Args:
        task: Natural-language goal (e.g. "improve test coverage to 90%").
        context: Optional context dict.

    Returns:
        A serializable plan: ``task``, ``strategy``, ``agents``
        (``{id, role}`` from the templates), ``estimated_cost``,
        ``estimated_duration``, ``quality_gates``.

    Raises:
        ValueError: If ``task`` is empty/invalid (from the orchestrator).

    """
    from attune.orchestration.meta_orchestrator import MetaOrchestrator

    plan = MetaOrchestrator().analyze_and_compose(task, context or {})
    return {
        "task": task,
        "strategy": plan.strategy.value,
        "agents": [{"id": t.id, "role": t.role} for t in plan.agents],
        "estimated_cost": plan.estimated_cost,
        "estimated_duration": plan.estimated_duration,
        "quality_gates": list(plan.quality_gates),
    }


async def run_team_for_task(
    task: str,
    context: dict[str, Any] | None = None,
    input_data: dict[str, Any] | None = None,
) -> Any:
    """Compose AND execute an agent team for a task.

    LLM-heavy: spins up the composed multi-agent team and runs it. Call
    only after a preview (``describe_team_for_task``) and user
    confirmation.

    Args:
        task: Natural-language goal.
        context: Optional context for composition.
        input_data: Structured input forwarded to the agents.

    Returns:
        The team's ``DynamicTeamResult``.

    Raises:
        ValueError: If ``task`` is empty/invalid.

    """
    from attune.orchestration.meta_orchestrator import MetaOrchestrator

    team = MetaOrchestrator().compose_team(task, context or {})
    return await team.execute(input_data or {})
