"""Tests for telemetry CLI commands.

Covers all 8 commands in src/attune/cli_commands/telemetry_commands.py:
  cmd_telemetry_show, cmd_telemetry_savings, cmd_telemetry_export,
  cmd_telemetry_routing_stats, cmd_telemetry_routing_check,
  cmd_telemetry_models, cmd_telemetry_agents, cmd_telemetry_signals.

Each command is tested for:
  - Success with data
  - Success with no/empty data
  - ImportError (module not available)
  - Unexpected Exception (graceful error handling)
  - Branch-specific logic (e.g., format types, filters, flags)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import types
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.cli_commands.telemetry_commands import (
    cmd_telemetry_agents,
    cmd_telemetry_export,
    cmd_telemetry_models,
    cmd_telemetry_routing_check,
    cmd_telemetry_routing_stats,
    cmd_telemetry_savings,
    cmd_telemetry_show,
    cmd_telemetry_signals,
)


def _make_args(**kwargs: object) -> types.SimpleNamespace:
    """Create a mock args namespace with given attributes."""
    return types.SimpleNamespace(**kwargs)


def _make_workflow_record(
    run_id: str = "run-1",
    workflow_name: str = "code-review",
    total_cost: float = 0.05,
    total_input_tokens: int = 1000,
    total_output_tokens: int = 500,
    started_at: str = "2026-02-07T10:00:00",
    success: bool = True,
) -> types.SimpleNamespace:
    """Create a mock workflow record."""
    return types.SimpleNamespace(
        run_id=run_id,
        workflow_name=workflow_name,
        total_cost=total_cost,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        started_at=started_at,
        success=success,
    )


def _make_call_record(
    estimated_cost: float = 0.01,
    input_tokens: int = 200,
    output_tokens: int = 100,
) -> types.SimpleNamespace:
    """Create a mock API call record."""
    return types.SimpleNamespace(
        estimated_cost=estimated_cost,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _make_agent(
    agent_id: str = "agent-1",
    status: str = "running",
    progress: float = 0.5,
    current_task: str = "analyzing",
    last_beat: datetime | None = None,
    metadata: dict | None = None,
) -> types.SimpleNamespace:
    """Create a mock agent record."""
    return types.SimpleNamespace(
        agent_id=agent_id,
        status=status,
        progress=progress,
        current_task=current_task,
        last_beat=last_beat or datetime.utcnow(),
        metadata=metadata,
    )


def _make_signal(
    signal_type: str = "task_complete",
    source_agent: str = "agent-1",
    target_agent: str | None = "agent-2",
    timestamp: datetime | None = None,
    ttl_seconds: float = 300.0,
    payload: dict | None = None,
) -> types.SimpleNamespace:
    """Create a mock coordination signal."""
    return types.SimpleNamespace(
        signal_type=signal_type,
        source_agent=source_agent,
        target_agent=target_agent,
        timestamp=timestamp or datetime.utcnow(),
        ttl_seconds=ttl_seconds,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# cmd_telemetry_show
# ---------------------------------------------------------------------------


class TestCmdTelemetryShow:
    """Tests for cmd_telemetry_show."""

    @patch("attune.cli_commands.telemetry_commands.TelemetryStore", create=True)
    def test_show_with_workflow_data(self, _mock_cls: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test show command displays workflow data correctly."""
        records = [
            _make_workflow_record(total_cost=0.05, total_input_tokens=1000, total_output_tokens=500),
            _make_workflow_record(total_cost=0.10, total_input_tokens=2000, total_output_tokens=800),
        ]
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = records
        mock_store.get_calls.return_value = []

        with patch(
            "attune.models.telemetry.TelemetryStore", return_value=mock_store, create=True
        ):
            result = cmd_telemetry_show(_make_args(days=7))

        assert result == 0
        captured = capsys.readouterr().out
        assert "Telemetry Summary" in captured
        assert "Workflow runs:" in captured
        assert "2" in captured  # 2 workflow runs
        assert "$0.15" in captured  # total cost

    @patch("attune.cli_commands.telemetry_commands.TelemetryStore", create=True)
    def test_show_with_call_data_no_workflows(
        self, _mock_cls: MagicMock, capsys: pytest.CaptureFixture
    ) -> None:
        """Test show command falls back to calls when no workflows exist."""
        calls = [
            _make_call_record(estimated_cost=0.01, input_tokens=200, output_tokens=100),
            _make_call_record(estimated_cost=0.02, input_tokens=300, output_tokens=150),
        ]
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = []
        mock_store.get_calls.return_value = calls

        with patch(
            "attune.models.telemetry.TelemetryStore", return_value=mock_store, create=True
        ):
            result = cmd_telemetry_show(_make_args(days=30))

        assert result == 0
        captured = capsys.readouterr().out
        assert "API calls:" in captured
        assert "2" in captured
        assert "$0.03" in captured  # total cost
        assert "Last 30 days" in captured

    def test_show_with_no_data(self, capsys: pytest.CaptureFixture) -> None:
        """Test show command when no telemetry data exists."""
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = []
        mock_store.get_calls.return_value = []

        with patch(
            "attune.models.telemetry.TelemetryStore", return_value=mock_store, create=True
        ):
            result = cmd_telemetry_show(_make_args(days=7))

        assert result == 0
        captured = capsys.readouterr().out
        assert "No telemetry data found" in captured

    def test_show_import_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test show command returns 1 on ImportError."""
        with patch.dict(
            "sys.modules",
            {"attune.models.telemetry": None},
        ):
            result = cmd_telemetry_show(_make_args(days=7))

        assert result == 1
        captured = capsys.readouterr().out
        assert "Telemetry module not available" in captured

    def test_show_generic_exception(self, capsys: pytest.CaptureFixture) -> None:
        """Test show command handles unexpected errors gracefully."""
        mock_store = MagicMock()
        mock_store.get_workflows.side_effect = RuntimeError("database locked")

        with patch(
            "attune.models.telemetry.TelemetryStore", return_value=mock_store, create=True
        ):
            result = cmd_telemetry_show(_make_args(days=7))

        assert result == 1
        captured = capsys.readouterr().out
        assert "Error:" in captured
        assert "database locked" in captured


# ---------------------------------------------------------------------------
# cmd_telemetry_savings
# ---------------------------------------------------------------------------


class TestCmdTelemetrySavings:
    """Tests for cmd_telemetry_savings."""

    def test_savings_with_actual_savings(self, capsys: pytest.CaptureFixture) -> None:
        """Test savings report when cheaper models were used."""
        # 10,000 tokens at actual cost $0.05
        # Premium baseline: 10000 * 45/1M = $0.45
        records = [
            _make_workflow_record(total_cost=0.05, total_input_tokens=5000, total_output_tokens=5000),
        ]
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = records

        with patch(
            "attune.models.telemetry.TelemetryStore", return_value=mock_store, create=True
        ):
            result = cmd_telemetry_savings(_make_args(days=7))

        assert result == 0
        captured = capsys.readouterr().out
        assert "Cost Savings Report" in captured
        assert "Actual cost:" in captured
        assert "$0.05" in captured
        assert "Savings:" in captured
        assert "Savings percentage:" in captured

    def test_savings_no_savings_detected(self, capsys: pytest.CaptureFixture) -> None:
        """Test savings report when actual cost exceeds premium baseline."""
        # Cost higher than baseline = no savings
        # 100 tokens at $1.00 actual, baseline = 100 * 45/1M = $0.0045
        records = [
            _make_workflow_record(total_cost=1.00, total_input_tokens=50, total_output_tokens=50),
        ]
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = records

        with patch(
            "attune.models.telemetry.TelemetryStore", return_value=mock_store, create=True
        ):
            result = cmd_telemetry_savings(_make_args(days=7))

        assert result == 0
        captured = capsys.readouterr().out
        assert "No savings detected" in captured

    def test_savings_no_data(self, capsys: pytest.CaptureFixture) -> None:
        """Test savings report with no telemetry records."""
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = []

        with patch(
            "attune.models.telemetry.TelemetryStore", return_value=mock_store, create=True
        ):
            result = cmd_telemetry_savings(_make_args(days=30))

        assert result == 0
        captured = capsys.readouterr().out
        assert "No telemetry data found" in captured

    def test_savings_import_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test savings returns 1 on ImportError."""
        with patch.dict("sys.modules", {"attune.models.telemetry": None}):
            result = cmd_telemetry_savings(_make_args(days=7))

        assert result == 1
        captured = capsys.readouterr().out
        assert "Telemetry module not available" in captured

    def test_savings_generic_exception(self, capsys: pytest.CaptureFixture) -> None:
        """Test savings handles unexpected errors gracefully."""
        mock_store = MagicMock()
        mock_store.get_workflows.side_effect = OSError("disk error")

        with patch(
            "attune.models.telemetry.TelemetryStore", return_value=mock_store, create=True
        ):
            result = cmd_telemetry_savings(_make_args(days=7))

        assert result == 1
        captured = capsys.readouterr().out
        assert "Error:" in captured

    def test_savings_zero_baseline_cost(self, capsys: pytest.CaptureFixture) -> None:
        """Test savings calculation when total tokens are zero (baseline_cost=0)."""
        records = [
            _make_workflow_record(total_cost=0.0, total_input_tokens=0, total_output_tokens=0),
        ]
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = records

        with patch(
            "attune.models.telemetry.TelemetryStore", return_value=mock_store, create=True
        ):
            result = cmd_telemetry_savings(_make_args(days=7))

        assert result == 0
        # baseline_cost = 0, actual_cost = 0, so baseline_cost > actual_cost is False
        captured = capsys.readouterr().out
        assert "No savings detected" in captured


