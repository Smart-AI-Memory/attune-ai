"""Integration test for :class:`DocAuditSource`.

Hits the real Anthropic API via the wrapped
:class:`DocAuditWorkflow`. Marked
``@pytest.mark.integration`` per the Phase 1.5 design decision so
the default ``-m "not integration"`` selector skips it; opt-in
with::

    pytest tests/integration/test_discovery_sweep_doc_audit_integration.py \\
        -m integration

Runs against a tiny on-disk fixture with ``depth="quick"`` so
spend stays low (~$2 SDK cap per :func:`get_max_budget_usd`).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep.sources.doc_audit import DocAuditSource

pytestmark = pytest.mark.integration


_FIXTURE_STALE_README = textwrap.dedent(
    """\
    # Fixture Project

    A test project for the doc-audit integration test.

    ## Installation

    The recommended install command is:

    ```bash
    pip install --legacy-flag fixture-project
    ```

    > NOTE: this flag was removed in pip 22.0; the doc-audit
    > should flag this section as stale.

    ## Usage

    Import the package and call `fixture.do_thing()`:

    ```python
    import fixture
    fixture.do_thing()  # function was renamed to .run() in 2.0
    ```

    See [the API reference](./docs/api-v0.md) for details. (broken
    link — file does not exist)
    """
)


@pytest.mark.asyncio
async def test_doc_audit_source_returns_findings_for_stale_readme(
    tmp_path: Path,
) -> None:
    """Real sweep on a fixture README produces at least one parsed finding.

    Doesn't assert specific titles or severities — the model's
    exact wording drifts between runs. Asserts only the structural
    contract: at least one Finding with our adapter's source name,
    and not the text-only-fallback shape (which would indicate the
    JSON-emit contract broke).
    """
    (tmp_path / "README.md").write_text(_FIXTURE_STALE_README, encoding="utf-8")

    source = DocAuditSource(depth="quick")
    findings = await source.discover([str(tmp_path)], budget_usd=2.0)

    assert findings, "expected at least one finding from real doc-audit run"
    assert all(f.source == "doc-audit" for f in findings)
    assert not any(
        "text-only-fallback" in f.tags for f in findings
    ), "structured-emit contract failed — adapter fell back to text-only path"
