---
type: reference
feature: fix-test
depth: reference
generated_at: 2026-05-04T02:29:09.486519+00:00
source_hash: bff04fe2ad91cb5eb72a0a1c91eccca5bb1b81eba3549bb3ac7e694b3e7a98b8
status: generated
---

# Fix Test reference

Event-driven test management with automatic lifecycle control, maintenance workflows, and execution tracking for automated test repair and monitoring.

## Classes

| Class | Description |
|-------|-------------|
| `TestTask` | A queued test management task |
| `TestLifecycleManager` | Manages test lifecycle based on source file events |
| `TestAction` | Actions available for test management |
| `TestPriority` | Priority levels for test actions |
| `TestPlanItem` | Single item in a test maintenance plan |
| `TestMaintenancePlan` | Complete test maintenance plan for a project |
| `TestMaintenanceWorkflow` | Workflow for automatic test lifecycle management |

### TestTask

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | | Task identifier |
| `file_path` | `str` | | Path to the file being tested |
| `action` | `TestAction` | | Action to perform |
| `priority` | `TestPriority` | | Task priority level |
| `created_at` | `datetime` | `field(default_factory=datetime.now)` | Task creation timestamp |
| `scheduled_for` | `datetime | None` | `None` | Scheduled execution time |
| `status` | `str` | `'pending'` | Current task status |
| `result` | `dict[str, Any] | None` | `None` | Task execution results |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict(self)` | `dict[str, Any]` | Convert task to dictionary format |

### TestLifecycleManager

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__(self, project_root, index, auto_execute, queue_file)` | `project_root: str, index: ProjectIndex | None = None, auto_execute: bool = False, queue_file: str | None = None` | | Initialize test lifecycle manager |
| `on_file_created(self, file_path)` | `file_path: str` | `TestTask | None` | Handle file creation event |
| `on_file_modified(self, file_path)` | `file_path: str` | `TestTask | None` | Handle file modification event |
| `on_file_deleted(self, file_path)` | `file_path: str` | `TestTask | None` | Handle file deletion event |
| `on_files_changed(self, changed_files)` | `changed_files: list[str]` | `list[TestTask]` | Handle multiple file changes |
| `get_queue(self)` | | `list[dict[str, Any]]` | Get current task queue |
| `get_pending_count(self)` | | `int` | Get count of pending tasks |
| `get_queue_by_priority(self, priority)` | `priority: TestPriority` | `list[TestTask]` | Get tasks filtered by priority |
| `clear_queue(self)` | | `int` | Clear all queued tasks |
| `process_queue(self, max_tasks, priority_filter)` | `max_tasks: int = 10, priority_filter: TestPriority | None = None` | `dict[str, Any]` | Process queued tasks |
| `schedule_maintenance(self, interval_hours, auto_execute)` | `interval_hours: int = 24, auto_execute: bool = False` | `dict[str, Any]` | Schedule maintenance tasks |
| `run_maintenance(self, auto_execute)` | `auto_execute: bool = False` | `dict[str, Any]` | Run maintenance workflow |
| `process_git_pre_commit(self, staged_files)` | `staged_files: list[str]` | `dict[str, Any]` | Process pre-commit file changes |
| `process_git_post_commit(self, changed_files)` | `changed_files: list[str]` | `dict[str, Any]` | Process post-commit file changes |
| `on_task_queued(self, callback)` | `callback: Callable[[TestTask], None]` | `None` | Register task queued callback |
| `on_task_completed(self, callback)` | `callback: Callable[[TestTask], None]` | `None` | Register task completed callback |
| `get_status(self)` | | `dict[str, Any]` | Get manager status |

### TestPlanItem

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file_path` | `str` | | Path to source file |
| `action` | `TestAction` | | Required action |
| `priority` | `TestPriority` | | Action priority |
| `reason` | `str` | | Reason for action |
| `test_file_path` | `str | None` | `None` | Associated test file |
| `estimated_effort` | `str` | `'unknown'` | Effort estimate |
| `auto_executable` | `bool` | `True` | Whether action can be automated |
| `metadata` | `dict[str, Any]` | `field(default_factory=dict)` | Additional metadata |

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict(self)` | `dict[str, Any]` | Convert item to dictionary format |

### TestMaintenancePlan

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `generated_at` | `datetime` | `field(default_factory=datetime.now)` | Plan generation timestamp |
| `items` | `list[TestPlanItem]` | `field(default_factory=list)` | Plan items |
| `summary` | `dict[str, Any]` | `field(default_factory=dict)` | Plan summary |
| `options` | `list[dict[str, Any]]` | `field(default_factory=list)` | Available options |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict(self)` | | `dict[str, Any]` | Convert plan to dictionary format |
| `get_items_by_action(self, action)` | `action: TestAction` | `list[TestPlanItem]` | Filter items by action type |
| `get_items_by_priority(self, priority)` | `priority: TestPriority` | `list[TestPlanItem]` | Filter items by priority |
| `get_auto_executable_items(self)` | | `list[TestPlanItem]` | Get items that can be automated |

### TestMaintenanceWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__(self, project_root, index)` | `project_root: str, index: ProjectIndex | None = None` | | Initialize maintenance workflow |
| `run(self, context)` | `context: dict[str, Any]` | `dict[str, Any]` | Run maintenance workflow |
| `on_file_created(self, file_path)` | `file_path: str` | `dict[str, Any]` | Handle file creation |
| `on_file_modified(self, file_path)` | `file_path: str` | `dict[str, Any]` | Handle file modification |
| `on_file_deleted(self, file_path)` | `file_path: str` | `dict[str, Any]` | Handle file deletion |
| `get_files_needing_tests(self, limit)` | `limit: int = 20` | `list[dict[str, Any]]` | Get files requiring test coverage |
| `get_stale_tests(self, limit)` | `limit: int = 20` | `list[dict[str, Any]]` | Get outdated test files |
| `get_test_health_summary(self)` | | `dict[str, Any]` | Get overall test health status |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `run_tests_with_tracking(test_suite, test_files, command, workflow_id, triggered_by)` | `test_suite: str = 'unit', test_files: list[str] | None = None, command: str | None = None, workflow_id: str | None = None, triggered_by: str = 'manual'` | `TestExecutionRecord` | Run tests with explicit tracking for Tier 1 monitoring |
| `track_coverage(coverage_file, workflow_id)` | `coverage_file: str = 'coverage.xml', workflow_id: str | None = None` | `CoverageRecord` | Track test coverage from coverage.xml file |
| `track_file_tests(source_file, test_file, workflow_id)` | `source_file: str, test_file: str | None = None, workflow_id: str | None = None` | `FileTestRecord` | Track test execution for a specific source file |
| `get_file_test_status(file_path)` | `file_path: str` | `FileTestRecord | None` | Get latest test status for a file |
| `get_files_needing_tests(stale_only, failed_only)` | `stale_only: bool = False, failed_only: bool = False` | `list[FileTestRecord]` | Get files that need test attention |

### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `track_coverage()` | `FileNotFoundError` | `'Coverage file not found: {...}'` |
| `track_coverage()` | `ValueError` | `'Invalid coverage.xml format: {...}'` |
