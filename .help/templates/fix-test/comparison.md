---
type: comparison
name: fix-test-comparison
feature: fix-test
depth: comparison
generated_at: 2026-06-22T11:30:53.046085+00:00
source_hash: 2a68f682c715ddba2510a8395022ba9b502452e2fce1c7a1d13419ce2a2f0f1b
status: generated
---

# Auto-diagnose test gaps from file changes and track test outcomes

## Comparison

Fix-test gives you two ways to engage tests: let
`TestMaintenanceWorkflow` *plan* the work from file changes, or call
the `test_runner` functions to *measure* tests directly. They answer
different questions and often pair.

| Capability | `TestMaintenanceWorkflow` (planning) | `test_runner` functions (measurement) |
|---|---|---|
| **Question answered** | "What test work does this change imply?" | "What did the tests actually do?" |
| **Import** | `from attune.workflows import TestMaintenanceWorkflow` | `from attune.workflows.test_runner import run_tests_with_tracking` |
| **Input** | File events / project index | A suite name, file list, or `coverage.xml` |
| **Output** | A `TestMaintenancePlan` of `TestPlanItem`s | `TestExecutionRecord` / `CoverageRecord` / `FileTestRecord` |
| **Concurrency** | Async (`run`, `on_file_*`); sync summary methods | Synchronous functions |
| **Runs tests?** | Only in `"execute"` / `"auto"` mode | `run_tests_with_tracking` / `track_file_tests` do |
| **State** | Index-backed; refreshes on change | Persists records to the telemetry store |
| **Typical caller** | File-watcher, git hook, CI maintenance step | Test runner wrapper, coverage pipeline |

**Use the workflow** when you want decisions — which files need tests,
how urgent, what is safe to auto-run. **Use the `test_runner`
functions** when you want facts — run a suite, capture coverage, look
up a file's status. A common loop is both: run tests with tracking,
then let the workflow plan from the recorded staleness and gaps.
