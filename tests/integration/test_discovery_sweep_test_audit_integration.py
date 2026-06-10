"""Integration test for :class:`TestAuditSource`.

Hits the real Anthropic API via the wrapped
:class:`TestAuditWorkflow`. Marked
``@pytest.mark.integration`` per the Phase 1.5 design decision so
the default ``-m "not integration"`` selector skips it; opt-in
with::

    pytest tests/integration/test_discovery_sweep_test_audit_integration.py \\
        -m integration

Runs against a tiny on-disk fixture with ``depth="quick"`` so
spend stays low (~$2 SDK cap per :func:`get_max_budget_usd`).
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep.sources.test_audit import TestAuditSource

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="hits the real Anthropic API — auth-gated (nightly auth job)",
    ),
]


_FIXTURE_UNDER_TESTED_SOURCE = textwrap.dedent(
    '''\
    """Fixture module — has obvious test-coverage gaps."""


    def divide(numerator: float, denominator: float) -> float:
        """Divide two numbers — ZeroDivisionError branch is untested."""
        if denominator == 0:
            raise ValueError("denominator must be non-zero")
        return numerator / denominator


    def parse_age(raw: str) -> int:
        """Parse an age string. Negative and non-numeric paths likely untested."""
        try:
            age = int(raw)
        except ValueError as exc:
            raise ValueError(f"invalid age: {raw!r}") from exc
        if age < 0:
            raise ValueError(f"age must be non-negative, got {age}")
        return age
    '''
)

_FIXTURE_THIN_TEST = textwrap.dedent(
    '''\
    """Only covers the happy path of divide; ignores parse_age entirely."""
    from buggy_module import divide


    def test_divide_happy_path():
        assert divide(10, 2) == 5
    '''
)


@pytest.mark.asyncio
async def test_test_audit_source_returns_findings_for_under_tested_fixture(
    tmp_path: Path,
) -> None:
    """Real sweep on a fixture with obvious coverage gaps produces findings.

    Doesn't assert specific titles or severities — the model's
    exact wording drifts between runs. Asserts only the structural
    contract: at least one Finding with our adapter's source name,
    and not the text-only-fallback shape (which would indicate the
    JSON-emit contract broke).
    """
    (tmp_path / "buggy_module.py").write_text(_FIXTURE_UNDER_TESTED_SOURCE, encoding="utf-8")
    (tmp_path / "test_buggy_module.py").write_text(_FIXTURE_THIN_TEST, encoding="utf-8")

    source = TestAuditSource(depth="quick")
    findings = await source.discover([str(tmp_path)], budget_usd=2.0)

    assert findings, "expected at least one finding from real test-audit run"
    assert all(f.source == "test-audit" for f in findings)
    assert not any(
        "text-only-fallback" in f.tags for f in findings
    ), "structured-emit contract failed — adapter fell back to text-only path"
    # source-failure = the wrapped workflow raised or returned
    # success=False. Without this assertion a broken key / dead SDK
    # "passes" the test (it did on run 27249292521 — 18 s, zero spend).
    assert not any(
        "source-failure" in f.tags for f in findings
    ), "wrapped workflow failed — findings are failure markers, not analysis"
