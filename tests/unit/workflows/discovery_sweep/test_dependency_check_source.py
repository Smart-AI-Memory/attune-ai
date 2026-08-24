"""Unit tests for :class:`DependencyCheckSource`.

Mocks ``DependencyCheckWorkflow`` at its source module (per the
existing CLAUDE.md lesson on deferred imports) so no
``claude_agent_sdk`` traffic happens during these tests.
Integration coverage gated on
``@pytest.mark.integration`` lives in
``tests/integration/test_discovery_sweep_dependency_check_integration.py``.

Same shape as the P2.1 / P2.2 adapter test files — every Phase 2B
adapter is testable from this pattern.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from unittest.mock import patch

import pytest

from attune.workflows.discovery_sweep import Finding
from attune.workflows.discovery_sweep.cli_workflow import default_sources
from attune.workflows.discovery_sweep.llm_source_base import (
    MIN_PER_CALL_BUDGET_USD,
    STRUCTURED_EMIT_FOOTER,
)
from attune.workflows.discovery_sweep.sources.dependency_check import (
    DependencyCheckSource,
)

SOURCE = "dependency-check"


@dataclass
class _FakeResult:
    """Mirrors the shape :func:`parse_findings_json` reads from."""

    success: bool = True
    final_output: str = ""
    cost_report: object | None = None


@dataclass
class _RecordedCall:
    init_kwargs: dict
    execute_kwargs: dict


@dataclass
class _FakeWorkflowFactory:
    """Hand-rolled stand-in for ``DependencyCheckWorkflow``."""

    results: list[_FakeResult] = field(default_factory=list)
    side_effects: list[Exception | None] = field(default_factory=list)
    calls: list[_RecordedCall] = field(default_factory=list)

    def __call__(self, **kwargs):
        instance_index = len(self.calls)
        recorded = _RecordedCall(init_kwargs=kwargs, execute_kwargs={})

        async def _execute(**execute_kwargs):
            recorded.execute_kwargs = execute_kwargs
            if instance_index < len(self.side_effects):
                exc = self.side_effects[instance_index]
                if exc is not None:
                    raise exc
            if instance_index < len(self.results):
                return self.results[instance_index]
            return _FakeResult(success=True, final_output="")

        instance = type(
            "FakeInstance",
            (),
            {"execute": staticmethod(_execute)},
        )()
        self.calls.append(recorded)
        return instance


def _wrap_json(payload: dict) -> str:
    return f"prose\n\n```json\n{json.dumps(payload)}\n```\n"


def _wellformed_payload() -> dict:
    return {
        "findings": [
            {
                "severity": "high",
                "title": "vulnerable requests version",
                "description": "CVE-2024-XXXXX affects requests<2.32.0.",
                "file": "pyproject.toml",
                "line": 12,
                "evidence": 'requests = ">=2.30.0"',
                "confidence": 0.9,
                "tags": ["cve", "outdated"],
            }
        ]
    }


# ---------------------------------------------------------------------------
# Source-level attributes
# ---------------------------------------------------------------------------


def test_source_defaults() -> None:
    """Defaults: 1.0 multiplier + quick depth + honest floor (#2214).

    The old 0.5 multiplier under-allocated below the workflow's
    measured cost, so the lane aborted at its cap on every sweep.
    """
    source = DependencyCheckSource()
    assert source.name == SOURCE
    assert source.is_llm is True
    assert source.budget_multiplier == 1.0
    assert source.depth == "quick"
    assert source.min_useful_usd == 0.40


def test_source_appears_in_default_sources() -> None:
    """Wired into ``default_sources()`` per task P2.3 step 5."""
    sources = default_sources()
    matched = [s for s in sources if s.name == SOURCE]
    assert len(matched) == 1
    assert isinstance(matched[0], DependencyCheckSource)


# ---------------------------------------------------------------------------
# discover() happy paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_path_returns_parsed_findings() -> None:
    """Single path → one execute() call → parsed structured findings."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=True, final_output=_wrap_json(_wellformed_payload()))],
    )

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover(["./"], budget_usd=0.5)

    assert findings == [
        Finding(
            source=SOURCE,
            severity="high",
            title="vulnerable requests version",
            description="CVE-2024-XXXXX affects requests<2.32.0.",
            file="pyproject.toml",
            line=12,
            evidence='requests = ">=2.30.0"',
            confidence=0.9,
            tags=("cve", "outdated"),
        )
    ]
    assert len(factory.calls) == 1
    assert factory.calls[0].execute_kwargs == {
        "path": "./",
        "depth": "quick",
        "max_budget_usd": 0.5,
    }


@pytest.mark.asyncio
async def test_constructor_receives_structured_emit_footer() -> None:
    """``system_prompt_suffix`` is the augmentation channel per design.md."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=True, final_output=_wrap_json({"findings": []}))],
    )

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        await DependencyCheckSource().discover(["./"], budget_usd=0.5)

    assert factory.calls[0].init_kwargs == {
        "system_prompt_suffix": STRUCTURED_EMIT_FOOTER,
    }


@pytest.mark.asyncio
async def test_custom_depth_is_passed_to_execute() -> None:
    """``depth="standard"`` override reaches the wrapped execute() call."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=True, final_output=_wrap_json({"findings": []}))],
    )

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        await DependencyCheckSource(depth="standard").discover(["./"], budget_usd=0.5)

    assert factory.calls[0].execute_kwargs == {
        "path": "./",
        "depth": "standard",
        "max_budget_usd": 0.5,
    }


