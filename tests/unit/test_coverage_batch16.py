# Licensed under the Apache License, Version 2.0
# Copyright 2025 Smart AI Memory, LLC
"""Tests for deprecation utils and data model classes -- Batch 16.

Covers: _deprecation, workflows/data_classes, workflows/step_config,
workflows/progress_models.

(Formerly also covered _workflow_helpers -- removed with the
legacy one-command family; see
docs/reports/d-block-triage-2026-07-14.md.)
"""

from __future__ import annotations

import json
import warnings
from datetime import datetime

# === Module: _deprecation.py ===


class TestDeprecation:
    def test_emits_deprecation_warning(self):
        from attune._deprecation import _emit_cli_deprecation

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _emit_cli_deprecation("attune.telemetry", "attune telemetry show")
        assert len(caught) == 1
        assert issubclass(caught[0].category, DeprecationWarning)

    def test_warning_message_contains_module(self):
        from attune._deprecation import _emit_cli_deprecation

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _emit_cli_deprecation("attune.telemetry", "attune telemetry show")
        assert "attune.telemetry" in str(caught[0].message)

    def test_warning_message_contains_canonical(self):
        from attune._deprecation import _emit_cli_deprecation

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _emit_cli_deprecation("attune.telemetry", "attune telemetry show")
        assert "attune telemetry show" in str(caught[0].message)

    def test_prints_to_stderr(self, capsys):
        from attune._deprecation import _emit_cli_deprecation

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            _emit_cli_deprecation("attune.mymod", "attune mymod")
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "attune.mymod" in err

    def test_different_modules_emit_separately(self):
        from attune._deprecation import _emit_cli_deprecation

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _emit_cli_deprecation("mod.a", "cmd a")
            _emit_cli_deprecation("mod.b", "cmd b")
        assert len(caught) == 2


# === Module: workflows/data_classes.py ===


class TestWorkflowDataClasses:
    def test_workflow_stage_creation(self):
        from attune.models import ModelTier
        from attune.workflows.data_classes import WorkflowStage

        stage = WorkflowStage(name="triage", tier=ModelTier.CHEAP, description="First pass")
        assert stage.name == "triage"
        assert stage.skipped is False
        assert stage.cost == 0.0

    def test_cost_report_creation(self):
        from attune.workflows.data_classes import CostReport

        report = CostReport(
            total_cost=0.50,
            baseline_cost=1.00,
            savings=0.50,
            savings_percent=50.0,
        )
        assert report.total_cost == 0.50
        assert report.cache_hits == 0

    def test_stage_quality_metrics_creation(self):
        from attune.workflows.data_classes import StageQualityMetrics

        metrics = StageQualityMetrics(
            execution_succeeded=True,
            output_valid=True,
            quality_improved=False,
            error_type=None,
            validation_error=None,
        )
        assert metrics.execution_succeeded is True

    def test_next_action_creation(self):
        from attune.workflows.data_classes import NextAction

        action = NextAction(
            workflow_name="security-audit",
            description="3 modules have unvalidated paths",
            reasoning="Path validation missing",
        )
        assert action.workflow_name == "security-audit"
        assert action.priority == "medium"
        assert action.confidence == 0.8

    def test_workflow_result_duration_seconds(self):
        from attune.workflows.data_classes import CostReport, WorkflowResult

        now = datetime.now()
        report = CostReport(total_cost=0.1, baseline_cost=0.2, savings=0.1, savings_percent=50.0)
        result = WorkflowResult(
            success=True,
            stages=[],
            final_output="done",
            cost_report=report,
            started_at=now,
            completed_at=now,
            total_duration_ms=2500,
        )
        assert result.duration_seconds == 2.5

    def test_workflow_result_with_error(self):
        from attune.workflows.data_classes import CostReport, WorkflowResult

        now = datetime.now()
        report = CostReport(total_cost=0.0, baseline_cost=0.0, savings=0.0, savings_percent=0.0)
        result = WorkflowResult(
            success=False,
            stages=[],
            final_output=None,
            cost_report=report,
            started_at=now,
            completed_at=now,
            total_duration_ms=100,
            error="Connection refused",
            error_type="runtime",
            transient=True,
        )
        assert result.error == "Connection refused"
        assert result.transient is True


# === Module: workflows/step_config.py ===


