"""Engine tests for DiscoverySweepWorkflow.

Covers the Phase 1 happy path: two fake sources fanned out
via ``asyncio.gather`` — one returning findings, one raising
— with verification rules + bucketing applied at the end.
"""

from __future__ import annotations

import pytest

from attune.workflows.discovery_sweep import (
    DiscoverySweepWorkflow,
    Finding,
    SweepResult,
)


class _FakeSource:
    """Minimal FindingSource that returns a fixed list."""

    is_llm = False  # treat as free so budget doesn't fan out

    def __init__(self, name: str, findings: list[Finding]) -> None:
        self.name = name
        self._findings = findings
        self.called_with: tuple[str, float] | None = None

    async def discover(self, path: str, budget_usd: float) -> list[Finding]:
        self.called_with = (path, budget_usd)
        return list(self._findings)


class _CrashingSource:
    """FindingSource that raises — engine must route to questions."""

    name = "crash-test"
    is_llm = False

    async def discover(self, path: str, budget_usd: float) -> list[Finding]:
        raise RuntimeError("simulated source failure")


@pytest.mark.asyncio
async def test_execute_routes_findings_and_isolates_crashes(tmp_path) -> None:
    good = _FakeSource(
        "good-source",
        [
            Finding(
                source="good-source",
                severity="high",
                title="bad-thing",
                description="...",
                file="a.py",
                line=10,
                confidence=0.9,
            ),
            Finding(
                source="good-source",
                severity="low",
                title="noise",
                description="...",
                file="a.py",
                line=20,
                confidence=0.9,
            ),
        ],
    )
    crash = _CrashingSource()

    wf = DiscoverySweepWorkflow(sources=[good, crash])
    result = await wf.execute(path=str(tmp_path), budget_usd=0.0)

    assert result.success is True
    sweep: SweepResult = result.metadata["sweep_result"]

    # High-severity finding is in queue.
    assert len(sweep.queue) == 1
    assert sweep.queue[0].title == "bad-thing"

    # Low-severity is rejected by the severity-threshold rule.
    assert any(r.rule == "SEVERITY_BELOW_THRESHOLD" for r in sweep.rejected)

    # Crashed source contributes a single questions entry.
    crash_questions = [q for q in sweep.questions if q.finding.source == "crash-test"]
    assert len(crash_questions) == 1
    assert "simulated source failure" in crash_questions[0].finding.description

    # Metadata mentions both sources, and lists the crash in failures.
    md = sweep.metadata
    assert set(md.sources) == {"good-source", "crash-test"}
    assert md.failures == ["crash-test"]

    # Good source was actually awaited with the resolved path.
    assert good.called_with is not None
    awaited_path, _ = good.called_with
    assert awaited_path.endswith(str(tmp_path))


@pytest.mark.asyncio
async def test_execute_no_llm_filters_llm_sources(tmp_path) -> None:
    """``no_llm=True`` keeps non-LLM sources and drops LLM-marked ones."""

    class _LLMFake:
        name = "llm-fake"
        is_llm = True

        async def discover(self, path: str, budget_usd: float) -> list[Finding]:
            return [
                Finding(
                    source="llm-fake",
                    severity="high",
                    title="should-not-appear",
                    description="...",
                    file="x.py",
                    line=1,
                    confidence=0.9,
                )
            ]

    deterministic = _FakeSource("det", [])
    llm = _LLMFake()
    wf = DiscoverySweepWorkflow(sources=[deterministic, llm])

    result = await wf.execute(path=str(tmp_path), no_llm=True)
    sweep: SweepResult = result.metadata["sweep_result"]

    # LLM source was filtered out — not awaited, not in metadata.
    assert "llm-fake" not in sweep.metadata.sources
    assert "det" in sweep.metadata.sources
    assert all(f.source != "llm-fake" for f in sweep.queue)
