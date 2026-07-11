"""Tests for the reusable spec-status-reminder workflow.

Task 6 of docs/specs/spec-status-integrity-hooks (workspace design §5).
Per the spec's testing strategy the workflow is validated via
``yaml.safe_load`` — triggers, permissions, workflow_call interface,
and the guard properties of the inline script — with no ``act`` dry
runs and no live gh calls.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

_WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "spec-status-reminder.yml"
)


@pytest.fixture(scope="module")
def workflow() -> dict:
    with open(_WORKFLOW, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def triggers(workflow) -> dict:
    # yaml.safe_load parses an unquoted ``on:`` key as boolean True.
    return workflow.get(True) or workflow.get("on")


@pytest.fixture(scope="module")
def script(workflow) -> str:
    """The inline python payload of the reminder step."""
    steps = workflow["jobs"]["remind"]["steps"]
    run_blocks = [s["run"] for s in steps if "run" in s]
    assert len(run_blocks) == 1
    body = run_blocks[0]
    start = body.index("<<'PYEOF'") + len("<<'PYEOF'")
    end = body.rindex("PYEOF")
    return textwrap.dedent(body[start:end])


class TestTriggersAndInterface:
    def test_fires_on_closed_prs_only(self, triggers) -> None:
        assert triggers["pull_request"]["types"] == ["closed"]

    def test_exposes_workflow_call_for_thin_callers(self, triggers) -> None:
        # No inputs/secrets — the 6-line caller passes nothing.
        assert "workflow_call" in triggers
        assert not triggers["workflow_call"]

    def test_job_gate_is_merged_only(self, workflow) -> None:
        # closed-unmerged PRs must never run the job at all.
        assert workflow["jobs"]["remind"]["if"] == "github.event.pull_request.merged == true"


class TestPermissions:
    def test_minimal_permissions(self, workflow) -> None:
        assert workflow["permissions"] == {
            "contents": "read",
            "pull-requests": "write",
        }


class TestCheckout:
    def test_checks_out_the_merged_tree(self, workflow) -> None:
        steps = workflow["jobs"]["remind"]["steps"]
        checkout = next(s for s in steps if "checkout" in (s.get("uses") or ""))
        assert "merge_commit_sha" in checkout["with"]["ref"]


class TestInlineScript:
    def test_script_is_valid_python(self, script) -> None:
        compile(script, "spec-status-reminder-inline", "exec")

    def test_marker_comment_guard(self, script) -> None:
        # Never comment twice on the same PR.
        assert "<!-- spec-status-reminder -->" in script
        assert "not commenting twice" in script

    def test_self_reference_carve_out(self, script) -> None:
        # A PR that modifies files under the referenced spec dir is
        # exempt (design §5 amendment 2026-07-10).
        assert 'f.startswith(r + "/")' in script
        assert "refs - touched" in script

    def test_merged_only_double_check(self, script) -> None:
        # Defense in depth behind the job-level if-gate.
        assert 'detail.get("merged")' in script

    def test_reminder_wording(self, script) -> None:
        assert "flip the status or mark it `parked`" in script

    def test_settled_vocabulary_mirrors_state_py(self, script) -> None:
        # The condensed parser must recognize the terminal additions and
        # the parked family shipped in tasks 3 of this spec.
        for token in ("implemented", "parked", "paused", "blocked", "deferred"):
            assert f'"{token}"' in script
