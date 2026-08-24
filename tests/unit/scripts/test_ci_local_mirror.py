"""Drift guard: scripts/ci_local.sh mirrors CI's test-lane invocation.

Retro 2026-08-24 item 3.2: local runs scoped to tests/unit missed
CI-visible failures twice in one night. The script exists so "run what
CI runs" is one command; this test fails if the two invocations drift.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

CI_PYTEST_LINE = (
    'pytest -n auto --timeout=60 --timeout-method=thread -m "not network and not integration"'
)


def test_script_matches_ci_invocation() -> None:
    script = (REPO_ROOT / "scripts" / "ci_local.sh").read_text(encoding="utf-8")
    assert CI_PYTEST_LINE in script


def test_ci_workflow_still_uses_that_invocation() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert CI_PYTEST_LINE in workflow, (
        "tests.yml's pytest line changed — update scripts/ci_local.sh "
        "and this constant in the same PR"
    )


def test_script_is_keyless_by_empty_string() -> None:
    script = (REPO_ROOT / "scripts" / "ci_local.sh").read_text(encoding="utf-8")
    assert 'ANTHROPIC_API_KEY=""' in script  # empty, never unset
