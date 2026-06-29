"""Unit tests for :class:`TestAuditSource`.

Mocks ``TestAuditWorkflow`` at its source module (per the existing
CLAUDE.md lesson on deferred imports). Integration coverage gated
on ``@pytest.mark.integration`` lives in
``tests/integration/test_discovery_sweep_test_audit_integration.py``.

Last adapter in Phase 2B. Same shape as P2.1–P2.5.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from unittest.mock import patch

import pytest

from attune.workflows.discovery_sweep import Finding
from attune.workflows.discovery_sweep.cli_workflow import default_sources
from attune.workflows.discovery_sweep.llm_source_base import STRUCTURED_EMIT_FOOTER
from attune.workflows.discovery_sweep.sources.test_audit import TestAuditSource

SOURCE = "test-audit"


@dataclass
class _FakeResult:
    success: bool = True
    final_output: str = ""


@dataclass
class _RecordedCall:
    init_kwargs: dict
    execute_kwargs: dict


@dataclass
class _FakeWorkflowFactory:
    """Hand-rolled stand-in for ``TestAuditWorkflow``."""

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
                "severity": "medium",
                "title": "untested error path",
                "description": "PermissionError branch is never exercised.",
                "file": "src/handler.py",
                "line": 56,
                "evidence": "except PermissionError as e: ...",
                "confidence": 0.75,
                "tags": ["coverage-gap", "error-path"],
            }
        ]
    }


# ---------------------------------------------------------------------------
# Source-level attributes
# ---------------------------------------------------------------------------


def test_source_defaults() -> None:
    """Defaults conform to LLMSource marker + default 1.0 budget multiplier."""
    source = TestAuditSource()
    assert source.name == SOURCE
    assert source.is_llm is True
    assert source.budget_multiplier == 1.0
    assert source.depth == "standard"


def test_source_appears_in_default_sources() -> None:
    """Wired into ``default_sources()`` per task P2.6 step 5."""
    sources = default_sources()
    matched = [s for s in sources if s.name == SOURCE]
    assert len(matched) == 1
    assert isinstance(matched[0], TestAuditSource)


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
        "attune.workflows.test_audit.workflow.TestAuditWorkflow",
        new=factory,
    ):
        findings = await TestAuditSource().discover(["src/"], budget_usd=1.0)

    assert findings == [
        Finding(
            source=SOURCE,
            severity="medium",
            title="untested error path",
            description="PermissionError branch is never exercised.",
            file="src/handler.py",
            line=56,
            evidence="except PermissionError as e: ...",
            confidence=0.75,
            tags=("coverage-gap", "error-path"),
        )
    ]
    assert len(factory.calls) == 1
    assert factory.calls[0].execute_kwargs == {
        "path": "src/",
        "depth": "standard",
        "max_budget_usd": 1.0,
    }


@pytest.mark.asyncio
async def test_constructor_receives_structured_emit_footer() -> None:
    """``system_prompt_suffix`` is the augmentation channel per design.md."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=True, final_output=_wrap_json({"findings": []}))],
    )

    with patch(
        "attune.workflows.test_audit.workflow.TestAuditWorkflow",
        new=factory,
    ):
        await TestAuditSource().discover(["src/"], budget_usd=1.0)

    assert factory.calls[0].init_kwargs == {
        "system_prompt_suffix": STRUCTURED_EMIT_FOOTER,
    }


@pytest.mark.asyncio
async def test_custom_depth_is_passed_to_execute() -> None:
    """``depth="quick"`` reaches the wrapped workflow's execute() call."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=True, final_output=_wrap_json({"findings": []}))],
    )

    with patch(
        "attune.workflows.test_audit.workflow.TestAuditWorkflow",
        new=factory,
    ):
        await TestAuditSource(depth="quick").discover(["src/"], budget_usd=1.0)

    assert factory.calls[0].execute_kwargs == {
        "path": "src/",
        "depth": "quick",
        "max_budget_usd": 1.0,
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
                                "severity": "medium",
                                "title": "first",
                                "description": "from path 1",
                                "confidence": 0.6,
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
                                "severity": "low",
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
        "attune.workflows.test_audit.workflow.TestAuditWorkflow",
        new=factory,
    ):
        findings = await TestAuditSource().discover(["src/a/", "src/b/"], budget_usd=1.0)

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
        "attune.workflows.test_audit.workflow.TestAuditWorkflow",
        new=factory,
    ):
        findings = await TestAuditSource().discover([], budget_usd=1.0)

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
        "attune.workflows.test_audit.workflow.TestAuditWorkflow",
        new=factory,
    ):
        findings = await TestAuditSource().discover(["bad/", "good/"], budget_usd=1.0)

    assert len(findings) == 2
    assert findings[0].tags == ("source-failure",)
    assert findings[0].file == "bad/"
    assert findings[1].title == "real finding"


@pytest.mark.asyncio
async def test_wrapped_workflow_returns_success_false() -> None:
    """``WorkflowResult.success=False`` → info-finding, no parse attempt."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=False, final_output="path argument is required")],
    )

    with patch(
        "attune.workflows.test_audit.workflow.TestAuditWorkflow",
        new=factory,
    ):
        findings = await TestAuditSource().discover(["src/"], budget_usd=1.0)

    assert len(findings) == 1
    only = findings[0]
    assert only.severity == "info"
    assert only.tags == ("source-failure",)
    assert only.file == "src/"


@pytest.mark.asyncio
async def test_unparseable_output_falls_back_to_parser_fallback() -> None:
    """No JSON block → parser's text-only-fallback finding."""
    factory = _FakeWorkflowFactory(
        results=[_FakeResult(success=True, final_output="Just prose; no json block.")],
    )

    with patch(
        "attune.workflows.test_audit.workflow.TestAuditWorkflow",
        new=factory,
    ):
        findings = await TestAuditSource().discover(["src/"], budget_usd=1.0)

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
        "attune.workflows.test_audit.workflow.TestAuditWorkflow",
        new=factory,
    ):
        findings = await TestAuditSource().discover(["src/"], budget_usd=1.0)

    assert len(findings) == 1
    assert findings[0].tags == ("text-only-fallback",)
