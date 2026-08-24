"""Unit tests for the generic parallel agent team (``attune.agents.team``).

Covers the shared score extractor's precedence, the gate evaluation's
critical-vs-warning split, parallel fan-out, and fail-closed behavior
when a wrapped workflow raises or produces no score.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from attune.agents.team import (
    AgentResult,
    AgentTeam,
    GateSpec,
    WorkflowAgent,
    extract_score,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


def _result(*, success=True, final_output=None, metadata=None, cost=0.0):
    """Build a duck-typed workflow result."""
    return SimpleNamespace(
        success=success,
        final_output=final_output,
        metadata=metadata,
        cost_report=SimpleNamespace(total_cost=cost),
    )


def _workflow(*, result=None, raises=None):
    """Return a no-arg workflow class whose ``execute`` returns/raises."""

    class _W:
        async def execute(self, path):  # noqa: ANN001
            if raises is not None:
                raise raises
            return result

    return _W


class _FakeAgent:
    """A team agent returning a preset :class:`AgentResult`."""

    def __init__(self, key, score, *, success=True, cost=0.0):
        self.key = key
        self._result = AgentResult(key, score, cost, success, {})

    async def run(self, target):  # noqa: ANN001
        return self._result


# ---------------------------------------------------------------------------
# extract_score — precedence (D5)
# ---------------------------------------------------------------------------


def test_extract_score_prefers_final_output_dict():
    assert extract_score(_result(final_output={"score": 91})) == 91.0


def test_extract_score_falls_back_to_metadata():
    r = _result(final_output="no score here", metadata={"score": 64})
    assert extract_score(r) == 64.0


def test_extract_score_regex_on_string_output():
    assert extract_score(_result(final_output="Review score: 42/100 done")) == 42.0


def test_extract_score_returns_default_when_absent():
    assert extract_score(_result(final_output="nothing"), default=None) is None
    assert extract_score(_result(final_output="nothing"), default=50.0) == 50.0


def test_extract_score_returns_default_when_unsuccessful():
    # A failed workflow never yields a score, regardless of output.
    assert extract_score(_result(success=False, final_output={"score": 99})) is None


# ---------------------------------------------------------------------------
# WorkflowAgent — scoring, min across files, fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workflow_agent_scores_single_file():
    agent = WorkflowAgent(
        "code-review",
        _workflow(result=_result(final_output={"score": 88}, cost=0.01)),
    )
    out = await agent.run("a.py")
    assert out.success is True
    assert out.score == 88.0
    assert out.cost == pytest.approx(0.01)


@pytest.mark.asyncio
async def test_workflow_agent_reports_min_across_files():
    class _PerPath:
        scores = {"a.py": 90.0, "b.py": 50.0}

        async def execute(self, path):  # noqa: ANN001
            return _result(final_output={"score": _PerPath.scores[path]}, cost=0.02)

    agent = WorkflowAgent("code-review", _PerPath, files=["a.py", "b.py"])
    out = await agent.run("ignored")
    assert out.score == 50.0  # worst file wins
    assert out.cost == pytest.approx(0.04)  # summed across files


@pytest.mark.asyncio
async def test_workflow_agent_fails_closed_on_raise():
    agent = WorkflowAgent("sec", _workflow(raises=RuntimeError("boom")))
    out = await agent.run("a.py")
    assert out.success is False
    assert out.score == 0.0
    assert "boom" in out.details["error"]


@pytest.mark.asyncio
async def test_workflow_agent_fails_closed_on_missing_score():
    agent = WorkflowAgent("sec", _workflow(result=_result(final_output="no score")))
    out = await agent.run("a.py")
    assert out.success is False
    assert out.score == 0.0


@pytest.mark.asyncio
async def test_workflow_agent_no_files_is_trivially_clean():
    agent = WorkflowAgent("sec", _workflow(), files=[])
    out = await agent.run("ignored")
    assert out.success is True
    assert out.details["reason"] == "no files"


@pytest.mark.asyncio
async def test_workflow_agent_score_fn_override():
    agent = WorkflowAgent(
        "x",
        _workflow(result=_result(final_output={"score": 10})),
        score_fn=lambda r: 99.0,
    )
    out = await agent.run("a.py")
    assert out.score == 99.0


# ---------------------------------------------------------------------------
# AgentTeam — gate split, verdict, parallelism
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_team_passes_when_all_gates_met():
    team = AgentTeam(
        agents=[_FakeAgent("cr", 90.0), _FakeAgent("sa", 85.0)],
        gates=[
            GateSpec("Code Quality", "cr", 70.0),
            GateSpec("Security", "sa", 70.0),
        ],
    )
    report = await team.run("x")
    assert report.passed is True
    assert report.blockers == []
    assert all(g.passed for g in report.gates)


@pytest.mark.asyncio
async def test_team_critical_failure_is_a_blocker():
    team = AgentTeam(
        agents=[_FakeAgent("cr", 90.0), _FakeAgent("sa", 40.0)],
        gates=[
            GateSpec("Code Quality", "cr", 70.0),
            GateSpec("Security", "sa", 70.0, critical=True),
        ],
    )
    report = await team.run("x")
    assert report.passed is False
    assert len(report.blockers) == 1
    assert "Security" in report.blockers[0]
    assert report.warnings == []


@pytest.mark.asyncio
async def test_team_noncritical_failure_is_a_warning_not_blocker():
    team = AgentTeam(
        agents=[_FakeAgent("cr", 40.0)],
        gates=[GateSpec("Style", "cr", 70.0, critical=False)],
    )
    report = await team.run("x")
    assert report.passed is True  # warnings do not block
    assert report.blockers == []
    assert len(report.warnings) == 1


@pytest.mark.asyncio
async def test_team_fails_closed_when_agent_unsuccessful():
    # A high score but success=False must still fail the gate closed.
    team = AgentTeam(
        agents=[_FakeAgent("cr", 100.0, success=False)],
        gates=[GateSpec("Code Quality", "cr", 70.0)],
    )
    report = await team.run("x")
    assert report.passed is False
    assert len(report.blockers) == 1


@pytest.mark.asyncio
async def test_team_sums_cost_across_agents():
    team = AgentTeam(
        agents=[_FakeAgent("cr", 90.0, cost=0.03), _FakeAgent("sa", 90.0, cost=0.05)],
        gates=[GateSpec("Code Quality", "cr", 70.0)],
    )
    report = await team.run("x")
    assert report.cost == pytest.approx(0.08)


@pytest.mark.asyncio
async def test_team_runs_agents_in_parallel():
    order: list[str] = []

    class _SlowAgent:
        def __init__(self, key, delay):
            self.key = key
            self.delay = delay

        async def run(self, target):  # noqa: ANN001
            order.append(f"{self.key}-start")
            await asyncio.sleep(self.delay)
            order.append(f"{self.key}-end")
            return AgentResult(self.key, 100.0, 0.0, True, {})

    team = AgentTeam(
        agents=[_SlowAgent("a", 0.02), _SlowAgent("b", 0.0)],
        gates=[GateSpec("A", "a", 70.0)],
    )
    await team.run("x")
    # Both agents started before the slow one finished → concurrent.
    assert order[:2] == ["a-start", "b-start"]


# ---------------------------------------------------------------------------
# gather-partial-failure guard (#2236)
# ---------------------------------------------------------------------------


class _RaisingAgent:
    def __init__(self, key):
        self.key = key

    async def run(self, target):  # noqa: ANN001
        raise RuntimeError("agent exploded")


@pytest.mark.asyncio
async def test_one_crashed_agent_still_produces_verdict():
    """#2236: a raising agent must not cancel siblings or crash run()."""
    team = AgentTeam(
        agents=[_FakeAgent("good", 95.0), _RaisingAgent("bad")],
        gates=[
            GateSpec(name="good-gate", agent_key="good", threshold=90.0, critical=True),
            GateSpec(name="bad-gate", agent_key="bad", threshold=50.0, critical=True),
        ],
    )
    report = await team.run("x")
    # The crashed agent's gate FAILS (absence is not a pass) -> blocker.
    assert report.passed is False
    assert any("bad-gate" in b for b in report.blockers)
    # The surviving agent's result and gate are intact.
    assert [r.key for r in report.results] == ["good"]
    assert any(g.name == "good-gate" and g.passed for g in report.gates)
    # The crash itself is surfaced.
    assert any("agent 'bad' raised RuntimeError" in w for w in report.warnings)


@pytest.mark.asyncio
async def test_crashed_agent_without_gate_is_a_warning_only():
    team = AgentTeam(
        agents=[_FakeAgent("good", 95.0), _RaisingAgent("ungated")],
        gates=[GateSpec(name="good-gate", agent_key="good", threshold=90.0, critical=True)],
    )
    report = await team.run("x")
    assert report.passed is True
    assert any("ungated" in w for w in report.warnings)


@pytest.mark.asyncio
async def test_cancellation_is_reraised_not_swallowed():
    """CancelledError (BaseException, not Exception) must propagate.

    ``gather(return_exceptions=True)`` DOES capture a child's
    CancelledError into the results list — the guard re-raises it
    instead of recording the cancellation as a mere agent failure.
    (KeyboardInterrupt/SystemExit never reach the guard: task
    machinery propagates them out of gather directly.)
    """

    class _CancelledAgent:
        key = "boom"

        async def run(self, target):  # noqa: ANN001
            raise asyncio.CancelledError

    team = AgentTeam(agents=[_CancelledAgent()], gates=[])
    with pytest.raises(asyncio.CancelledError):
        await team.run("x")
