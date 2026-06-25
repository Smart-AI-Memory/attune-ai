"""Tests for the Claude-driven agent-team driver (Phase 2).

Covers ``attune.orchestration.team_driver.describe_team_for_task`` — the
deterministic, no-LLM compose/preview surface the `agent` skill uses.

``run_team_for_task`` is NOT exercised here: it spins up a real
multi-agent LLM run (cost + the keyed-CI hazard), so it is left to
manual/integration use, mirroring the wizard driver tests.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.orchestration import describe_team_for_task, run_team_for_task


@pytest.mark.unit
class TestDescribeTeamForTask:
    def test_returns_serializable_plan(self) -> None:
        plan = describe_team_for_task("improve test coverage to 90%")
        assert plan["task"] == "improve test coverage to 90%"
        assert isinstance(plan["agents"], list)
        assert plan["agents"], "expected at least one composed agent"
        assert all("id" in a and "role" in a for a in plan["agents"])
        assert isinstance(plan["strategy"], str)
        # estimated_cost / quality_gates present and JSON-friendly
        assert "estimated_cost" in plan
        assert isinstance(plan["quality_gates"], list)

    def test_agents_come_from_real_templates(self) -> None:
        from attune.orchestration.agent_templates import get_registry

        known = set(get_registry().keys())
        plan = describe_team_for_task("audit this module for security issues")
        assert {a["id"] for a in plan["agents"]} <= known

    def test_empty_task_raises(self) -> None:
        with pytest.raises(ValueError):
            describe_team_for_task("")

    def test_describe_does_not_require_a_run(self) -> None:
        """Two previews are cheap/deterministic — same task, same agents."""
        a = describe_team_for_task("improve test coverage")
        b = describe_team_for_task("improve test coverage")
        assert [x["id"] for x in a["agents"]] == [x["id"] for x in b["agents"]]


@pytest.mark.unit
class TestRunTeamExported:
    def test_run_team_for_task_is_exported_and_async(self) -> None:
        """The skill drives runs through this; just confirm it's importable
        and a coroutine function (no execution — that would call LLMs)."""
        import inspect

        assert inspect.iscoroutinefunction(run_team_for_task)
