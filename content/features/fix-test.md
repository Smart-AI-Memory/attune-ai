---
feature: fix-test
summary: Auto-diagnose test gaps from file changes and track test outcomes
tags: [tests, debugging, fixes]
source_globs:
  - src/attune/workflows/test_maintenance.py
  - src/attune/workflows/test_runner.py
  - src/attune/models/telemetry/data_models.py
nav:
  help: fix-test
  mkdocs:
    how-to: how-to/fix-test
    architecture: architecture/fix-test
    reference: reference/fix-test
---

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

## Quickstart

**Fastest path — `/fix-test` in Claude Code.** For an interactive
fix, run `/fix-test <test file or pattern>` in a Claude Code
session — it scopes the target, classifies the root cause, applies
a fix, and re-runs (up to 3 attempts) before reporting. The full
walkthrough, including wiring a tests-on-edit hook so failures are
caught and fixed the moment an edit creates them, is the tutorial
at `docs/tutorials/fix-test.md`.

For the Python API, generate a maintenance plan for the whole project.
`TestMaintenanceWorkflow.run` is an async coroutine, so drive it with
`asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import TestMaintenanceWorkflow


async def main() -> None:
    workflow = TestMaintenanceWorkflow(project_root=".")
    result = await workflow.run({"mode": "analyze"})
    print(result["status"])               # "plan_generated"
    print(result["message"])              # "Generated plan with N items"
    for item in result["plan"]["items"]:
        print(item["priority"], item["action"], item["file_path"])


asyncio.run(main())
```

`run` returns a plain dict (the plan is `result["plan"]`, already
serialized via `TestMaintenancePlan.to_dict`). The `"analyze"` mode
only *plans* — it never writes tests. Use `"auto"` to execute the
items flagged `auto_executable`, or `"report"` for a health summary.

## Tasks

### React to a single file change

**Goal:** translate one file event into the test work it implies —
the hook into a file-watcher or git hook.

**Steps:**

```python
import asyncio

from attune.workflows import TestMaintenanceWorkflow


async def main() -> None:
    workflow = TestMaintenanceWorkflow(project_root=".")

    created = await workflow.on_file_created("src/attune/new_module.py")
    print(created["status"])      # e.g. "needs_tests" or "no_tests_required"

    modified = await workflow.on_file_modified("src/attune/config.py")
    print(modified["status"])     # e.g. "tests_may_need_update"

    deleted = await workflow.on_file_deleted("src/attune/old_module.py")
    print(deleted["status"])      # e.g. "orphaned_tests" or "file_removed"


asyncio.run(main())
```

**Verify:** each handler is a coroutine — `await` it. Each returns a
dict whose `status` names the outcome and (when relevant) carries a
`plan_item` built from a `TestPlanItem`. A created file that requires
tests reports `"needs_tests"`; a deleted file whose test file still
exists reports `"orphaned_tests"`.

### Auto-execute only the safe items

**Goal:** run the test work that is safe to run unattended, and leave
higher-touch items for a human.

**Steps:**

```python
import asyncio

from attune.workflows import TestMaintenanceWorkflow


async def main() -> None:
    workflow = TestMaintenanceWorkflow(project_root=".")

    # Preview first — dry_run plans without executing.
    preview = await workflow.run({"mode": "auto", "dry_run": True})
    print(preview["message"])     # "Would auto-execute N items"

    # Then execute the auto_executable subset.
    result = await workflow.run({"mode": "auto"})
    print(result["status"])       # "auto_executed"
    print(result["execution"])    # per-item execution outcomes


asyncio.run(main())
```

**Verify:** `"auto"` mode executes only the items
`TestMaintenancePlan.get_auto_executable_items` returns (those with
`auto_executable=True`). `dry_run=True` reports the count without
executing. Items needing `REVIEW` or `MANUAL` are never auto-run.

### Track a test run and read coverage back

**Goal:** record a suite execution and its coverage so the workflow
can reason about gaps later.

**Steps:**

```python
from attune.workflows.test_runner import (
    run_tests_with_tracking,
    track_coverage,
    get_file_test_status,
)

# Run a suite and persist a TestExecutionRecord.
execution = run_tests_with_tracking(
    test_suite="unit",
    test_files=["tests/unit/test_config.py"],
    triggered_by="manual",
)
print(execution.success, execution.passed, execution.failed)

# Parse an existing coverage.xml into a CoverageRecord.
coverage = track_coverage("coverage.xml")
print(f"{coverage.overall_percentage:.1f}%")

# Read the latest status for one file.
status = get_file_test_status("src/attune/config.py")
print(status)                     # FileTestRecord | None
```

