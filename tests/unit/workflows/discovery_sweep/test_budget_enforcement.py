"""Unit tests for discovery-sweep budget enforcement.

Covers the budget-enforcement spec
(``docs/specs/discovery-sweep-budget-enforcement/``):

* **FR-1** — ``get_max_budget_usd(depth, explicit=...)`` precedence:
  an explicit cap wins; ``None`` falls back to today's env/depth cap.
* **FR-2 / D2** — a source even-splits its allocation across ``paths``
  and passes each share down as the wrapped ``execute()``'s
  ``max_budget_usd``.
* **FR-3** — the floor guard skips runs (one info Finding, no
  ``execute()`` calls) when the per-call share is below
  :data:`MIN_PER_CALL_BUDGET_USD`; the cap-hit note fires when a run
  spent ~all of its share.

These are necessary-not-sufficient (mocks): the real spend ceiling is
proven by the de-nested dogfood (D5). ``SecurityAuditSource`` stands in
for all six LLM sources — the plumbing is identical across them.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from unittest.mock import patch

import pytest

from attune.workflows.agent_sdk_adapter import get_max_budget_usd
from attune.workflows.discovery_sweep.llm_source_base import (
    budget_too_small_finding,
    cap_hit_finding_if_bound,
)
from attune.workflows.discovery_sweep.sources.security_audit import (
    SecurityAuditSource,
)

_WF_PATH = "attune.workflows.security_audit.SecurityAuditWorkflow"


# ---------------------------------------------------------------------------
# Fakes — record execute() kwargs and carry an optional cost_report
# ---------------------------------------------------------------------------


@dataclass
class _FakeCostReport:
    total_cost: float = 0.0


@dataclass
class _FakeResult:
    success: bool = True
    final_output: str = ""
    cost_report: _FakeCostReport | None = None


@dataclass
class _RecordedCall:
    execute_kwargs: dict


@dataclass
class _FakeWorkflowFactory:
    """Stand-in for ``SecurityAuditWorkflow`` recording execute() calls."""

    results: list[_FakeResult] = field(default_factory=list)
    calls: list[_RecordedCall] = field(default_factory=list)

    def __call__(self, **_init_kwargs):
        index = len(self.calls)
        recorded = _RecordedCall(execute_kwargs={})

        async def _execute(**execute_kwargs):
            recorded.execute_kwargs = execute_kwargs
            if index < len(self.results):
                return self.results[index]
            return _FakeResult(success=True, final_output="")

        self.calls.append(recorded)
        return type("FakeInstance", (), {"execute": staticmethod(_execute)})()


def _empty_findings_output() -> str:
    return f"prose\n\n```json\n{json.dumps({'findings': []})}\n```\n"


# ---------------------------------------------------------------------------
# FR-1 — get_max_budget_usd precedence
# ---------------------------------------------------------------------------


def test_explicit_cap_wins_over_env_and_depth(monkeypatch) -> None:
    """An explicit cap overrides both the env var and the depth default."""
    monkeypatch.setenv("ATTUNE_MAX_BUDGET_USD", "9.99")
    assert get_max_budget_usd("standard", explicit=0.25) == 0.25


def test_explicit_none_falls_back_to_env(monkeypatch) -> None:
    """``explicit=None`` preserves today's env-override behavior."""
    monkeypatch.setenv("ATTUNE_MAX_BUDGET_USD", "3.5")
    assert get_max_budget_usd("standard") == 3.5


def test_explicit_none_falls_back_to_depth_default(monkeypatch) -> None:
    """No env var + ``explicit=None`` → the depth-derived default."""
    monkeypatch.delenv("ATTUNE_MAX_BUDGET_USD", raising=False)
    assert get_max_budget_usd("standard") is not None


