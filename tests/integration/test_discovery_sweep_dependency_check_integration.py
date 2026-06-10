"""Integration test for :class:`DependencyCheckSource`.

Hits the real Anthropic API via the wrapped
:class:`DependencyCheckWorkflow`. Marked
``@pytest.mark.integration`` per the Phase 1.5 design decision so
the default ``-m "not integration"`` selector skips it; opt-in
with::

    pytest tests/integration/test_discovery_sweep_dependency_check_integration.py \\
        -m integration

Runs against a tiny on-disk manifest with ``depth="quick"`` so
spend stays low (~$2 SDK cap per :func:`get_max_budget_usd`).
Dependency-check is cheaper than security-audit (two subagents,
mostly Bash/Read calls) — well within the cap.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep.sources.dependency_check import (
    DependencyCheckSource,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="hits the real Anthropic API — auth-gated (nightly auth job)",
    ),
]


# Deliberately pinned to OLD versions of well-known packages so the
# inventory-assessor has obvious targets. The exact CVE list shifts
# over time; assertions stay structural rather than text-matching.
_FIXTURE_PYPROJECT = textwrap.dedent(
    """\
    [project]
    name = "fixture-project"
    version = "0.0.1"
    dependencies = [
      "requests==2.25.0",
      "urllib3==1.26.0",
      "pyyaml==5.3.0",
    ]
    """
)


@pytest.mark.asyncio
async def test_dependency_check_source_returns_findings_for_outdated_pyproject(
    tmp_path: Path,
) -> None:
    """Real sweep on a fixture pyproject produces at least one finding.

    Doesn't assert specific CVE IDs or package names — those drift
    as the model's training data and the live CVE feed evolve.
    Asserts only the structural contract: at least one Finding
    with our adapter's source name, and not the text-only-fallback
    shape (which would indicate the JSON-emit contract broke).
    """
    (tmp_path / "pyproject.toml").write_text(_FIXTURE_PYPROJECT, encoding="utf-8")

    source = DependencyCheckSource(depth="quick")
    findings = await source.discover([str(tmp_path)], budget_usd=2.0)

    assert findings, "expected at least one finding from real dependency-check run"
    assert all(f.source == "dependency-check" for f in findings)
    assert not any(
        "text-only-fallback" in f.tags for f in findings
    ), "structured-emit contract failed — adapter fell back to text-only path"
    # source-failure = the wrapped workflow raised or returned
    # success=False. Without this assertion a broken key / dead SDK
    # "passes" the test (it did on run 27249292521 — 18 s, zero spend).
    assert not any(
        "source-failure" in f.tags for f in findings
    ), "wrapped workflow failed — findings are failure markers, not analysis"
