"""Tests for WorkflowBatchRunner.

Covers WorkflowSpec, WorkflowBatchResult, BatchRunReport, BATCH_PRESETS,
and all WorkflowBatchRunner methods.  All workflow executions are mocked
so no real API calls are made.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.workflow_batch_runner import (
    BATCH_PRESETS,
    BatchRunReport,
    WorkflowBatchResult,
    WorkflowBatchRunner,
    WorkflowSpec,
)

# =============================================================================
# WorkflowSpec
# =============================================================================


class TestWorkflowSpec:
    """Tests for the WorkflowSpec dataclass."""

    def test_create_with_required_fields_only(self) -> None:
        """WorkflowSpec can be created with only workflow_id."""
        spec = WorkflowSpec(workflow_id="security-audit")

        assert spec.workflow_id == "security-audit"
        assert spec.config == {}
        assert spec.input_data == {}

    def test_create_with_all_fields(self) -> None:
        """WorkflowSpec stores config and input_data correctly."""
        spec = WorkflowSpec(
            workflow_id="bug-predict",
            config={"risk_threshold": 0.8},
            input_data={"path": "src/"},
        )

        assert spec.workflow_id == "bug-predict"
        assert spec.config == {"risk_threshold": 0.8}
        assert spec.input_data == {"path": "src/"}

    def test_default_dicts_are_independent(self) -> None:
        """Each WorkflowSpec instance gets its own default dicts."""
        spec_a = WorkflowSpec(workflow_id="foo")
        spec_b = WorkflowSpec(workflow_id="bar")

        spec_a.config["key"] = "value"

        assert spec_b.config == {}


# =============================================================================
# WorkflowBatchResult
# =============================================================================


class TestWorkflowBatchResult:
    """Tests for the WorkflowBatchResult dataclass."""

    def test_successful_result_defaults(self) -> None:
        """WorkflowBatchResult success=True has sensible defaults."""
        result = WorkflowBatchResult(workflow_id="security-audit", success=True)

        assert result.workflow_id == "security-audit"
        assert result.success is True
        assert result.result is None
        assert result.error is None
        assert result.duration_seconds == 0.0
        assert result.cost == 0.0

    def test_failed_result_with_error(self) -> None:
        """WorkflowBatchResult captures error message on failure."""
        result = WorkflowBatchResult(
            workflow_id="bug-predict",
            success=False,
            error="Connection refused",
            duration_seconds=1.5,
        )

        assert result.success is False
        assert result.error == "Connection refused"
        assert result.duration_seconds == 1.5

    def test_result_with_cost(self) -> None:
        """WorkflowBatchResult stores cost correctly."""
        mock_result = MagicMock()
        result = WorkflowBatchResult(
            workflow_id="perf-audit",
            success=True,
            result=mock_result,
            duration_seconds=3.2,
            cost=0.0042,
        )

        assert result.cost == pytest.approx(0.0042)
        assert result.result is mock_result


# =============================================================================
# BatchRunReport.format_summary
# =============================================================================


class TestBatchRunReportFormatSummary:
    """Tests for BatchRunReport.format_summary()."""

    def _make_report(self) -> BatchRunReport:
        """Build a representative BatchRunReport for assertion tests."""
        results = [
            WorkflowBatchResult(
                workflow_id="security-audit",
                success=True,
                duration_seconds=2.0,
                cost=0.0010,
            ),
            WorkflowBatchResult(
                workflow_id="bug-predict",
                success=False,
                error="timeout",
                duration_seconds=5.0,
                cost=0.0,
            ),
        ]
        return BatchRunReport(
            preset="daily-quality",
            results=results,
            total_duration=7.0,
            total_cost=0.0010,
            success_count=1,
            failure_count=1,
        )

    def test_summary_contains_preset_name(self) -> None:
        """format_summary includes the preset name."""
        report = self._make_report()
        summary = report.format_summary()

        assert "daily-quality" in summary

    def test_summary_contains_workflow_counts(self) -> None:
        """format_summary reports pass/fail/total counts."""
        report = self._make_report()
        summary = report.format_summary()

        assert "1 passed" in summary
        assert "1 failed" in summary
        assert "2 total" in summary

    def test_summary_contains_duration(self) -> None:
        """format_summary includes formatted duration."""
        report = self._make_report()
        summary = report.format_summary()

        assert "7.0s" in summary

    def test_summary_contains_cost(self) -> None:
        """format_summary includes estimated cost."""
        report = self._make_report()
        summary = report.format_summary()

        assert "$" in summary
        assert "0.0010" in summary

    def test_summary_contains_ok_status(self) -> None:
        """format_summary marks successful workflows with [OK]."""
        report = self._make_report()
        summary = report.format_summary()

        assert "[OK]" in summary
        assert "security-audit" in summary

    def test_summary_contains_fail_status(self) -> None:
        """format_summary marks failed workflows with [FAIL]."""
        report = self._make_report()
        summary = report.format_summary()

        assert "[FAIL]" in summary

    def test_summary_contains_error_message(self) -> None:
        """format_summary includes error message for failed workflows."""
        report = self._make_report()
        summary = report.format_summary()

        assert "timeout" in summary

    def test_summary_has_separator_lines(self) -> None:
        """format_summary wraps content with separator lines."""
        report = self._make_report()
        summary = report.format_summary()

        assert "=" * 60 in summary

    def test_summary_empty_results(self) -> None:
        """format_summary works when there are no results."""
        report = BatchRunReport(
            preset="custom",
            results=[],
            total_duration=0.0,
            total_cost=0.0,
            success_count=0,
            failure_count=0,
        )
        summary = report.format_summary()

        assert "custom" in summary
        assert "0 passed" in summary
        assert "0 failed" in summary
        assert "0 total" in summary


# =============================================================================
# BATCH_PRESETS
# =============================================================================


class TestBatchPresets:
    """Tests for the BATCH_PRESETS module-level constant."""

    def test_all_four_presets_exist(self) -> None:
        """BATCH_PRESETS contains exactly the four documented presets."""
        expected = {"daily-quality", "pre-release", "coverage-boost", "full-audit"}
        assert set(BATCH_PRESETS.keys()) == expected

    def test_daily_quality_workflow_ids(self) -> None:
        """daily-quality preset has correct workflow IDs."""
        ids = [s.workflow_id for s in BATCH_PRESETS["daily-quality"]]
        assert "security-audit" in ids
        assert "bug-predict" in ids
        assert "dependency-check" in ids

    def test_pre_release_workflow_ids(self) -> None:
        """pre-release preset has correct workflow IDs."""
        ids = [s.workflow_id for s in BATCH_PRESETS["pre-release"]]
        assert "security-audit" in ids
        assert "dependency-check" in ids
        assert "perf-audit" in ids

    def test_coverage_boost_workflow_ids(self) -> None:
        """coverage-boost preset has correct workflow IDs."""
        ids = [s.workflow_id for s in BATCH_PRESETS["coverage-boost"]]
        assert "test-gen-parallel" in ids

    def test_full_audit_workflow_ids(self) -> None:
        """full-audit preset has all four analysis workflow IDs."""
        ids = [s.workflow_id for s in BATCH_PRESETS["full-audit"]]
        assert "security-audit" in ids
        assert "bug-predict" in ids
        assert "perf-audit" in ids
        assert "dependency-check" in ids

    def test_each_preset_has_at_least_one_spec(self) -> None:
        """Every preset contains at least one WorkflowSpec."""
        for name, specs in BATCH_PRESETS.items():
            assert len(specs) >= 1, f"Preset '{name}' has no specs"

    def test_all_specs_are_workflow_spec_instances(self) -> None:
        """Every entry in every preset is a WorkflowSpec instance."""
        for name, specs in BATCH_PRESETS.items():
            for spec in specs:
                assert isinstance(
                    spec,
                    WorkflowSpec,
                ), f"Preset '{name}' contains non-WorkflowSpec: {spec!r}"


# =============================================================================
# WorkflowBatchRunner.list_presets
# =============================================================================


class TestListPresets:
    """Tests for WorkflowBatchRunner.list_presets()."""

    def test_returns_all_four_presets(self) -> None:
        """list_presets() returns descriptions for all four presets."""
        presets = WorkflowBatchRunner.list_presets()

        assert set(presets.keys()) == {
            "daily-quality",
            "pre-release",
            "coverage-boost",
            "full-audit",
        }

    def test_all_descriptions_are_non_empty_strings(self) -> None:
        """list_presets() descriptions are all non-empty strings."""
        presets = WorkflowBatchRunner.list_presets()

        for name, description in presets.items():
            assert isinstance(description, str), f"Preset '{name}' description is not a string"
            assert description.strip(), f"Preset '{name}' has an empty description"


# =============================================================================
# WorkflowBatchRunner.list_batch_safe_workflows
# =============================================================================


class TestListBatchSafeWorkflows:
    """Tests for WorkflowBatchRunner.list_batch_safe_workflows()."""

    def test_returns_sorted_list(self) -> None:
        """list_batch_safe_workflows() returns a sorted list."""
        result = WorkflowBatchRunner.list_batch_safe_workflows()

        assert result == sorted(result)

    def test_returns_list_type(self) -> None:
        """list_batch_safe_workflows() returns a plain list."""
        result = WorkflowBatchRunner.list_batch_safe_workflows()

        assert isinstance(result, list)

    def test_contains_known_safe_workflows(self) -> None:
        """list_batch_safe_workflows() includes the expected workflow IDs."""
        result = WorkflowBatchRunner.list_batch_safe_workflows()

        for expected in (
            "bug-predict",
            "security-audit",
            "perf-audit",
            "dependency-check",
            "test-gen",
            "test-gen-parallel",
        ):
            assert expected in result, f"'{expected}' missing from batch-safe list"

    def test_all_preset_workflows_are_batch_safe(self) -> None:
        """Every workflow ID used in presets is in the batch-safe list."""
        safe = set(WorkflowBatchRunner.list_batch_safe_workflows())

        for preset_name, specs in BATCH_PRESETS.items():
            for spec in specs:
                assert (
                    spec.workflow_id in safe
                ), f"Preset '{preset_name}' uses non-batch-safe workflow '{spec.workflow_id}'"


# =============================================================================
# WorkflowBatchRunner._validate_specs
# =============================================================================


class TestValidateSpecs:
    """Tests for WorkflowBatchRunner._validate_specs()."""

    def setup_method(self) -> None:
        """Create a fresh runner before each test."""
        self.runner = WorkflowBatchRunner()

    def test_empty_list_raises_value_error(self) -> None:
        """_validate_specs raises ValueError when given an empty list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            self.runner._validate_specs([])

    def test_unknown_workflow_raises_value_error(self) -> None:
        """_validate_specs raises ValueError for non-batch-safe workflow IDs."""
        specs = [WorkflowSpec(workflow_id="interactive-wizard")]

        with pytest.raises(ValueError, match="not in the batch-safe allowlist"):
            self.runner._validate_specs(specs)

    def test_valid_specs_do_not_raise(self) -> None:
        """_validate_specs does not raise for all-batch-safe specs."""
        specs = [
            WorkflowSpec(workflow_id="security-audit"),
            WorkflowSpec(workflow_id="bug-predict"),
        ]

        # Should not raise
        self.runner._validate_specs(specs)

    def test_error_message_includes_workflow_id(self) -> None:
        """_validate_specs error mentions the offending workflow ID."""
        bad_id = "not-a-real-workflow"
        specs = [WorkflowSpec(workflow_id=bad_id)]

        with pytest.raises(ValueError, match=bad_id):
            self.runner._validate_specs(specs)

    def test_single_invalid_in_mixed_list_raises(self) -> None:
        """_validate_specs raises even if only one spec is invalid."""
        specs = [
            WorkflowSpec(workflow_id="security-audit"),
            WorkflowSpec(workflow_id="bad-workflow"),
        ]

        with pytest.raises(ValueError):
            self.runner._validate_specs(specs)