@pytest.mark.asyncio
async def test_multiple_paths_yield_per_path_calls_and_concat_findings() -> None:
    """Each path → its own execute() call; findings concatenate in order."""
    factory = _FakeWorkflowFactory(
        results=[
            _FakeResult(
                success=True,
                final_output=_wrap_json(
                    {
                        "findings": [
                            {
                                "severity": "high",
                                "title": "first",
                                "description": "from path 1",
                                "confidence": 0.9,
                            }
                        ]
                    }
                ),
            ),
            _FakeResult(
                success=True,
                final_output=_wrap_json(
                    {
                        "findings": [
                            {
                                "severity": "medium",
                                "title": "second",
                                "description": "from path 2",
                                "confidence": 0.7,
                            }
                        ]
                    }
                ),
            ),
        ],
    )

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover(["./pkg-a/", "./pkg-b/"], budget_usd=1.0)

    assert len(factory.calls) == 2
    assert [f.title for f in findings] == ["first", "second"]


# ---------------------------------------------------------------------------
# discover() degradation paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_paths_returns_source_failure_finding() -> None:
    """Empty paths list → one info-finding, no workflow invocation."""
    factory = _FakeWorkflowFactory()

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover([], budget_usd=0.5)

    assert factory.calls == []
    assert len(findings) == 1
    only = findings[0]
    assert only.source == SOURCE
    assert only.severity == "info"
    assert only.tags == ("source-failure",)


@pytest.mark.asyncio
async def test_wrapped_workflow_raise_does_not_abort_other_paths() -> None:
    """One path raises → recorded as source-failure; remaining paths run."""
    factory = _FakeWorkflowFactory(
        results=[
            _FakeResult(),  # ignored — first instance raises
            _FakeResult(
                success=True,
                final_output=_wrap_json(
                    {
                        "findings": [
                            {
                                "severity": "high",
                                "title": "real finding",
                                "description": "from second path",
                                "confidence": 0.9,
                            }
                        ]
                    }
                ),
            ),
        ],
        side_effects=[RuntimeError("boom"), None],
    )

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover(["./bad/", "./good/"], budget_usd=1.0)

    assert len(findings) == 2
    assert findings[0].tags == ("source-failure",)
    assert findings[0].file == "./bad/"
    assert findings[1].title == "real finding"


@pytest.mark.asyncio
async def test_wrapped_workflow_returns_success_false() -> None:
    """``WorkflowResult.success=False`` → info-finding, no parse attempt."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=False, final_output="path argument is required")],
    )

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover(["./"], budget_usd=0.5)

    assert len(findings) == 1
    only = findings[0]
    assert only.severity == "info"
    assert only.tags == ("source-failure",)
    assert only.file == "./"


@pytest.mark.asyncio
async def test_unparseable_output_falls_back_to_parser_fallback() -> None:
    """No JSON block → parser's text-only-fallback finding."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=True, final_output="Just prose; no json block.")],
    )

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover(["./"], budget_usd=0.5)

    assert len(findings) == 1
    only = findings[0]
    assert only.severity == "info"
    assert only.confidence == 0.1
    assert only.tags == ("text-only-fallback",)


@pytest.mark.asyncio
async def test_empty_final_output_falls_back() -> None:
    """``final_output`` may be None/empty — handle defensively."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=True, final_output="")],
    )

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover(["./"], budget_usd=0.5)

    assert len(findings) == 1
    assert findings[0].tags == ("text-only-fallback",)


# ---------------------------------------------------------------------------
# discover() budget-enforcement paths
# ---------------------------------------------------------------------------


@dataclass
class _FakeCostReport:
    """Minimal stand-in for ``WorkflowResult.cost_report``."""

    total_cost: float = 0.0


@pytest.mark.asyncio
async def test_budget_below_floor_skips_runs_and_emits_finding() -> None:
    """Per-call share under the floor → skip every run, one info finding."""
    factory = _FakeWorkflowFactory()

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover(
            ["./"], budget_usd=MIN_PER_CALL_BUDGET_USD / 2
        )

    assert factory.calls == []
    assert len(findings) == 1
    only = findings[0]
    assert only.severity == "info"
    assert only.tags == ("budget-cap",)
    assert only.file is None


@pytest.mark.asyncio
async def test_share_below_min_useful_skips_instead_of_aborting() -> None:
    """#2214 — a share above the generic floor but below this source's
    measured minimum (~$0.45 quick run) skips honestly rather than
    launching a run guaranteed to die at its budget cap ($0, failure
    marker — the probe registry's reproducible '$0 lane')."""
    factory = _FakeWorkflowFactory()

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover(["./"], budget_usd=0.29)

    assert factory.calls == []  # no doomed run launched
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert findings[0].tags == ("budget-cap",)


@pytest.mark.asyncio
async def test_run_at_budget_ceiling_appends_cap_finding() -> None:
    """Cost ≥95% of the per-call share → append an info 'ceiling' finding."""
    factory = _FakeWorkflowFactory(
        results=[
            _FakeResult(
                success=True,
                final_output=_wrap_json(_wellformed_payload()),
                cost_report=_FakeCostReport(total_cost=1.0),
            )
        ],
    )

    with patch(
        "attune.workflows.dependency_check.DependencyCheckWorkflow",
        new=factory,
    ):
        findings = await DependencyCheckSource().discover(["./"], budget_usd=1.0)

    # The path's own finding plus one appended cap-ceiling note.
    assert len(findings) == 2
    cap = findings[-1]
    assert cap.severity == "info"
    assert cap.tags == ("budget-cap",)
    assert cap.file is None
    assert "./" in cap.description
