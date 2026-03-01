"""Tests for TestMaintenanceWorkflow.

Covers initialization, plan generation, priority sorting,
convenience methods, and event handlers.

Note: TestMaintenanceWorkflow is NOT a BaseWorkflow subclass.
It is a standalone utility class with its own run() interface.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock, patch

import pytest

from attune.project_index.models import FileRecord, TestRequirement
from attune.workflows.test_maintenance import (
    TestAction,
    TestMaintenancePlan,
    TestPlanItem,
    TestPriority,
)


def _make_record(
    path="src/foo.py",
    impact_score=5.0,
    lines_of_code=100,
    language="python",
    tests_exist=False,
    test_file_path=None,
    staleness_days=0,
    is_stale=False,
    complexity_score=3.0,
    test_requirement=TestRequirement.REQUIRED,
):
    """Helper to build a FileRecord with sensible defaults."""
    return FileRecord(
        path=path,
        name=path.split("/")[-1],
        language=language,
        impact_score=impact_score,
        lines_of_code=lines_of_code,
        tests_exist=tests_exist,
        test_file_path=test_file_path,
        staleness_days=staleness_days,
        is_stale=is_stale,
        complexity_score=complexity_score,
        test_requirement=test_requirement,
    )


@pytest.mark.unit
class TestTestMaintenanceInit:
    """Verify initialization."""

    def test_attributes(self, test_maintenance_workflow, tmp_path):
        wf = test_maintenance_workflow
        assert wf.name == "test_maintenance"
        assert wf.description == "Automatic test lifecycle management"
        assert wf.project_root == tmp_path


@pytest.mark.unit
class TestCreatePlanItemForFile:
    """Tests for _create_plan_item_for_file()."""

    def test_missing_tests_creates_create_action(self, test_maintenance_workflow):
        record = _make_record(tests_exist=False)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")

        assert item.action == TestAction.CREATE
        assert "require" in item.reason.lower()

    def test_stale_creates_update_action(self, test_maintenance_workflow):
        record = _make_record(staleness_days=30, is_stale=True)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="stale")

        assert item.action == TestAction.UPDATE
        assert "30" in item.reason

    def test_modified_with_tests_creates_review(self, test_maintenance_workflow):
        record = _make_record(tests_exist=True, test_file_path="tests/test_foo.py")
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="modified")

        assert item.action == TestAction.REVIEW

    def test_modified_without_tests_creates_create(self, test_maintenance_workflow):
        record = _make_record(tests_exist=False)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="modified")

        assert item.action == TestAction.CREATE

    def test_deleted_creates_delete_action(self, test_maintenance_workflow):
        record = _make_record()
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="deleted")

        assert item.action == TestAction.DELETE

    def test_unknown_event_creates_skip(self, test_maintenance_workflow):
        record = _make_record()
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="unknown")

        assert item.action == TestAction.SKIP


@pytest.mark.unit
class TestPriorityMapping:
    """Tests for impact_score -> priority mapping."""

    def test_critical_priority(self, test_maintenance_workflow):
        record = _make_record(impact_score=10.0)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert item.priority == TestPriority.CRITICAL

    def test_high_priority(self, test_maintenance_workflow):
        record = _make_record(impact_score=5.0)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert item.priority == TestPriority.HIGH

    def test_medium_priority(self, test_maintenance_workflow):
        record = _make_record(impact_score=2.0)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert item.priority == TestPriority.MEDIUM

    def test_low_priority(self, test_maintenance_workflow):
        record = _make_record(impact_score=1.0)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert item.priority == TestPriority.LOW


@pytest.mark.unit
class TestEffortEstimation:
    """Tests for effort estimation based on lines_of_code."""

    def test_small_effort(self, test_maintenance_workflow):
        record = _make_record(lines_of_code=30)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert "small" in item.estimated_effort

    def test_medium_effort(self, test_maintenance_workflow):
        record = _make_record(lines_of_code=150)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert "medium" in item.estimated_effort

    def test_large_effort(self, test_maintenance_workflow):
        record = _make_record(lines_of_code=300)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert "large" in item.estimated_effort


@pytest.mark.unit
class TestAutoExecutable:
    """Tests for auto_executable determination."""

    def test_python_create_under_500_is_auto(self, test_maintenance_workflow):
        record = _make_record(language="python", lines_of_code=200, tests_exist=False)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert item.auto_executable is True

    def test_large_file_not_auto(self, test_maintenance_workflow):
        record = _make_record(language="python", lines_of_code=600, tests_exist=False)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert item.auto_executable is False

    def test_non_python_not_auto(self, test_maintenance_workflow):
        record = _make_record(language="javascript", lines_of_code=100, tests_exist=False)
        item = test_maintenance_workflow._create_plan_item_for_file(record, event="missing_tests")
        assert item.auto_executable is False


@pytest.mark.unit
class TestGeneratePlan:
    """Tests for _generate_plan()."""

    def test_generates_plan_from_changed_files(self, test_maintenance_workflow):
        record = _make_record(path="src/changed.py", tests_exist=False)
        test_maintenance_workflow.index.get_file.return_value = record
        test_maintenance_workflow.index.get_files_needing_tests.return_value = []
        test_maintenance_workflow.index.get_stale_files.return_value = []

        plan = test_maintenance_workflow._generate_plan(
            changed_files=["src/changed.py"], max_items=20
        )

        assert isinstance(plan, TestMaintenancePlan)
        assert len(plan.items) >= 1
        assert plan.items[0].file_path == "src/changed.py"

    def test_limits_items(self, test_maintenance_workflow):
        records = [_make_record(path=f"src/file{i}.py", impact_score=float(i)) for i in range(10)]
        test_maintenance_workflow.index.get_file.side_effect = lambda p: next(
            (r for r in records if r.path == p), None
        )
        test_maintenance_workflow.index.get_files_needing_tests.return_value = records
        test_maintenance_workflow.index.get_stale_files.return_value = []

        plan = test_maintenance_workflow._generate_plan(changed_files=[], max_items=3)

        assert len(plan.items) <= 3

    def test_plan_has_summary(self, test_maintenance_workflow):
        test_maintenance_workflow.index.get_file.return_value = None
        test_maintenance_workflow.index.get_files_needing_tests.return_value = []
        test_maintenance_workflow.index.get_stale_files.return_value = []

        plan = test_maintenance_workflow._generate_plan(changed_files=[], max_items=20)

        assert "total_items" in plan.summary
        assert "by_action" in plan.summary
        assert "by_priority" in plan.summary


@pytest.mark.unit
class TestRun:
    """Tests for the async run() entry point."""

    @pytest.mark.asyncio
    async def test_analyze_mode(self, test_maintenance_workflow):
        test_maintenance_workflow.index.get_file.return_value = None
        test_maintenance_workflow.index.get_files_needing_tests.return_value = []
        test_maintenance_workflow.index.get_stale_files.return_value = []

        result = await test_maintenance_workflow.run({"mode": "analyze"})

        assert result["status"] == "plan_generated"
        assert result["workflow"] == "test_maintenance"

    @pytest.mark.asyncio
    async def test_execute_dry_run(self, test_maintenance_workflow):
        test_maintenance_workflow.index.get_file.return_value = None
        test_maintenance_workflow.index.get_files_needing_tests.return_value = []
        test_maintenance_workflow.index.get_stale_files.return_value = []

        result = await test_maintenance_workflow.run({"mode": "execute", "dry_run": True})

        assert result["status"] == "dry_run"

    @pytest.mark.asyncio
    async def test_report_mode(self, test_maintenance_workflow):
        mock_summary = MagicMock()
        test_maintenance_workflow.index.get_summary.return_value = mock_summary
        test_maintenance_workflow.index.get_all_files.return_value = []
        test_maintenance_workflow.index.get_file.return_value = None
        test_maintenance_workflow.index.get_files_needing_tests.return_value = []
        test_maintenance_workflow.index.get_stale_files.return_value = []

        with patch("attune.workflows.test_maintenance.ReportGenerator") as MockGen:
            mock_gen = MockGen.return_value
            mock_gen.health_report.return_value = {}
            mock_gen.test_gap_report.return_value = {}
            mock_gen.staleness_report.return_value = {}
            mock_gen.coverage_report.return_value = {}

            result = await test_maintenance_workflow.run({"mode": "report"})

        assert result["status"] == "report_generated"
        assert "report" in result


@pytest.mark.unit
class TestConvenienceMethods:
    """Tests for get_files_needing_tests, get_stale_tests, etc."""

    def test_get_files_needing_tests(self, test_maintenance_workflow):
        records = [
            _make_record(path="src/a.py", impact_score=10.0),
            _make_record(path="src/b.py", impact_score=2.0),
            _make_record(path="src/c.py", impact_score=8.0),
        ]
        test_maintenance_workflow.index.get_files_needing_tests.return_value = records

        result = test_maintenance_workflow.get_files_needing_tests(limit=2)

        assert len(result) == 2
        assert result[0]["path"] == "src/a.py"
        assert result[1]["path"] == "src/c.py"

    def test_get_stale_tests(self, test_maintenance_workflow):
        records = [
            _make_record(
                path="src/old.py",
                staleness_days=90,
                test_file_path="tests/test_old.py",
            ),
            _make_record(
                path="src/newer.py",
                staleness_days=10,
                test_file_path="tests/test_newer.py",
            ),
        ]
        test_maintenance_workflow.index.get_stale_files.return_value = records

        result = test_maintenance_workflow.get_stale_tests(limit=2)

        assert len(result) == 2
        assert result[0]["staleness_days"] == 90

    def test_get_test_health_summary(self, test_maintenance_workflow):
        mock_summary = MagicMock()
        mock_summary.files_requiring_tests = 50
        mock_summary.files_with_tests = 40
        mock_summary.files_without_tests = 10
        mock_summary.test_coverage_avg = 85.0
        mock_summary.stale_file_count = 5
        mock_summary.test_to_code_ratio = 0.8
        test_maintenance_workflow.index.get_summary.return_value = mock_summary

        result = test_maintenance_workflow.get_test_health_summary()

        assert result["files_requiring_tests"] == 50
        assert result["files_with_tests"] == 40
        assert result["coverage_avg"] == 85.0


@pytest.mark.unit
class TestTestPlanItem:
    """Tests for TestPlanItem dataclass."""

    def test_to_dict(self):
        item = TestPlanItem(
            file_path="src/foo.py",
            action=TestAction.CREATE,
            priority=TestPriority.HIGH,
            reason="Needs tests",
        )
        d = item.to_dict()

        assert d["file_path"] == "src/foo.py"
        assert d["action"] == "create"
        assert d["priority"] == "high"


@pytest.mark.unit
class TestTestMaintenancePlan:
    """Tests for TestMaintenancePlan dataclass."""

    def test_get_items_by_action(self):
        plan = TestMaintenancePlan(
            items=[
                TestPlanItem("a.py", TestAction.CREATE, TestPriority.HIGH, "r"),
                TestPlanItem("b.py", TestAction.UPDATE, TestPriority.LOW, "r"),
                TestPlanItem("c.py", TestAction.CREATE, TestPriority.LOW, "r"),
            ]
        )
        creates = plan.get_items_by_action(TestAction.CREATE)
        assert len(creates) == 2

    def test_get_auto_executable_items(self):
        plan = TestMaintenancePlan(
            items=[
                TestPlanItem(
                    "a.py",
                    TestAction.CREATE,
                    TestPriority.HIGH,
                    "r",
                    auto_executable=True,
                ),
                TestPlanItem(
                    "b.py",
                    TestAction.MANUAL,
                    TestPriority.HIGH,
                    "r",
                    auto_executable=False,
                ),
            ]
        )
        auto = plan.get_auto_executable_items()
        assert len(auto) == 1
