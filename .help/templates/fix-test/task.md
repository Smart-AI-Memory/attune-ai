---
type: task
feature: fix-test
depth: task
generated_at: 2026-05-04T02:28:54.250565+00:00
source_hash: bff04fe2ad91cb5eb72a0a1c91eccca5bb1b81eba3549bb3ac7e694b3e7a98b8
status: generated
---

# Work with fix test

Use the fix-test system when you need to implement or modify automatic test diagnosis and repair capabilities in your project.

## Prerequisites

- Access to the project source code
- Understanding of test execution workflows
- Familiarity with the test lifecycle management system

## Understand the test lifecycle architecture

Start by examining how the test lifecycle system works:

1. Open `src/attune/workflows/test_lifecycle.py` to see the `TestLifecycleManager` class
2. Review the `TestTask` and `TestAction` dataclasses to understand the task queue structure
3. Check `src/attune/workflows/test_maintenance.py` for the `TestMaintenanceWorkflow` that handles automatic test management

The system uses event-driven test management where file changes trigger test tasks that get queued and processed automatically.

## Identify the target component

Determine which component needs modification based on your goal:

- **Test execution tracking**: Modify functions in `src/attune/workflows/test_runner.py`
- **Test lifecycle events**: Update `TestLifecycleManager` methods in `test_lifecycle.py`
- **Maintenance workflows**: Change `TestMaintenanceWorkflow` in `test_maintenance.py`

## Modify test execution functions

For changes to test running and tracking:

1. Locate the specific function in `test_runner.py`:
   - `run_tests_with_tracking()` for test execution with monitoring
   - `track_coverage()` for coverage analysis
   - `track_file_tests()` for file-specific test tracking
   - `get_file_test_status()` for retrieving test status
   - `get_files_needing_tests()` for identifying test gaps

2. Read the function's docstring and examine its parameters and return type
3. Study the existing error handling patterns and logging style
4. Implement your changes following the established conventions

## Update lifecycle management

For changes to the test lifecycle system:

1. Modify the appropriate method in `TestLifecycleManager`:
   - `on_file_created()`, `on_file_modified()`, or `on_file_deleted()` for file event handling
   - `process_queue()` for task execution
   - `schedule_maintenance()` or `run_maintenance()` for automated maintenance

2. Update the corresponding `TestTask` or `TestPlanItem` properties if needed
3. Ensure the task priority and action enums are used correctly

## Test your changes

Run the test suite to verify your modifications work correctly:

```bash
pytest -k "test_lifecycle" tests/
pytest -k "test_runner" tests/
```

Your changes should pass all existing tests without breaking the test lifecycle workflow.

## Success criteria

Your fix-test modifications are complete when:
- All targeted tests pass
- The test lifecycle manager processes tasks correctly
- Test execution tracking records data as expected
- No regressions appear in the existing test suite
