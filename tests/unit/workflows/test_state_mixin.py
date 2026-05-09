"""Tests for StatePersistenceMixin integration with BaseWorkflow.

Tests that the state persistence mixin correctly records workflow
lifecycle events and saves stage checkpoints, while being completely
transparent (no-op) when state_store is None.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from attune.agents.state.store import AgentStateStore
from attune.cost_tracker import CostTracker
from attune.workflows.base import BaseWorkflow
from attune.workflows.compat import ModelTier

# ---------------------------------------------------------------------------
# Minimal concrete workflow for testing
# ---------------------------------------------------------------------------


class _StubWorkflow(BaseWorkflow):
    """Minimal workflow subclass for testing state persistence."""

    name = "stub-workflow"
    description = "Stub for state persistence tests"
    stages = ["stage_a", "stage_b"]
    tier_map = {
        "stage_a": ModelTier.CHEAP,
        "stage_b": ModelTier.CAPABLE,
    }

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Return dummy output."""
        return {"stage": stage_name, "result": "ok"}, 100, 50


class _FailingStubWorkflow(BaseWorkflow):
    """Workflow that raises during stage execution."""

    name = "failing-stub"
    description = "Fails during stage_b"
    stages = ["stage_a", "stage_b"]
    tier_map = {
        "stage_a": ModelTier.CHEAP,
        "stage_b": ModelTier.CAPABLE,
    }

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        """Raise on stage_b."""
        if stage_name == "stage_b":
            raise ValueError("Intentional test error")
        return {"stage": stage_name}, 100, 50


# ---------------------------------------------------------------------------
# Tests: state_store is None (no-op path)
# ---------------------------------------------------------------------------


class TestStatePersistenceNoop:
    """Verify that everything works normally when state_store is None."""

    async def test_execute_without_state_store(self, tmp_path: Path) -> None:
        """Workflow executes normally without state_store."""
        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))
        wf = _StubWorkflow(cost_tracker=cost_tracker)

        result = await wf.execute(data="test")

        assert result.success is True
        assert len(result.stages) == 2

    def test_state_store_defaults_to_none(self, tmp_path: Path) -> None:
        """state_store defaults to None."""
        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))
        wf = _StubWorkflow(cost_tracker=cost_tracker)

        assert wf._state_store is None


# ---------------------------------------------------------------------------
# Tests: state_store is provided
# ---------------------------------------------------------------------------


class TestStatePersistenceEnabled:
    """Verify that state store methods are called during workflow execution."""

    @pytest.fixture
    def state_store(self, tmp_path: Path) -> AgentStateStore:
        """Create an AgentStateStore in a temp directory."""
        return AgentStateStore(storage_dir=str(tmp_path / "state"))

    @pytest.fixture
    def cost_tracker(self, tmp_path: Path) -> CostTracker:
        """Create isolated CostTracker."""
        return CostTracker(storage_dir=str(tmp_path / ".empathy"))

    async def test_records_workflow_start(
        self,
        state_store: AgentStateStore,
        cost_tracker: CostTracker,
    ) -> None:
        """record_start is called during execute()."""
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=state_store)

        # Spy on the state store
        original_record_start = state_store.record_start
        calls: list[tuple] = []

        def spy_record_start(*args: Any, **kwargs: Any) -> str:
            calls.append((args, kwargs))
            return original_record_start(*args, **kwargs)

        state_store.record_start = spy_record_start

        await wf.execute(data="test")

        assert len(calls) == 1
        # Agent ID is auto-set: "{name}-{run_id[:8]}"
        agent_id = calls[0][1].get("agent_id") or calls[0][0][0]
        assert "stub-workflow" in agent_id

    async def test_records_stage_checkpoints(
        self,
        state_store: AgentStateStore,
        cost_tracker: CostTracker,
    ) -> None:
        """Checkpoints are saved for each stage start and completion."""
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=state_store)

        save_calls: list[tuple] = []
        original_save = state_store.save_checkpoint

        def spy_save(*args: Any, **kwargs: Any) -> None:
            save_calls.append((args, kwargs))
            return original_save(*args, **kwargs)

        state_store.save_checkpoint = spy_save

        await wf.execute(data="test")

        # 2 stages -> 2 start checkpoints + 2 complete checkpoints = 4
        assert len(save_calls) == 4

    async def test_checkpoint_tracks_completed_stages(
        self,
        state_store: AgentStateStore,
        cost_tracker: CostTracker,
    ) -> None:
        """Final checkpoint includes all completed stage names."""
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=state_store)

        await wf.execute(data="test")

        # Get the last checkpoint
        agent_id = wf._agent_id
        checkpoint = state_store.get_last_checkpoint(agent_id)

        assert checkpoint is not None
        assert "completed_stages" in checkpoint
        assert checkpoint["completed_stages"] == ["stage_a", "stage_b"]

    async def test_records_workflow_completion(
        self,
        state_store: AgentStateStore,
        cost_tracker: CostTracker,
    ) -> None:
        """record_completion is called on successful workflow."""
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=state_store)

        completion_calls: list[tuple] = []
        original_complete = state_store.record_completion

        def spy_complete(*args: Any, **kwargs: Any) -> None:
            completion_calls.append((args, kwargs))
            return original_complete(*args, **kwargs)

        state_store.record_completion = spy_complete

        await wf.execute(data="test")

        assert len(completion_calls) == 1
        assert completion_calls[0][1]["success"] is True

    async def test_records_workflow_failure(
        self,
        state_store: AgentStateStore,
        cost_tracker: CostTracker,
    ) -> None:
        """record_failure is called on failed workflow."""
        wf = _FailingStubWorkflow(cost_tracker=cost_tracker, state_store=state_store)

        failure_calls: list[tuple] = []
        original_fail = state_store.record_failure

        def spy_fail(*args: Any, **kwargs: Any) -> None:
            failure_calls.append((args, kwargs))
            return original_fail(*args, **kwargs)

        state_store.record_failure = spy_fail

        result = await wf.execute(data="test")

        assert result.success is False
        assert len(failure_calls) == 1

    async def test_stage_costs_tracked_in_checkpoint(
        self,
        state_store: AgentStateStore,
        cost_tracker: CostTracker,
    ) -> None:
        """Checkpoint includes per-stage cost breakdown."""
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=state_store)

        await wf.execute(data="test")

        checkpoint = state_store.get_last_checkpoint(wf._agent_id)

        assert checkpoint is not None
        assert "stage_costs" in checkpoint
        assert "stage_a" in checkpoint["stage_costs"]
        assert "stage_b" in checkpoint["stage_costs"]


