"""Integration test for :class:`BugPredictSource`.

Hits the real Anthropic API via the wrapped
:class:`BugPredictionWorkflow`. Marked ``@pytest.mark.integration``
per the Phase 1.5 design decision so the default ``-m "not
integration"`` selector skips it; opt-in with::

    pytest tests/integration/test_discovery_sweep_bug_predict_integration.py \\
        -m integration

The test runs against a tiny on-disk fixture so spend stays low
(``depth="quick"`` is roughly $2 of SDK budget per the
``_DEFAULT_BUDGET_USD["quick"]`` cap).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep.sources.bug_predict import BugPredictSource

pytestmark = pytest.mark.integration


_FIXTURE_BUGGY_SOURCE = textwrap.dedent(
    '''\
    """Fixture module — deliberately contains patterns bug-predict should flag."""


    def parse_user_formula(formula: str):
        # Obvious code-execution risk: trusting raw user input as a Python expression.
        return eval(formula)  # noqa: S307


    def read_config(path):
        try:
            with open(path) as fh:
                return fh.read()
        except Exception:  # noqa: BLE001
            # Swallows everything including OSError/PermissionError/etc.
            return None
    '''
)


@pytest.mark.asyncio
async def test_bug_predict_source_returns_findings_for_buggy_fixture(
    tmp_path: Path,
) -> None:
    """Real sweep on a fixture file produces at least one parsed finding.

    Doesn't assert specific titles or severities — the model's exact
    wording drifts between runs. Asserts only the structural
    contract: at least one Finding with our adapter's source name,
    and not the text-only-fallback shape (which would indicate the
    JSON-emit contract broke).
    """
    fixture = tmp_path / "buggy_module.py"
    fixture.write_text(_FIXTURE_BUGGY_SOURCE, encoding="utf-8")

    source = BugPredictSource(depth="quick")
    findings = await source.discover([str(fixture)], budget_usd=2.0)

    assert findings, "expected at least one finding from real bug-predict run"
    assert all(f.source == "bug-predict" for f in findings)
    assert not any(
        "text-only-fallback" in f.tags for f in findings
    ), "structured-emit contract failed — adapter fell back to text-only path"
