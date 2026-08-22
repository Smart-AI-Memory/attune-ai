"""Reconcile receipt (release-audit-stage R3 step 1).

The binding is the security property: a green run for an EARLIER commit
must not authorize the release. Every refusal below is a way that could
otherwise happen, so each one is pinned.

No network: the runs provider is injected.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.classes.reconcile import (
    ReconcileError,
    ReconcileReceipt,
    reconcile,
)

_SHA = "a" * 40
_OTHER = "b" * 40
_REPO = "Smart-AI-Memory/attune-ai"


def _run(**over):
    run = {
        "databaseId": 123,
        "name": "Tests",
        "conclusion": "success",
        "status": "completed",
        "headSha": _SHA,
    }
    run.update(over)
    return run


def _provider(*runs):
    return lambda repo, sha: list(runs)


class TestAuthorizes:
    def test_green_allowlisted_run_for_this_sha(self):
        receipt = reconcile(_REPO, _SHA, runs_provider=_provider(_run()))

        assert isinstance(receipt, ReconcileReceipt)
        assert receipt.conclusion == "success"
        assert receipt.head_sha == _SHA
        assert receipt.workflow == "Tests"
        assert receipt.run_id == "123"

    def test_receipt_serialises_for_packet_section_1(self):
        receipt = reconcile(_REPO, _SHA, runs_provider=_provider(_run()))

        assert set(receipt.as_dict()) == {
            "run_id",
            "workflow",
            "repo",
            "head_sha",
            "conclusion",
        }

    def test_picks_the_allowlisted_run_among_others(self):
        runs = [_run(name="Documentation", conclusion="success"), _run(name="Tests")]

        assert reconcile(_REPO, _SHA, runs_provider=_provider(*runs)).workflow == "Tests"


class TestBindingRefusals:
    """A green run elsewhere must never authorize this commit."""

    def test_green_run_for_an_earlier_commit_does_not_authorize(self):
        stale = _run(headSha=_OTHER)

        with pytest.raises(ReconcileError) as exc:
            reconcile(_REPO, _SHA, runs_provider=_provider(stale))

        assert exc.value.reason == "sha-mismatch"
        assert "does not authorize" in str(exc.value)

    def test_no_run_at_all_fails_closed(self):
        with pytest.raises(ReconcileError) as exc:
            reconcile(_REPO, _SHA, runs_provider=_provider())

        assert exc.value.reason == "no-run"

    def test_non_allowlisted_workflow_does_not_authorize(self):
        """A docs workflow going green says nothing about the gates."""
        with pytest.raises(ReconcileError) as exc:
            reconcile(_REPO, _SHA, runs_provider=_provider(_run(name="Documentation")))

        assert exc.value.reason == "workflow-not-allowlisted"

    @pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped", "timed_out", None])
    def test_only_success_authorizes(self, conclusion):
        """cancelled/skipped are how a required lane silently stops guarding."""
        with pytest.raises(ReconcileError) as exc:
            reconcile(_REPO, _SHA, runs_provider=_provider(_run(conclusion=conclusion)))

        assert exc.value.reason == "not-green"

    def test_still_running_is_not_green(self):
        in_flight = _run(status="in_progress", conclusion=None)

        with pytest.raises(ReconcileError) as exc:
            reconcile(_REPO, _SHA, runs_provider=_provider(in_flight))

        assert exc.value.reason == "still-running"

    def test_short_sha_is_refused(self):
        """Binding to an abbreviated SHA is not binding."""
        with pytest.raises(ReconcileError) as exc:
            reconcile(_REPO, "abc1234", runs_provider=_provider(_run()))

        assert exc.value.reason == "bad-head-sha"

    def test_a_failing_provider_fails_closed_not_open(self):
        def broken(repo, sha):
            return []

        with pytest.raises(ReconcileError) as exc:
            reconcile(_REPO, _SHA, runs_provider=broken)

        assert exc.value.reason == "no-run"


class TestAllowlistIsConfigurable:
    def test_caller_can_name_its_own_workflows(self):
        receipt = reconcile(
            _REPO,
            _SHA,
            runs_provider=_provider(_run(name="CI")),
            allowed_workflows=("CI",),
        )

        assert receipt.workflow == "CI"
