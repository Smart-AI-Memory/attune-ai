---
feature: fix-test
depth: task
generated_at: 2026-04-06T04:29:39.032965+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Work with fix test

Use fix test when you need to manage test lifecycle and execution tracking for your project.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/test_runner.py

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what fix test
   does today before making changes.
   The primary functions are:
   - `run_tests_with_tracking()` in `src/attune/workflows/test_runner.py` — Run tests with explicit tracking (opt-in for Tier 1 monitoring).
   - `track_coverage()` in `src/attune/workflows/test_runner.py` — Track test coverage from coverage.xml file (opt-in for Tier 1 monitoring).
   - `track_file_tests()` in `src/attune/workflows/test_runner.py` — Track test execution for a specific source file.
   - `get_file_test_status()` in `src/attune/workflows/test_runner.py` — Get the latest test status for a specific file.
   - `get_files_needing_tests()` in `src/attune/workflows/test_runner.py` — Get files that need test attention.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "fix-test"`.

## Key files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`
- `src/attune/workflows/test_lifecycle.py`

## Common modifications

Functions you are most likely to modify:

- `run_tests_with_tracking()` in `src/attune/workflows/test_runner.py`
- `track_coverage()` in `src/attune/workflows/test_runner.py`
- `track_file_tests()` in `src/attune/workflows/test_runner.py`
- `get_file_test_status()` in `src/attune/workflows/test_runner.py`
- `get_files_needing_tests()` in `src/attune/workflows/test_runner.py`
