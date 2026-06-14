"""Coverage-completing tests for TestMaintenanceWorkflow.

Targets the behavior left uncovered by ``test_test_maintenance.py``:
the index-load fallback, the execute/auto ``run()`` branches, the
``_execute_plan`` loop and its placeholder executors, the stale-file
and option-generation branches, and the three file-event handlers.

The shared ``test_maintenance_workflow`` fixture (conftest.py) provides
a workflow backed by a ``MagicMock`` index; tests configure the index
methods they exercise. Async methods run under ``asyncio_mode = auto``.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock

import pytest

from attune.project_index.models import FileRecord, TestRequirement
from attune.workflows.test_maintenance import (
    TestAction,
    TestMaintenancePlan,
    TestMaintenanceWorkflow,
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


def _make_item(action=TestAction.CREATE, auto_executable=True, path="src/x.py"):
    """Build a TestPlanItem for direct _execute_plan tests."""
    return TestPlanItem(
        file_path=path,
        action=action,
        priority=TestPriority.MEDIUM,
        reason="test",
        auto_executable=auto_executable,
    )


@pytest.mark.unit
class TestEnsureIndexLoaded:
    """The __init__ -> _ensure_index_loaded fallback."""

    def test_refreshes_when_index_not_loaded(self, tmp_path):
        idx = MagicMock()
        idx.load.return_value = False
        TestMaintenanceWorkflow(project_root=str(tmp_path), index=idx)
        idx.refresh.assert_called_once()

    def test_no_refresh_when_index_loaded(self, tmp_path):
        idx = MagicMock()
        idx.load.return_value = True
        TestMaintenanceWorkflow(project_root=str(tmp_path), index=idx)
        idx.refresh.assert_not_called()


@pytest.mark.unit
class TestRunExecuteAndAutoModes:
    """run() branches beyond analyze/dry-run/report."""

    def _stub_empty(self, wf):
        wf.index.get_file.return_value = None
        wf.index.get_files_needing_tests.return_value = []
        wf.index.get_stale_files.return_value = []

    @pytest.mark.asyncio
    async def test_changed_files_trigger_refresh(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        self._stub_empty(wf)
        await wf.run({"mode": "analyze", "changed_files": ["src/a.py"]})
        wf.index.refresh.assert_called()

    @pytest.mark.asyncio
    async def test_execute_mode_runs_plan(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        record = _make_record(path="src/needs.py", impact_score=6.0, lines_of_code=120)
        wf.index.get_file.return_value = None
        wf.index.get_files_needing_tests.return_value = [record]
        wf.index.get_stale_files.return_value = []

        result = await wf.run({"mode": "execute", "dry_run": False})

        assert result["status"] == "executed"
        assert "execution" in result
        assert result["execution"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_auto_mode_dry_run(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        self._stub_empty(wf)
        result = await wf.run({"mode": "auto", "dry_run": True})
        assert result["status"] == "dry_run"
        assert "auto-execute" in result["message"]

    @pytest.mark.asyncio
    async def test_auto_mode_executes(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        record = _make_record(path="src/auto.py", impact_score=3.0, lines_of_code=80)
        wf.index.get_file.return_value = None
        wf.index.get_files_needing_tests.return_value = [record]
        wf.index.get_stale_files.return_value = []

        result = await wf.run({"mode": "auto", "dry_run": False})

        assert result["status"] == "auto_executed"
        assert "execution" in result


@pytest.mark.unit
class TestGeneratePlanStaleAndOptions:
    """Stale-file inclusion and critical/update option branches."""

    def test_includes_stale_files(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        stale = _make_record(
            path="src/stale.py",
            staleness_days=45,
            tests_exist=True,
            test_file_path="tests/test_stale.py",
        )
        wf.index.get_file.return_value = stale
        wf.index.get_files_needing_tests.return_value = []
        wf.index.get_stale_files.return_value = [stale]

        plan = wf._generate_plan(changed_files=[], max_items=20)

        actions = {item.action for item in plan.items}
        assert TestAction.UPDATE in actions

    def test_options_include_critical_and_update(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        critical = _make_record(path="src/critical.py", impact_score=12.0)
        stale = _make_record(
            path="src/stale.py",
            staleness_days=30,
            tests_exist=True,
            test_file_path="tests/test_stale.py",
            impact_score=1.0,
        )
        wf.index.get_file.side_effect = lambda p: {
            "src/critical.py": critical,
            "src/stale.py": stale,
        }.get(p)
        wf.index.get_files_needing_tests.return_value = [critical]
        wf.index.get_stale_files.return_value = [stale]

        plan = wf._generate_plan(changed_files=[], max_items=20)

        option_ids = {opt["id"] for opt in plan.options}
        assert "critical_only" in option_ids
        assert "update_stale" in option_ids
        assert "manual_review" in option_ids


@pytest.mark.unit
class TestExecutePlan:
    """The _execute_plan loop, executors, and error handling."""

    @pytest.mark.asyncio
    async def test_runs_each_action_and_skips(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        plan = TestMaintenancePlan()
        plan.items = [
            _make_item(TestAction.CREATE, path="a.py"),
            _make_item(TestAction.UPDATE, path="b.py"),
            _make_item(TestAction.REVIEW, path="c.py"),
            _make_item(TestAction.DELETE, path="d.py"),
            _make_item(TestAction.SKIP, path="e.py"),
        ]

        result = await wf._execute_plan(plan, auto_only=False)

        assert result["total"] == 5
        assert result["succeeded"] == 4  # create/update/review/delete placeholders
        assert result["skipped"] == 1  # SKIP action
        assert len(result["details"]) == 4  # SKIP continues before appending
        # Index updated once per succeeded item.
        assert wf.index.update_file.call_count == 4

    @pytest.mark.asyncio
    async def test_auto_only_filters_items(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        plan = TestMaintenancePlan()
        plan.items = [
            _make_item(TestAction.CREATE, auto_executable=True, path="auto.py"),
            _make_item(TestAction.CREATE, auto_executable=False, path="manual.py"),
        ]

        result = await wf._execute_plan(plan, auto_only=True)

        assert result["total"] == 1
        assert result["succeeded"] == 1

    @pytest.mark.asyncio
    async def test_executor_exception_is_recorded(self, test_maintenance_workflow):
        wf = test_maintenance_workflow

        async def _boom(_item):
            raise RuntimeError("gen failed")

        wf._create_tests_for_file = _boom
        plan = TestMaintenancePlan()
        plan.items = [_make_item(TestAction.CREATE, path="bad.py")]

        result = await wf._execute_plan(plan, auto_only=False)

        assert result["failed"] == 1
        assert result["succeeded"] == 0
        assert result["details"][0]["error"] == "gen failed"

    @pytest.mark.asyncio
    async def test_executor_returning_false_counts_failed(self, test_maintenance_workflow):
        wf = test_maintenance_workflow

        async def _fail(_item):
            return False

        wf._create_tests_for_file = _fail
        plan = TestMaintenancePlan()
        plan.items = [_make_item(TestAction.CREATE, path="nope.py")]

        result = await wf._execute_plan(plan, auto_only=False)

        assert result["failed"] == 1
        assert result["succeeded"] == 0
        assert result["details"][0]["success"] is False
        # No index update when the executor reports failure.
        wf.index.update_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_placeholder_executors_return_true(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        item = _make_item()
        assert await wf._create_tests_for_file(item) is True
        assert await wf._update_tests_for_file(item) is True
        assert await wf._review_tests_for_file(item) is True
        assert await wf._delete_orphaned_tests(item) is True


@pytest.mark.unit
class TestOnFileCreated:
    """on_file_created event handler."""

    @pytest.mark.asyncio
    async def test_not_indexed(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        wf.index.get_file.return_value = None
        result = await wf.on_file_created("src/new.py")
        assert result["status"] == "not_indexed"

    @pytest.mark.asyncio
    async def test_needs_tests(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        wf.index.get_file.return_value = _make_record(
            path="src/new.py", test_requirement=TestRequirement.REQUIRED
        )
        result = await wf.on_file_created("src/new.py")
        assert result["status"] == "needs_tests"
        assert result["plan_item"] is not None

    @pytest.mark.asyncio
    async def test_no_tests_required(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        wf.index.get_file.return_value = _make_record(
            path="src/new.py", test_requirement=TestRequirement.OPTIONAL
        )
        result = await wf.on_file_created("src/new.py")
        assert result["status"] == "no_tests_required"


@pytest.mark.unit
class TestOnFileModified:
    """on_file_modified event handler."""

    @pytest.mark.asyncio
    async def test_not_indexed_after_refresh(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        wf.index.get_file.return_value = None
        result = await wf.on_file_modified("src/gone.py")
        assert result["status"] == "not_indexed"
        wf.index.refresh.assert_called()

    @pytest.mark.asyncio
    async def test_tests_may_need_update(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        wf.index.get_file.return_value = _make_record(
            path="src/mod.py",
            tests_exist=True,
            test_file_path="tests/test_mod.py",
        )
        result = await wf.on_file_modified("src/mod.py")
        assert result["status"] == "tests_may_need_update"
        assert result["test_file"] == "tests/test_mod.py"
        wf.index.update_file.assert_called()

    @pytest.mark.asyncio
    async def test_needs_tests_when_required_no_tests(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        wf.index.get_file.return_value = _make_record(
            path="src/mod.py",
            tests_exist=False,
            test_requirement=TestRequirement.REQUIRED,
        )
        result = await wf.on_file_modified("src/mod.py")
        assert result["status"] == "needs_tests"

    @pytest.mark.asyncio
    async def test_no_action_needed(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        wf.index.get_file.return_value = _make_record(
            path="src/mod.py",
            tests_exist=False,
            test_requirement=TestRequirement.OPTIONAL,
        )
        result = await wf.on_file_modified("src/mod.py")
        assert result["status"] == "no_action_needed"


@pytest.mark.unit
class TestOnFileDeleted:
    """on_file_deleted event handler."""

    @pytest.mark.asyncio
    async def test_orphaned_tests_when_test_file_exists(self, test_maintenance_workflow, tmp_path):
        wf = test_maintenance_workflow
        test_rel = "tests/test_orphan.py"
        test_abs = tmp_path / test_rel
        test_abs.parent.mkdir(parents=True, exist_ok=True)
        test_abs.write_text("# orphan\n")
        wf.index.get_file.return_value = _make_record(path="src/orphan.py", test_file_path=test_rel)

        result = await wf.on_file_deleted("src/orphan.py")

        assert result["status"] == "orphaned_tests"
        assert result["action"] == "review_for_deletion"

    @pytest.mark.asyncio
    async def test_file_removed_when_no_test_file(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        wf.index.get_file.return_value = _make_record(path="src/gone.py", test_file_path=None)
        result = await wf.on_file_deleted("src/gone.py")
        assert result["status"] == "file_removed"
        wf.index.refresh.assert_called()

    @pytest.mark.asyncio
    async def test_file_removed_when_not_indexed(self, test_maintenance_workflow):
        wf = test_maintenance_workflow
        wf.index.get_file.return_value = None
        result = await wf.on_file_deleted("src/gone.py")
        assert result["status"] == "file_removed"
