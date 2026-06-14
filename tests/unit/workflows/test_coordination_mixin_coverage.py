"""Coverage tests for CoordinationMixin's remaining branches.

Targets the lazy-init body of ``_get_adaptive_router`` and the
exception paths of ``send_signal`` / ``wait_for_signal`` /
``check_signal`` — branches not exercised by
``test_workflow_coordination.py``.

Module-level lines 35-37 (the ``ImportError`` telemetry-import
guard) are unreachable when ``attune.telemetry`` imports cleanly,
so they remain uncovered by design (~92% ceiling).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.base import BaseWorkflow, ModelTier


class SimpleWorkflow(BaseWorkflow):
    """Minimal host workflow for exercising the mixin."""

    name = "coord-test-workflow"
    description = "Host for coordination mixin coverage"
    stages = ["stage1"]
    tier_map = {"stage1": ModelTier.CHEAP}

    async def run_stage(self, stage_name, tier, input_data):
        return {"stage": stage_name}, 1, 1


@pytest.fixture
def workflow() -> SimpleWorkflow:
    """Workflow with all coordination features enabled."""
    return SimpleWorkflow(
        enable_heartbeat_tracking=True,
        enable_coordination=True,
        enable_adaptive_routing=True,
        agent_id="coord-agent",
    )


# ---------------------------------------------------------------------------
# _get_adaptive_router()
# ---------------------------------------------------------------------------


class TestGetAdaptiveRouter:
    """Cover the lazy-init body of _get_adaptive_router (lines 60-93)."""

    def test_disabled_returns_none(self, workflow):
        """Routing disabled short-circuits before any import."""
        workflow._enable_adaptive_routing = False
        assert workflow._get_adaptive_router() is None

    def test_successful_init(self, workflow):
        """Telemetry available → AdaptiveModelRouter constructed and cached."""
        workflow._enable_adaptive_routing = True
        workflow._adaptive_router = None

        mock_router = MagicMock()
        mock_router_cls = MagicMock(return_value=mock_router)
        mock_tracker = MagicMock()
        mock_models = MagicMock(AdaptiveModelRouter=mock_router_cls)

        with (
            patch.dict("sys.modules", {"attune.models": mock_models}),
            patch("attune.workflows.coordination_mixin.TELEMETRY_AVAILABLE", True),
            patch(
                "attune.workflows.coordination_mixin.UsageTracker",
                MagicMock(get_instance=MagicMock(return_value=mock_tracker)),
            ),
        ):
            result = workflow._get_adaptive_router()

        assert result is mock_router
        mock_router_cls.assert_called_once_with(telemetry=mock_tracker)

    def test_telemetry_unavailable_disables_routing(self, workflow):
        """No telemetry → warning logged and routing disabled, returns None."""
        workflow._enable_adaptive_routing = True
        workflow._adaptive_router = None

        mock_models = MagicMock(AdaptiveModelRouter=MagicMock())
        with (
            patch.dict("sys.modules", {"attune.models": mock_models}),
            patch("attune.workflows.coordination_mixin.TELEMETRY_AVAILABLE", False),
            patch("attune.workflows.coordination_mixin.logger"),
        ):
            result = workflow._get_adaptive_router()

        assert result is None
        assert workflow._enable_adaptive_routing is False

    def test_import_error_disables_routing(self, workflow):
        """ImportError on AdaptiveModelRouter disables routing gracefully."""
        workflow._enable_adaptive_routing = True
        workflow._adaptive_router = None

        # spec=[] → ``from attune.models import AdaptiveModelRouter`` raises ImportError.
        mock_models = MagicMock(spec=[])
        with (
            patch.dict("sys.modules", {"attune.models": mock_models}),
            patch("attune.workflows.coordination_mixin.logger"),
        ):
            result = workflow._get_adaptive_router()

        assert result is None
        assert workflow._enable_adaptive_routing is False

    def test_cached_router_returned_without_reinit(self, workflow):
        """An already-initialized router is returned as-is."""
        sentinel = MagicMock()
        workflow._enable_adaptive_routing = True
        workflow._adaptive_router = sentinel
        assert workflow._get_adaptive_router() is sentinel


# ---------------------------------------------------------------------------
# send_signal / wait_for_signal / check_signal — exception paths
# ---------------------------------------------------------------------------


class TestSignalExceptionPaths:
    """Coordinator raising → method swallows and returns the safe default."""

    def test_send_signal_swallows_exception(self, workflow):
        coordinator = MagicMock()
        coordinator.signal.side_effect = RuntimeError("redis exploded")
        with patch.object(workflow, "_get_coordination_signals", return_value=coordinator):
            assert workflow.send_signal(signal_type="task_complete") == ""

    def test_wait_for_signal_swallows_exception(self, workflow):
        coordinator = MagicMock()
        coordinator.wait_for_signal.side_effect = RuntimeError("redis exploded")
        with patch.object(workflow, "_get_coordination_signals", return_value=coordinator):
            assert workflow.wait_for_signal(signal_type="approval", timeout=0.1) is None

    def test_check_signal_swallows_exception(self, workflow):
        coordinator = MagicMock()
        coordinator.check_signal.side_effect = RuntimeError("redis exploded")
        with patch.object(workflow, "_get_coordination_signals", return_value=coordinator):
            assert workflow.check_signal(signal_type="abort") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
