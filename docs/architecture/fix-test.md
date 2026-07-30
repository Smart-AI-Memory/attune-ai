# Fix Test

## Overview

Fix-test keeps a project's tests in step with its source. It turns
file-system events into a prioritized, partly auto-executable
maintenance plan, and it records what actually ran so the next plan
can reason about staleness and coverage gaps.

Two modules cooperate:

- **`test_maintenance`** owns planning. `TestMaintenanceWorkflow`
  inspects file events and produces a `TestMaintenancePlan` — an
  ordered set of `TestPlanItem` entries, each describing one piece of
  test work (which file, what `TestAction`, at what `TestPriority`).
- **`test_runner`** owns measurement. Standalone functions
  (`run_tests_with_tracking`, `track_coverage`, `track_file_tests`)
  execute tests and persist the results as telemetry records, and
  query functions (`get_file_test_status`, `get_files_needing_tests`)
  read those records back.

Fix-test is **not** a test *generator* — it decides *what* test work a
change implies and *whether* it can run unattended. It is reached as
the `/fix-test` skill; there is no dedicated `attune` CLI subcommand.
This page documents the Python API you call directly when wiring test
maintenance into a hook, a CI step, or a custom tool.

## Concepts

### From a file event to a plan

`TestMaintenanceWorkflow` is the coordinator. Construct it with a
project root, then drive it one of two ways:

1. **Event handlers** — `on_file_created`, `on_file_modified`, and
   `on_file_deleted` each take a single `file_path` and return a dict
   describing the test work that change implies. These are the
   integration point for a file-watcher or a git hook.
2. **`run(context)`** — generates a whole-project `TestMaintenancePlan`
   in one of four modes (`analyze`, `execute`, `auto`, `report`).

Both paths lean on the same building blocks:

| Type | What it represents |
|------|--------------------|
| `TestPlanItem` | One unit of test work: `file_path`, the `action` (`TestAction`), the `priority` (`TestPriority`), a `reason`, an optional `test_file_path`, an `estimated_effort` string, an `auto_executable` flag, and a free-form `metadata` dict. |
| `TestMaintenancePlan` | The assembled plan: `generated_at`, the list of `items`, a `summary` dict, and `options`. Filter it with `get_items_by_action`, `get_items_by_priority`, or `get_auto_executable_items`. |
| `TestAction` | What to do with a test — one of `CREATE`, `UPDATE`, `REVIEW`, `DELETE`, `SKIP`, `MANUAL`. |
| `TestPriority` | How urgent — one of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `DEFERRED`. |

### The two modules fit together

- **Planning (`test_maintenance`)** answers *"given this change, what
  test work is needed and how urgent is it?"* It is index-backed: the
  workflow holds a `ProjectIndex` and refreshes it when files change,
  so impact and staleness drive the priorities it assigns.
- **Measurement (`test_runner`)** answers *"what did the tests actually
  do?"* Its functions run pytest (or a custom command), parse the
  results, and write `TestExecutionRecord`, `CoverageRecord`, and
  `FileTestRecord` entries into the telemetry store. The query
  functions then surface "is this file covered?" and "what still needs
  tests?" — the same signals the workflow's `get_stale_tests` and
  `get_test_health_summary` summarize.

### Async vs sync — the one thing to get right

The workflow's *event and run* surface is asynchronous; everything
else is a plain function call:

- **`async`** — `run`, `on_file_created`, `on_file_modified`,
  `on_file_deleted`. `await` them (or drive with `asyncio.run`).
- **sync** — the plan-filter methods (`get_items_by_action`, …), the
  workflow's summary methods (`get_files_needing_tests`,
  `get_stale_tests`, `get_test_health_summary`), and **every**
  `test_runner` function.

### Two functions named `get_files_needing_tests`

Mind the namespace: there is a module-level
`test_runner.get_files_needing_tests(stale_only=False,
failed_only=False)` that reads telemetry records, **and** a
`TestMaintenanceWorkflow.get_files_needing_tests(limit=20)` method that
reads the project index. They are different functions with different
signatures and return types — import or call the one you mean.

## Design & extension

### Design decisions

- **Planning is separated from measurement.** `test_maintenance`
  decides what test work is needed; `test_runner` records what tests
  did. Keeping them apart lets a hook plan without running tests, and
  lets a CI step record results without planning — each side is useful
  alone, and they compose when you want the full loop.
- **Plans are data, results are records.** A `TestMaintenancePlan`
  serializes via `to_dict`, and the `test_runner` functions return
  dataclass records (`TestExecutionRecord`, `CoverageRecord`,
  `FileTestRecord`) persisted to the telemetry store. Both sides hand
  back inspectable values rather than printing — callers own
  presentation.
- **`auto_executable` is a per-item flag, not a global mode.** Whether
  an item may run unattended is decided when the `TestPlanItem` is
  built, so a single plan can mix auto-runnable work with items that
  require human `REVIEW` or `MANUAL` attention. `"auto"` mode simply
  filters on the flag.

### Extension points

- **Wire fix-test into a file-watcher or git hook:** call the
  `on_file_created` / `on_file_modified` / `on_file_deleted`
  coroutines with the changed path and act on the returned status
  dict.
- **Add a maintenance step to CI:** `await workflow.run({"mode":
  "auto"})` to execute the safe subset, or `{"mode": "report"}` for a
  health summary you can gate on.
- **Feed measurement back into planning:** record runs with
  `run_tests_with_tracking` / `track_coverage`, then let the workflow's
  `get_stale_tests` and `get_test_health_summary` surface the gaps the
  recorded telemetry exposes.

<!-- attune-generated: source_hash=56383ae48a3d6c0dcdadb645912bf30697dbdd296c66e69e3c40100a6c12ab69 feature=fix-test kind=architecture generated_at=2026-07-30 -->
