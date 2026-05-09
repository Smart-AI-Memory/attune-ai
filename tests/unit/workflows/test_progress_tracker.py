"""Direct tests for ProgressTracker — covers branches not exercised elsewhere.

The tracker has many lifecycle hooks (start/complete/fail/skip/fallback/retry)
that other tests don't exercise directly. These tests fill the coverage gaps.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.workflows.progress import (
    ProgressStatus,
    ProgressTracker,
    create_progress_tracker,
)


def _make_tracker(stage_names=None) -> ProgressTracker:
    return ProgressTracker(
        workflow_name="test-wf",
        workflow_id="wf-001",
        stage_names=stage_names or ["a", "b", "c"],
    )


@pytest.mark.unit
class TestCallbackManagement:
    def test_add_async_callback(self):
        """add_async_callback appends to the async list (line 92)."""
        tracker = _make_tracker()

        async def cb(update):
            return None

        tracker.add_async_callback(cb)
        assert cb in tracker._async_callbacks

    def test_remove_callback_removes_when_present(self):
        """remove_callback removes a registered sync callback (lines 96-97)."""
        tracker = _make_tracker()

        def cb(update):
            return None

        tracker.add_callback(cb)
        assert cb in tracker._callbacks
        tracker.remove_callback(cb)
        assert cb not in tracker._callbacks

    def test_remove_callback_noop_when_absent(self):
        """remove_callback silently ignores unknown callbacks (line 96 False branch)."""
        tracker = _make_tracker()

        def cb(update):
            return None

        # Not previously added — should not raise
        tracker.remove_callback(cb)


@pytest.mark.unit
class TestStageLifecycleUnknownStage:
    """Cover the `if stage:` False branches when stage_name is unknown."""

    def test_start_stage_unknown_emits_running_anyway(self):
        """start_stage with unknown name still emits an update (branch 107->116)."""
        tracker = _make_tracker()
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))

        tracker.start_stage("unknown-stage")

        assert any(u.status == ProgressStatus.RUNNING for u in emitted)

    def test_complete_stage_unknown_still_accumulates(self):
        """complete_stage with unknown name still updates totals (branch 127->139)."""
        tracker = _make_tracker()
        tracker.complete_stage("unknown-stage", cost=1.5, tokens_in=10, tokens_out=5)

        assert tracker.cost_accumulated == 1.5
        assert tracker.tokens_accumulated == 15

    def test_complete_stage_without_started_at(self):
        """complete_stage on a stage that never started skips duration calc (branch 134->139)."""
        tracker = _make_tracker()
        # Note: complete WITHOUT calling start_stage first → started_at is None
        tracker.complete_stage("a", cost=0.0)

        stage = tracker._get_stage("a")
        assert stage is not None
        assert stage.duration_ms == 0  # default, not computed

    def test_fail_stage_unknown_emits_failed(self):
        """fail_stage with unknown name still emits FAILED (branch 149->159)."""
        tracker = _make_tracker()
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))

        tracker.fail_stage("unknown-stage", error="boom")
        assert any(u.status == ProgressStatus.FAILED for u in emitted)

    def test_fail_stage_without_started_at_skips_duration(self):
        """fail_stage on a never-started stage skips duration calc (branch 154->159)."""
        tracker = _make_tracker()
        tracker.fail_stage("a", error="kaboom")
        stage = tracker._get_stage("a")
        assert stage is not None
        assert stage.duration_ms == 0


@pytest.mark.unit
class TestSkipStage:
    def test_skip_stage_with_reason(self):
        """skip_stage with reason includes it in the message (lines 163-170)."""
        tracker = _make_tracker()
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))

        tracker.skip_stage("a", reason="cache hit")
        skipped = [u for u in emitted if u.status == ProgressStatus.SKIPPED]
        assert skipped
        assert "cache hit" in skipped[-1].message

    def test_skip_stage_without_reason(self):
        tracker = _make_tracker()
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))

        tracker.skip_stage("a")
        skipped = [u for u in emitted if u.status == ProgressStatus.SKIPPED]
        assert skipped
        assert "Skipped a" in skipped[-1].message


@pytest.mark.unit
class TestUpdateTier:
    def test_update_tier_with_reason(self):
        """update_tier with reason appends it to the message (lines 187, 190)."""
        tracker = _make_tracker()
        tracker.start_stage("a", tier="cheap")
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))

        tracker.update_tier("a", "capable", reason="cheap failed validation")

        assert any(
            "capable failed validation" in u.message.lower()
            or "cheap failed validation" in u.message.lower()
            for u in emitted
        )

    def test_update_tier_unknown_stage_still_emits_no_message(self):
        """update_tier on unknown stage hits the `if stage:` False branch (182->exit)."""
        tracker = _make_tracker()
        # Should not raise — function silently no-ops because stage is None
        tracker.update_tier("unknown-stage", "capable")


@pytest.mark.unit
class TestFallbackOccurred:
    def test_fallback_occurred_records_state(self):
        """fallback_occurred sets stage.fallback_info and emits (lines 200-207)."""
        tracker = _make_tracker()
        tracker.start_stage("a", model="cheap-model")
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))

        tracker.fallback_occurred("a", "cheap-model", "capable-model", "rate limit")

        stage = tracker._get_stage("a")
        assert stage is not None
        assert stage.status == ProgressStatus.FALLBACK
        assert "cheap-model" in stage.fallback_info
        assert "capable-model" in stage.fallback_info
        assert any(u.status == ProgressStatus.FALLBACK for u in emitted)


@pytest.mark.unit
class TestRetryOccurred:
    def test_retry_occurred_increments_retry_count(self):
        """retry_occurred sets RETRYING and increments retry_count (lines 215-220)."""
        tracker = _make_tracker()
        tracker.start_stage("a")
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))

        tracker.retry_occurred("a", attempt=2, max_attempts=3)

        stage = tracker._get_stage("a")
        assert stage is not None
        assert stage.status == ProgressStatus.RETRYING
        assert stage.retry_count == 2
        assert any(u.status == ProgressStatus.RETRYING for u in emitted)


@pytest.mark.unit
class TestGetStageNotFound:
    def test_get_stage_returns_none_for_unknown(self):
        """_get_stage returns None when name doesn't match (line 245)."""
        tracker = _make_tracker()
        assert tracker._get_stage("nonexistent") is None