# =============================================================================
# WorkflowBatchRunner._create_workflow
# =============================================================================


class TestCreateWorkflow:
    """Tests for WorkflowBatchRunner._create_workflow()."""

    def setup_method(self) -> None:
        """Create a fresh runner before each test."""
        self.runner = WorkflowBatchRunner()

    def test_valid_workflow_id_returns_instance(self) -> None:
        """_create_workflow returns an instance for a known workflow ID."""
        mock_class = MagicMock(return_value=MagicMock())

        with patch(
            "attune.workflows.get_workflow",
            return_value=mock_class,
        ):
            spec = WorkflowSpec(workflow_id="security-audit", config={"x": 1})
            instance = self.runner._create_workflow(spec)

        mock_class.assert_called_once_with(x=1)
        assert instance is mock_class.return_value

    def test_unknown_workflow_id_raises_value_error(self) -> None:
        """_create_workflow raises ValueError when get_workflow raises KeyError."""
        with patch(
            "attune.workflows.get_workflow",
            side_effect=KeyError("Unknown workflow: ghost"),
        ):
            spec = WorkflowSpec(workflow_id="ghost")
            with pytest.raises(ValueError, match="not found in registry"):
                self.runner._create_workflow(spec)

    def test_constructor_type_error_falls_back_to_no_args(self) -> None:
        """_create_workflow falls back to no-arg constructor on TypeError."""
        mock_instance = MagicMock()
        call_count = 0

        def mock_class(**kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TypeError("unexpected keyword argument 'x'")
            return mock_instance

        with patch(
            "attune.workflows.get_workflow",
            return_value=mock_class,
        ):
            spec = WorkflowSpec(workflow_id="security-audit", config={"x": 1})
            instance = self.runner._create_workflow(spec)

        assert instance is mock_instance


# =============================================================================
# WorkflowBatchRunner._execute_one
# =============================================================================


class TestExecuteOne:
    """Tests for WorkflowBatchRunner._execute_one()."""

    def _make_runner(self, timeout: int = 600) -> WorkflowBatchRunner:
        """Create a runner with a configurable timeout."""
        return WorkflowBatchRunner(timeout_per_workflow=timeout)

    def _make_mock_workflow(self, result: object) -> MagicMock:
        """Return a mock workflow whose execute() resolves to result."""
        workflow = MagicMock()
        workflow.execute = AsyncMock(return_value=result)
        return workflow

    async def test_success_returns_success_result(self) -> None:
        """_execute_one returns WorkflowBatchResult with success=True."""
        mock_result = MagicMock()
        mock_result.total_cost = 0.005
        mock_result.cost_report = None

        runner = self._make_runner()
        spec = WorkflowSpec(
            workflow_id="security-audit",
            input_data={"path": "src/"},
        )

        with patch.object(
            runner,
            "_create_workflow",
            return_value=self._make_mock_workflow(mock_result),
        ):
            result = await runner._execute_one(spec)

        assert result.success is True
        assert result.workflow_id == "security-audit"
        assert result.error is None
        assert result.cost == pytest.approx(0.005)
        assert result.duration_seconds >= 0.0

    async def test_success_uses_cost_report_when_present(self) -> None:
        """_execute_one prefers cost_report.total_cost over result.total_cost."""
        mock_result = MagicMock()
        mock_result.total_cost = 0.001
        mock_result.cost_report = {"total_cost": 0.009}

        runner = self._make_runner()
        spec = WorkflowSpec(workflow_id="bug-predict", input_data={"path": "src/"})

        with patch.object(
            runner,
            "_create_workflow",
            return_value=self._make_mock_workflow(mock_result),
        ):
            result = await runner._execute_one(spec)

        assert result.cost == pytest.approx(0.009)

    async def test_timeout_returns_failure_result(self) -> None:
        """_execute_one returns success=False when workflow exceeds timeout."""
        runner = self._make_runner(timeout=1)
        spec = WorkflowSpec(workflow_id="bug-predict", input_data={"path": "src/"})

        async def slow_execute(**_kwargs: object) -> None:
            await asyncio.sleep(10)

        slow_workflow = MagicMock()
        slow_workflow.execute = slow_execute

        with patch.object(runner, "_create_workflow", return_value=slow_workflow):
            result = await runner._execute_one(spec)

        assert result.success is False
        assert "Timed out" in (result.error or "")
        assert "1s" in (result.error or "")

    async def test_exception_returns_failure_result(self) -> None:
        """_execute_one returns success=False when workflow raises an exception."""
        runner = self._make_runner()
        spec = WorkflowSpec(workflow_id="perf-audit", input_data={"path": "src/"})

        failing_workflow = MagicMock()
        failing_workflow.execute = AsyncMock(side_effect=RuntimeError("something broke"))

        with patch.object(runner, "_create_workflow", return_value=failing_workflow):
            result = await runner._execute_one(spec)

        assert result.success is False
        assert result.error == "something broke"
        assert result.duration_seconds >= 0.0

    async def test_failure_workflow_id_preserved(self) -> None:
        """_execute_one preserves workflow_id in the result on failure."""
        runner = self._make_runner()
        spec = WorkflowSpec(workflow_id="dependency-check")

        failing_workflow = MagicMock()
        failing_workflow.execute = AsyncMock(side_effect=ValueError("bad input"))

        with patch.object(runner, "_create_workflow", return_value=failing_workflow):
            result = await runner._execute_one(spec)

        assert result.workflow_id == "dependency-check"


# =============================================================================
# WorkflowBatchRunner.run_batch — serial
# =============================================================================


class TestRunBatchSerial:
    """Tests for run_batch() with serial (max_parallel=1) execution."""

    def _make_fake_workflow_class(self, cost: float = 0.001) -> type:
        """Return a fake workflow class whose execute() returns a mock result."""
        mock_result = MagicMock()
        mock_result.total_cost = cost
        mock_result.cost_report = None

        class FakeWorkflow:
            def __init__(self, **kwargs: object) -> None:
                pass

            async def execute(self, **kwargs: object) -> MagicMock:
                return mock_result

        return FakeWorkflow

    async def test_serial_all_succeed(self) -> None:
        """run_batch serial mode returns report with all successes."""
        runner = WorkflowBatchRunner(max_parallel=1)
        specs = [
            WorkflowSpec(workflow_id="security-audit", input_data={"path": "src/"}),
            WorkflowSpec(workflow_id="bug-predict", input_data={"path": "src/"}),
        ]

        fake_class = self._make_fake_workflow_class(cost=0.002)

        with patch(
            "attune.workflows.get_workflow",
            return_value=fake_class,
        ):
            report = await runner.run_batch(specs, preset_name="test-serial")

        assert report.preset == "test-serial"
        assert report.success_count == 2
        assert report.failure_count == 0
        assert len(report.results) == 2
        assert all(r.success for r in report.results)

    async def test_serial_preserves_order(self) -> None:
        """run_batch serial mode preserves the order of workflow results."""
        runner = WorkflowBatchRunner(max_parallel=1)
        specs = [
            WorkflowSpec(workflow_id="security-audit"),
            WorkflowSpec(workflow_id="bug-predict"),
            WorkflowSpec(workflow_id="dependency-check"),
        ]

        fake_class = self._make_fake_workflow_class()

        with patch(
            "attune.workflows.get_workflow",
            return_value=fake_class,
        ):
            report = await runner.run_batch(specs)

        ids = [r.workflow_id for r in report.results]
        assert ids == ["security-audit", "bug-predict", "dependency-check"]

    async def test_serial_partial_failure(self) -> None:
        """run_batch serial mode counts failures correctly."""
        runner = WorkflowBatchRunner(max_parallel=1)
        specs = [
            WorkflowSpec(workflow_id="security-audit"),
            WorkflowSpec(workflow_id="bug-predict"),
        ]

        call_count = 0

        class SometimesFailing:
            def __init__(self, **kwargs: object) -> None:
                pass

            async def execute(self, **kwargs: object) -> MagicMock:
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise RuntimeError("API error")
                result = MagicMock()
                result.total_cost = 0.001
                result.cost_report = None
                return result

        with patch(
            "attune.workflows.get_workflow",
            return_value=SometimesFailing,
        ):
            report = await runner.run_batch(specs)

        assert report.success_count == 1
        assert report.failure_count == 1

    async def test_serial_accumulates_total_cost(self) -> None:
        """run_batch serial mode sums per-workflow costs."""
        runner = WorkflowBatchRunner(max_parallel=1)
        specs = [
            WorkflowSpec(workflow_id="security-audit"),
            WorkflowSpec(workflow_id="bug-predict"),
        ]

        fake_class = self._make_fake_workflow_class(cost=0.003)

        with patch(
            "attune.workflows.get_workflow",
            return_value=fake_class,
        ):
            report = await runner.run_batch(specs)

        assert report.total_cost == pytest.approx(0.006)

    async def test_run_batch_empty_specs_raises(self) -> None:
        """run_batch raises ValueError when given an empty specs list."""
        runner = WorkflowBatchRunner(max_parallel=1)

        with pytest.raises(ValueError, match="cannot be empty"):
            await runner.run_batch([])

    async def test_run_batch_invalid_workflow_raises(self) -> None:
        """run_batch raises ValueError for non-batch-safe workflow IDs."""
        runner = WorkflowBatchRunner(max_parallel=1)
        specs = [WorkflowSpec(workflow_id="interactive-wizard")]

        with pytest.raises(ValueError, match="not in the batch-safe allowlist"):
            await runner.run_batch(specs)


# =============================================================================
# WorkflowBatchRunner.run_batch — parallel
# =============================================================================


class TestRunBatchParallel:
    """Tests for run_batch() with parallel (max_parallel > 1) execution."""

    def _make_fake_class(self, cost: float = 0.001) -> type:
        """Return a fake workflow class for parallel tests."""
        mock_result = MagicMock()
        mock_result.total_cost = cost
        mock_result.cost_report = None

        class FakeWorkflow:
            def __init__(self, **kwargs: object) -> None:
                pass

            async def execute(self, **kwargs: object) -> MagicMock:
                return mock_result

        return FakeWorkflow

    async def test_parallel_all_succeed(self) -> None:
        """run_batch parallel mode returns all successes."""
        runner = WorkflowBatchRunner(max_parallel=2)
        specs = [
            WorkflowSpec(workflow_id="security-audit"),
            WorkflowSpec(workflow_id="bug-predict"),
            WorkflowSpec(workflow_id="dependency-check"),
        ]

        fake_class = self._make_fake_class()

        with patch(
            "attune.workflows.get_workflow",
            return_value=fake_class,
        ):
            report = await runner.run_batch(specs, preset_name="parallel-test")

        assert report.success_count == 3
        assert report.failure_count == 0
        assert len(report.results) == 3

    async def test_parallel_accumulates_cost(self) -> None:
        """run_batch parallel mode sums costs from all workflows."""
        runner = WorkflowBatchRunner(max_parallel=2)
        specs = [
            WorkflowSpec(workflow_id="security-audit"),
            WorkflowSpec(workflow_id="bug-predict"),
        ]

        fake_class = self._make_fake_class(cost=0.005)

        with patch(
            "attune.workflows.get_workflow",
            return_value=fake_class,
        ):
            report = await runner.run_batch(specs)

        assert report.total_cost == pytest.approx(0.010)

    async def test_parallel_results_list_length(self) -> None:
        """run_batch parallel mode returns one result per spec."""
        runner = WorkflowBatchRunner(max_parallel=2)
        specs = [
            WorkflowSpec(workflow_id="security-audit"),
            WorkflowSpec(workflow_id="bug-predict"),
            WorkflowSpec(workflow_id="dependency-check"),
            WorkflowSpec(workflow_id="perf-audit"),
        ]

        fake_class = self._make_fake_class()

        with patch(
            "attune.workflows.get_workflow",
            return_value=fake_class,
        ):
            report = await runner.run_batch(specs)

        assert len(report.results) == 4

    async def test_parallel_failure_counted(self) -> None:
        """run_batch parallel mode correctly counts failures."""
        runner = WorkflowBatchRunner(max_parallel=2)
        specs = [
            WorkflowSpec(workflow_id="security-audit"),
            WorkflowSpec(workflow_id="bug-predict"),
        ]

        class AlwaysFailing:
            def __init__(self, **kwargs: object) -> None:
                pass

            async def execute(self, **kwargs: object) -> None:
                raise RuntimeError("forced failure")

        with patch(
            "attune.workflows.get_workflow",
            return_value=AlwaysFailing,
        ):
            report = await runner.run_batch(specs)

        assert report.failure_count == 2
        assert report.success_count == 0


# =============================================================================
# WorkflowBatchRunner.run_preset
# =============================================================================


class TestRunPreset:
    """Tests for WorkflowBatchRunner.run_preset()."""

    def _make_fake_class(self) -> type:
        """Return a minimal fake workflow class."""
        mock_result = MagicMock()
        mock_result.total_cost = 0.001
        mock_result.cost_report = None

        class FakeWorkflow:
            def __init__(self, **kwargs: object) -> None:
                pass

            async def execute(self, **kwargs: object) -> MagicMock:
                return mock_result

        return FakeWorkflow

    async def test_unknown_preset_raises_value_error(self) -> None:
        """run_preset raises ValueError for an unrecognised preset name."""
        runner = WorkflowBatchRunner()

        with pytest.raises(ValueError, match="Unknown preset"):
            await runner.run_preset("does-not-exist")

    async def test_unknown_preset_error_lists_available(self) -> None:
        """run_preset error message lists the available presets."""
        runner = WorkflowBatchRunner()

        with pytest.raises(ValueError) as exc_info:
            await runner.run_preset("ghost-preset")

        message = str(exc_info.value)
        for preset in ("daily-quality", "pre-release", "coverage-boost", "full-audit"):
            assert preset in message

    async def test_known_preset_returns_report(self) -> None:
        """run_preset returns a BatchRunReport for a valid preset name."""
        runner = WorkflowBatchRunner()

        with patch(
            "attune.workflows.get_workflow",
            return_value=self._make_fake_class(),
        ):
            report = await runner.run_preset("daily-quality")

        assert isinstance(report, BatchRunReport)
        assert report.preset == "daily-quality"

    async def test_path_override_replaces_default_path(self) -> None:
        """run_preset path_override substitutes the path in all specs."""
        runner = WorkflowBatchRunner()
        captured_paths: list[str] = []

        class CapturingWorkflow:
            def __init__(self, **kwargs: object) -> None:
                pass

            async def execute(self, path: str = "", **kwargs: object) -> MagicMock:
                captured_paths.append(path)
                result = MagicMock()
                result.total_cost = 0.0
                result.cost_report = None
                return result

        with patch(
            "attune.workflows.get_workflow",
            return_value=CapturingWorkflow,
        ):
            await runner.run_preset("daily-quality", path_override="/custom/path")

        assert all(
            p == "/custom/path" for p in captured_paths
        ), f"Expected all paths to be '/custom/path', got: {captured_paths}"
        # daily-quality has 3 workflows
        assert len(captured_paths) == 3

    async def test_preset_report_preset_field_matches_name(self) -> None:
        """run_preset sets report.preset to the preset name."""
        runner = WorkflowBatchRunner()

        with patch(
            "attune.workflows.get_workflow",
            return_value=self._make_fake_class(),
        ):
            report = await runner.run_preset("coverage-boost")

        assert report.preset == "coverage-boost"

    async def test_all_presets_can_run(self) -> None:
        """All four presets can be executed without errors (mocked)."""
        runner = WorkflowBatchRunner()

        for preset_name in ("daily-quality", "pre-release", "coverage-boost", "full-audit"):
            with patch(
                "attune.workflows.get_workflow",
                return_value=self._make_fake_class(),
            ):
                report = await runner.run_preset(preset_name)

            assert isinstance(
                report,
                BatchRunReport,
            ), f"Preset '{preset_name}' did not return a BatchRunReport"


# =============================================================================
# WorkflowBatchRunner constructor
# =============================================================================


class TestWorkflowBatchRunnerInit:
    """Tests for WorkflowBatchRunner.__init__() defaults and overrides."""

    def test_default_max_parallel_is_one(self) -> None:
        """Default max_parallel is 1 (serial execution)."""
        runner = WorkflowBatchRunner()
        assert runner.max_parallel == 1

    def test_default_timeout_is_600(self) -> None:
        """Default timeout_per_workflow is 600 seconds."""
        runner = WorkflowBatchRunner()
        assert runner.timeout_per_workflow == 600

    def test_custom_max_parallel(self) -> None:
        """max_parallel is stored correctly when provided."""
        runner = WorkflowBatchRunner(max_parallel=4)
        assert runner.max_parallel == 4

    def test_custom_timeout(self) -> None:
        """timeout_per_workflow is stored correctly when provided."""
        runner = WorkflowBatchRunner(timeout_per_workflow=120)
        assert runner.timeout_per_workflow == 120
