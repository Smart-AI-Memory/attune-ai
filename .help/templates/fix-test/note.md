---
type: note
feature: fix-test
depth: note
generated_at: 2026-04-14T14:58:08.551287+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Note: fix test

## Context

The fix-test feature provides automated test lifecycle management through event-driven workflows. It tracks test coverage, identifies files needing test attention, and manages test maintenance plans with priority-based execution.

## Architecture

The feature combines three complementary modules:

**Test execution tracking** (`test_runner.py`) provides opt-in monitoring functions that record test results and coverage data for Tier 1 automation. Key functions include `run_tests_with_tracking()` for explicit test execution tracking and `track_coverage()` for parsing coverage.xml files.

**Test maintenance planning** (`test_maintenance.py`) defines the data structures for organizing test work. `TestMaintenancePlan` contains prioritized `TestPlanItem` instances that specify actions like creating new tests or updating existing ones. Each item includes metadata like estimated effort and auto-execution flags.

**Event-driven lifecycle management** (`test_lifecycle.py`) responds to file system changes through `TestLifecycleManager`. When source files are created, modified, or deleted, the manager queues appropriate `TestTask` instances. The workflow supports Git hooks for pre-commit and post-commit processing.

## Integration pattern

The modules work together through shared data types. Test execution functions accept workflow IDs that link results to specific maintenance plans. The lifecycle manager generates tasks that reference the same action and priority enums used in maintenance plans. This allows the system to automatically queue test work when files change and execute it according to configured priorities.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`
- `src/attune/workflows/test_lifecycle.py`

**Tags:** `tests`, `debugging`, `fixes`