@pytest.mark.unit
class TestEmitCallbackErrors:
    def test_sync_callback_exception_swallowed(self, caplog):
        """A raising sync callback gets logged but does not stop emission (lines 296-299)."""
        tracker = _make_tracker()

        def bad_callback(update):
            raise RuntimeError("callback exploded")

        good_emissions = []

        def good_callback(update):
            good_emissions.append(update)

        tracker.add_callback(bad_callback)
        tracker.add_callback(good_callback)

        # Must not raise; both callbacks attempted
        tracker.start_workflow()
        # The good callback still got called even though bad_callback threw
        assert good_emissions

    @pytest.mark.asyncio
    async def test_async_callback_path(self):
        """Async callback path runs without RuntimeError when an event loop exists (lines 303-307)."""
        tracker = _make_tracker()
        captured: list = []

        async def async_cb(update):
            captured.append(update)

        tracker.add_async_callback(async_cb)
        tracker.start_workflow()
        # Allow the scheduled task to run
        import asyncio

        await asyncio.sleep(0)
        assert captured  # async cb was scheduled and ran

    def test_async_callback_runtime_error_swallowed(self):
        """Without a running event loop, async callback path catches RuntimeError (line 305-307)."""
        tracker = _make_tracker()

        async def async_cb(update):
            return None

        tracker.add_async_callback(async_cb)
        # Calling start_workflow synchronously (no event loop) — must not raise
        tracker.start_workflow()


