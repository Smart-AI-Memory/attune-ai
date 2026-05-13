"""Tests for the BaseWorkflow CLI wrapper and registry registration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep import (
    DiscoverySweepWorkflow,
    Finding,
    PatternScanSource,
    Severity,
    read_jsonl,
)


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@dataclass
class _CannedSource:
    """A FindingSource double that emits canned Findings."""

    name: str = "canned"
    canned: list[Finding] | None = None
    estimated_spend_usd: float = 0.5

    def discover(self, scope: Path, budget_usd: float, sweep_id: str) -> Iterable[Finding]:
        for f in self.canned or []:
            yield Finding(
                source_workflow=f.source_workflow,
                file_path=f.file_path,
                severity=f.severity,
                message=f.message,
                raw_finding=f.raw_finding,
                sweep_id=sweep_id,
                line=f.line,
            )


@pytest.mark.asyncio
async def test_execute_requires_path():
    wf = DiscoverySweepWorkflow()
    result = await wf.execute()
    assert result.success is False
    assert "path" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_execute_with_default_pattern_scanner(tmp_path):
    _write(
        tmp_path / "fragile.py",
        [
            "def fragile():",
            "    try:",
            "        pass",
            "    except:",
            "        pass",
        ],
    )
    wf = DiscoverySweepWorkflow()
    result = await wf.execute(path=str(tmp_path), output_dir=str(tmp_path / "queue"))

    assert result.success is True
    assert result.metadata["sweep_id"]
    # The bare-except finding survives REJECT (no INTENTIONAL marker) →
    # UNSURE in the questions file.
    assert result.metadata["unsure_count"] >= 1
    assert result.metadata["queue_path"]
    assert Path(result.metadata["queue_path"]).exists()
    assert Path(result.metadata["rejected_path"]).exists()
    assert Path(result.metadata["questions_path"]).exists()


@pytest.mark.asyncio
async def test_execute_with_custom_sources(tmp_path):
    finding = Finding(
        source_workflow="canned",
        file_path="src/attune/whatever.py",
        severity=Severity.MEDIUM,
        message="some finding",
        raw_finding={"pattern": "x"},
        sweep_id="placeholder",
        line=10,
    )
    wf = DiscoverySweepWorkflow()
    result = await wf.execute(
        path=str(tmp_path),
        output_dir=str(tmp_path / "queue"),
        sources=[_CannedSource(canned=[finding])],
    )
    assert result.success is True
    # The canned finding has no matching rule → UNSURE.
    assert result.metadata["unsure_count"] == 1
    assert result.metadata["accept_count"] == 0


@pytest.mark.asyncio
async def test_execute_budget_overrides_propagate(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_DISCOVERY_SWEEP_BUDGET_USD", "100.0")
    wf = DiscoverySweepWorkflow()
    result = await wf.execute(
        path=str(tmp_path),
        output_dir=str(tmp_path / "queue"),
        sweep_budget_usd=2.0,
    )
    assert result.success is True
    # No findings, but budget metadata is exposed via the sweep result.
    assert "sweep_result" in result.metadata


@pytest.mark.asyncio
async def test_execute_writes_to_default_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(
        tmp_path / "fragile.py",
        ["def f():", "    try: pass", "    except: pass"],
    )
    wf = DiscoverySweepWorkflow()
    result = await wf.execute(path=str(tmp_path))
    assert result.success is True
    assert ".claude/discovery-queue" in result.metadata["queue_path"].replace("\\", "/")


@pytest.mark.asyncio
async def test_execute_summary_contains_counts(tmp_path):
    _write(
        tmp_path / "fragile.py",
        ["def f():", "    try: pass", "    except: pass"],
    )
    wf = DiscoverySweepWorkflow()
    result = await wf.execute(path=str(tmp_path), output_dir=str(tmp_path / "out"))
    assert result.summary is not None
    assert "accept=" in result.summary
    assert "reject=" in result.summary
    assert "unsure=" in result.summary
    assert result.metadata["sweep_id"] in result.summary


@pytest.mark.asyncio
async def test_real_pattern_scanner_finds_findings_in_seeded_tree(tmp_path):
    """End-to-end: real PatternScanSource against a real fixture tree."""
    src = tmp_path / "src"
    src.mkdir()
    _write(
        src / "fragile.py",
        [
            "import subprocess",
            "",
            "def go(cmd):",
            "    # TODO: validate cmd",
            "    try:",
            "        subprocess.run(cmd)",
            "    except:",
            "        pass",
        ],
    )

    wf = DiscoverySweepWorkflow()
    result = await wf.execute(
        path=str(src),
        output_dir=str(tmp_path / "queue"),
        sources=[PatternScanSource()],
    )
    assert result.success is True
    total = (
        result.metadata["accept_count"]
        + result.metadata["reject_count"]
        + result.metadata["unsure_count"]
    )
    # bare_except + TODO at minimum → 2 findings.
    assert total >= 2

    # The bare_except finding lands somewhere — queue or questions.
    rejected = read_jsonl(result.metadata["rejected_path"])
    # No intentional-broad-except marker, so it shouldn't REJECT.
    assert all(
        f.raw_finding.get("pattern") != "bare_except" for f in rejected
    ), "bare_except without INTENTIONAL should not be REJECTed"


class TestWorkflowRegistry:
    def test_discovery_sweep_registered(self):
        from attune.workflows import discover_workflows

        wfs = discover_workflows()
        assert "discovery-sweep" in wfs
        assert wfs["discovery-sweep"] is DiscoverySweepWorkflow

    def test_workflow_has_required_baseworkflow_surface(self):
        from attune.workflows.base import BaseWorkflow

        assert issubclass(DiscoverySweepWorkflow, BaseWorkflow)
        assert DiscoverySweepWorkflow.name == "discovery-sweep"
        assert isinstance(DiscoverySweepWorkflow.description, str)
        assert DiscoverySweepWorkflow.description
        assert DiscoverySweepWorkflow.stages
