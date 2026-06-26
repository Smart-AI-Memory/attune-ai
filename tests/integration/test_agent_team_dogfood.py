"""Non-mocked dogfood receipt for the generic agent team (R5).

Proves the keystone claim of ``docs/specs/generic-agent-teams``: a real
``AgentTeam`` of ``code-review`` + ``security-audit`` run over a
deliberately-vulnerable file returns a **blocked** verdict, with at
least one dimension scoring below threshold and non-zero LLM cost.

Per "registered != working", mocked unit tests do NOT close R5 — this
test exercises the real workflows end-to-end. It requires a live
``ANTHROPIC_API_KEY`` and skips when none is configured (the keyless-CI
convention: CI sets the key to the empty string, so the skip fires and
no spend happens in per-PR lanes).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

# Pick up a local key from ~/.attune/anthropic.env style .env files.
load_dotenv()

#: A file that should fail both review dimensions: a path-traversal-style
#: arbitrary eval of user input plus a hardcoded credential.
_VULNERABLE_SOURCE = '''
"""Intentionally insecure module (test fixture, not real code)."""

import os

# A hardcoded secret — security audit must flag this.
API_KEY = "sk-ant-api03-FAKE-not-a-real-key-000000000000"  # pragma: allowlist secret


def run_user_formula(user_input):
    # Arbitrary code execution — the canonical CWE-95 finding.
    return eval(user_input)  # noqa


def delete(path):
    os.system("rm -rf " + path)  # noqa: shell injection, also bad
'''


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="non-mocked dogfood needs a live ANTHROPIC_API_KEY (keyless CI skips)",
)
async def test_real_team_blocks_vulnerable_file(tmp_path):
    """A real code-review + security-audit team blocks a bad file (R5)."""
    from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
    from attune.workflows.code_review import CodeReviewWorkflow
    from attune.workflows.security_audit import SecurityAuditWorkflow

    bad_file = tmp_path / "vulnerable.py"
    bad_file.write_text(_VULNERABLE_SOURCE)

    team = AgentTeam(
        agents=[
            WorkflowAgent("code-review", CodeReviewWorkflow, files=[str(bad_file)]),
            WorkflowAgent("security-audit", SecurityAuditWorkflow, files=[str(bad_file)]),
        ],
        gates=[
            GateSpec("Code Quality", "code-review", 70.0),
            GateSpec("Security", "security-audit", 70.0),
        ],
    )

    report = await team.run([str(bad_file)])

    # Blocked verdict — never a fake pass on a file with eval() + a secret.
    assert report.passed is False
    assert report.blockers, "a vulnerable file must produce at least one blocker"
    # At least one dimension scored below the 70 threshold (real signal).
    assert min(g.actual for g in report.gates) < 70.0
    # Real work happened: non-zero LLM cost.
    assert report.cost > 0.0