@pytest.mark.unit
class TestStageDurationTracking:
    def test_complete_stage_with_started_at_records_duration(self):
        """complete_stage after start_stage records duration_ms (lines 135-137)."""
        tracker = _make_tracker()
        tracker.start_stage("a")
        tracker.complete_stage("a", cost=0.0)

        stage = tracker._get_stage("a")
        assert stage is not None
        # Duration is computed from start→complete; will be small but non-negative
        assert stage.duration_ms >= 0
        # Duration was appended to the rolling list
        assert tracker._stage_durations

    def test_fail_stage_with_started_at_records_duration(self):
        """fail_stage after start_stage records duration_ms (line 155)."""
        tracker = _make_tracker()
        tracker.start_stage("a")
        tracker.fail_stage("a", error="oops")
        stage = tracker._get_stage("a")
        assert stage is not None
        assert stage.duration_ms >= 0


@pytest.mark.unit
class TestUnknownStageBranches:
    def test_skip_stage_unknown_branch(self):
        """skip_stage with unknown name takes the if-False branch (164->167)."""
        tracker = _make_tracker()
        # Should not raise; emits a SKIPPED message even though stage lookup failed
        tracker.skip_stage("missing-stage")

    def test_update_tier_no_reason(self):
        """update_tier with no reason takes the False branch (187->190)."""
        tracker = _make_tracker()
        tracker.start_stage("a", tier="cheap")
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))

        tracker.update_tier("a", "capable")  # no reason kwarg

        # Message goes out without parenthesized reason suffix
        assert any("Tier upgrade" in u.message for u in emitted)
        assert not any("()" in u.message for u in emitted)

    def test_fallback_occurred_unknown_stage(self):
        """fallback_occurred on unknown stage (branch 203->207)."""
        tracker = _make_tracker()
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))
        tracker.fallback_occurred("missing", "m1", "m2", "rate limit")
        # Still emits a FALLBACK update
        assert any(u.status == ProgressStatus.FALLBACK for u in emitted)

    def test_retry_occurred_unknown_stage(self):
        """retry_occurred on unknown stage (branch 216->220)."""
        tracker = _make_tracker()
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))
        tracker.retry_occurred("missing", attempt=1, max_attempts=3)
        assert any(u.status == ProgressStatus.RETRYING for u in emitted)


@pytest.mark.unit
class TestWorkflowCompletion:
    def test_complete_workflow_emits(self):
        """complete_workflow emits a COMPLETED update (line 227)."""
        tracker = _make_tracker()
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))
        tracker.complete_workflow()
        assert any(u.status == ProgressStatus.COMPLETED for u in emitted)

    def test_fail_workflow_emits(self):
        """fail_workflow emits a FAILED update with error (line 234)."""
        tracker = _make_tracker()
        emitted = []
        tracker.add_callback(lambda u: emitted.append(u))
        tracker.fail_workflow(error="catastrophic")
        failed = [u for u in emitted if u.status == ProgressStatus.FAILED]
        assert failed
        assert failed[-1].error == "catastrophic"


@pytest.mark.unit
class TestEstimateRemaining:
    def test_estimate_remaining_with_durations(self):
        """_estimate_remaining_ms computes from rolling average (lines 257-259)."""
        tracker = _make_tracker()
        # Complete one stage to populate _stage_durations
        tracker.start_stage("a")
        tracker.complete_stage("a", cost=0.0)
        # Now there's at least one duration recorded; estimating remaining is valid
        remaining = tracker._estimate_remaining_ms()
        assert remaining is not None
        assert remaining >= 0


@pytest.mark.unit
class TestCreateProgressTracker:
    def test_factory_with_reporter_attaches_callback(self):
        """create_progress_tracker with a reporter attaches its `report` method as a callback."""

        class _Reporter:
            def __init__(self):
                self.calls = []

            def report(self, update):
                self.calls.append(update)

        reporter = _Reporter()
        tracker = create_progress_tracker(
            workflow_name="wf",
            stage_names=["a", "b"],
            reporter=reporter,
        )
        tracker.start_workflow()
        assert reporter.calls

    def test_factory_without_reporter(self):
        """create_progress_tracker with no reporter still works."""
        tracker = create_progress_tracker(
            workflow_name="wf",
            stage_names=["a"],
            reporter=None,
        )
        assert tracker._callbacks == []
