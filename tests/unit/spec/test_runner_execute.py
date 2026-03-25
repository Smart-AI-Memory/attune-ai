"""Tests for spec.runner — execute_with_approval and edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.spec.runner import execute_with_approval, get_pending_tasks
from attune.spec.state import SpecState
from attune.wizards.decomposer import DecomposedTask

# Lazy imports in execute_with_approval come from their source modules.
# Patch at the source, not at attune.spec.runner.
_LOAD_STATE = "attune.spec.state.load_state"
_SAVE_STATE = "attune.spec.state.save_state"
_ORCH_CLS = "attune.pipeline.orchestrator.PipelineOrchestrator"


def _make_task(task_id):
    return DecomposedTask(
        task_id=task_id,
        name=f"task-{task_id}",
        objective="Test",
        files_to_create=[],
        files_to_modify=[],
        validation_checks=[],
        risks=[],
        dependencies=[],
    )


# ---------------------------------------------------------------------------
# get_pending_tasks — additional edge cases
# ---------------------------------------------------------------------------


class TestGetPendingTasksEdgeCases:
    """Additional edge cases for get_pending_tasks."""

    def test_empty_tasks_and_empty_state(self):
        state = SpecState(plan_path="x")
        assert get_pending_tasks([], state) == []

    def test_duplicate_completed_ids_handled(self):
        tasks = [_make_task("1"), _make_task("2")]
        state = SpecState(plan_path="x", completed=["1", "1", "1"])
        pending = get_pending_tasks(tasks, state)
        assert len(pending) == 1
        assert pending[0].task_id == "2"


# ---------------------------------------------------------------------------
# execute_with_approval
# ---------------------------------------------------------------------------


class TestExecuteWithApproval:
    """Tests for execute_with_approval orchestration."""

    @pytest.mark.asyncio
    async def test_loads_existing_state_for_resume(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n\n<task id='1'>\nDo thing\n</task>\n", encoding="utf-8")

        existing_state = SpecState(plan_path=str(plan_file), completed=["1"])

        mock_result = MagicMock()
        mock_orch_instance = MagicMock()
        mock_orch_instance.run_all = AsyncMock(return_value=mock_result)

        callback = AsyncMock(return_value="approve")

        with (
            patch(_LOAD_STATE, return_value=existing_state),
            patch(_SAVE_STATE),
            patch(_ORCH_CLS, return_value=mock_orch_instance),
        ):
            result = await execute_with_approval(
                spec_path=str(plan_file),
                on_task_complete=callback,
            )

        assert result is mock_result
        call_kwargs = mock_orch_instance.run_all.call_args[1]
        assert "1" in call_kwargs["skip_task_ids"]

    @pytest.mark.asyncio
    async def test_creates_new_state_when_none_exists(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        mock_result = MagicMock()
        mock_orch_instance = MagicMock()
        mock_orch_instance.run_all = AsyncMock(return_value=mock_result)

        callback = AsyncMock(return_value="approve")

        with (
            patch(_LOAD_STATE, return_value=None),
            patch(_SAVE_STATE),
            patch(_ORCH_CLS, return_value=mock_orch_instance),
        ):
            result = await execute_with_approval(
                spec_path=str(plan_file),
                on_task_complete=callback,
            )

        assert result is mock_result
        call_kwargs = mock_orch_instance.run_all.call_args[1]
        assert call_kwargs["skip_task_ids"] == set()

    @pytest.mark.asyncio
    async def test_passes_skip_flags_to_orchestrator(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        mock_orch_cls = MagicMock()
        mock_orch_instance = MagicMock()
        mock_orch_instance.run_all = AsyncMock(return_value=MagicMock())
        mock_orch_cls.return_value = mock_orch_instance

        callback = AsyncMock(return_value="approve")

        with (
            patch(_LOAD_STATE, return_value=None),
            patch(_SAVE_STATE),
            patch(_ORCH_CLS, mock_orch_cls),
        ):
            await execute_with_approval(
                spec_path=str(plan_file),
                on_task_complete=callback,
                skip_gates=True,
                skip_tests=True,
                skip_simplify=True,
            )

        constructor_args = mock_orch_cls.call_args
        assert constructor_args[1]["skip_gates"] is True
        assert constructor_args[1]["skip_tests"] is True
        assert constructor_args[1]["skip_simplify"] is True

    @pytest.mark.asyncio
    async def test_wrapped_callback_saves_state_on_approve(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        save_calls = []

        def mock_save(state):
            save_calls.append(state.to_dict())

        mock_orch_instance = MagicMock()

        async def fake_run_all(on_task_complete, skip_task_ids):
            task = MagicMock()
            task.task_id = "42"
            result = MagicMock()
            decision = await on_task_complete(task, result)
            assert decision == "approve"
            return MagicMock()

        mock_orch_instance.run_all = fake_run_all

        user_callback = AsyncMock(return_value="approve")

        with (
            patch(_LOAD_STATE, return_value=None),
            patch(_SAVE_STATE, side_effect=mock_save),
            patch(_ORCH_CLS, return_value=mock_orch_instance),
        ):
            await execute_with_approval(
                spec_path=str(plan_file),
                on_task_complete=user_callback,
            )

        # save_state called at least twice: setting current, then after approve
        assert len(save_calls) >= 2
        assert "42" in save_calls[-1]["completed"]
        assert save_calls[-1]["current"] is None

    @pytest.mark.asyncio
    async def test_wrapped_callback_sets_auto_run(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        saved_states = []

        def mock_save(state):
            saved_states.append(
                SpecState(
                    plan_path=state.plan_path,
                    completed=list(state.completed),
                    current=state.current,
                    auto_run=state.auto_run,
                )
            )

        mock_orch_instance = MagicMock()

        async def fake_run_all(on_task_complete, skip_task_ids):
            task = MagicMock()
            task.task_id = "5"
            decision = await on_task_complete(task, MagicMock())
            assert decision == "auto"
            return MagicMock()

        mock_orch_instance.run_all = fake_run_all
        user_callback = AsyncMock(return_value="auto")

        with (
            patch(_LOAD_STATE, return_value=None),
            patch(_SAVE_STATE, side_effect=mock_save),
            patch(_ORCH_CLS, return_value=mock_orch_instance),
        ):
            await execute_with_approval(
                spec_path=str(plan_file),
                on_task_complete=user_callback,
            )

        assert any(s.auto_run for s in saved_states)

    @pytest.mark.asyncio
    async def test_wrapped_callback_defaults_none_to_approve(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        mock_orch_instance = MagicMock()

        async def fake_run_all(on_task_complete, skip_task_ids):
            task = MagicMock()
            task.task_id = "1"
            decision = await on_task_complete(task, MagicMock())
            assert decision == "approve"
            return MagicMock()

        mock_orch_instance.run_all = fake_run_all
        user_callback = AsyncMock(return_value=None)

        with (
            patch(_LOAD_STATE, return_value=None),
            patch(_SAVE_STATE),
            patch(_ORCH_CLS, return_value=mock_orch_instance),
        ):
            await execute_with_approval(
                spec_path=str(plan_file),
                on_task_complete=user_callback,
            )

    @pytest.mark.asyncio
    async def test_wrapped_callback_does_not_save_on_redo(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n", encoding="utf-8")

        save_calls = []

        def mock_save(state):
            save_calls.append(state.to_dict())

        mock_orch_instance = MagicMock()

        async def fake_run_all(on_task_complete, skip_task_ids):
            task = MagicMock()
            task.task_id = "7"
            decision = await on_task_complete(task, MagicMock())
            assert decision == "redo"
            return MagicMock()

        mock_orch_instance.run_all = fake_run_all
        user_callback = AsyncMock(return_value="redo")

        with (
            patch(_LOAD_STATE, return_value=None),
            patch(_SAVE_STATE, side_effect=mock_save),
            patch(_ORCH_CLS, return_value=mock_orch_instance),
        ):
            await execute_with_approval(
                spec_path=str(plan_file),
                on_task_complete=user_callback,
            )

        # Only the first save (setting current) should happen
        assert len(save_calls) == 1
        assert "7" not in save_calls[0].get("completed", [])
