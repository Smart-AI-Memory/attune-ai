---
type: reference
feature: fix-test
depth: reference
generated_at: 2026-04-14T14:56:20.248580+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Fix Test reference

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_tests_with_tracking` | `test_suite: str = 'unit'`<br>`test_files: list[str] | None = None`<br>`command: str | None = None`<br>`workflow_id: str | None = None`<br>`triggered_by: str = 'manual'` | `TestExecutionRecord` | Run tests with explicit tracking (opt-in for Tier 1 monitoring) |
| `track_coverage` | `coverage_file: str = 'coverage.xml'`<br>`workflow_id: str | None = None` | `CoverageRecord` | Track test coverage from coverage.xml file (opt-in for Tier 1 monitoring) |
| `track_file_tests` | `source_file: str`<br>`test_file: str | None = None`<br>`workflow_id: str | None = None` | `FileTestRecord` | Track test execution for a specific source file |
| `get_file_test_status` | `file_path: str` | `FileTestRecord | None` | Get the latest test status for a specific file |
| `get_files_needing_tests` | `stale_only: bool = False`<br>`failed_only: bool = False` | `list[FileTestRecord]` | Get files that need test attention |

### Exceptions

| Function | Raises |
|----------|--------|
| `track_coverage` | `FileNotFoundError` — 'Coverage file not found: {...}'<br>`ValueError` — 'Invalid coverage.xml format: {...}' |

## Dataclasses

### TestPlanItem

A single item in a test maintenance plan.

| Field | Type | Default |
|-------|------|---------|
| `file_path` | `str` | |
| `action` | `TestAction` | |
| `priority` | `TestPriority` | |
| `reason` | `str` | |
| `test_file_path` | `str | None` | `None` |
| `estimated_effort` | `str` | `'unknown'` |
| `auto_executable` | `bool` | `True` |
| `metadata` | `dict[str, Any]` | `field(default_factory=dict)` |

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict` | `dict[str, Any]` | Convert to dictionary representation |

### TestMaintenancePlan

Complete test maintenance plan for a project.

| Field | Type | Default |
|-------|------|---------|
| `generated_at` | `datetime` | `field(default_factory=datetime.now)` |
| `items` | `list[TestPlanItem]` | `field(default_factory=list)` |
| `summary` | `dict[str, Any]` | `field(default_factory=dict)` |
| `options` | `list[dict[str, Any]]` | `field(default_factory=list)` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | | `dict[str, Any]` | Convert to dictionary representation |
| `get_items_by_action` | `action: TestAction` | `list[TestPlanItem]` | Get items filtered by action type |
| `get_items_by_priority` | `priority: TestPriority` | `list[TestPlanItem]` | Get items filtered by priority level |
| `get_auto_executable_items` | | `list[TestPlanItem]` | Get items marked as auto-executable |

### TestTask

A queued test management task.

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | |
| `file_path` | `str` | |
| `action` | `TestAction` | |
| `priority` | `TestPriority` | |
| `created_at` | `datetime` | `field(default_factory=datetime.now)` |
| `scheduled_for` | `datetime | None` | `None` |
| `status` | `str` | `'pending'` |
| `result` | `dict[str, Any] | None` | `None` |

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict` | `dict[str, Any]` | Convert to dictionary representation |

## Classes

### TestAction

Actions that can be taken for test management.

### TestPriority

Priority levels for test actions.

### TestMaintenanceWorkflow

Workflow for automatic test lifecycle management.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `project_root: str`<br>`index: ProjectIndex | None = None` | | Initialize workflow |
| `run` | `context: dict[str, Any]` | `dict[str, Any]` | Execute maintenance workflow |
| `on_file_created` | `file_path: str` | `dict[str, Any]` | Handle file creation event |
| `on_file_modified` | `file_path: str` | `dict[str, Any]` | Handle file modification event |
| `on_file_deleted` | `file_path: str` | `dict[str, Any]` | Handle file deletion event |
| `get_files_needing_tests` | `limit: int = 20` | `list[dict[str, Any]]` | Get files requiring test coverage |
| `get_stale_tests` | `limit: int = 20` | `list[dict[str, Any]]` | Get outdated test files |
| `get_test_health_summary` | | `dict[str, Any]` | Get overall test health metrics |

### TestLifecycleManager

Manages the lifecycle of tests based on source file events.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `project_root: str`<br>`index: ProjectIndex | None = None`<br>`auto_execute: bool = False`<br>`queue_file: str | None = None` | | Initialize lifecycle manager |
| `on_file_created` | `file_path: str` | `TestTask | None` | Handle file creation event |
| `on_file_modified` | `file_path: str` | `TestTask | None` | Handle file modification event |
| `on_file_deleted` | `file_path: str` | `TestTask | None` | Handle file deletion event |
| `on_files_changed` | `changed_files: list[str]` | `list[TestTask]` | Handle batch file changes |
| `get_queue` | | `list[dict[str, Any]]` | Get task queue contents |
| `get_pending_count` | | `int` | Get number of pending tasks |
| `get_queue_by_priority` | `priority: TestPriority` | `list[TestTask]` | Get tasks filtered by priority |
| `clear_queue` | | `int` | Clear all queued tasks |
| `process_queue` | `max_tasks: int = 10`<br>`priority_filter: TestPriority | None = None` | `dict[str, Any]` | Process queued tasks |
| `schedule_maintenance` | `interval_hours: int = 24`<br>`auto_execute: bool = False` | `dict[str, Any]` | Schedule periodic maintenance |
| `run_maintenance` | `auto_execute: bool = False` | `dict[str, Any]` | Execute maintenance tasks |
| `process_git_pre_commit` | `staged_files: list[str]` | `dict[str, Any]` | Handle pre-commit Git hook |
| `process_git_post_commit` | `changed_files: list[str]` | `dict[str, Any]` | Handle post-commit Git hook |
| `on_task_queued` | `callback: Callable[[TestTask], None]` | | Register task queue callback |
| `on_task_completed` | `callback: Callable[[TestTask], None]` | | Register task completion callback |
| `get_status` | | `dict[str, Any]` | Get lifecycle manager status |
