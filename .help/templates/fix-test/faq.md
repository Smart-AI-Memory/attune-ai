---
type: faq
feature: fix-test
depth: faq
generated_at: 2026-04-14T14:57:37.506391+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Fix Test FAQ

## What is the fix-test feature?

The fix-test feature provides automated test lifecycle management for your project. It tracks test execution, monitors coverage, and creates maintenance plans to keep your tests healthy and up-to-date with your code changes.

## When should I use fix-test?

Use fix-test when you need to:
- Automatically track which files need tests
- Monitor test coverage and execution
- Get maintenance plans for stale or missing tests
- Respond to file changes with appropriate test actions
- Schedule regular test health checks

## What are the main functions I should know about?

Start with these functions based on what you want to do:

- `run_tests_with_tracking()` — Run your test suite while tracking execution for Tier 1 monitoring
- `track_coverage()` — Import coverage data from a coverage.xml file
- `track_file_tests()` — Track test status for a specific source file
- `get_files_needing_tests()` — Find files that need new tests or have stale tests

## How do I create a test maintenance plan?

Use the `TestMaintenanceWorkflow` class. It analyzes your project and generates a `TestMaintenancePlan` with specific actions, priorities, and effort estimates for each file that needs attention.

## How do I respond to file changes automatically?

The `TestLifecycleManager` handles file events for you. It creates `TestTask` objects when files are created, modified, or deleted, then queues them for processing based on priority.

## What happens when I run `track_coverage()`?

The function reads your coverage.xml file and creates a `CoverageRecord`. If the file doesn't exist, you'll get a `FileNotFoundError`. If the XML format is invalid, you'll get a `ValueError` with details about what went wrong.

## How do I debug test tracking issues?

First, run `pytest -k "fix-test" -v` to check if the feature's own tests pass. If they do but you're still having problems, add debug logging at the point where things go wrong and re-run with logging enabled.

## Where are the source files?

The fix-test feature spans three files:
- `src/attune/workflows/test_runner.py` — Test execution and coverage tracking
- `src/attune/workflows/test_maintenance.py` — Maintenance workflow and planning
- `src/attune/workflows/test_lifecycle.py` — Event-driven test lifecycle management

**Tags:** `tests`, `debugging`, `fixes`
