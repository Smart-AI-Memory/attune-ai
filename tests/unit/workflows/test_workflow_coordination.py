"""Unit tests for workflow coordination integration.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from attune.workflows.base import BaseWorkflow, ModelTier


class SimpleWorkflow(BaseWorkflow):
    """Simple test workflow."""

    name = "test-workflow"
    description = "Test workflow for coordination"
    stages = ["stage1", "stage2"]
    tier_map = {
        "stage1": ModelTier.CHEAP,
        "stage2": ModelTier.CAPABLE,
    }

    async def run_stage(self, stage_name: str, tier: ModelTier, input_data: dict):
        """Run a simple test stage."""
        await asyncio.sleep(0.1)  # Simulate work
        result = {"stage": stage_name, "completed": True}
        return result, 10, 5


class TestWorkflowHeartbeatIntegration:
    """Test heartbeat tracking integration with BaseWorkflow."""

    def test_workflow_without_heartbeat_tracking(self):
        """Test workflow initialization without heartbeat tracking."""
        workflow = SimpleWorkflow(enable_heartbeat_tracking=False)

        assert workflow._enable_heartbeat_tracking is False
        assert workflow._heartbeat_coordinator is None

    def test_workflow_with_heartbeat_tracking_enabled(self):
        """Test workflow initialization with heartbeat tracking enabled."""
        workflow = SimpleWorkflow(enable_heartbeat_tracking=True, agent_id="test-agent")

        assert workflow._enable_heartbeat_tracking is True
        assert workflow._agent_id == "test-agent"

    @pytest.mark.asyncio
    async def test_workflow_sets_agent_id_automatically(self):
        """Test that workflow auto-generates agent_id if not provided."""
        workflow = SimpleWorkflow(enable_heartbeat_tracking=True)

        # Agent ID is None before execute
        assert workflow._agent_id is None

        # Mock the stage execution to avoid actual LLM calls
        with patch.object(workflow, "run_stage", return_value=({"result": "test"}, 10, 5)):
            await workflow.execute()

        # Agent ID should be auto-generated during execute
        assert workflow._agent_id is not None
        assert workflow._agent_id.startswith("test-workflow-")

    @pytest.mark.asyncio
    async def test_workflow_heartbeat_graceful_degradation(self):
        """Test workflow continues when heartbeat tracking fails."""
        workflow = SimpleWorkflow(enable_heartbeat_tracking=True)

        # Mock _get_heartbeat_coordinator to return None (simulating Redis unavailable)
        with patch.object(workflow, "_get_heartbeat_coordinator", return_value=None):
            with patch.object(workflow, "run_stage", return_value=({"result": "test"}, 10, 5)):
                result = await workflow.execute()

        # Workflow should succeed even without heartbeat tracking
        assert result.success


class TestWorkflowCoordinationIntegration:
    """Test coordination signals integration with BaseWorkflow."""

    def test_workflow_without_coordination(self):
        """Test workflow initialization without coordination."""
        workflow = SimpleWorkflow(enable_coordination=False)

        assert workflow._enable_coordination is False
        assert workflow._coordination_signals is None

    def test_workflow_with_coordination_enabled(self):
        """Test workflow initialization with coordination enabled."""
        workflow = SimpleWorkflow(enable_coordination=True, agent_id="test-agent")

        assert workflow._enable_coordination is True
        assert workflow._agent_id == "test-agent"

    def test_send_signal_without_coordination_returns_empty(self):
        """Test send_signal returns empty string when coordination disabled."""
        workflow = SimpleWorkflow(enable_coordination=False)

        signal_id = workflow.send_signal(
            signal_type="test", target_agent="target", payload={"data": "value"}
        )

        assert signal_id == ""

    def test_wait_for_signal_without_coordination_returns_none(self):
        """Test wait_for_signal returns None when coordination disabled."""
        workflow = SimpleWorkflow(enable_coordination=False)

        signal = workflow.wait_for_signal(signal_type="test", timeout=0.1)

        assert signal is None

    def test_check_signal_without_coordination_returns_none(self):
        """Test check_signal returns None when coordination disabled."""
        workflow = SimpleWorkflow(enable_coordination=False)

        signal = workflow.check_signal(signal_type="test")

        assert signal is None

    @pytest.mark.asyncio
    async def test_workflow_coordination_graceful_degradation(self):
        """Test workflow continues when coordination fails."""
        workflow = SimpleWorkflow(enable_coordination=True)

        # Mock _get_coordination_signals to return None (simulating Redis unavailable)
        with patch.object(workflow, "_get_coordination_signals", return_value=None):
            # send_signal should not raise
            signal_id = workflow.send_signal(signal_type="test", payload={})
            assert signal_id == ""

            # wait_for_signal should not raise
            signal = workflow.wait_for_signal(signal_type="test", timeout=0.1)
            assert signal is None

            # check_signal should not raise
            signal = workflow.check_signal(signal_type="test")
            assert signal is None


class TestWorkflowCoordinationAPI:
    """Test coordination API methods."""

    def test_send_signal_with_mocked_coordinator(self):
        """Test send_signal calls coordinator correctly."""
        workflow = SimpleWorkflow(enable_coordination=True, agent_id="test-agent")

        # Mock the coordination signals
        mock_coordinator = Mock()
        mock_coordinator.signal.return_value = "signal_abc123"

        with patch.object(workflow, "_get_coordination_signals", return_value=mock_coordinator):
            signal_id = workflow.send_signal(
                signal_type="task_complete",
                target_agent="orchestrator",
                payload={"result": "success"},
                ttl_seconds=120,
            )

        assert signal_id == "signal_abc123"
        mock_coordinator.signal.assert_called_once_with(
            signal_type="task_complete",
            source_agent="test-agent",
            target_agent="orchestrator",
            payload={"result": "success"},
            ttl_seconds=120,
        )

    def test_wait_for_signal_with_mocked_coordinator(self):
        """Test wait_for_signal calls coordinator correctly."""
        workflow = SimpleWorkflow(enable_coordination=True, agent_id="test-agent")

        # Mock the coordination signals
        mock_coordinator = Mock()
        mock_signal = Mock()
        mock_signal.signal_type = "approval"
        mock_signal.payload = {"approved": True}
        mock_coordinator.wait_for_signal.return_value = mock_signal

        with patch.object(workflow, "_get_coordination_signals", return_value=mock_coordinator):
            signal = workflow.wait_for_signal(
                signal_type="approval", source_agent="orchestrator", timeout=60.0, poll_interval=1.0
            )

        assert signal == mock_signal
        mock_coordinator.wait_for_signal.assert_called_once_with(
            signal_type="approval", source_agent="orchestrator", timeout=60.0, poll_interval=1.0
        )

    def test_check_signal_with_mocked_coordinator(self):
        """Test check_signal calls coordinator correctly."""
        workflow = SimpleWorkflow(enable_coordination=True, agent_id="test-agent")

        # Mock the coordination signals
        mock_coordinator = Mock()
        mock_signal = Mock()
        mock_signal.signal_type = "abort"
        mock_coordinator.check_signal.return_value = mock_signal

        with patch.object(workflow, "_get_coordination_signals", return_value=mock_coordinator):
            signal = workflow.check_signal(signal_type="abort", source_agent="admin", consume=False)

        assert signal == mock_signal
        mock_coordinator.check_signal.assert_called_once_with(
            signal_type="abort", source_agent="admin", consume=False
        )


class TestWorkflowBothFeaturesEnabled:
    """Test workflow with both heartbeat tracking and coordination enabled."""

    @pytest.mark.asyncio
    async def test_workflow_with_both_features(self):
        """Test workflow with both heartbeat tracking and coordination enabled."""
        workflow = SimpleWorkflow(
            enable_heartbeat_tracking=True, enable_coordination=True, agent_id="test-both"
        )

        assert workflow._enable_heartbeat_tracking is True
        assert workflow._enable_coordination is True
        assert workflow._agent_id == "test-both"

        # Mock both coordinators to avoid Redis dependency
        mock_heartbeat = Mock()
        mock_coordination = Mock()

        with patch.object(workflow, "_get_heartbeat_coordinator", return_value=mock_heartbeat):
            with patch.object(
                workflow, "_get_coordination_signals", return_value=mock_coordination
            ):
                with patch.object(workflow, "run_stage", return_value=({"result": "test"}, 10, 5)):
                    result = await workflow.execute()

        # Workflow should succeed
        assert result.success

        # Both features should remain enabled
        assert workflow._enable_heartbeat_tracking is True
        assert workflow._enable_coordination is True


@pytest.fixture
def simple_workflow():
    """Create a SimpleWorkflow instance for testing."""
    return SimpleWorkflow(
        enable_heartbeat_tracking=True,
        enable_coordination=True,
        enable_adaptive_routing=True,
        agent_id="test-agent",
    )


class TestGetHeartbeatCoordinator:
    """Tests for CoordinationMixin._get_heartbeat_coordinator()."""

    def test_disabled_returns_none(self, simple_workflow):
        """Test returns None when heartbeat tracking is disabled."""
        simple_workflow._enable_heartbeat_tracking = False
        assert simple_workflow._get_heartbeat_coordinator() is None

    def test_successful_init(self, simple_workflow):
        """Test successful heartbeat coordinator initialization."""
        from unittest.mock import MagicMock, patch

        simple_workflow._enable_heartbeat_tracking = True
        simple_workflow._heartbeat_coordinator = None
        mock_hb = MagicMock()
        with patch(
            "attune.workflows.coordination_mixin.HeartbeatCoordinator",
            create=True,
        ) as mock_cls:
            # Patch the import inside the method
            with patch.dict(
                "sys.modules",
                {"attune.telemetry": MagicMock(HeartbeatCoordinator=mock_cls)},
            ):
                mock_cls.return_value = mock_hb
                result = simple_workflow._get_heartbeat_coordinator()
                assert result is mock_hb

    def test_import_error_disables_feature(self, simple_workflow):
        """Test ImportError disables heartbeat tracking."""
        from unittest.mock import MagicMock, patch

        simple_workflow._enable_heartbeat_tracking = True
        simple_workflow._heartbeat_coordinator = None

        mock_module = MagicMock(spec=[])  # Empty spec = no attributes
        with (
            patch.dict("sys.modules", {"attune.telemetry": mock_module}),
            patch("attune.workflows.coordination_mixin.logger"),
        ):
            simple_workflow._get_heartbeat_coordinator()
        assert simple_workflow._enable_heartbeat_tracking is False

    def test_init_exception_disables_feature(self, simple_workflow):
        """Test generic Exception during init disables heartbeat tracking."""
        from unittest.mock import MagicMock, patch

        simple_workflow._enable_heartbeat_tracking = True
        simple_workflow._heartbeat_coordinator = None

        mock_module = MagicMock()
        mock_module.HeartbeatCoordinator.side_effect = RuntimeError("Redis unavailable")
        with (
            patch.dict("sys.modules", {"attune.telemetry": mock_module}),
            patch("attune.workflows.coordination_mixin.logger"),
        ):
            result = simple_workflow._get_heartbeat_coordinator()
        assert simple_workflow._enable_heartbeat_tracking is False
        assert result is None


class TestGetCoordinationSignals:
    """Tests for CoordinationMixin._get_coordination_signals()."""

    def test_disabled_returns_none(self, simple_workflow):
        """Test returns None when coordination is disabled."""
        simple_workflow._enable_coordination = False
        assert simple_workflow._get_coordination_signals() is None

    def test_successful_init(self, simple_workflow):
        """Test successful coordination signals initialization."""
        from unittest.mock import MagicMock, patch

        simple_workflow._enable_coordination = True
        simple_workflow._coordination_signals = None
        mock_cs = MagicMock()
        mock_module = MagicMock()
        mock_module.CoordinationSignals.return_value = mock_cs
        with patch.dict("sys.modules", {"attune.telemetry": mock_module}):
            result = simple_workflow._get_coordination_signals()
            assert result is mock_cs

    def test_import_error_disables_feature(self, simple_workflow):
        """Test ImportError disables coordination."""
        from unittest.mock import MagicMock, patch

        simple_workflow._enable_coordination = True
        simple_workflow._coordination_signals = None
        mock_module = MagicMock(spec=[])  # Empty spec = no attributes
        with (
            patch.dict("sys.modules", {"attune.telemetry": mock_module}),
            patch("attune.workflows.coordination_mixin.logger"),
        ):
            simple_workflow._get_coordination_signals()
        assert simple_workflow._enable_coordination is False

    def test_init_exception_disables_feature(self, simple_workflow):
        """Test generic Exception during init disables coordination."""
        from unittest.mock import MagicMock, patch

        simple_workflow._enable_coordination = True
        simple_workflow._coordination_signals = None
        mock_module = MagicMock()
        mock_module.CoordinationSignals.side_effect = RuntimeError("Redis down")
        with (
            patch.dict("sys.modules", {"attune.telemetry": mock_module}),
            patch("attune.workflows.coordination_mixin.logger"),
        ):
            result = simple_workflow._get_coordination_signals()
        assert simple_workflow._enable_coordination is False
        assert result is None


class TestCheckAdaptiveTierUpgrade:
    """Tests for CoordinationMixin._check_adaptive_tier_upgrade()."""

    def test_no_router_returns_current_tier(self, simple_workflow):
        """Test returns current tier when no router is available."""
        from attune.workflows.compat import ModelTier

        simple_workflow._enable_adaptive_routing = False
        result = simple_workflow._check_adaptive_tier_upgrade("analyze", ModelTier.CHEAP)
        assert result == ModelTier.CHEAP

    def test_no_upgrade_returns_current_tier(self, simple_workflow):
        """Test returns current tier when router says no upgrade needed."""
        from unittest.mock import MagicMock

        from attune.workflows.compat import ModelTier

        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (False, "No upgrade needed")
        simple_workflow._enable_adaptive_routing = True
        simple_workflow._adaptive_router = mock_router
        result = simple_workflow._check_adaptive_tier_upgrade("analyze", ModelTier.CHEAP)
        assert result == ModelTier.CHEAP

    def test_upgrade_cheap_to_capable(self, simple_workflow):
        """Test upgrade from CHEAP to CAPABLE when recommended."""
        from unittest.mock import MagicMock, patch

        from attune.workflows.compat import ModelTier

        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (True, "High failure rate")
        simple_workflow._enable_adaptive_routing = True
        simple_workflow._adaptive_router = mock_router
        with patch("attune.workflows.coordination_mixin.logger"):
            result = simple_workflow._check_adaptive_tier_upgrade("analyze", ModelTier.CHEAP)
        assert result == ModelTier.CAPABLE

    def test_upgrade_capable_to_premium(self, simple_workflow):
        """Test upgrade from CAPABLE to PREMIUM when recommended."""
        from unittest.mock import MagicMock, patch

        from attune.workflows.compat import ModelTier

        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (True, "High failure rate")
        simple_workflow._enable_adaptive_routing = True
        simple_workflow._adaptive_router = mock_router
        with patch("attune.workflows.coordination_mixin.logger"):
            result = simple_workflow._check_adaptive_tier_upgrade("analyze", ModelTier.CAPABLE)
        assert result == ModelTier.PREMIUM

    def test_premium_stays_premium(self, simple_workflow):
        """Test PREMIUM tier stays at PREMIUM even with upgrade recommendation."""
        from unittest.mock import MagicMock, patch

        from attune.workflows.compat import ModelTier

        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (True, "High failure rate")
        simple_workflow._enable_adaptive_routing = True
        simple_workflow._adaptive_router = mock_router
        with patch("attune.workflows.coordination_mixin.logger"):
            result = simple_workflow._check_adaptive_tier_upgrade("analyze", ModelTier.PREMIUM)
        assert result == ModelTier.PREMIUM