**Verify:** these are plain (synchronous) functions — no `await`.
`run_tests_with_tracking` returns a `TestExecutionRecord` (`success`,
`passed`, `failed`); `track_coverage` returns a `CoverageRecord` and
raises `FileNotFoundError` if `coverage.xml` is missing or `ValueError`
if it is malformed; `get_file_test_status` returns the latest
`FileTestRecord` for a file, or `None` if nothing was recorded.

## Reference

Fix-test's public API spans two workflow modules. The record types
(`TestExecutionRecord`, `CoverageRecord`, `FileTestRecord`) come from
`attune.models`.

### Planning — `attune.workflows.test_maintenance`

| Symbol | Purpose |
|--------|---------|
| `TestMaintenanceWorkflow(project_root, index=None)` | Coordinator. Builds (or accepts) a `ProjectIndex` and ensures it is loaded. |
| `TestMaintenanceWorkflow.run(context)` | **Async.** Generate (and optionally execute) a plan. `context["mode"]` is `"analyze"` / `"execute"` / `"auto"` / `"report"`; other keys: `changed_files`, `max_items` (default 20), `dry_run` (default `False`). Returns a result dict. |
| `TestMaintenanceWorkflow.on_file_created(file_path)` | **Async.** Plan test work for a new file; returns a status dict. |
| `TestMaintenanceWorkflow.on_file_modified(file_path)` | **Async.** Mark a changed file's tests as possibly stale; returns a status dict. |
| `TestMaintenanceWorkflow.on_file_deleted(file_path)` | **Async.** Flag a deleted file's tests as possibly orphaned; returns a status dict. |
| `TestMaintenanceWorkflow.get_files_needing_tests(limit=20)` | Top-`limit` files needing tests, by impact, as dicts. |
| `TestMaintenanceWorkflow.get_stale_tests(limit=20)` | Top-`limit` files with stale tests, by staleness, as dicts. |
| `TestMaintenanceWorkflow.get_test_health_summary()` | Quick counts: files requiring/with/without tests, average coverage, stale count, test-to-code ratio. |
| `TestMaintenancePlan.get_items_by_action(action)` | Plan items filtered by a `TestAction`. |
| `TestMaintenancePlan.get_items_by_priority(priority)` | Plan items filtered by a `TestPriority`. |
| `TestMaintenancePlan.get_auto_executable_items()` | Plan items with `auto_executable=True`. |
| `TestAction` | Enum: `CREATE`, `UPDATE`, `REVIEW`, `DELETE`, `SKIP`, `MANUAL`. |
| `TestPriority` | Enum: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `DEFERRED`. |

### Measurement — `attune.workflows.test_runner`

| Symbol | Purpose |
|--------|---------|
| `run_tests_with_tracking(test_suite="unit", test_files=None, command=None, workflow_id=None, triggered_by="manual")` | Run a suite and persist a `TestExecutionRecord`. |
| `track_coverage(coverage_file="coverage.xml", workflow_id=None)` | Parse a coverage XML file into a `CoverageRecord`. Raises `FileNotFoundError` / `ValueError`. |
| `track_file_tests(source_file, test_file=None, workflow_id=None)` | Run a single file's tests and persist a `FileTestRecord`. |
| `get_file_test_status(file_path)` | Latest `FileTestRecord` for a file, or `None`. |
| `get_files_needing_tests(stale_only=False, failed_only=False)` | `FileTestRecord` list for files needing attention (telemetry-backed; **not** the workflow method of the same name). |

### TestPlanItem fields

