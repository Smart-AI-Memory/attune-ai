"""Unit tests for DiscoverySweepWorkflow.execute().

Covers:

- Happy path with two fake sources (one returns findings, one raises)
- Budget allocation between LLM and non-LLM sources
- ``no_llm`` filter
- ``path`` validation
- Source-failure isolation (per spec NFR-1)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from attune.workflows.discovery_sweep import (
    DEFAULT_BUDGET_USD,
    DiscoverySweepWorkflow,
    Finding,
    SweepResult,
)


@dataclass
class FakeSource:
    """Test double conforming structurally to FindingSource.

    ``budget_multiplier`` defaults to ``1.0`` for LLM sources and
    ``0.0`` for non-LLM sources via ``__post_init__`` so tests can omit
    it unless they want a specific share.
    """

    name: str
    is_llm: bool = True
    budget_multiplier: float | None = None
    findings: list[Finding] | None = None
    raises: BaseException | None = None
    received_budget: float | None = None
    received_paths: list[str] | None = None

    def __post_init__(self) -> None:
        if self.budget_multiplier is None:
            self.budget_multiplier = 1.0 if self.is_llm else 0.0

    async def discover(self, paths: list[str], budget_usd: float) -> list[Finding]:
        self.received_paths = list(paths)
        self.received_budget = budget_usd
        if self.raises is not None:
            raise self.raises
        return list(self.findings or [])


def _finding(**overrides: object) -> Finding:
    base: dict[str, object] = {
        "source": "fake",
        "severity": "high",
        "title": "t",
        "description": "d",
        "file": "src/a.py",
        "line": 10,
        "evidence": None,
        "confidence": 0.9,
        "tags": (),
    }
    base.update(overrides)
    return Finding(**base)  # type: ignore[arg-type]


class TestExecuteHappyPath:
    def test_findings_route_to_queue(self) -> None:
        src = FakeSource(name="fake-src", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        assert res.success is True
        sweep: SweepResult = res.metadata["sweep"]
        assert len(sweep.queue) == 1
        assert sweep.queue[0].source == "fake"
        assert sweep.metadata.sources == ["fake-src"]
        assert sweep.metadata.failures == []

    def test_two_sources_one_findings_one_raises(self) -> None:
        good = FakeSource(name="good", findings=[_finding()])
        bad = FakeSource(name="bad", raises=RuntimeError("boom"))
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[good, bad]))
        sweep: SweepResult = res.metadata["sweep"]
        # Good source's finding makes it through.
        assert len(sweep.queue) == 1
        # Bad source surfaces as a question, not a sweep-level failure.
        assert any(q.reason == "SOURCE_FAILED" for q in sweep.questions)
        assert sweep.metadata.failures == ["bad: RuntimeError"]
        assert sweep.metadata.sources == ["good", "bad"]
        assert res.success is True

    def test_final_output_renders_buckets(self) -> None:
        src = FakeSource(name="fake-src", findings=[_finding()])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[src]))
        assert isinstance(res.final_output, str)
        assert "## Queue" in res.final_output
        assert "## Questions" in res.final_output
        assert "## Rejected" in res.final_output


class TestBudgetAllocation:
    def test_per_source_budget_splits_across_llm_only(self) -> None:
        # Two LLM sources with default multiplier=1.0; one non-LLM
        # source with multiplier=0.0 (excluded from the pool).
        llm_a = FakeSource(name="llm-a", is_llm=True, findings=[])
        llm_b = FakeSource(name="llm-b", is_llm=True, findings=[])
        non_llm = FakeSource(name="pattern", is_llm=False, findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(
            wf.execute(
                path="src/",
                budget_usd=10.0,
                sources=[llm_a, llm_b, non_llm],
            )
        )
        # 10.00 * (1.0 / 2.0) = 5.00 to each LLM source.
        assert llm_a.received_budget == pytest.approx(5.0)
        assert llm_b.received_budget == pytest.approx(5.0)
        # Non-LLM gets 0.0 — it sums to a zero share of the pool.
        assert non_llm.received_budget == pytest.approx(0.0)

    def test_proportional_allocation_by_multiplier(self) -> None:
        # Mirrors the spec defaults: security-audit gets a 4x share,
        # dependency-check 0.5x, default 1.0x.
        heavy = FakeSource(name="security", is_llm=True, budget_multiplier=4.0, findings=[])
        light = FakeSource(name="deps", is_llm=True, budget_multiplier=0.5, findings=[])
        default = FakeSource(name="bug", is_llm=True, budget_multiplier=1.0, findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(
            wf.execute(path="src/", budget_usd=11.0, sources=[heavy, light, default]),
        )
        total = 4.0 + 0.5 + 1.0
        assert heavy.received_budget == pytest.approx(11.0 * 4.0 / total)
        assert light.received_budget == pytest.approx(11.0 * 0.5 / total)
        assert default.received_budget == pytest.approx(11.0 * 1.0 / total)

    def test_no_llm_sources_passes_full_budget(self) -> None:
        non_llm = FakeSource(name="pattern", is_llm=False, findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="src/", budget_usd=7.50, sources=[non_llm]))
        # With no positive-multiplier sources, the engine passes the
        # full budget through as a signal — non-LLM ignores it anyway.
        assert non_llm.received_budget == pytest.approx(7.50)

    def test_default_budget_is_ten_dollars(self) -> None:
        assert DEFAULT_BUDGET_USD == 10.00


class TestPathExpansion:
    def test_non_glob_path_passed_through(self) -> None:
        src = FakeSource(name="s", findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="src/attune/", sources=[src]))
        assert src.received_paths == ["src/attune/"]

    def test_glob_pattern_expanded(self, tmp_path: object) -> None:
        # Build two files matching a glob, one not.
        from pathlib import Path as _P

        base = _P(str(tmp_path))
        (base / "a.py").write_text("x = 1\n", encoding="utf-8")
        (base / "b.py").write_text("x = 1\n", encoding="utf-8")
        (base / "c.txt").write_text("ignore\n", encoding="utf-8")

        src = FakeSource(name="s", findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path=str(base / "*.py"), sources=[src]))
        assert src.received_paths is not None
        # Sorted glob result. Only .py files matched.
        assert all(p.endswith(".py") for p in src.received_paths)
        assert len(src.received_paths) == 2

    def test_glob_with_no_matches_falls_back_to_pattern(self) -> None:
        src = FakeSource(name="s", findings=[])
        wf = DiscoverySweepWorkflow()
        asyncio.run(wf.execute(path="nonexistent/**/*.zzz", sources=[src]))
        # Falls back to the raw pattern so sources can report it.
        assert src.received_paths == ["nonexistent/**/*.zzz"]


class TestSourceFiltering:
    def test_no_llm_filters_llm_sources(self) -> None:
        llm = FakeSource(name="llm", is_llm=True, findings=[_finding()])
        pat = FakeSource(name="pat", is_llm=False, findings=[])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[llm, pat], no_llm=True))
        sweep: SweepResult = res.metadata["sweep"]
        assert sweep.metadata.sources == ["pat"]
        # llm source never ran (no findings reached the queue).
        assert sweep.queue == []

    def test_no_sources_after_filter_errors(self) -> None:
        llm = FakeSource(name="llm", is_llm=True, findings=[])
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(path="src/", sources=[llm], no_llm=True))
        assert res.success is False
        assert "no sources to run" in (res.error or "")


class TestValidation:
    def test_missing_path_errors(self) -> None:
        wf = DiscoverySweepWorkflow()
        res = asyncio.run(wf.execute(sources=[]))
        assert res.success is False
        assert "path argument is required" in (res.error or "")