# ---------------------------------------------------------------------------
# FR-2 / D2 — even-split across paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_path_passes_whole_allocation() -> None:
    """One path → the wrapped execute() gets the full allocation as its cap."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(final_output=_empty_findings_output())],
    )
    with patch(_WF_PATH, new=factory):
        await SecurityAuditSource().discover(["src/"], budget_usd=4.0)

    assert factory.calls[0].execute_kwargs["max_budget_usd"] == 4.0


@pytest.mark.asyncio
async def test_multi_path_even_splits_allocation() -> None:
    """N paths → each execute() gets ``allocation / N`` as its cap (D2)."""
    factory = _FakeWorkflowFactory(
        results=[
            _FakeResult(final_output=_empty_findings_output()),
            _FakeResult(final_output=_empty_findings_output()),
            _FakeResult(final_output=_empty_findings_output()),
        ],
    )
    with patch(_WF_PATH, new=factory):
        await SecurityAuditSource().discover(["a/", "b/", "c/"], budget_usd=6.0)

    assert len(factory.calls) == 3
    for call in factory.calls:
        assert call.execute_kwargs["max_budget_usd"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# FR-3 — floor guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_floor_guard_skips_all_runs() -> None:
    """Per-call share below the floor → one info Finding, zero execute()s."""
    n_paths = 100
    factory = _FakeWorkflowFactory()
    with patch(_WF_PATH, new=factory):
        # 100 paths share $1 → $0.01 each, below the $0.05 floor.
        findings = await SecurityAuditSource().discover(
            [f"p{i}/" for i in range(n_paths)], budget_usd=1.0
        )

    assert factory.calls == []  # no doomed near-zero runs fired
    assert len(findings) == 1
    only = findings[0]
    assert only.severity == "info"
    assert "budget-cap" in only.tags
    # file=None + no file-level tag → routes to the questions bucket.
    assert only.file is None
    assert "file-level" not in only.tags


def test_budget_too_small_finding_shape() -> None:
    """The floor-guard Finding is info-severity and questions-routable."""
    finding = budget_too_small_finding("security-audit", 50, 0.02, 1.0)
    assert finding.severity == "info"
    assert finding.file is None
    assert finding.tags == ("budget-cap",)


@pytest.mark.asyncio
async def test_floor_boundary_share_at_min_runs() -> None:
    """A share exactly at the floor runs (the guard is strict ``<``)."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(final_output=_empty_findings_output())],
    )
    source = SecurityAuditSource()
    with patch(_WF_PATH, new=factory):
        # single path, allocation == the source's own floor (#2214:
        # per-source min_useful_usd, above the generic MIN) → share ==
        # floor → not below → runs.
        await source.discover(["src/"], budget_usd=source.min_useful_usd)

    assert len(factory.calls) == 1
    assert factory.calls[0].execute_kwargs["max_budget_usd"] == source.min_useful_usd


# ---------------------------------------------------------------------------
# FR-3 — cap-hit note (cost-proximity, SDK-independent)
# ---------------------------------------------------------------------------


def test_cap_hit_finding_when_cost_near_share() -> None:
    """Cost ≥ 95% of the share → an info Finding flagging the ceiling."""
    result = _FakeResult(cost_report=_FakeCostReport(total_cost=0.97))
    finding = cap_hit_finding_if_bound("security-audit", "src/", result, 1.0)
    assert finding is not None
    assert finding.severity == "info"
    assert finding.file is None  # questions-routable
    assert "budget-cap" in finding.tags


def test_no_cap_hit_when_cost_low() -> None:
    """Cost well under the share → no note (the run finished comfortably)."""
    result = _FakeResult(cost_report=_FakeCostReport(total_cost=0.10))
    assert cap_hit_finding_if_bound("security-audit", "src/", result, 1.0) is None


def test_no_cap_hit_when_no_cap_applied() -> None:
    """``share=None`` (no cap) → never a cap-hit note."""
    result = _FakeResult(cost_report=_FakeCostReport(total_cost=9.0))
    assert cap_hit_finding_if_bound("security-audit", "src/", result, None) is None


def test_no_cap_hit_when_no_cost_report() -> None:
    """A result without a cost_report contributes no cap-hit note."""
    result = _FakeResult(cost_report=None)
    assert cap_hit_finding_if_bound("security-audit", "src/", result, 1.0) is None


@pytest.mark.asyncio
async def test_cap_hit_note_appended_after_findings() -> None:
    """A near-cap run yields its parsed findings PLUS one cap-hit note."""
    factory = _FakeWorkflowFactory(
        results=[
            _FakeResult(
                final_output=_empty_findings_output(),
                cost_report=_FakeCostReport(total_cost=4.0),
            ),
        ],
    )
    with patch(_WF_PATH, new=factory):
        findings = await SecurityAuditSource().discover(["src/"], budget_usd=4.0)

    cap_notes = [f for f in findings if "budget-cap" in f.tags]
    assert len(cap_notes) == 1
    assert cap_notes[0].severity == "info"
