"""Unit tests for the discovery-sweep engine's event_sink API.

Spec: docs/specs/discovery-sweep-ops-integration/design.md
      (Phase 1 — engine telemetry API)

Covers:

- ``event_sink=None`` is a no-op (preserves today's CLI behavior).
- The sink receives ``source_started`` + (``source_finished`` xor
  ``source_failed``) — exactly one start + one terminal event per
  source per run.
- Event payload shape matches the spec (event/source/sweep_id/ts/
  findings_count|error).
- A sink that raises does not propagate into the sweep result.
- A slow sink does not block other sources' execution
  (fire-and-forget via ``asyncio.create_task``).
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import pytest

from attune.workflows.discovery_sweep import (
    DiscoverySweepWorkflow,
    Finding,
    SweepResult,
)


@dataclass
class FakeSource:
    """Test double — same shape as the FakeSource in test_engine.py."""

    name: str
    is_llm: bool = True
    budget_multiplier: float | None = None
    findings: list[Finding] | None = None
    raises: BaseException | None = None
    delay: float = 0.0

    def __post_init__(self) -> None:
        if self.budget_multiplier is None:
            self.budget_multiplier = 1.0 if self.is_llm else 0.0

    async def discover(self, paths: list[str], budget_usd: float) -> list[Finding]:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.raises is not None:
            raise self.raises
        return list(self.findings or [])


def _finding() -> Finding:
    return Finding(
        source="fake",
        severity="high",
        title="t",
        description="d",
        file="src/a.py",
        line=10,
        evidence=None,
        confidence=0.9,
        tags=(),
    )


async def _drain_pending_tasks() -> None:
    """Yield enough times for fire-and-forget emit tasks to complete.

    The engine emits events via ``asyncio.create_task``; the test
    body needs to let those tasks run to completion before
    assertions on the captured-event list. Multiple yields cover
    chained awaits inside _safe_emit.
    """
    for _ in range(5):
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# Behavior — sink wiring
# ---------------------------------------------------------------------------


class TestEventSinkNoneIsNoOp:
    def test_no_kwarg_passes(self) -> None:
        src = FakeSource(name="s", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        assert res.success is True

    def test_explicit_none_kwarg(self) -> None:
        src = FakeSource(name="s", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src], event_sink=None, sweep_id=None))
        assert res.success is True


class TestEventSinkHappyPath:
    @pytest.mark.asyncio
    async def test_started_then_finished_on_success(self) -> None:
        events: list[dict] = []

        async def sink(event: dict) -> None:
            events.append(event)

        src = FakeSource(name="alpha", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        await wf.execute(path="src/", sources=[src], event_sink=sink, sweep_id="run-x")
        await _drain_pending_tasks()

        kinds = [e["event"] for e in events]
        assert kinds == ["source_started", "source_finished"]
        for e in events:
            assert e["source"] == "alpha"
            assert e["sweep_id"] == "run-x"
            assert isinstance(e["ts"], str)
            assert re.match(r"\d{4}-\d{2}-\d{2}T", e["ts"])
        finished = events[1]
        assert finished["findings_count"] == 1

    @pytest.mark.asyncio
    async def test_started_then_failed_on_raise(self) -> None:
        events: list[dict] = []

        async def sink(event: dict) -> None:
            events.append(event)

        src = FakeSource(name="bad", raises=RuntimeError("boom"))
        wf = DiscoverySweepWorkflow()
        await wf.execute(path="src/", sources=[src], event_sink=sink, sweep_id="run-y")
        await _drain_pending_tasks()

        kinds = [e["event"] for e in events]
        assert kinds == ["source_started", "source_failed"]
        failed = events[1]
        assert failed["source"] == "bad"
        assert failed["sweep_id"] == "run-y"
        assert failed["error"] == "RuntimeError"

    @pytest.mark.asyncio
    async def test_two_sources_emit_independently(self) -> None:
        events: list[dict] = []

        async def sink(event: dict) -> None:
            events.append(event)

        good = FakeSource(name="good", findings=[_finding()])
        bad = FakeSource(name="bad", raises=ValueError("nope"))
        wf = DiscoverySweepWorkflow()
        res = await wf.execute(
            path="src/",
            sources=[good, bad],
            event_sink=sink,
            sweep_id="run-z",
        )
        await _drain_pending_tasks()

        # Exactly four events: one started + one terminal per source.
        kinds_by_source: dict[str, list[str]] = {}
        for e in events:
            kinds_by_source.setdefault(e["source"], []).append(e["event"])
        assert kinds_by_source["good"] == ["source_started", "source_finished"]
        assert kinds_by_source["bad"] == ["source_started", "source_failed"]

        # Sweep itself still succeeds — bad source surfaces as a question.
        sweep: SweepResult = res.metadata["sweep"]
        assert res.success is True
        assert any(q.reason == "SOURCE_FAILED" for q in sweep.questions)


# ---------------------------------------------------------------------------
# Behavior — fault tolerance
# ---------------------------------------------------------------------------


class TestSinkFaultTolerance:
    @pytest.mark.asyncio
    async def test_raising_sink_does_not_break_sweep(self, caplog) -> None:
        async def angry_sink(event: dict) -> None:
            raise RuntimeError(f"sink-failed-for-{event['event']}")

        src = FakeSource(name="s", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        res = await wf.execute(path="src/", sources=[src], event_sink=angry_sink, sweep_id="r")
        await _drain_pending_tasks()
        assert res.success is True
        sweep: SweepResult = res.metadata["sweep"]
        assert len(sweep.queue) == 1
        # _safe_emit logs at exception level — verify at least one
        # message references the sink failure so the operator has a
        # diagnostic.
        assert any("event_sink failed" in rec.getMessage() for rec in caplog.records), [
            r.getMessage() for r in caplog.records
        ]

    @pytest.mark.asyncio
    async def test_slow_sink_does_not_block_sources(self) -> None:
        # The sink awaits a long sleep; if events were awaited inline,
        # the sweep would take ~10s. Fire-and-forget delivery means the
        # sweep returns in well under a second.
        sink_event = asyncio.Event()

        async def slow_sink(event: dict) -> None:
            try:
                await asyncio.wait_for(sink_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                return

        src = FakeSource(name="fast", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        t0 = asyncio.get_event_loop().time()
        await wf.execute(path="src/", sources=[src], event_sink=slow_sink, sweep_id="r")
        elapsed = asyncio.get_event_loop().time() - t0
        sink_event.set()  # release parked sink tasks promptly

        # Sweep must finish while sinks are still waiting. The bound
        # distinguishes REGIMES, not speed: inline-awaited delivery
        # would take ~10s (the sink's wait), fire-and-forget takes
        # well under a second on a quiet machine — but a loaded CI
        # runner was measured at 1.578s (windows-latest under xdist,
        # 2026-08-01), so a 1.0s bound flaked without any blocking.
        # 5.0s keeps ≥2x margin against both regimes.
        assert elapsed < 5.0, f"sweep took {elapsed:.3f}s, expected well under the sink's 10s wait"

        # Release the still-pending sink tasks so the test loop exits
        # cleanly without a "Task was destroyed but it is pending"
        # warning.
        sink_event.set()
        await _drain_pending_tasks()


# ---------------------------------------------------------------------------
# Behavior — payload shape (spec contract)
# ---------------------------------------------------------------------------


class TestEventShape:
    @pytest.mark.asyncio
    async def test_started_event_keys(self) -> None:
        events: list[dict] = []

        async def sink(event: dict) -> None:
            events.append(event)

        src = FakeSource(name="s", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        await wf.execute(path="src/", sources=[src], event_sink=sink, sweep_id="r")
        await _drain_pending_tasks()

        started = next(e for e in events if e["event"] == "source_started")
        assert set(started.keys()) == {"event", "source", "sweep_id", "ts"}

    @pytest.mark.asyncio
    async def test_finished_event_keys(self) -> None:
        events: list[dict] = []

        async def sink(event: dict) -> None:
            events.append(event)

        src = FakeSource(name="s", findings=[_finding(), _finding()])
        wf = DiscoverySweepWorkflow()
        await wf.execute(path="src/", sources=[src], event_sink=sink, sweep_id="r")
        await _drain_pending_tasks()

        finished = next(e for e in events if e["event"] == "source_finished")
        assert set(finished.keys()) == {
            "event",
            "source",
            "sweep_id",
            "ts",
            "findings_count",
        }
        assert finished["findings_count"] == 2

    @pytest.mark.asyncio
    async def test_failed_event_keys(self) -> None:
        events: list[dict] = []

        async def sink(event: dict) -> None:
            events.append(event)

        src = FakeSource(name="s", raises=KeyError("missing"))
        wf = DiscoverySweepWorkflow()
        await wf.execute(path="src/", sources=[src], event_sink=sink, sweep_id="r")
        await _drain_pending_tasks()

        failed = next(e for e in events if e["event"] == "source_failed")
        assert set(failed.keys()) == {
            "event",
            "source",
            "sweep_id",
            "ts",
            "error",
        }
        assert failed["error"] == "KeyError"

    @pytest.mark.asyncio
    async def test_sweep_id_none_propagates(self) -> None:
        events: list[dict] = []

        async def sink(event: dict) -> None:
            events.append(event)

        src = FakeSource(name="s", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        # Pass an event_sink but no sweep_id — sweep_id field must
        # still appear in every event payload (set to None) so
        # parsers don't have to special-case its absence.
        await wf.execute(path="src/", sources=[src], event_sink=sink)
        await _drain_pending_tasks()
        for e in events:
            assert "sweep_id" in e
            assert e["sweep_id"] is None
