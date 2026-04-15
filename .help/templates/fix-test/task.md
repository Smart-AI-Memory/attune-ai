---
type: task
feature: fix-test
depth: task
generated_at: 2026-04-14T14:56:04.844517+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Work with fix test

Use the fix-test feature when you need to automatically diagnose failing tests and apply lifecycle management to maintain test health across your project.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/workflows/test_runner.py`

## Steps

1. **Identify the failing tests.**
   Use `get_files_needing_tests()` to find files requiring test attention:
   ```python
   from attune.workflows.test_runner import get_files_needing_tests

   # Get all files needing tests
   files_needing_attention = get_files_needing_tests()

   # Get only files with stale tests
   stale_files = get_files_needing_tests(stale_only=True)

   # Get only files with failed tests
   failed_files = get_files_needing_tests(failed_only=True)
   ```

2. **Check individual file test status.**
   Use `get_file_test_status()` to examine specific files:
   ```python
   from attune.workflows.test_runner import get_file_test_status

   status = get_file_test_status('src/my_module.py')
   if status:
       print(f"Last test result: {status}")
   ```

3. **Run tests with tracking enabled.**
   Execute tests while capturing detailed execution data:
   ```python
   from attune.workflows.test_runner import run_tests_with_tracking

   # Run specific test suite
   result = run_tests_with_tracking(
       test_suite='unit',
       test_files=['tests/test_my_module.py'],
       triggered_by='fix-test-workflow'
   )
   ```

4. **Set up automated test lifecycle management.**
   Initialize the TestLifecycleManager to handle file changes:
   ```python
   from attune.workflows.test_lifecycle import TestLifecycleManager

   manager = TestLifecycleManager(
       project_root='/path/to/project',
       auto_execute=True
   )

   # Process changed files
   tasks = manager.on_files_changed(['src/modified_file.py'])
   ```

5. **Process the test maintenance queue.**
   Execute queued test tasks based on priority:
   ```python
   # Process high-priority tasks first
   result = manager.process_queue(
       max_tasks=5,
       priority_filter=TestPriority.HIGH
   )
   print(f"Processed {result['completed']} tasks")
   ```

## Verify success

Your fix-test implementation works correctly when:

- `get_files_needing_tests()` returns an empty list or only expected files
- Test execution records show passing status in the tracking system
- The TestLifecycleManager processes file changes without errors
- Coverage tracking updates successfully after test runs

## Key files

- `src/attune/workflows/test_runner.py` - Core test execution and tracking
- `src/attune/workflows/test_maintenance.py` - Test maintenance planning
- `src/attune/workflows/test_lifecycle.py` - Automated test lifecycle management

## Primary functions

- `run_tests_with_tracking()` - Execute tests with monitoring enabled
- `track_coverage()` - Record coverage data from coverage.xml
- `track_file_tests()` - Link source files to their test executions
- `get_file_test_status()` - Retrieve current test status for a file
- `get_files_needing_tests()` - Find files requiring test attention
