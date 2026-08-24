"""Orchestration tests for ReleasePrepTeam (test-quality-program #1569).

Covers the seams the existing suites skip: the ``assess_readiness``
async fan-out (parallel agent execution → gates → blockers →
approval → confidence → report assembly), the Redis-optional
``__init__`` branches (fake redis_lib — no live server), and the
failed-security-agent sentinel branch in gate evaluation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

from attune.agents.release import release_prep_team as rpt
from attune.agents.release.release_models import ReleaseAgentResult, Tier


def result(
    role: str,
    findings: dict[str, Any],
    success: bool = True,
    score: float = 9.0,
    cost: float = 0.25,
) -> ReleaseAgentResult:
    return ReleaseAgentResult(
        agent_id=role.lower().replace(" ", "-"),
        agent_role=role,
        success=success,
        tier_used=Tier.CHEAP,
        findings=findings,
        score=score,
        confidence=0.9,
        cost=cost,
        execution_time_ms=5,
        escalated=False,
    )


GREEN = {
    "Security Auditor": {"critical_issues": 0},
    "Test Coverage": {"coverage_percent": 92.0},
    "Code Quality": {"quality_score": 9.1},
    "Documentation": {"coverage_percent": 88.0},
}


@dataclass
class StubAgent:
    """Stands in for a ReleaseAgent: records the path it was given."""

    reply: ReleaseAgentResult
    total_cost: float = 0.25
    seen_paths: list[str] = field(default_factory=list)

    def process(self, codebase_path: str) -> ReleaseAgentResult:
        self.seen_paths.append(codebase_path)
        return self.reply


def team_with(replies: dict[str, dict[str, Any]], **result_kw: Any) -> rpt.ReleasePrepTeam:
    """A ReleasePrepTeam whose four agents are stubs (no subprocess, no LLM)."""
    team = rpt.ReleasePrepTeam(redis_url=None)
    team.agents = [  # type: ignore[assignment]
        StubAgent(reply=result(role, findings, **result_kw)) for role, findings in replies.items()
    ]
    return team


class TestAssessReadiness:
    def test_all_green_approves_with_high_confidence(self):
        team = team_with(GREEN)
        report = asyncio.run(team.assess_readiness("some/path"))
        assert report.approved is True
        assert report.confidence == "high"
        assert report.blockers == [] and report.warnings == []
        assert [g.passed for g in report.quality_gates] == [True, True, True, True]
        assert "RELEASE APPROVED" in report.summary
        assert report.total_duration >= 0
        assert report.total_cost == pytest.approx(1.0)  # 4 stub agents x 0.25
        # every agent was fanned the same codebase path
        assert [a.seen_paths for a in team.agents] == [["some/path"]] * 4

    def test_noncritical_doc_failure_is_medium_confidence(self):
        replies = dict(GREEN)
        replies["Documentation"] = {"coverage_percent": 10.0}
        report = asyncio.run(team_with(replies).assess_readiness())
        assert report.approved is True  # doc gate is non-critical
        assert report.confidence == "medium"
        assert len(report.warnings) == 1 and "Documentation" in report.warnings[0]
        assert report.blockers == []

    def test_critical_coverage_failure_blocks_with_low_confidence(self):
        replies = dict(GREEN)
        replies["Test Coverage"] = {"coverage_percent": 12.0}
        report = asyncio.run(team_with(replies).assess_readiness())
        assert report.approved is False
        assert report.confidence == "low"
        assert any("Test Coverage" in b for b in report.blockers)
        assert "RELEASE NOT APPROVED" in report.summary

    def test_agent_error_surfaces_as_blocker(self):
        replies = dict(GREEN)
        team = team_with(replies)
        team.agents[1] = StubAgent(  # type: ignore[index]
            reply=result(
                "Test Coverage",
                {"coverage_percent": 95.0, "error": "pytest crashed"},
                success=False,
            )
        )
        report = asyncio.run(team.assess_readiness())
        assert report.approved is False
        assert any("pytest crashed" in b for b in report.blockers)

    def test_failed_security_agent_fails_gate_and_blocks(self):
        # The 2026-07-29 gate-hardening contract (chair-ruled): a
        # security agent that FAILED (success=False, even with no
        # error key) can never satisfy the Security gate — unknown is
        # not clean. The -1 sentinel stays as the DISPLAY value, the
        # gate fails, and the failed agent blocks with a fallback
        # reason even without diagnostic output.
        replies = dict(GREEN)
        team = team_with(replies)
        team.agents[0] = StubAgent(  # type: ignore[index]
            reply=result("Security Auditor", {}, success=False)
        )
        report = asyncio.run(team.assess_readiness())
        security_gate = next(g for g in report.quality_gates if g.name == "Security")
        assert security_gate.actual == -1.0
        assert security_gate.passed is False
        assert report.approved is False
        assert report.confidence == "low"
        assert any("failed without diagnostic output" in b for b in report.blockers)

    def test_missing_security_result_fails_gate(self):
        # No security result at all is the same unknown — the gate
        # cannot pass on absence.
        replies = {k: v for k, v in GREEN.items() if k != "Security Auditor"}
        report = asyncio.run(team_with(replies).assess_readiness())
        security_gate = next(g for g in report.quality_gates if g.name == "Security")
        assert security_gate.passed is False
        assert report.approved is False


class FakeRedisClient:
    def __init__(self, alive: bool = True):
        self.alive = alive

    def ping(self):
        if not self.alive:
            raise ConnectionError("no redis here")
        return True


class TestRedisOptionalInit:
    def test_redis_url_connects_and_reaches_agents(self, monkeypatch):
        client = FakeRedisClient()
        fake_lib = type("L", (), {"from_url": staticmethod(lambda url: client)})
        monkeypatch.setattr(rpt, "REDIS_AVAILABLE", True)
        monkeypatch.setattr(rpt, "redis_lib", fake_lib)
        team = rpt.ReleasePrepTeam(redis_url="redis://example:6379/0")
        assert team.redis is client
        assert all(agent.redis is client for agent in team.agents)

    def test_redis_url_ping_failure_degrades_to_none(self, monkeypatch):
        fake_lib = type(
            "L", (), {"from_url": staticmethod(lambda url: FakeRedisClient(alive=False))}
        )
        monkeypatch.setattr(rpt, "REDIS_AVAILABLE", True)
        monkeypatch.setattr(rpt, "redis_lib", fake_lib)
        team = rpt.ReleasePrepTeam(redis_url="redis://example:6379/0")
        assert team.redis is None

    # The two no-URL cases below use a REAL listening socket rather than a
    # patched ``redis_lib``. They previously asserted that a fake lib's
    # ``Redis(**kw)`` was called and were named "tries_localhost" —
    # pinning a literal endpoint, which is class H1: a team configured
    # against rediss://cache:6380/3 would have coordinated through a
    # different server, or none. Patching the lib also proved only that
    # the test handed itself its own fake (class M), never which endpoint
    # was dialled. The contract is now "no URL → the CONFIGURED endpoint".

    def test_no_url_uses_configured_endpoint(self, monkeypatch):
        from tests.support.redis_stub import RespStub

        stub = RespStub()
        monkeypatch.setattr(rpt, "REDIS_AVAILABLE", True)
        for name in ("ATTUNE_REDIS_URL", "REDIS_PASSWORD", "REDIS_HOST", "REDIS_PORT"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{stub.port}/0")
        try:
            team = rpt.ReleasePrepTeam()
            assert team.redis is not None, (
                "no-URL init did not reach the CONFIGURED endpoint, which a "
                "real server was answering on"
            )
            assert all(agent.redis is team.redis for agent in team.agents)
        finally:
            stub.close()

    def test_no_url_configured_endpoint_down_degrades_to_none(self, monkeypatch):
        from tests.support.redis_stub import closed_port

        monkeypatch.setattr(rpt, "REDIS_AVAILABLE", True)
        for name in ("ATTUNE_REDIS_URL", "REDIS_PASSWORD", "REDIS_HOST", "REDIS_PORT"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{closed_port()}/0")
        team = rpt.ReleasePrepTeam()
        assert team.redis is None

    def test_redis_unavailable_stays_none(self, monkeypatch):
        monkeypatch.setattr(rpt, "REDIS_AVAILABLE", False)
        team = rpt.ReleasePrepTeam(redis_url="redis://example:6379/0")
        assert team.redis is None


class TestGatherPartialFailure:
    """#2236: a raising agent becomes a failed result, never an abort."""

    def test_raising_agent_fails_its_gate_and_siblings_survive(self):
        team = team_with(GREEN)

        class _RaisingAgent:
            agent_id = "security-auditor"
            role = "Security Auditor"
            total_cost = 0.0

            def process(self, codebase_path: str) -> ReleaseAgentResult:
                raise RuntimeError("auditor exploded")

        # Replace the security agent with one that raises mid-process.
        team.agents[0] = _RaisingAgent()  # type: ignore[assignment]
        report = asyncio.run(team.assess_readiness("."))

        # A report is still produced, the crashed agent shows as a
        # FAILED result (a failed gatekeeper fails the gate), and the
        # three sibling results survive.
        failed = [r for r in report.agent_results if not r.success]
        assert [r.agent_id for r in failed] == ["security-auditor"]
        assert "RuntimeError" in failed[0].findings.get("error", "")
        assert len(report.agent_results) == 4
        assert report.approved is False