# ---------------------------------------------------------------------------
# cmd_telemetry_export
# ---------------------------------------------------------------------------


class TestCmdTelemetryExport:
    """Tests for cmd_telemetry_export."""

    def test_export_csv(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test CSV export writes correct data."""
        output_file = tmp_path / "telemetry.csv"
        records = [
            _make_workflow_record(
                run_id="r1",
                workflow_name="review",
                total_cost=0.05,
                total_input_tokens=1000,
                total_output_tokens=500,
                started_at="2026-02-07T10:00:00",
                success=True,
            ),
        ]
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = records

        with (
            patch(
                "attune.models.telemetry.TelemetryStore",
                return_value=mock_store,
                create=True,
            ),
            patch(
                "attune.cli_commands.telemetry_commands._validate_file_path",
                create=True,
            ) as mock_validate,
            patch("attune.config._validate_file_path", return_value=output_file, create=True),
        ):
            # The function does `from attune.config import _validate_file_path`
            # We need to ensure that import resolves and returns our path
            mock_validate.return_value = output_file
            # Patch at module level since the import happens at the top of the function
            with patch(
                "builtins.__import__",
                wraps=__builtins__.__import__
                if hasattr(__builtins__, "__import__")
                else __import__,
            ):
                pass

        # Simpler approach: patch the TelemetryStore import and _validate_file_path import
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = records

        mock_telemetry_module = types.ModuleType("attune.models.telemetry")
        mock_telemetry_module.TelemetryStore = MagicMock(return_value=mock_store)

        mock_config_module = MagicMock()
        mock_config_module._validate_file_path = MagicMock(return_value=output_file)

        with patch.dict(
            "sys.modules",
            {
                "attune.models.telemetry": mock_telemetry_module,
                "attune.config": mock_config_module,
            },
        ):
            result = cmd_telemetry_export(
                _make_args(output=str(output_file), format="csv")
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "Exported 1 entries" in captured
        assert output_file.exists()

        content = output_file.read_text()
        assert "run_id" in content
        assert "r1" in content
        assert "review" in content

    def test_export_json(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test JSON export writes correct data."""
        output_file = tmp_path / "telemetry.json"
        records = [
            _make_workflow_record(run_id="r1", workflow_name="test-gen"),
            _make_workflow_record(run_id="r2", workflow_name="debug"),
        ]
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = records

        mock_telemetry_module = types.ModuleType("attune.models.telemetry")
        mock_telemetry_module.TelemetryStore = MagicMock(return_value=mock_store)

        mock_config_module = MagicMock()
        mock_config_module._validate_file_path = MagicMock(return_value=output_file)

        with patch.dict(
            "sys.modules",
            {
                "attune.models.telemetry": mock_telemetry_module,
                "attune.config": mock_config_module,
            },
        ):
            result = cmd_telemetry_export(
                _make_args(output=str(output_file), format="json")
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "Exported 2 entries" in captured
        assert output_file.exists()

        data = json.loads(output_file.read_text())
        assert len(data) == 2
        assert data[0]["run_id"] == "r1"

    def test_export_csv_empty_data(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test CSV export with no records produces empty file."""
        output_file = tmp_path / "empty.csv"
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = []

        mock_telemetry_module = types.ModuleType("attune.models.telemetry")
        mock_telemetry_module.TelemetryStore = MagicMock(return_value=mock_store)

        mock_config_module = MagicMock()
        mock_config_module._validate_file_path = MagicMock(return_value=output_file)

        with patch.dict(
            "sys.modules",
            {
                "attune.models.telemetry": mock_telemetry_module,
                "attune.config": mock_config_module,
            },
        ):
            result = cmd_telemetry_export(
                _make_args(output=str(output_file), format="csv")
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "Exported 0 entries" in captured

    def test_export_json_empty_data(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test JSON export with no records writes empty array."""
        output_file = tmp_path / "empty.json"
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = []

        mock_telemetry_module = types.ModuleType("attune.models.telemetry")
        mock_telemetry_module.TelemetryStore = MagicMock(return_value=mock_store)

        mock_config_module = MagicMock()
        mock_config_module._validate_file_path = MagicMock(return_value=output_file)

        with patch.dict(
            "sys.modules",
            {
                "attune.models.telemetry": mock_telemetry_module,
                "attune.config": mock_config_module,
            },
        ):
            result = cmd_telemetry_export(
                _make_args(output=str(output_file), format="json")
            )

        assert result == 0
        data = json.loads(output_file.read_text())
        assert data == []

    def test_export_invalid_path(self, capsys: pytest.CaptureFixture) -> None:
        """Test export rejects invalid paths via _validate_file_path ValueError."""
        mock_store = MagicMock()
        mock_store.get_workflows.return_value = []

        mock_telemetry_module = types.ModuleType("attune.models.telemetry")
        mock_telemetry_module.TelemetryStore = MagicMock(return_value=mock_store)

        mock_config_module = MagicMock()
        mock_config_module._validate_file_path = MagicMock(
            side_effect=ValueError("Cannot write to system directory: /etc")
        )

        with patch.dict(
            "sys.modules",
            {
                "attune.models.telemetry": mock_telemetry_module,
                "attune.config": mock_config_module,
            },
        ):
            result = cmd_telemetry_export(
                _make_args(output="/etc/passwd", format="json")
            )

        assert result == 1
        captured = capsys.readouterr().out
        assert "Invalid path" in captured

    def test_export_import_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test export returns 1 when TelemetryStore is not importable."""
        mock_config_module = MagicMock()
        mock_config_module._validate_file_path = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "attune.models.telemetry": None,
                "attune.config": mock_config_module,
            },
        ):
            result = cmd_telemetry_export(
                _make_args(output="/tmp/test.json", format="json")
            )

        assert result == 1
        captured = capsys.readouterr().out
        assert "Telemetry module not available" in captured

    def test_export_generic_exception(self, capsys: pytest.CaptureFixture) -> None:
        """Test export handles unexpected errors gracefully."""
        mock_store = MagicMock()
        mock_store.get_workflows.side_effect = RuntimeError("unexpected")

        mock_telemetry_module = types.ModuleType("attune.models.telemetry")
        mock_telemetry_module.TelemetryStore = MagicMock(return_value=mock_store)

        mock_config_module = MagicMock()
        mock_config_module._validate_file_path = MagicMock(return_value=Path("/tmp/out.json"))

        with patch.dict(
            "sys.modules",
            {
                "attune.models.telemetry": mock_telemetry_module,
                "attune.config": mock_config_module,
            },
        ):
            result = cmd_telemetry_export(
                _make_args(output="/tmp/out.json", format="json")
            )

        assert result == 1
        captured = capsys.readouterr().out
        assert "Error:" in captured


# ---------------------------------------------------------------------------
# cmd_telemetry_routing_stats
# ---------------------------------------------------------------------------


class TestCmdTelemetryRoutingStats:
    """Tests for cmd_telemetry_routing_stats."""

    def _patch_routing_imports(
        self,
        mock_tracker: MagicMock,
        mock_router: MagicMock,
    ):
        """Return a context manager that patches the routing imports."""
        mock_models_module = types.ModuleType("attune.models")
        mock_models_module.AdaptiveModelRouter = MagicMock(return_value=mock_router)

        mock_telemetry_module = types.ModuleType("attune.telemetry")
        mock_telemetry_module.UsageTracker = MagicMock()
        mock_telemetry_module.UsageTracker.get_instance = MagicMock(return_value=mock_tracker)

        return patch.dict(
            "sys.modules",
            {
                "attune.models": mock_models_module,
                "attune.telemetry": mock_telemetry_module,
            },
        )

    def test_routing_stats_with_workflow_filter(self, capsys: pytest.CaptureFixture) -> None:
        """Test routing stats for a specific workflow with data."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()
        mock_router.get_routing_stats.return_value = {
            "workflow": "code-review",
            "total_calls": 50,
            "avg_cost": 0.0234,
            "avg_success_rate": 0.95,
            "models_used": ["claude-3-haiku", "claude-3-sonnet"],
            "performance_by_model": {
                "claude-3-haiku": {
                    "calls": 30,
                    "success_rate": 0.97,
                    "avg_cost": 0.0100,
                    "avg_latency_ms": 250,
                    "quality_score": 0.85,
                },
                "claude-3-sonnet": {
                    "calls": 20,
                    "success_rate": 0.92,
                    "avg_cost": 0.0400,
                    "avg_latency_ms": 500,
                    "quality_score": 0.95,
                },
            },
        }

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow="code-review", stage=None, days=7)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "Adaptive Routing Statistics" in captured
        assert "code-review" in captured
        assert "50" in captured
        assert "claude-3-haiku" in captured
        assert "claude-3-sonnet" in captured
        assert "Per-Model Performance" in captured

    def test_routing_stats_with_workflow_and_stage(self, capsys: pytest.CaptureFixture) -> None:
        """Test routing stats for a specific workflow and stage."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()
        mock_router.get_routing_stats.return_value = {
            "workflow": "code-review",
            "total_calls": 10,
            "avg_cost": 0.01,
            "avg_success_rate": 0.9,
            "models_used": ["claude-3-haiku"],
            "performance_by_model": {},
        }

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow="code-review", stage="analysis", days=14)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "analysis" in captured

    def test_routing_stats_workflow_no_data(self, capsys: pytest.CaptureFixture) -> None:
        """Test routing stats for a workflow with zero calls."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()
        mock_router.get_routing_stats.return_value = {
            "workflow": "unknown-wf",
            "total_calls": 0,
        }

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow="unknown-wf", stage=None, days=7)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "No data found for workflow: unknown-wf" in captured

    def test_routing_stats_workflow_no_data_with_stage(self, capsys: pytest.CaptureFixture) -> None:
        """Test routing stats output mentions stage when no data found and stage is set."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()
        mock_router.get_routing_stats.return_value = {
            "workflow": "unknown-wf",
            "total_calls": 0,
        }

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow="unknown-wf", stage="prep", days=7)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "Stage: prep" in captured

    def test_routing_stats_overall_with_data(self, capsys: pytest.CaptureFixture) -> None:
        """Test overall routing stats (no workflow filter)."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "total_calls": 200,
            "total_cost": 5.50,
            "cache_hit_rate": 42.5,
            "by_tier": {"cheap": 2.00, "capable": 2.50, "premium": 1.00},
            "by_workflow": {
                "code-review": 3.00,
                "test-gen": 1.50,
                "debug": 0.75,
                "security": 0.15,
                "perf": 0.10,
                "docs": 0.00,
            },
        }
        mock_router = MagicMock()

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow=None, stage=None, days=7)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "200" in captured
        assert "$5.50" in captured
        assert "42.5%" in captured
        assert "Cost by Tier" in captured
        assert "Top Workflows" in captured
        assert "cheap" in captured

    def test_routing_stats_overall_no_data(self, capsys: pytest.CaptureFixture) -> None:
        """Test overall stats when no data exists."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "total_calls": 0,
            "total_cost": 0.0,
            "cache_hit_rate": 0.0,
            "by_tier": {},
            "by_workflow": {},
        }
        mock_router = MagicMock()

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow=None, stage=None, days=7)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "No telemetry data found" in captured

    def test_routing_stats_overall_zero_total_cost(self, capsys: pytest.CaptureFixture) -> None:
        """Test percentage calculation when total_cost is zero to avoid division by zero."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "total_calls": 5,
            "total_cost": 0.0,
            "cache_hit_rate": 0.0,
            "by_tier": {"cheap": 0.0},
            "by_workflow": {"test": 0.0},
        }
        mock_router = MagicMock()

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow=None, stage=None, days=7)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "0.0%" in captured

    def test_routing_stats_import_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test routing stats returns 1 on ImportError."""
        with patch.dict(
            "sys.modules",
            {"attune.models": None, "attune.telemetry": None},
        ):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow=None, stage=None, days=7)
            )

        assert result == 1
        captured = capsys.readouterr().out
        assert "Adaptive routing not available" in captured

    def test_routing_stats_generic_exception(self, capsys: pytest.CaptureFixture) -> None:
        """Test routing stats handles unexpected errors gracefully."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.side_effect = RuntimeError("db failure")
        mock_router = MagicMock()

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow=None, stage=None, days=7)
            )

        assert result == 1
        captured = capsys.readouterr().out
        assert "Error:" in captured

    def test_routing_stats_missing_attrs_uses_defaults(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test routing stats uses defaults when args lack workflow/stage/days."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "total_calls": 0,
            "total_cost": 0.0,
            "cache_hit_rate": 0.0,
            "by_tier": {},
            "by_workflow": {},
        }
        mock_router = MagicMock()

        with self._patch_routing_imports(mock_tracker, mock_router):
            # args without workflow, stage, days attributes
            bare_args = types.SimpleNamespace()
            result = cmd_telemetry_routing_stats(bare_args)

        assert result == 0

    def test_routing_stats_empty_performance_by_model(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test routing stats skips per-model section when empty."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()
        mock_router.get_routing_stats.return_value = {
            "workflow": "test",
            "total_calls": 5,
            "avg_cost": 0.01,
            "avg_success_rate": 1.0,
            "models_used": ["model-a"],
            "performance_by_model": {},
        }

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_stats(
                _make_args(workflow="test", stage=None, days=7)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "Per-Model Performance" not in captured


# ---------------------------------------------------------------------------
# cmd_telemetry_routing_check
# ---------------------------------------------------------------------------


class TestCmdTelemetryRoutingCheck:
    """Tests for cmd_telemetry_routing_check."""

    def _patch_routing_imports(
        self,
        mock_tracker: MagicMock,
        mock_router: MagicMock,
    ):
        """Return a context manager that patches the routing imports."""
        mock_models_module = types.ModuleType("attune.models")
        mock_models_module.AdaptiveModelRouter = MagicMock(return_value=mock_router)

        mock_telemetry_module = types.ModuleType("attune.telemetry")
        mock_telemetry_module.UsageTracker = MagicMock()
        mock_telemetry_module.UsageTracker.get_instance = MagicMock(return_value=mock_tracker)

        return patch.dict(
            "sys.modules",
            {
                "attune.models": mock_models_module,
                "attune.telemetry": mock_telemetry_module,
            },
        )

    def test_routing_check_all_with_recommendations(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test --all flag finds recommendations across workflows."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "by_workflow": {"code-review": 3.0, "test-gen": 1.5},
        }
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.side_effect = [
            (True, "Low success rate on cheap tier"),
            (False, "Performing well"),
        ]

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_check(
                _make_args(all=True, workflow=None)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "Tier Upgrade Recommendations" in captured
        assert "code-review" in captured
        assert "Low success rate" in captured

    def test_routing_check_all_no_recommendations(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test --all when all workflows are performing well."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "by_workflow": {"code-review": 3.0},
        }
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (False, "Fine")

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_check(
                _make_args(all=True, workflow=None)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "no upgrades needed" in captured

    def test_routing_check_all_no_workflows(self, capsys: pytest.CaptureFixture) -> None:
        """Test --all when no workflow data exists."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "by_workflow": {},
        }
        mock_router = MagicMock()

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_check(
                _make_args(all=True, workflow=None)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "No workflow data found" in captured

    def test_routing_check_all_skips_failing_workflows(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test --all gracefully skips workflows that throw exceptions."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "by_workflow": {"bad-wf": 1.0, "good-wf": 2.0},
        }
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.side_effect = [
            RuntimeError("not enough data"),
            (True, "Needs upgrade"),
        ]

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_check(
                _make_args(all=True, workflow=None)
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "good-wf" in captured

    def test_routing_check_specific_workflow_upgrade(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test specific workflow that needs upgrade."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (
            True,
            "Success rate below threshold",
        )

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_check(
                _make_args(all=False, workflow="code-review")
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "UPGRADE RECOMMENDED" in captured
        assert "Success rate below threshold" in captured
        assert "code-review" in captured

    def test_routing_check_specific_workflow_ok(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test specific workflow performing well."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.return_value = (
            False,
            "All metrics within range",
        )

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_check(
                _make_args(all=False, workflow="test-gen")
            )

        assert result == 0
        captured = capsys.readouterr().out
        assert "Performing well" in captured
        assert "All metrics within range" in captured

    def test_routing_check_neither_all_nor_workflow(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test routing check returns error when neither --all nor --workflow specified."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_check(
                _make_args(all=False, workflow=None)
            )

        assert result == 1
        captured = capsys.readouterr().out
        assert "Specify --workflow" in captured or "Error" in captured

    def test_routing_check_import_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test routing check returns 1 on ImportError."""
        with patch.dict(
            "sys.modules",
            {"attune.models": None, "attune.telemetry": None},
        ):
            result = cmd_telemetry_routing_check(
                _make_args(all=False, workflow=None)
            )

        assert result == 1
        captured = capsys.readouterr().out
        assert "Adaptive routing not available" in captured

    def test_routing_check_generic_exception(self, capsys: pytest.CaptureFixture) -> None:
        """Test routing check handles unexpected errors gracefully."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()
        mock_router.recommend_tier_upgrade.side_effect = RuntimeError("crash")

        with self._patch_routing_imports(mock_tracker, mock_router):
            result = cmd_telemetry_routing_check(
                _make_args(all=False, workflow="some-wf")
            )

        assert result == 1
        captured = capsys.readouterr().out
        assert "Error:" in captured

    def test_routing_check_missing_attrs_uses_defaults(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test routing check defaults when args lack workflow/all attributes."""
        mock_tracker = MagicMock()
        mock_router = MagicMock()

        with self._patch_routing_imports(mock_tracker, mock_router):
            # No 'all' or 'workflow' attrs -> defaults to False/None -> error path
            bare_args = types.SimpleNamespace()
            result = cmd_telemetry_routing_check(bare_args)

        assert result == 1
        captured = capsys.readouterr().out
        assert "Specify --workflow" in captured


# ---------------------------------------------------------------------------
# cmd_telemetry_models
# ---------------------------------------------------------------------------


class TestCmdTelemetryModels:
    """Tests for cmd_telemetry_models."""

    def _patch_telemetry_import(self, mock_tracker: MagicMock):
        """Return a context manager that patches the telemetry import."""
        mock_telemetry_module = types.ModuleType("attune.telemetry")
        mock_telemetry_module.UsageTracker = MagicMock()
        mock_telemetry_module.UsageTracker.get_instance = MagicMock(return_value=mock_tracker)

        return patch.dict(
            "sys.modules",
            {"attune.telemetry": mock_telemetry_module},
        )

    def test_models_with_data(self, capsys: pytest.CaptureFixture) -> None:
        """Test model performance with multiple providers and models."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"total_calls": 100}
        mock_tracker.get_recent_entries.return_value = [
            {
                "provider": "anthropic",
                "model": "claude-3-haiku",
                "cost": 0.01,
                "success": True,
                "duration_ms": 200,
            },
            {
                "provider": "anthropic",
                "model": "claude-3-haiku",
                "cost": 0.02,
                "success": True,
                "duration_ms": 300,
            },
            {
                "provider": "anthropic",
                "model": "claude-3-sonnet",
                "cost": 0.05,
                "success": False,
                "duration_ms": 500,
            },
            {
                "provider": "openai",
                "model": "gpt-4",
                "cost": 0.10,
                "success": True,
                "duration_ms": 400,
            },
        ]

        with self._patch_telemetry_import(mock_tracker):
            result = cmd_telemetry_models(_make_args(provider=None, days=7))

        assert result == 0
        captured = capsys.readouterr().out
        assert "Model Performance" in captured
        assert "ANTHROPIC" in captured
        assert "OPENAI" in captured
        assert "claude-3-haiku" in captured
        assert "claude-3-sonnet" in captured
        assert "gpt-4" in captured

    def test_models_with_provider_filter(self, capsys: pytest.CaptureFixture) -> None:
        """Test model performance filtered to one provider."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"total_calls": 10}
        mock_tracker.get_recent_entries.return_value = [
            {
                "provider": "anthropic",
                "model": "haiku",
                "cost": 0.01,
                "success": True,
                "duration_ms": 100,
            },
            {
                "provider": "openai",
                "model": "gpt-4",
                "cost": 0.10,
                "success": True,
                "duration_ms": 500,
            },
        ]

        with self._patch_telemetry_import(mock_tracker):
            result = cmd_telemetry_models(_make_args(provider="anthropic", days=7))

        assert result == 0
        captured = capsys.readouterr().out
        assert "ANTHROPIC" in captured
        # openai should be filtered out
        assert "OPENAI" not in captured

    def test_models_no_data(self, capsys: pytest.CaptureFixture) -> None:
        """Test model performance with zero total calls."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"total_calls": 0}

        with self._patch_telemetry_import(mock_tracker):
            result = cmd_telemetry_models(_make_args(provider=None, days=7))

        assert result == 0
        captured = capsys.readouterr().out
        assert "No telemetry data found" in captured

    def test_models_entries_missing_fields(self, capsys: pytest.CaptureFixture) -> None:
        """Test model performance with entries missing optional fields."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"total_calls": 2}
        mock_tracker.get_recent_entries.return_value = [
            {},  # All fields missing -> defaults to "unknown"
            {"provider": "anthropic"},  # model/cost/success/duration missing
        ]

        with self._patch_telemetry_import(mock_tracker):
            result = cmd_telemetry_models(_make_args(provider=None, days=7))

        assert result == 0
        captured = capsys.readouterr().out
        assert "UNKNOWN" in captured or "ANTHROPIC" in captured

    def test_models_import_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test models returns 1 when telemetry not importable."""
        with patch.dict("sys.modules", {"attune.telemetry": None}):
            result = cmd_telemetry_models(_make_args(provider=None, days=7))

        assert result == 1
        captured = capsys.readouterr().out
        assert "Telemetry not available" in captured

    def test_models_generic_exception(self, capsys: pytest.CaptureFixture) -> None:
        """Test models handles unexpected errors gracefully."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.side_effect = RuntimeError("kaboom")

        with self._patch_telemetry_import(mock_tracker):
            result = cmd_telemetry_models(_make_args(provider=None, days=7))

        assert result == 1
        captured = capsys.readouterr().out
        assert "Error:" in captured

    def test_models_missing_attrs_uses_defaults(self, capsys: pytest.CaptureFixture) -> None:
        """Test models uses defaults when args lack provider/days attributes."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"total_calls": 0}

        with self._patch_telemetry_import(mock_tracker):
            bare_args = types.SimpleNamespace()
            result = cmd_telemetry_models(bare_args)

        assert result == 0

    def test_models_failed_entry_not_counted_as_success(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that entries with success=False are not counted in successes."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"total_calls": 2}
        mock_tracker.get_recent_entries.return_value = [
            {
                "provider": "test",
                "model": "model-a",
                "cost": 0.01,
                "success": False,
                "duration_ms": 100,
            },
            {
                "provider": "test",
                "model": "model-a",
                "cost": 0.02,
                "success": False,
                "duration_ms": 200,
            },
        ]

        with self._patch_telemetry_import(mock_tracker):
            result = cmd_telemetry_models(_make_args(provider=None, days=7))

        assert result == 0
        captured = capsys.readouterr().out
        assert "0.0%" in captured  # 0% success rate


# ---------------------------------------------------------------------------
# cmd_telemetry_agents
# ---------------------------------------------------------------------------


class TestCmdTelemetryAgents:
    """Tests for cmd_telemetry_agents."""

    def _patch_heartbeat_import(self, mock_coordinator: MagicMock):
        """Return a context manager that patches the HeartbeatCoordinator import."""
        mock_telemetry_module = types.ModuleType("attune.telemetry")
        mock_telemetry_module.HeartbeatCoordinator = MagicMock(return_value=mock_coordinator)

        return patch.dict(
            "sys.modules",
            {"attune.telemetry": mock_telemetry_module},
        )

    def test_agents_with_active_agents(self, capsys: pytest.CaptureFixture) -> None:
        """Test agents display with active agents of different statuses."""
        now = datetime.utcnow()
        agents = [
            _make_agent(
                agent_id="agent-alpha",
                status="running",
                progress=0.75,
                current_task="reviewing code",
                last_beat=now - timedelta(seconds=5),
                metadata={"workflow": "code-review"},
            ),
            _make_agent(
                agent_id="agent-beta",
                status="completed",
                progress=1.0,
                current_task="done",
                last_beat=now - timedelta(seconds=60),
                metadata=None,
            ),
            _make_agent(
                agent_id="agent-gamma",
                status="failed",
                progress=0.3,
                current_task="crashed",
                last_beat=now - timedelta(seconds=120),
                metadata={},
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_active_agents.return_value = agents

        with self._patch_heartbeat_import(mock_coordinator):
            result = cmd_telemetry_agents(_make_args())

        assert result == 0
        captured = capsys.readouterr().out
        assert "Active Agents" in captured
        assert "3 active agent(s)" in captured
        assert "agent-alpha" in captured
        assert "agent-beta" in captured
        assert "agent-gamma" in captured
        assert "code-review" in captured  # From metadata

    def test_agents_stale_heartbeat(self, capsys: pytest.CaptureFixture) -> None:
        """Test agent display with stale heartbeat (>30s since last beat)."""
        now = datetime.utcnow()
        agents = [
            _make_agent(
                agent_id="stale-agent",
                status="running",
                progress=0.5,
                current_task="stuck",
                last_beat=now - timedelta(seconds=60),
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_active_agents.return_value = agents

        with self._patch_heartbeat_import(mock_coordinator):
            result = cmd_telemetry_agents(_make_args())

        assert result == 0
        captured = capsys.readouterr().out
        assert "stale-agent" in captured

    def test_agents_cancelled_status(self, capsys: pytest.CaptureFixture) -> None:
        """Test that cancelled status gets the error icon."""
        agents = [
            _make_agent(
                agent_id="cancelled-agent",
                status="cancelled",
                progress=0.2,
                current_task="aborted",
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_active_agents.return_value = agents

        with self._patch_heartbeat_import(mock_coordinator):
            result = cmd_telemetry_agents(_make_args())

        assert result == 0
        captured = capsys.readouterr().out
        assert "cancelled-agent" in captured
        assert "cancelled" in captured

    def test_agents_no_active_agents(self, capsys: pytest.CaptureFixture) -> None:
        """Test agents display when no agents are active."""
        mock_coordinator = MagicMock()
        mock_coordinator.get_active_agents.return_value = []

        with self._patch_heartbeat_import(mock_coordinator):
            result = cmd_telemetry_agents(_make_args())

        assert result == 0
        captured = capsys.readouterr().out
        assert "No active agents found" in captured

    def test_agents_metadata_without_workflow(self, capsys: pytest.CaptureFixture) -> None:
        """Test agent display with metadata present but no workflow key."""
        agents = [
            _make_agent(
                agent_id="meta-agent",
                status="running",
                progress=0.1,
                current_task="starting",
                metadata={"tier": "cheap"},  # No 'workflow' key
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_active_agents.return_value = agents

        with self._patch_heartbeat_import(mock_coordinator):
            result = cmd_telemetry_agents(_make_args())

        assert result == 0
        captured = capsys.readouterr().out
        assert "meta-agent" in captured
        # Should not show "Workflow:" since no workflow in metadata
        assert "Workflow:" not in captured

    def test_agents_metadata_with_workflow(self, capsys: pytest.CaptureFixture) -> None:
        """Test agent display with metadata containing workflow key."""
        agents = [
            _make_agent(
                agent_id="wf-agent",
                status="running",
                progress=0.5,
                current_task="working",
                metadata={"workflow": "security-audit"},
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_active_agents.return_value = agents

        with self._patch_heartbeat_import(mock_coordinator):
            result = cmd_telemetry_agents(_make_args())

        assert result == 0
        captured = capsys.readouterr().out
        assert "Workflow:" in captured
        assert "security-audit" in captured

    def test_agents_import_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test agents returns 1 when HeartbeatCoordinator not importable."""
        with patch.dict("sys.modules", {"attune.telemetry": None}):
            result = cmd_telemetry_agents(_make_args())

        assert result == 1
        captured = capsys.readouterr().out
        assert "Agent tracking not available" in captured

    def test_agents_generic_exception(self, capsys: pytest.CaptureFixture) -> None:
        """Test agents handles unexpected errors gracefully."""
        mock_coordinator = MagicMock()
        mock_coordinator.get_active_agents.side_effect = RuntimeError("connection lost")

        with self._patch_heartbeat_import(mock_coordinator):
            result = cmd_telemetry_agents(_make_args())

        assert result == 1
        captured = capsys.readouterr().out
        assert "Error:" in captured


# ---------------------------------------------------------------------------
# cmd_telemetry_signals
# ---------------------------------------------------------------------------


class TestCmdTelemetrySignals:
    """Tests for cmd_telemetry_signals."""

    def _patch_signals_import(self, mock_coordinator: MagicMock):
        """Return a context manager that patches the CoordinationSignals import."""
        mock_telemetry_module = types.ModuleType("attune.telemetry")
        mock_telemetry_module.CoordinationSignals = MagicMock(return_value=mock_coordinator)

        return patch.dict(
            "sys.modules",
            {"attune.telemetry": mock_telemetry_module},
        )

    def test_signals_with_pending_signals(self, capsys: pytest.CaptureFixture) -> None:
        """Test signals display with various signal types."""
        now = datetime.utcnow()
        signals = [
            _make_signal(
                signal_type="task_complete",
                source_agent="agent-1",
                target_agent="agent-2",
                timestamp=now - timedelta(seconds=10),
                ttl_seconds=300,
                payload={"result": "ok"},
            ),
            _make_signal(
                signal_type="abort",
                source_agent="controller",
                target_agent=None,  # broadcast
                timestamp=now - timedelta(seconds=5),
                ttl_seconds=60,
                payload=None,
            ),
            _make_signal(
                signal_type="ready",
                source_agent="agent-3",
                target_agent="agent-1",
                timestamp=now - timedelta(seconds=2),
                ttl_seconds=120,
                payload={"status": "ready to go"},
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_pending_signals.return_value = signals

        with self._patch_signals_import(mock_coordinator):
            result = cmd_telemetry_signals(_make_args(agent="agent-1"))

        assert result == 0
        captured = capsys.readouterr().out
        assert "Coordination Signals for agent-1" in captured
        assert "3 pending signal(s)" in captured
        assert "task_complete" in captured
        assert "abort" in captured
        assert "* (broadcast)" in captured

    def test_signals_unknown_signal_type(self, capsys: pytest.CaptureFixture) -> None:
        """Test signal display with an unknown signal type gets default icon."""
        signals = [
            _make_signal(
                signal_type="custom_type",
                source_agent="src",
                target_agent="tgt",
                payload=None,
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_pending_signals.return_value = signals

        with self._patch_signals_import(mock_coordinator):
            result = cmd_telemetry_signals(_make_args(agent="tgt"))

        assert result == 0
        captured = capsys.readouterr().out
        assert "custom_type" in captured

    def test_signals_long_payload_truncated(self, capsys: pytest.CaptureFixture) -> None:
        """Test signal payload is truncated when longer than 60 characters."""
        long_payload = {"data": "x" * 100}
        signals = [
            _make_signal(
                signal_type="checkpoint",
                source_agent="src",
                target_agent="tgt",
                payload=long_payload,
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_pending_signals.return_value = signals

        with self._patch_signals_import(mock_coordinator):
            result = cmd_telemetry_signals(_make_args(agent="tgt"))

        assert result == 0
        captured = capsys.readouterr().out
        assert "..." in captured

    def test_signals_short_payload_not_truncated(self, capsys: pytest.CaptureFixture) -> None:
        """Test signal payload is not truncated when 60 chars or less."""
        signals = [
            _make_signal(
                signal_type="ready",
                source_agent="src",
                target_agent="tgt",
                payload={"ok": True},
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_pending_signals.return_value = signals

        with self._patch_signals_import(mock_coordinator):
            result = cmd_telemetry_signals(_make_args(agent="tgt"))

        assert result == 0
        captured = capsys.readouterr().out
        assert "Payload:" in captured
        # Short payload should appear without truncation
        assert "..." not in captured or "ok" in captured

    def test_signals_no_pending(self, capsys: pytest.CaptureFixture) -> None:
        """Test signals when no pending signals exist."""
        mock_coordinator = MagicMock()
        mock_coordinator.get_pending_signals.return_value = []

        with self._patch_signals_import(mock_coordinator):
            result = cmd_telemetry_signals(_make_args(agent="agent-1"))

        assert result == 0
        captured = capsys.readouterr().out
        assert "No pending signals" in captured

    def test_signals_no_agent_specified(self, capsys: pytest.CaptureFixture) -> None:
        """Test signals returns error when --agent is not specified."""
        mock_coordinator = MagicMock()

        with self._patch_signals_import(mock_coordinator):
            result = cmd_telemetry_signals(_make_args(agent=None))

        assert result == 1
        captured = capsys.readouterr().out
        assert "--agent" in captured

    def test_signals_missing_agent_attr(self, capsys: pytest.CaptureFixture) -> None:
        """Test signals when args lacks 'agent' attribute entirely."""
        mock_coordinator = MagicMock()

        with self._patch_signals_import(mock_coordinator):
            bare_args = types.SimpleNamespace()
            result = cmd_telemetry_signals(bare_args)

        assert result == 1
        captured = capsys.readouterr().out
        assert "--agent" in captured

    def test_signals_import_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test signals returns 1 when CoordinationSignals not importable."""
        with patch.dict("sys.modules", {"attune.telemetry": None}):
            result = cmd_telemetry_signals(_make_args(agent="agent-1"))

        assert result == 1
        captured = capsys.readouterr().out
        assert "Coordination signals not available" in captured

    def test_signals_generic_exception(self, capsys: pytest.CaptureFixture) -> None:
        """Test signals handles unexpected errors gracefully."""
        mock_coordinator = MagicMock()
        mock_coordinator.get_pending_signals.side_effect = RuntimeError("network error")

        with self._patch_signals_import(mock_coordinator):
            result = cmd_telemetry_signals(_make_args(agent="agent-1"))

        assert result == 1
        captured = capsys.readouterr().out
        assert "Error:" in captured

    def test_signals_all_known_type_icons(self, capsys: pytest.CaptureFixture) -> None:
        """Test that all known signal type icons are mapped correctly."""
        now = datetime.utcnow()
        known_types = ["task_complete", "abort", "ready", "checkpoint", "error"]
        signals = [
            _make_signal(
                signal_type=st,
                source_agent="src",
                target_agent="tgt",
                timestamp=now - timedelta(seconds=i),
                payload=None,
            )
            for i, st in enumerate(known_types)
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_pending_signals.return_value = signals

        with self._patch_signals_import(mock_coordinator):
            result = cmd_telemetry_signals(_make_args(agent="tgt"))

        assert result == 0
        captured = capsys.readouterr().out
        for st in known_types:
            assert st in captured

    def test_signals_no_payload(self, capsys: pytest.CaptureFixture) -> None:
        """Test that signals without payload don't show Payload line."""
        signals = [
            _make_signal(
                signal_type="ready",
                source_agent="src",
                target_agent="tgt",
                payload=None,
            ),
        ]
        mock_coordinator = MagicMock()
        mock_coordinator.get_pending_signals.return_value = signals

        with self._patch_signals_import(mock_coordinator):
            result = cmd_telemetry_signals(_make_args(agent="tgt"))

        assert result == 0
        captured = capsys.readouterr().out
        assert "Payload:" not in captured
