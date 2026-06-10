"""Integration test for :class:`PerfAuditSource`.

Hits the real Anthropic API via the wrapped
:class:`PerformanceAuditWorkflow`. Marked
``@pytest.mark.integration`` per the Phase 1.5 design decision so
the default ``-m "not integration"`` selector skips it; opt-in
with::

    pytest tests/integration/test_discovery_sweep_perf_audit_integration.py \\
        -m integration

Runs against a tiny on-disk fixture with ``depth="quick"`` so
spend stays low (~$2 SDK cap per :func:`get_max_budget_usd`).
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep.sources.perf_audit import PerfAuditSource

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="hits the real Anthropic API — auth-gated (nightly auth job)",
    ),
]


_FIXTURE_SLOW_SOURCE = textwrap.dedent(
    '''\
    """Fixture module — deliberately contains patterns perf-audit should flag."""


    def load_users_with_roles(user_ids):
        """N+1 query: one DB call per user instead of a join."""
        results = []
        for user_id in user_ids:
            user = db.users.get(user_id)  # noqa: F821
            user.role = db.roles.get(user.role_id)  # noqa: F821 — extra query per user
            results.append(user)
        return results


    def find_duplicates(items):
        """O(n^2) deduplication — should use a set for O(n)."""
        unique = []
        for item in items:
            if item not in unique:
                unique.append(item)
        return unique


    def read_whole_file(path):
        """Reads entire file into memory; better to stream for large files."""
        with open(path) as f:
            return f.read().split("\\n")
    '''
)


@pytest.mark.asyncio
async def test_perf_audit_source_returns_findings_for_slow_fixture(
    tmp_path: Path,
) -> None:
    """Real sweep on a fixture file produces at least one parsed finding.

    Doesn't assert specific titles or severities — the model's
    exact wording drifts between runs. Asserts only the structural
    contract: at least one Finding with our adapter's source name,
    and not the text-only-fallback shape (which would indicate the
    JSON-emit contract broke).
    """
    fixture = tmp_path / "slow_module.py"
    fixture.write_text(_FIXTURE_SLOW_SOURCE, encoding="utf-8")

    source = PerfAuditSource(depth="quick")
    findings = await source.discover([str(fixture)], budget_usd=2.0)

    assert findings, "expected at least one finding from real perf-audit run"
    assert all(f.source == "perf-audit" for f in findings)
    assert not any(
        "text-only-fallback" in f.tags for f in findings
    ), "structured-emit contract failed — adapter fell back to text-only path"
