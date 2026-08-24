"""Generic parallel agent teams.

A team is an explicit list of agents plus a declarative gate spec. The
coordinator fans the agents out via ``asyncio.gather``, aggregates their
0-100 scores, and gates on the results — splitting critical failures into
blockers and non-critical failures into warnings.

This **generalizes the working ``ReleasePrepTeam`` pattern**; it does NOT
revive the dead dynamic-team / stub-agent engine removed in #1096. Each
agent does real work by wrapping a registered ``BaseWorkflow`` whose run
yields an actual score — never a stub constant.

See ``docs/specs/generic-agent-teams/`` for the design and decisions.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from attune.agents.release.release_models import QualityGate

logger = logging.getLogger(__name__)

#: Fallback score parse for reviews that produced no findings dict.
#: Mirrors ``pipeline.orchestrator._SCORE_RE`` (lifted here per D5).
_SCORE_RE = re.compile(r"\bscore:?\s*(\d{1,3})\s*/\s*100", re.IGNORECASE)

#: A team target is one path or a list of paths.
TeamTarget = str | list[str]


# =============================================================================
# Data models
# =============================================================================


@dataclass
class AgentResult:
    """Outcome of one agent's run over a target.

    Attributes:
        key: Agent identifier (e.g. ``"code-review"``).
        score: Aggregated 0-100 score (min across files for a
            multi-file target).
        cost: Summed LLM cost in USD.
        success: ``False`` if the wrapped workflow errored or produced
            no score (the gate then fails closed).
        details: Free-form diagnostic context.
    """

    key: str
    score: float
    cost: float
    success: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateSpec:
    """Declarative gate: which agent's score to threshold, and how.

    Attributes:
        name: Human-readable gate name (e.g. ``"Code Quality"``).
        agent_key: ``AgentResult.key`` whose score this gate reads.
        threshold: Minimum passing score (0-100).
        critical: When ``True`` a failure is a blocker; otherwise a
            warning.
    """

    name: str
    agent_key: str
    threshold: float
    critical: bool = True


@dataclass
class TeamReport:
    """Aggregated verdict from an :class:`AgentTeam` run.

    Attributes:
        passed: ``True`` only when no critical gate failed.
        gates: Evaluated :class:`QualityGate` results, one per spec.
        results: Per-agent :class:`AgentResult` outputs.
        blockers: Messages from failed critical gates.
        warnings: Messages from failed non-critical gates.
        cost: Total LLM cost across all agents in USD.
    """

    passed: bool
    gates: list[QualityGate]
    results: list[AgentResult]
    blockers: list[str]
    warnings: list[str]
    cost: float


# =============================================================================
# Score / cost extraction (shared default scorer, D5)
# =============================================================================


def extract_score(result: Any, default: float | None = None) -> float | None:
    """Pull a 0-100 score from a workflow ``WorkflowResult``.

    Precedence (D5): ``final_output["score"]`` → ``metadata["score"]`` →
    a ``score: N/100`` regex over string output → ``default``. Returns
    ``default`` (``None`` by default) when the workflow did not succeed
    or carried no score, so the caller can fail the gate closed rather
    than fake a pass.

    Args:
        result: A workflow result object (duck-typed: ``success``,
            ``final_output``, optional ``metadata``).
        default: Value returned when no score is present.

    Returns:
        The extracted score, or ``default`` if none could be found.
    """
    if not getattr(result, "success", False):
        return default
    output = getattr(result, "final_output", None)
    if isinstance(output, dict) and output.get("score") is not None:
        return float(output["score"])
    metadata = getattr(result, "metadata", None)
    if isinstance(metadata, dict) and metadata.get("score") is not None:
        return float(metadata["score"])
    if isinstance(output, str):
        match = _SCORE_RE.search(output)
        if match:
            return float(match.group(1))
    return default


def _result_cost(result: Any) -> float:
    """Best-effort cost of a workflow result, in USD."""
    report = getattr(result, "cost_report", None)
    return float(getattr(report, "total_cost", 0.0) or 0.0)


def _min_score(scores: list[float | None]) -> float | None:
    """Worst score across files; ``None`` if any file failed to score."""
    if not scores or any(s is None for s in scores):
        return None
    return min(s for s in scores if s is not None)


# =============================================================================
# Agent contract + workflow-backed implementation
# =============================================================================


@runtime_checkable
class TeamAgent(Protocol):
    """A team member: an async unit of work that scores a target.

    The contract is async (D7). A sync agent adapts by offloading its
    work via ``loop.run_in_executor`` inside its own ``run`` — the shim
    lives in the agent, never in the coordinator.
    """

    key: str

    async def run(self, target: TeamTarget) -> AgentResult:  # pragma: no cover
        """Run over ``target`` and return an :class:`AgentResult`."""
        ...


class WorkflowAgent:
    """A team agent that runs a ``BaseWorkflow`` over a target and scores it.

    Wraps a registered workflow class (D1). For a multi-file target it
    runs the workflow over each file and reports the **min** score (the
    worst file), matching the ``/spec`` gate's per-dimension behavior.
    Fails closed: any exception, or a file that produces no score,
    yields ``success=False`` and score ``0.0`` so a gate fails rather
    than fake-passing.

    Args:
        key: Agent identifier; matched against :class:`GateSpec`.
        workflow_cls: A ``BaseWorkflow`` subclass; instantiated per run.
        files: Explicit file list to score. When ``None``, the paths
            passed to :meth:`run` are used.
        score_fn: Optional override for the default :func:`extract_score`
            (D5 escape hatch for workflows that report differently).
        default_score: Value the default scorer returns when no score is
            present (``None`` → fail closed).
        escalate: Reserved tier-escalation flag; off by default (D8).
    """

    def __init__(
        self,
        key: str,
        workflow_cls: type,
        *,
        files: list[str] | None = None,
        score_fn: Callable[[Any], float | None] | None = None,
        default_score: float | None = None,
        escalate: bool = False,
    ) -> None:
        """Initialize the workflow-backed agent."""
        self.key = key
        self.workflow_cls = workflow_cls
        self.files = files
        self.score_fn = score_fn
        self.default_score = default_score
        self.escalate = escalate  # D8: reserved, off by default

    def _resolve_paths(self, target: TeamTarget) -> list[str]:
        """Constructor ``files`` win; otherwise normalize ``target``."""
        if self.files is not None:
            return list(self.files)
        if isinstance(target, str):
            return [target]
        return list(target or [])

    async def run(self, target: TeamTarget) -> AgentResult:
        """Run the wrapped workflow over each file and aggregate.

        Args:
            target: One path or a list of paths to score.

        Returns:
            An :class:`AgentResult` with the min score, summed cost, and
            ``success=False`` on any error or missing score.
        """
        paths = self._resolve_paths(target)
        if not paths:
            # No files to score — nothing to gate on; trivially clean.
            return AgentResult(
                key=self.key,
                score=0.0,
                cost=0.0,
                success=True,
                details={"reason": "no files"},
            )

        scorer = self.score_fn or (lambda r: extract_score(r, self.default_score))
        scores: list[float | None] = []
        total_cost = 0.0
        for path in paths:
            try:
                workflow = self.workflow_cls()
                result = await workflow.execute(path=path)
            except Exception as exc:  # noqa: BLE001
                # INTENTIONAL: a workflow failure fails the gate closed;
                # it must never crash the team or fake a pass.
                logger.error("Agent %s failed on %s: %s", self.key, path, exc)
                return AgentResult(
                    key=self.key,
                    score=0.0,
                    cost=total_cost,
                    success=False,
                    details={"error": str(exc), "path": path},
                )
            scores.append(scorer(result))
            total_cost += _result_cost(result)

        score = _min_score(scores)
        if score is None:
            # A file produced no score — fail closed, do not fake-pass.
            return AgentResult(
                key=self.key,
                score=0.0,
                cost=total_cost,
                success=False,
                details={"reason": "no score", "files": paths},
            )
        return AgentResult(
            key=self.key,
            score=score,
            cost=total_cost,
            success=True,
            details={"files": paths},
        )


# =============================================================================
# Coordinator
# =============================================================================


class AgentTeam:
    """Fan out agents in parallel, aggregate, and gate.

    Runs each agent's ``run(target)`` concurrently via ``asyncio.gather``
    (D2 fan-out only — no sequential/DAG topology), evaluates the
    declarative :class:`GateSpec` list against the results, and splits
    failures into blockers (critical) and warnings (non-critical). The
    verdict passes only when no critical gate fails.

    Args:
        agents: The team members (anything satisfying :class:`TeamAgent`).
        gates: Declarative gates evaluated against agent scores.
    """

    def __init__(self, agents: list[TeamAgent], gates: list[GateSpec]) -> None:
        """Initialize the team with its agents and gate specs."""
        self.agents = agents
        self.gates = gates

    async def run(self, target: TeamTarget) -> TeamReport:
        """Run all agents over ``target`` and produce a gated verdict.

        Args:
            target: One path or a list of paths handed to each agent.

        Returns:
            A :class:`TeamReport` with the pass/fail verdict, evaluated
            gates, per-agent results, blockers, warnings, and total cost.
        """
        gathered = await asyncio.gather(
            *(agent.run(target) for agent in self.agents),
            return_exceptions=True,
        )
        # #2236: without return_exceptions one raised coroutine cancelled
        # siblings and corrupted the gate verdict. A crashed agent now
        # yields no result — its gate fails below (result None -> not
        # passed), preserving "a failed gatekeeper fails the gate".
        results: list[AgentResult] = []
        crash_notes: list[str] = []
        for agent, outcome in zip(self.agents, gathered, strict=False):
            if isinstance(outcome, BaseException) and not isinstance(outcome, Exception):
                raise outcome
            if isinstance(outcome, Exception):
                logger.error(
                    "Team agent %r raised during run: %s",
                    agent.key,
                    outcome,
                    exc_info=outcome,
                )
                crash_notes.append(
                    f"agent '{agent.key}' raised {type(outcome).__name__}: {outcome}"
                )
            else:
                results.append(outcome)
        by_key = {r.key: r for r in results}

        gates: list[QualityGate] = []
        blockers: list[str] = []
        warnings: list[str] = list(crash_notes)
        for spec in self.gates:
            result = by_key.get(spec.agent_key)
            actual = result.score if result is not None else 0.0
            passed = result is not None and result.success and actual >= spec.threshold
            gate = QualityGate(
                name=spec.name,
                threshold=spec.threshold,
                actual=actual,
                passed=passed,
                critical=spec.critical,
            )
            gates.append(gate)
            if not passed:
                (blockers if spec.critical else warnings).append(gate.message)

        return TeamReport(
            passed=not blockers,
            gates=gates,
            results=results,
            blockers=blockers,
            warnings=warnings,
            cost=sum(r.cost for r in results),
        )