# ---------------------------------------------------------------------------
# Tests: error isolation
# ---------------------------------------------------------------------------


class TestStatePersistenceErrorIsolation:
    """Verify that state store errors don't crash the workflow."""

    async def test_broken_state_store_does_not_crash_workflow(self, tmp_path: Path) -> None:
        """A state store that throws on every call doesn't break the workflow."""
        broken_store = MagicMock(spec=AgentStateStore)
        broken_store.record_start.side_effect = OSError("Disk full")
        broken_store.save_checkpoint.side_effect = OSError("Disk full")
        broken_store.record_completion.side_effect = OSError("Disk full")
        broken_store.record_failure.side_effect = OSError("Disk full")

        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=broken_store)

        result = await wf.execute(data="test")

        # Workflow should still succeed despite broken state store
        assert result.success is True
        assert len(result.stages) == 2

    async def test_state_store_exception_logged(self, tmp_path: Path) -> None:
        """State store errors are logged at debug level."""
        broken_store = MagicMock(spec=AgentStateStore)
        broken_store.record_start.side_effect = RuntimeError("test error")
        broken_store.save_checkpoint.side_effect = RuntimeError("test error")
        broken_store.record_completion.side_effect = RuntimeError("test error")

        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=broken_store)

        with patch("attune.workflows.state_mixin.logger") as mock_logger:
            await wf.execute(data="test")

            # At least one debug log for the state store errors
            assert mock_logger.debug.call_count > 0

    async def test_completion_persistence_exception_logged(self, tmp_path: Path) -> None:
        """When record_start succeeds but record_completion throws, the error is
        caught and logged (lines 122-124 in state_mixin.record_workflow_complete)."""
        store = MagicMock(spec=AgentStateStore)
        # record_start succeeds and produces an exec_id so completion is reached
        store.record_start.return_value = "exec-abc"
        store.save_checkpoint.return_value = None
        # record_completion explodes — this is the path under test
        store.record_completion.side_effect = OSError("disk full at completion")

        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=store)

        with patch("attune.workflows.state_mixin.logger") as mock_logger:
            result = await wf.execute(data="test")

        assert result.success is True  # workflow itself still succeeds
        # The exception path emitted a debug log
        assert any(
            "failed to record workflow completion" in str(c)
            for c in mock_logger.debug.call_args_list
        )


# ---------------------------------------------------------------------------
# Tests: recovery checkpoint
# ---------------------------------------------------------------------------


class TestStatePersistenceRecovery:
    """Tests for the recovery checkpoint helper."""

    def test_get_recovery_checkpoint_none_store(self, tmp_path: Path) -> None:
        """Returns None when state_store is None."""
        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))
        wf = _StubWorkflow(cost_tracker=cost_tracker)

        assert wf._state_get_recovery_checkpoint() is None

    async def test_get_recovery_checkpoint_after_execution(self, tmp_path: Path) -> None:
        """Returns checkpoint data after workflow has run."""
        state_store = AgentStateStore(storage_dir=str(tmp_path / "state"))
        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=state_store)

        await wf.execute(data="test")

        checkpoint = wf._state_get_recovery_checkpoint()

        assert checkpoint is not None
        assert checkpoint["workflow_name"] == "stub-workflow"
        assert "completed_stages" in checkpoint

    def test_get_recovery_checkpoint_broken_store(self, tmp_path: Path) -> None:
        """Returns None when state store throws."""
        broken_store = MagicMock(spec=AgentStateStore)
        broken_store.get_last_checkpoint.side_effect = OSError("fail")

        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))
        wf = _StubWorkflow(cost_tracker=cost_tracker, state_store=broken_store)
        wf._agent_id = "test-agent"

        assert wf._state_get_recovery_checkpoint() is None
