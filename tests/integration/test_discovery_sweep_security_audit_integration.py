"""Integration test for :class:`SecurityAuditSource`.

Hits the real Anthropic API via the wrapped
:class:`SecurityAuditWorkflow`. Marked
``@pytest.mark.integration`` per the Phase 1.5 design decision so
the default ``-m "not integration"`` selector skips it; opt-in
with::

    pytest tests/integration/test_discovery_sweep_security_audit_integration.py \\
        -m integration

Runs against a tiny on-disk fixture with ``depth="quick"`` so spend
stays low (~$2 SDK cap per :func:`get_max_budget_usd`). Security
audit's four subagents will still spend faster than bug-predict's
three; budget accordingly when iterating.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep.sources.security_audit import SecurityAuditSource

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="hits the real Anthropic API — auth-gated (nightly auth job)",
    ),
]


_FIXTURE_VULNERABLE_SOURCE = textwrap.dedent(
    '''\
    """Fixture module — deliberately contains patterns security-audit should flag."""

    import hashlib
    import subprocess

    # Hardcoded credential — secret-detector should flag.
    API_KEY = "sk-live-FAKE-LOOKING-CREDENTIAL-FOR-FIXTURE"  # noqa: S105


    def hash_password(password: str) -> str:
        # Weak hash — vuln-scanner should flag (MD5 for credentials).
        return hashlib.md5(password.encode()).hexdigest()


    def run_user_command(cmd: str) -> str:
        # Shell injection — vuln-scanner should flag (shell=True with user input).
        return subprocess.check_output(cmd, shell=True).decode()
    '''
)


@pytest.mark.asyncio
async def test_security_audit_source_returns_findings_for_vulnerable_fixture(
    tmp_path: Path,
) -> None:
    """Real sweep on a fixture file produces at least one parsed finding.

    Doesn't assert specific titles or severities — the model's
    exact wording drifts between runs. Asserts only the structural
    contract: at least one Finding with our adapter's source name,
    and not the text-only-fallback shape (which would indicate the
    JSON-emit contract broke).
    """
    fixture = tmp_path / "vulnerable_module.py"
    fixture.write_text(_FIXTURE_VULNERABLE_SOURCE, encoding="utf-8")

    source = SecurityAuditSource(depth="quick")
    findings = await source.discover([str(fixture)], budget_usd=4.0)

    assert findings, "expected at least one finding from real security-audit run"
    assert all(f.source == "security-audit" for f in findings)
    assert not any(
        "text-only-fallback" in f.tags for f in findings
    ), "structured-emit contract failed — adapter fell back to text-only path"
    # source-failure = the wrapped workflow raised or returned
    # success=False. Without this assertion a broken key / dead SDK
    # "passes" the test (it did on run 27249292521 — 18 s, zero spend).
    assert not any(
        "source-failure" in f.tags for f in findings
    ), "wrapped workflow failed — findings are failure markers, not analysis"
