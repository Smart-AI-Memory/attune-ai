---
type: comparison
name: fix-test-comparison
feature: fix-test
depth: comparison
generated_at: 2026-07-30T21:39:00.970482+00:00
source_hash: 56383ae48a3d6c0dcdadb645912bf30697dbdd296c66e69e3c40100a6c12ab69
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