| Field | Type | Meaning |
|-------|------|---------|
| `file_path` | `str` | The source file this item concerns. |
| `action` | `TestAction` | What to do with the test. |
| `priority` | `TestPriority` | How urgent. |
| `reason` | `str` | Why this item exists. |
| `test_file_path` | `str \| None` | The associated test file, if known. |
| `estimated_effort` | `str` | Effort hint (default `"unknown"`). |
| `auto_executable` | `bool` | Whether `"auto"` mode may run it (default `True`). |
| `metadata` | `dict` | Free-form extra context. |

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

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeError: coroutine ... was never awaited` | `run` / `on_file_*` called without `await` | These are coroutines — `await` them or use `asyncio.run` | high |
| `FileNotFoundError: Coverage file not found` | `track_coverage` given a missing path | Generate `coverage.xml` first (e.g. `pytest --cov --cov-report=xml`) | high |
| `ValueError: Invalid coverage.xml format` | `track_coverage` given a malformed/empty XML | Regenerate the report; confirm the run finished | medium |
| Plan comes back with zero items | No tracked changes / index reports nothing needing work | Pass `changed_files`, or confirm the `ProjectIndex` is populated | medium |
| `"auto"` mode executes nothing | No plan item has `auto_executable=True` | Inspect `get_auto_executable_items()`; `REVIEW`/`MANUAL` items never auto-run | medium |
| Calling the wrong `get_files_needing_tests` | Two functions share the name (module fn vs workflow method) | Import the module function or call the method explicitly; their signatures differ | medium |
| `get_file_test_status` returns `None` | No `FileTestRecord` was ever recorded for that file | Run `track_file_tests` or `run_tests_with_tracking` first | low |

### Risk areas

- **The async/sync split is easy to get wrong.** Only `run` and the
  three `on_file_*` handlers are coroutines; the summary methods and
  every `test_runner` function are plain calls. Awaiting a sync
  function (or forgetting to await a coroutine) is the most common
  fix-test bug.
- **`auto_executable` defaults to `True`.** A `TestPlanItem` is
  auto-runnable unless something sets the flag to `False`. Before
  trusting `"auto"` mode in CI, inspect the plan and confirm the
  auto-executable subset is what you expect.
- **Planning is only as current as the index.** The workflow refreshes
  its `ProjectIndex` when you pass `changed_files`, but a stale index
  yields stale priorities. Pass the files that changed, or refresh
  before planning.

### Diagnosis order

1. Reproduce with a minimal `await workflow.run({"mode": "analyze"})`
   — inspect `result["status"]` and `result["plan"]["items"]`.
2. If a handler misbehaves, call it directly
   (`await workflow.on_file_modified(path)`) and read the returned
   `status`.
3. For measurement issues, call the `test_runner` function in
   isolation and inspect the returned record (or the raised
   `FileNotFoundError` / `ValueError`).
4. Confirm the index: `workflow.get_test_health_summary()` should
   report sane counts.
5. Run the related tests: `pytest -k "test_maintenance or test_runner" -v`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md
> D6). This section is **not** projected verbatim as the FAQ; it
> contributes the feature's author-curated seed questions. Keep entries
> to genuine, feature-specific seeds.

- **Q:** Does fix-test write tests for me?
  **A:** No. It decides *what* test work a change implies and *whether*
  it is safe to run automatically. Generating test code is the
  smart-test feature's job.
- **Q:** Is there an `attune fix-test` command?
  **A:** No dedicated CLI subcommand — fix-test is reached as the
  `/fix-test` skill, and the planning/measurement logic is the Python
  API on this page (`TestMaintenanceWorkflow` and the `test_runner`
  functions).
- **Q:** What's the entry point?
  **A:** `await TestMaintenanceWorkflow(project_root).run({"mode":
  "analyze"})` for a whole-project plan, or the `on_file_*` handlers
  for a single file event.
- **Q:** Which calls are async?
  **A:** `run` and the three `on_file_*` handlers. The summary methods
  and all `test_runner` functions are synchronous.
- **Q:** How do I run only the safe items?
  **A:** `await workflow.run({"mode": "auto"})` — it executes the
  `auto_executable` subset and leaves `REVIEW` / `MANUAL` items for a
  human. Add `"dry_run": True` to preview the count first.

## Notes & tips

- **Depend on the documented public surface.**
  `test_maintenance` gives you `TestMaintenanceWorkflow`,
  `TestMaintenancePlan`, `TestPlanItem`, `TestAction`, and
  `TestPriority`. `test_runner` gives you `run_tests_with_tracking`,
  `track_coverage`, `track_file_tests`, `get_file_test_status`, and
  `get_files_needing_tests`. Names with a leading underscore are
  internal and may change.
- **Preview with `dry_run` before executing.** Both `"execute"` and
  `"auto"` modes accept `dry_run=True`, which reports what *would* run
  without touching anything — the cheapest way to sanity-check a plan.
- **Pass `changed_files` for event-driven runs.** Supplying the files
  that changed refreshes the index and focuses the plan, instead of
  re-evaluating the whole project.

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
