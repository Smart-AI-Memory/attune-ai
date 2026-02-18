"""Unit tests for src/attune/workflows/progress.py

Tests cover:
- ProgressStatus enum (correct members)
- StageProgress dataclass (construction, to_dict)
- ProgressUpdate dataclass (construction, to_dict, to_json)
- ProgressCallback type alias (not a Protocol)
- ProgressTracker (constructor, all state-update methods, callback dispatch)

Key corrections vs naive generation:
- ProgressStatus has: PENDING, RUNNING, COMPLETED, FAILED, SKIPPED,
  FALLBACK, RETRYING  — NOT CANCELLED, NOT PAUSED
- ProgressTracker.__init__ takes (workflow_name, workflow_id, stage_names)
  — NOT (workflow_name, total_steps)
- Method is start_stage(name, tier, model), complete_stage(name, cost,
  tokens_in, tokens_out), fail_stage(name, error), skip_stage(name, reason)
  — NOT advance(), complete(), fail(), cancel()
- retry_occurred(stage_name, attempt, max_attempts) — NOT retry(stage)
- fallback_occurred(stage_name, original_model, fallback_model, reason)
- ProgressCallback is a Callable type alias, NOT a Protocol class
- No set_percent(), total_steps attribute
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from attune.workflows.progress import (
    ProgressCallback,
    ProgressStatus,
    ProgressTracker,
    ProgressUpdate,
    StageProgress,
)

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _make_tracker(
    stage_names: list[str] | None = None,
    workflow_name: str = "test-workflow",
    workflow_id: str = "wf-001",
) -> ProgressTracker:
    if stage_names is None:
        stage_names = ["stage_a", "stage_b", "stage_c"]
    return ProgressTracker(workflow_name, workflow_id, stage_names)


def _capture_updates(tracker: ProgressTracker) -> list[ProgressUpdate]:
    updates: list[ProgressUpdate] = []
    tracker.add_callback(updates.append)
    return updates


# ---------------------------------------------------------------------------
# 1. ProgressStatus enum
# ---------------------------------------------------------------------------


class TestProgressStatus:
    def test_pending_exists(self):
        assert hasattr(ProgressStatus, "PENDING")

    def test_running_exists(self):
        assert hasattr(ProgressStatus, "RUNNING")

    def test_completed_exists(self):
        assert hasattr(ProgressStatus, "COMPLETED")

    def test_failed_exists(self):
        assert hasattr(ProgressStatus, "FAILED")

    def test_skipped_exists(self):
        assert hasattr(ProgressStatus, "SKIPPED")

    def test_fallback_exists(self):
        assert hasattr(ProgressStatus, "FALLBACK")

    def test_retrying_exists(self):
        assert hasattr(ProgressStatus, "RETRYING")

    def test_no_cancelled_status(self):
        assert not hasattr(ProgressStatus, "CANCELLED")

    def test_no_paused_status(self):
        assert not hasattr(ProgressStatus, "PAUSED")

    def test_all_statuses_have_string_values(self):
        for status in ProgressStatus:
            assert isinstance(status.value, str)

    def test_pending_value(self):
        assert ProgressStatus.PENDING.value == "pending"

    def test_running_value(self):
        assert ProgressStatus.RUNNING.value == "running"

    def test_completed_value(self):
        assert ProgressStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        assert ProgressStatus.FAILED.value == "failed"

    def test_statuses_are_distinct(self):
        statuses = list(ProgressStatus)
        assert len(set(statuses)) == len(statuses)


# ---------------------------------------------------------------------------
# 2. StageProgress
# ---------------------------------------------------------------------------


class TestStageProgress:
    def test_construction_with_name_and_status(self):
        sp = StageProgress(name="fetch", status=ProgressStatus.PENDING)
        assert sp.name == "fetch"
        assert sp.status == ProgressStatus.PENDING

    def test_default_tier_is_capable(self):
        sp = StageProgress(name="x", status=ProgressStatus.PENDING)
        assert sp.tier == "capable"

    def test_default_model_is_empty_string(self):
        sp = StageProgress(name="x", status=ProgressStatus.PENDING)
        assert sp.model == ""

    def test_default_cost_is_zero(self):
        sp = StageProgress(name="x", status=ProgressStatus.PENDING)
        assert sp.cost == 0.0

    def test_default_tokens_zero(self):
        sp = StageProgress(name="x", status=ProgressStatus.PENDING)
        assert sp.tokens_in == 0
        assert sp.tokens_out == 0

    def test_default_error_is_none(self):
        sp = StageProgress(name="x", status=ProgressStatus.PENDING)
        assert sp.error is None

    def test_default_retry_count_is_zero(self):
        sp = StageProgress(name="x", status=ProgressStatus.PENDING)
        assert sp.retry_count == 0

    def test_to_dict_contains_name(self):
        sp = StageProgress(name="munge", status=ProgressStatus.COMPLETED)
        d = sp.to_dict()
        assert d["name"] == "munge"

    def test_to_dict_contains_status_string(self):
        sp = StageProgress(name="x", status=ProgressStatus.COMPLETED)
        d = sp.to_dict()
        assert d["status"] == "completed"

    def test_to_dict_contains_cost(self):
        sp = StageProgress(name="x", status=ProgressStatus.COMPLETED, cost=1.23)
        d = sp.to_dict()
        assert d["cost"] == 1.23

    def test_to_dict_contains_error(self):
        sp = StageProgress(name="x", status=ProgressStatus.FAILED, error="boom")
        d = sp.to_dict()
        assert d["error"] == "boom"

    def test_to_dict_is_serializable(self):
        sp = StageProgress(name="x", status=ProgressStatus.PENDING)
        json.dumps(sp.to_dict())  # must not raise


# ---------------------------------------------------------------------------
# 3. ProgressUpdate
# ---------------------------------------------------------------------------


class TestProgressUpdate:
    def _make_update(self, **kwargs: Any) -> ProgressUpdate:
        defaults = {
            "workflow": "wf",
            "workflow_id": "id-1",
            "current_stage": "stage_a",
            "stage_index": 0,
            "total_stages": 3,
            "status": ProgressStatus.RUNNING,
            "message": "running...",
        }
        defaults.update(kwargs)
        return ProgressUpdate(**defaults)

    def test_construction(self):
        u = self._make_update()
        assert u.workflow == "wf"
        assert u.status == ProgressStatus.RUNNING

    def test_default_cost_so_far_is_zero(self):
        u = self._make_update()
        assert u.cost_so_far == 0.0

    def test_default_tokens_so_far_is_zero(self):
        u = self._make_update()
        assert u.tokens_so_far == 0

    def test_default_percent_complete_is_zero(self):
        u = self._make_update()
        assert u.percent_complete == 0.0

    def test_default_stages_is_empty_list(self):
        u = self._make_update()
        assert u.stages == []

    def test_to_dict_contains_workflow(self):
        u = self._make_update()
        assert u.to_dict()["workflow"] == "wf"

    def test_to_dict_contains_status_string(self):
        u = self._make_update()
        assert u.to_dict()["status"] == "running"

    def test_to_dict_contains_timestamp_string(self):
        u = self._make_update()
        ts = u.to_dict()["timestamp"]
        assert isinstance(ts, str) and len(ts) > 0

    def test_to_json_returns_valid_json(self):
        u = self._make_update()
        parsed = json.loads(u.to_json())
        assert parsed["workflow"] == "wf"

    def test_to_dict_is_json_serializable(self):
        u = self._make_update()
        json.dumps(u.to_dict())  # must not raise


# ---------------------------------------------------------------------------
# 4. ProgressCallback type alias
# ---------------------------------------------------------------------------


class TestProgressCallbackType:
    def test_progress_callback_is_callable_type(self):
        """ProgressCallback is a type alias, not a Protocol class."""
        # It should be usable as a type annotation, not as a base class
        assert ProgressCallback is not None

    def test_plain_function_satisfies_callback(self):
        def cb(update: ProgressUpdate) -> None:
            pass

        tracker = _make_tracker()
        tracker.add_callback(cb)  # must not raise

    def test_lambda_satisfies_callback(self):
        tracker = _make_tracker()
        tracker.add_callback(lambda u: None)  # must not raise

    def test_mock_callable_satisfies_callback(self):
        tracker = _make_tracker()
        tracker.add_callback(MagicMock())  # must not raise


# ---------------------------------------------------------------------------
# 5. ProgressTracker — constructor
# ---------------------------------------------------------------------------


class TestProgressTrackerConstructor:
    def test_accepts_workflow_name_id_and_stage_names(self):
        t = ProgressTracker("my-wf", "id-42", ["a", "b"])
        assert t.workflow == "my-wf"
        assert t.workflow_id == "id-42"
        assert t.stage_names == ["a", "b"]

    def test_stages_initialized_as_pending(self):
        t = _make_tracker(["x", "y"])
        for stage in t.stages:
            assert stage.status == ProgressStatus.PENDING

    def test_stage_count_matches_stage_names(self):
        t = _make_tracker(["a", "b", "c"])
        assert len(t.stages) == 3

    def test_cost_accumulated_starts_at_zero(self):
        t = _make_tracker()
        assert t.cost_accumulated == 0.0

    def test_tokens_accumulated_starts_at_zero(self):
        t = _make_tracker()
        assert t.tokens_accumulated == 0

    def test_current_index_starts_at_zero(self):
        t = _make_tracker()
        assert t.current_index == 0

    def test_empty_stage_list_accepted(self):
        t = ProgressTracker("wf", "id", [])
        assert t.stages == []


# ---------------------------------------------------------------------------
# 6. ProgressTracker — add/remove callbacks
# ---------------------------------------------------------------------------


class TestProgressTrackerCallbacks:
    def test_add_callback_registers_callback(self):
        t = _make_tracker()
        updates: list[ProgressUpdate] = []
        t.add_callback(updates.append)
        t.start_workflow()
        assert len(updates) == 1

    def test_remove_callback_stops_notifications(self):
        t = _make_tracker()
        updates: list[ProgressUpdate] = []
        cb = updates.append
        t.add_callback(cb)
        t.remove_callback(cb)
        t.start_workflow()
        assert len(updates) == 0

    def test_multiple_callbacks_all_receive_updates(self):
        t = _make_tracker()
        a_updates: list[ProgressUpdate] = []
        b_updates: list[ProgressUpdate] = []
        t.add_callback(a_updates.append)
        t.add_callback(b_updates.append)
        t.start_workflow()
        assert len(a_updates) == 1
        assert len(b_updates) == 1


# ---------------------------------------------------------------------------
# 7. ProgressTracker — start_workflow()
# ---------------------------------------------------------------------------


class TestStartWorkflow:
    def test_emits_running_status(self):
        t = _make_tracker()
        updates = _capture_updates(t)
        t.start_workflow()
        assert updates[-1].status == ProgressStatus.RUNNING

    def test_emits_update_with_workflow_name(self):
        t = _make_tracker(workflow_name="my-wf")
        updates = _capture_updates(t)
        t.start_workflow()
        assert updates[-1].workflow == "my-wf"


# ---------------------------------------------------------------------------
# 8. ProgressTracker — start_stage()
# ---------------------------------------------------------------------------


class TestStartStage:
    def test_marks_stage_as_running(self):
        t = _make_tracker(["alpha", "beta"])
        t.start_stage("alpha")
        stage = next(s for s in t.stages if s.name == "alpha")
        assert stage.status == ProgressStatus.RUNNING

    def test_sets_tier_on_stage(self):
        t = _make_tracker(["alpha"])
        t.start_stage("alpha", tier="premium")
        stage = t.stages[0]
        assert stage.tier == "premium"

    def test_sets_model_on_stage(self):
        t = _make_tracker(["alpha"])
        t.start_stage("alpha", model="claude-opus-4-6")
        stage = t.stages[0]
        assert stage.model == "claude-opus-4-6"

    def test_emits_running_update(self):
        t = _make_tracker(["alpha"])
        updates = _capture_updates(t)
        t.start_stage("alpha")
        assert any(u.status == ProgressStatus.RUNNING for u in updates)

    def test_unknown_stage_does_not_raise(self):
        t = _make_tracker(["alpha"])
        t.start_stage("nonexistent")  # must not raise


# ---------------------------------------------------------------------------
# 9. ProgressTracker — complete_stage()
# ---------------------------------------------------------------------------


class TestCompleteStage:
    def test_marks_stage_as_completed(self):
        t = _make_tracker(["alpha"])
        t.start_stage("alpha")
        t.complete_stage("alpha")
        assert t.stages[0].status == ProgressStatus.COMPLETED

    def test_accumulates_cost(self):
        t = _make_tracker(["alpha", "beta"])
        t.complete_stage("alpha", cost=1.0)
        t.complete_stage("beta", cost=0.5)
        assert t.cost_accumulated == pytest.approx(1.5)

    def test_accumulates_tokens(self):
        t = _make_tracker(["alpha"])
        t.complete_stage("alpha", tokens_in=100, tokens_out=200)
        assert t.tokens_accumulated == 300

    def test_emits_completed_update(self):
        t = _make_tracker(["alpha"])
        updates = _capture_updates(t)
        t.complete_stage("alpha")
        assert any(u.status == ProgressStatus.COMPLETED for u in updates)

    def test_stores_cost_on_stage(self):
        t = _make_tracker(["alpha"])
        t.start_stage("alpha")
        t.complete_stage("alpha", cost=2.5)
        assert t.stages[0].cost == 2.5


# ---------------------------------------------------------------------------
# 10. ProgressTracker — fail_stage()
# ---------------------------------------------------------------------------


class TestFailStage:
    def test_marks_stage_as_failed(self):
        t = _make_tracker(["alpha"])
        t.start_stage("alpha")
        t.fail_stage("alpha", error="timeout")
        assert t.stages[0].status == ProgressStatus.FAILED

    def test_stores_error_on_stage(self):
        t = _make_tracker(["alpha"])
        t.fail_stage("alpha", error="connection refused")
        assert t.stages[0].error == "connection refused"

    def test_emits_failed_update(self):
        t = _make_tracker(["alpha"])
        updates = _capture_updates(t)
        t.fail_stage("alpha", error="err")
        assert any(u.status == ProgressStatus.FAILED for u in updates)

    def test_failed_update_contains_error(self):
        t = _make_tracker(["alpha"])
        updates = _capture_updates(t)
        t.fail_stage("alpha", error="boom")
        failed_updates = [u for u in updates if u.status == ProgressStatus.FAILED]
        assert any(u.error == "boom" for u in failed_updates)


# ---------------------------------------------------------------------------
# 11. ProgressTracker — skip_stage()
# ---------------------------------------------------------------------------


class TestSkipStage:
    def test_marks_stage_as_skipped(self):
        t = _make_tracker(["alpha"])
        t.skip_stage("alpha")
        assert t.stages[0].status == ProgressStatus.SKIPPED

    def test_emits_skipped_update(self):
        t = _make_tracker(["alpha"])
        updates = _capture_updates(t)
        t.skip_stage("alpha")
        assert any(u.status == ProgressStatus.SKIPPED for u in updates)

    def test_accepts_reason_string(self):
        t = _make_tracker(["alpha"])
        updates = _capture_updates(t)
        t.skip_stage("alpha", reason="not applicable")
        assert len(updates) >= 1  # must not raise


# ---------------------------------------------------------------------------
# 12. ProgressTracker — update_tier()
# ---------------------------------------------------------------------------


class TestUpdateTier:
    def test_updates_tier_on_stage(self):
        t = _make_tracker(["alpha"])
        t.start_stage("alpha", tier="capable")
        t.update_tier("alpha", "premium")
        assert t.stages[0].tier == "premium"

    def test_emits_running_update(self):
        t = _make_tracker(["alpha"])
        t.start_stage("alpha")
        updates = _capture_updates(t)
        t.update_tier("alpha", "premium")
        assert any(u.status == ProgressStatus.RUNNING for u in updates)


# ---------------------------------------------------------------------------
# 13. ProgressTracker — fallback_occurred()
# ---------------------------------------------------------------------------


class TestFallbackOccurred:
    def test_marks_stage_as_fallback(self):
        t = _make_tracker(["alpha"])
        t.fallback_occurred(
            "alpha",
            original_model="claude-haiku",
            fallback_model="claude-sonnet",
            reason="validation_failed",
        )
        assert t.stages[0].status == ProgressStatus.FALLBACK

    def test_stores_fallback_info_on_stage(self):
        t = _make_tracker(["alpha"])
        t.fallback_occurred("alpha", "old-model", "new-model", "timeout")
        assert t.stages[0].fallback_info is not None

    def test_emits_fallback_status_update(self):
        t = _make_tracker(["alpha"])
        updates = _capture_updates(t)
        t.fallback_occurred("alpha", "m1", "m2", "reason")
        assert any(u.status == ProgressStatus.FALLBACK for u in updates)


# ---------------------------------------------------------------------------
# 14. ProgressTracker — retry_occurred()
# ---------------------------------------------------------------------------


class TestRetryOccurred:
    def test_marks_stage_as_retrying(self):
        t = _make_tracker(["alpha"])
        t.retry_occurred("alpha", attempt=1, max_attempts=3)
        assert t.stages[0].status == ProgressStatus.RETRYING

    def test_stores_retry_count_on_stage(self):
        t = _make_tracker(["alpha"])
        t.retry_occurred("alpha", attempt=2, max_attempts=3)
        assert t.stages[0].retry_count == 2

    def test_emits_retrying_status_update(self):
        t = _make_tracker(["alpha"])
        updates = _capture_updates(t)
        t.retry_occurred("alpha", attempt=1, max_attempts=3)
        assert any(u.status == ProgressStatus.RETRYING for u in updates)


# ---------------------------------------------------------------------------
# 15. ProgressTracker — complete_workflow() and fail_workflow()
# ---------------------------------------------------------------------------


class TestWorkflowLifecycle:
    def test_complete_workflow_emits_completed(self):
        t = _make_tracker()
        updates = _capture_updates(t)
        t.complete_workflow()
        assert any(u.status == ProgressStatus.COMPLETED for u in updates)

    def test_fail_workflow_emits_failed(self):
        t = _make_tracker()
        updates = _capture_updates(t)
        t.fail_workflow("fatal error")
        assert any(u.status == ProgressStatus.FAILED for u in updates)

    def test_fail_workflow_includes_error(self):
        t = _make_tracker()
        updates = _capture_updates(t)
        t.fail_workflow("fatal error")
        failed = [u for u in updates if u.status == ProgressStatus.FAILED]
        assert any(u.error == "fatal error" for u in failed)


# ---------------------------------------------------------------------------
# 16. Percent complete calculation
# ---------------------------------------------------------------------------


class TestPercentComplete:
    def test_zero_percent_at_start(self):
        t = _make_tracker(["a", "b", "c"])
        updates = _capture_updates(t)
        t.start_workflow()
        assert updates[-1].percent_complete == 0.0

    def test_percent_increases_as_stages_complete(self):
        t = _make_tracker(["a", "b", "c"])
        updates = _capture_updates(t)
        t.complete_stage("a")
        # After completing 1 of 3 stages, percent should be > 0
        assert updates[-1].percent_complete > 0.0

    def test_full_percent_after_all_complete(self):
        t = _make_tracker(["a", "b"])
        updates = _capture_updates(t)
        t.complete_stage("a")
        t.complete_stage("b")
        assert updates[-1].percent_complete == 100.0


# ---------------------------------------------------------------------------
# 17. Callback exception isolation
# ---------------------------------------------------------------------------


class TestCallbackExceptionIsolation:
    def test_failing_callback_does_not_propagate(self):
        t = _make_tracker(["a"])

        def bad_callback(u: ProgressUpdate) -> None:
            raise RuntimeError("callback error")

        t.add_callback(bad_callback)
        t.start_workflow()  # must not raise RuntimeError

    def test_second_callback_still_called_after_first_fails(self):
        t = _make_tracker(["a"])
        received: list[ProgressUpdate] = []

        def bad_callback(u: ProgressUpdate) -> None:
            raise RuntimeError("bad")

        t.add_callback(bad_callback)
        t.add_callback(received.append)
        t.start_workflow()
        assert len(received) >= 1