class TestWorkflowStepConfig:
    def test_basic_creation(self):
        from attune.workflows.step_config import WorkflowStepConfig

        step = WorkflowStepConfig(name="triage", task_type="classify")
        assert step.name == "triage"
        assert step.tier_hint is None

    def test_effective_tier_uses_hint(self):
        from attune.workflows.step_config import WorkflowStepConfig

        step = WorkflowStepConfig(name="triage", task_type="classify", tier_hint="cheap")
        assert step.effective_tier == "cheap"

    def test_effective_tier_from_task_type(self):
        from attune.workflows.step_config import WorkflowStepConfig

        step = WorkflowStepConfig(name="analysis", task_type="summarize")
        tier = step.effective_tier
        assert tier in ("cheap", "capable", "premium")

    def test_effective_tier_enum(self):
        from attune.models import ModelTier
        from attune.workflows.step_config import WorkflowStepConfig

        step = WorkflowStepConfig(name="s", task_type="classify", tier_hint="cheap")
        assert isinstance(step.effective_tier_enum, ModelTier)

    def test_with_overrides_creates_new_instance(self):
        from attune.workflows.step_config import WorkflowStepConfig

        step = WorkflowStepConfig(name="s", task_type="classify", tier_hint="capable")
        new_step = step.with_overrides(tier_hint="premium")
        assert new_step.tier_hint == "premium"
        assert step.tier_hint == "capable"  # Original unchanged

    def test_to_dict(self):
        from attune.workflows.step_config import WorkflowStepConfig

        step = WorkflowStepConfig(name="s", task_type="classify", timeout_seconds=30)
        d = step.to_dict()
        assert d["name"] == "s"
        assert d["timeout_seconds"] == 30
        assert "effective_tier" in d

    def test_from_dict(self):
        from attune.workflows.step_config import WorkflowStepConfig

        d = {"name": "s", "task_type": "classify", "tier_hint": "cheap"}
        step = WorkflowStepConfig.from_dict(d)
        assert step.name == "s"
        assert step.tier_hint == "cheap"

    def test_validate_step_config_valid(self):
        from attune.workflows.step_config import WorkflowStepConfig, validate_step_config

        step = WorkflowStepConfig(name="s", task_type="classify")
        errors = validate_step_config(step)
        assert errors == []

    def test_validate_step_config_invalid_tier(self):
        from attune.workflows.step_config import WorkflowStepConfig, validate_step_config

        step = WorkflowStepConfig(name="s", task_type="classify", tier_hint="ultra")
        errors = validate_step_config(step)
        assert any("tier_hint" in e for e in errors)

    def test_validate_step_config_negative_timeout(self):
        from attune.workflows.step_config import WorkflowStepConfig, validate_step_config

        step = WorkflowStepConfig(name="s", task_type="classify", timeout_seconds=-1)
        errors = validate_step_config(step)
        assert any("timeout" in e for e in errors)

    def test_steps_from_tier_map(self):
        from attune.workflows.step_config import steps_from_tier_map

        stages = ["triage", "fix", "review"]
        tier_map = {"triage": "cheap", "fix": "capable", "review": "premium"}
        steps = steps_from_tier_map(stages, tier_map)
        assert len(steps) == 3
        assert steps[0].name == "triage"
        assert steps[0].tier_hint == "cheap"

    def test_steps_from_tier_map_default_tier(self):
        from attune.workflows.step_config import steps_from_tier_map

        stages = ["unknown_stage"]
        steps = steps_from_tier_map(stages, {})
        assert steps[0].tier_hint == "capable"


# === Module: workflows/progress_models.py ===


class TestProgressModels:
    def test_progress_status_values(self):
        from attune.workflows.progress_models import ProgressStatus

        assert ProgressStatus.PENDING.value == "pending"
        assert ProgressStatus.RUNNING.value == "running"
        assert ProgressStatus.COMPLETED.value == "completed"
        assert ProgressStatus.FAILED.value == "failed"
        assert ProgressStatus.SKIPPED.value == "skipped"
        assert ProgressStatus.FALLBACK.value == "fallback"
        assert ProgressStatus.RETRYING.value == "retrying"

    def test_stage_progress_to_dict(self):
        from attune.workflows.progress_models import ProgressStatus, StageProgress

        sp = StageProgress(name="triage", status=ProgressStatus.COMPLETED)
        d = sp.to_dict()
        assert d["name"] == "triage"
        assert d["status"] == "completed"
        assert d["started_at"] is None

    def test_stage_progress_with_timestamps(self):
        from attune.workflows.progress_models import ProgressStatus, StageProgress

        now = datetime.now()
        sp = StageProgress(
            name="fix",
            status=ProgressStatus.RUNNING,
            started_at=now,
            cost=0.05,
        )
        d = sp.to_dict()
        assert d["started_at"] is not None
        assert d["cost"] == 0.05

    def test_progress_update_creation(self):
        from attune.workflows.progress_models import ProgressStatus, ProgressUpdate

        update = ProgressUpdate(
            workflow="health-check",
            workflow_id="wf-001",
            current_stage="security",
            stage_index=1,
            total_stages=3,
            status=ProgressStatus.RUNNING,
            message="Running security audit",
        )
        assert update.workflow == "health-check"
        assert update.percent_complete == 0.0

    def test_progress_update_to_dict(self):
        from attune.workflows.progress_models import ProgressStatus, ProgressUpdate

        update = ProgressUpdate(
            workflow="health-check",
            workflow_id="wf-001",
            current_stage="security",
            stage_index=0,
            total_stages=2,
            status=ProgressStatus.COMPLETED,
            message="Done",
            percent_complete=100.0,
        )
        d = update.to_dict()
        assert d["status"] == "completed"
        assert d["percent_complete"] == 100.0
        assert "timestamp" in d

    def test_progress_update_to_json(self):
        from attune.workflows.progress_models import ProgressStatus, ProgressUpdate

        update = ProgressUpdate(
            workflow="test",
            workflow_id="w1",
            current_stage="s1",
            stage_index=0,
            total_stages=1,
            status=ProgressStatus.PENDING,
            message="waiting",
        )
        s = update.to_json()
        parsed = json.loads(s)
        assert parsed["workflow"] == "test"

    def test_progress_update_with_stages(self):
        from attune.workflows.progress_models import ProgressStatus, ProgressUpdate, StageProgress

        sp = StageProgress(name="triage", status=ProgressStatus.COMPLETED)
        update = ProgressUpdate(
            workflow="health-check",
            workflow_id="wf-002",
            current_stage="fix",
            stage_index=1,
            total_stages=2,
            status=ProgressStatus.RUNNING,
            message="Fixing issues",
            stages=[sp],
        )
        d = update.to_dict()
        assert len(d["stages"]) == 1
        assert d["stages"][0]["name"] == "triage"
