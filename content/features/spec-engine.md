---
feature: spec-engine
summary: Spec-driven development with approval loops
tags: [spec, planning]
source_globs: [src/attune/spec/**, src/attune/pipeline/**]
nav:
  help: spec-engine
  mkdocs:
    how-to: how-to/spec-engine
    tutorial: tutorials/spec-engine
    architecture: architecture/spec-engine
    reference: reference/spec-engine
---

## Overview

The spec engine turns a plan file — an XML task list stored in
`.claude/plans/` — into executed, gate-checked code. It owns two
distinct concerns: running the pipeline (`pipeline.*`) and managing
interactive, approval-gated execution with persistent state
(`spec.*`).

It is **not** responsible for authoring plan files, running the
Socratic brainstorm / decompose / review phases, or displaying output
in the Claude Code UI — those belong to the skill layer above it.

The engine matters whenever you need to understand why a run stopped,
how to resume it, or how quality-gate outcomes map to the `severity`
and `gate_score` fields on a `TaskResult`. If you are writing code
that hooks into execution — an `on_task_complete` callback or a custom
presenter — these are the types and functions you work with directly.

## Concepts

A spec plan is an XML file under `.claude/plans/`. When you trigger
execution, the engine works through four concerns in sequence:

1. **Reading** — `read_spec(plan_path)` parses the plan file and
   returns a list of `DecomposedTask` objects.
2. **Orchestrating** — `PipelineOrchestrator` iterates those tasks,
   calls quality gates after each via `run_gates_for_task`, and
   collects results into a `PipelineResult`.
3. **Gating** — each task produces a `TaskResult` with fields like
   `quality_gate_passed`, `tests_passed`, `gate_score`, and the
   `severity` property. The orchestrator uses these to decide whether
   to continue, pause for approval, or surface an error.
4. **State tracking** — `SpecState` records which task IDs are
   `completed` and which is `current`. `save_state` writes this back
   into an HTML comment inside the plan file itself, so the file is
   the single source of truth. `get_pending_tasks` filters the full
   task list down to whatever hasn't finished, enabling resumption
   mid-run.

### Core data structures

| Type | What it represents |
|------|--------------------|
| `TaskResult` | The outcome of one task: whether it executed, whether `quality_gate_passed` and `tests_passed` are satisfied, the `gate_score` (float), and any `error` string. The `severity` property classifies the gate result for display. |
| `PipelineResult` | The rolled-up outcome across all tasks: `spec_path`, every `TaskResult` in `tasks`, `total_cost`, `duration_ms`, and `success` (true only when all tasks executed and passed gates). |
| `SpecState` | Durable progress record: `plan_path`, the list of `completed` task IDs, the `current` task ID, and an `auto_run` flag that controls whether the engine prompts for approval between tasks. |

### How the two packages fit together

The engine spans two packages, each with a distinct role:

- **`pipeline`** owns execution. `PipelineOrchestrator` reads an XML
  plan file, runs tasks one at a time, and evaluates quality gates
  after each. `read_spec()` parses a plan file into `DecomposedTask`
  objects. `TaskResult` and `PipelineResult` carry the outcome data.
- **`spec`** owns state and presentation. `SpecState` tracks progress;
  `load_state` / `save_state` / `clear_state` manage the embedded
  state comment; the presenter functions render engine output for
  display; and `execute_with_approval` (in `spec.runner`) wraps the
  orchestrator with a per-task approval loop.

### State lifecycle

```text
load_state(plan_path)             # returns SpecState | None
    │
    ▼
get_pending_tasks(tasks, state)   # filters out completed IDs
    │
    ▼
[execute tasks, update state.completed after each]
    │
    ├─ save_state(state)          # persists progress into the plan file
    │
    └─ clear_state(plan_path)     # removes state when the run finishes
```

`find_resumable_plans(plans_dir)` scans `.claude/plans/` (the default)
for any plan file that still carries a `SpecState` comment, giving you
a list of interrupted runs you can pick back up.

## Quickstart

Run a spec plan end-to-end with quality gates in a single Python call:

```python
from attune.pipeline import PipelineOrchestrator, PipelineResult

orchestrator = PipelineOrchestrator(".claude/plans/my-feature.md")
result: PipelineResult = orchestrator.run_all()

print(result.summary)   # human-readable run summary
print(result.success)   # True if all tasks executed and passed gates
```

`summary` and `success` are properties — read them, don't call them.
Running this produces a `PipelineResult` with per-task outcomes, total
cost, and duration.

To skip quality gates during a quick smoke test, pass
`skip_gates=True` to the constructor.

## Tasks

### Run a plan programmatically with progress output

**Goal:** read a plan, run every task through quality gates, print a
progress bar after each task, and exit non-zero if any gate failed.

**Steps:**

```python
from attune.pipeline import (
    PipelineOrchestrator,
    PipelineResult,
    TaskResult,
    read_spec,
)
from attune.spec import present_tasks, present_task_result, format_progress_bar, load_state

PLAN_PATH = ".claude/plans/my-feature.md"

tasks = read_spec(PLAN_PATH)
state = load_state(PLAN_PATH)          # None if no prior run exists
print(present_tasks(tasks, state))     # inspect the plan before running

completed_count = 0

def on_task_complete(task, task_result: TaskResult) -> None:
    global completed_count
    completed_count += 1
    print(format_progress_bar(completed_count, len(tasks)))
    print(present_task_result(task, task_result))

orchestrator = PipelineOrchestrator(PLAN_PATH)
result: PipelineResult = orchestrator.run_all(on_task_complete=on_task_complete)

print(result.summary)

if not result.success:
    raise SystemExit(1)
```

**Verify:** a fully passing run prints the summary and exits `0`. The
separation between reading (`read_spec`, `present_tasks`) and running
(`run_all`) is intentional — you can inspect the full plan before
committing to a run.

### Resume an interrupted run

**Goal:** find plans that didn't finish and continue them from where
they stopped.

**Steps:**

```python
from attune.pipeline import PipelineOrchestrator, read_spec
from attune.spec import get_pending_tasks, find_resumable_plans

resumable = find_resumable_plans(".claude/plans")

for spec_state in resumable:
    tasks = read_spec(spec_state.plan_path)
    pending = get_pending_tasks(tasks, spec_state)
    if not pending:
        continue
    completed_ids = set(spec_state.completed)
    orchestrator = PipelineOrchestrator(spec_state.plan_path)
    result = orchestrator.run_all(skip_task_ids=completed_ids)
    print(result.summary)
```

**Verify:** `get_pending_tasks` returns only the tasks whose IDs are
not in `SpecState.completed`. Passing those IDs as `skip_task_ids`
prevents re-running completed work.

### Run with per-task approval

**Goal:** pause after each task for human sign-off instead of running
the whole plan unattended.

**Steps:**

```python
import asyncio
from attune.spec.runner import execute_with_approval

async def main():
    result = await execute_with_approval(
        ".claude/plans/my-feature.md",
        on_task_complete,
        skip_gates=False,
        skip_tests=False,
        skip_simplify=False,
    )
    print(result.summary)

asyncio.run(main())
```

`execute_with_approval` is an async coroutine — `await` it (or drive
it with `asyncio.run`). It accepts the same `skip_gates`,
`skip_tests`, and `skip_simplify` flags as `PipelineOrchestrator`, and
returns the same `PipelineResult`. Flip `SpecState.auto_run = True` to
skip the per-task pause for the rest of the run.

**Verify:** the loop pauses after each task. An interrupted approval
run leaves a resumable `SpecState` in the plan file.

### Re-run a subset of tasks without restarting

**Goal:** re-run specific tasks without clearing state and reprocessing
the whole plan.

**Steps:** pass a `set[str]` of already-completed task IDs to
`run_all(skip_task_ids=...)`:

```python
result = orchestrator.run_all(skip_task_ids={"task-1", "task-2"})
```

**Verify:** skipping completed tasks preserves `SpecState.completed`
and keeps `total_cost` and `duration_ms` accurate in the final
`PipelineResult`. You are responsible for knowing which IDs to skip —
if a skipped task produced an artifact a later task depends on, check
`TaskResult.quality_gate_passed` and `gate_score` on the result before
assuming success.

## Reference

The spec engine exposes its public API through two packages:
`attune.pipeline` (execution) and `attune.spec` (state and
presentation). `execute_with_approval` lives in `attune.spec.runner`.

### Pipeline execution

| Symbol | Purpose |
|--------|---------|
| `PipelineOrchestrator(spec_path, *, skip_gates=False, skip_tests=False, skip_simplify=False)` | Load a plan file and prepare tasks for execution with optional gate overrides. |
| `PipelineOrchestrator.run_all(*, on_task_complete=None, skip_task_ids=None)` | Execute all tasks, firing an optional callback after each; returns a `PipelineResult`. |
| `PipelineOrchestrator.run_gates_for_task(task)` | Run quality gates for a single `DecomposedTask` and return a `TaskResult`. |
| `read_spec(plan_path)` | Parse a plan file and extract its XML task blocks into `DecomposedTask` objects. Raises `FileNotFoundError` (missing file) or `ValueError` (empty path). |
| `execute_with_approval(spec_path, on_task_complete, *, skip_gates=False, skip_tests=False, skip_simplify=False)` | **Async.** Execute a spec with an interactive per-task approval loop. Import from `attune.spec.runner`. |

### State management

| Symbol | Purpose |
|--------|---------|
| `load_state(plan_path)` | Read a `SpecState` from the HTML comment embedded in a plan file; returns `None` if no state exists. |
| `save_state(state)` | Write or update the spec-state comment in a plan file. |
| `clear_state(plan_path)` | Remove the spec-state comment from a plan file. |
| `find_resumable_plans(plans_dir='.claude/plans')` | Return all `SpecState` objects whose plans have incomplete execution. |
| `get_pending_tasks(tasks, state)` | Filter a task list to those whose IDs are not in `state.completed`. |

### Presentation

| Symbol | Purpose |
|--------|---------|
| `present_tasks(tasks, state)` | Format a task list as a markdown table, optionally annotated with completion state. |
| `present_task_detail(task)` | Format a single task with its full acceptance criteria and metadata. |
| `present_task_result(task, gate_result)` | Format execution output including quality-gate status and score. |
| `format_progress_bar(completed, total)` | Render a visual progress indicator for a running pipeline. |

### Result fields

`TaskResult` fields you'll inspect most often:

| Field | Type | Meaning |
|-------|------|---------|
| `quality_gate_passed` | `bool \| None` | Gate outcome; `None` when gates were skipped. |
| `tests_passed` | `bool \| None` | Test outcome; `None` when tests were skipped. |
| `gate_score` | `float \| None` | Numeric quality score from the gate. |
| `severity` | `str` (property) | Classified severity of the gate result. |
| `error` | `str \| None` | Error message if the task failed to execute. |
| `cost` | `float` | Cost attributed to this task. |

`PipelineResult` top-level members:

| Member | Type | Meaning |
|--------|------|---------|
| `success` | `bool` (property) | `True` only when all tasks executed and passed gates. |
| `summary` | `str` (property) | Human-readable run summary. |
| `tasks` | `list[TaskResult]` | Per-task outcomes. |
| `total_cost` | `float` | Aggregated cost across all tasks. |
| `duration_ms` | `int` | Wall-clock time for the full run. |

### Example output

An approval run prints a progress bar, per-task gate results, and a
final summary:

```text
[========--] 4/5 tasks

✔ task-1  add-jwt-config          gate: passed  score: 92.0  cost: $0.003
✔ task-2  token-service           gate: passed  score: 87.5  cost: $0.004
✔ task-3  auth-middleware         gate: passed  score: 81.0  cost: $0.005
✔ task-4  wire-routes             gate: passed  score: 78.3  cost: $0.004
  task-5  integration-tests       pending

Pipeline complete: 4/5 tasks executed  total_cost: $0.016  duration: 18402ms
```

## Comparison

The engine exposes two layers for running spec-driven workflows: a
high-level interactive layer (`spec.runner.execute_with_approval`) and
a low-level pipeline layer (`PipelineOrchestrator`). Both execute the
same tasks with the same quality gates, but differ in who controls the
approval loop and how much state they manage for you.

| Capability | `spec` layer (`execute_with_approval`) | `pipeline` layer (`PipelineOrchestrator`) |
|---|---|---|
| **Import path** | `from attune.spec.runner import execute_with_approval` | `from attune.pipeline import PipelineOrchestrator` |
| **Approval loop** | Per-task, interactive — pauses after each task | Batch — runs all tasks unless you pass `skip_task_ids` |
| **Resume support** | Yes — `load_state` / `save_state` / `find_resumable_plans` persist `SpecState` | No built-in persistence; caller owns resumability |
| **Progress feedback** | Presenter functions render live output | Callback only — wire `on_task_complete` yourself |
| **Skip flags** | `skip_gates`, `skip_tests`, `skip_simplify` | Same flags on `__init__` |
| **Task filtering** | `get_pending_tasks` against persisted state | Pass `skip_task_ids: set[str]` to `run_all` |
| **Result model** | `PipelineResult` (shared) | `PipelineResult` (shared) |
| **Concurrency** | Async coroutine — `await` it | Synchronous call |
| **Typical caller** | Conversational / interactive session | Automated scripts, CI pipelines |

**Use the `spec` layer** when a human approves each task, you want
automatic resume support, and you want formatted output without
writing presenter logic. **Use the `pipeline` layer** when running in
CI with no interactive step, when you need to skip tasks by ID at call
time, or when you want to inspect gate results programmatically with
no display logic in the way.

When in doubt, start with the `spec` layer. The `pipeline` layer is
the better fit only when you are certain you do not need state
persistence or interactive approval — and are prepared to manage both
yourself.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `ValueError: plan_path must be a non-empty string` | Empty string or `None` passed to `read_spec` / `PipelineOrchestrator` | Resolve the path before passing it | high |
| `FileNotFoundError: Plan file not found` | The plan file does not exist at the given path | Verify the path; use `os.path.abspath` to be sure | high |
| `PipelineResult.success` is `False` | One or more tasks failed to execute or failed a gate | Iterate `result.tasks`; check each `TaskResult.error`, `quality_gate_passed`, `tests_passed` | high |
| A task never appears in output | The XML task block is malformed or absent | Call `read_spec` directly and inspect the returned list | medium |
| Execution resumes from the wrong task | `SpecState.completed` / `current` is stale | `load_state` to inspect, then `clear_state` to reset | medium |
| `get_pending_tasks` returns `[]` unexpectedly | `SpecState.completed` already holds all task IDs | State is stale or the plan finished; `clear_state` to start fresh | medium |
| Quality gate always passes | `skip_gates=True` left in from development | Remove the flag to re-enable gates | medium |
| State comment vanished after editing the plan | An editor/formatter/VCS step stripped HTML comments | Ensure tooling preserves HTML comments in `.md`; confirm the comment is present after `save_state` | medium |

### Risk areas

- **Resuming re-runs tasks when state drifts.** `get_pending_tasks`
  matches `task_id` values from `SpecState.completed` against the task
  list from `read_spec`. If task IDs are renumbered or reordered
  between sessions, completed tasks can look pending and run twice.
  Treat plan files as append-only once execution starts; if you must
  edit mid-run, `clear_state` first.
- **Skip flags silently lower quality guarantees.** `skip_gates`,
  `skip_tests`, and `skip_simplify` set the corresponding `TaskResult`
  fields to `None`/`False` rather than raising. `PipelineResult.success`
  still returns `True` if all tasks executed, even with gates skipped.
  After any skip-flag run, inspect `quality_gate_passed`,
  `tests_passed`, and `gate_score` explicitly.
- **`read_spec` does not warn on empty task lists.** A valid file with
  no parseable XML task blocks returns `[]` silently, and downstream
  orchestration completes with nothing to do. Check for a non-empty
  list before orchestrating.
- **`on_task_complete` errors abort the pipeline.** An unhandled
  exception in the callback stops the run at that task; the saved
  state marks it `current`, so resuming re-runs it. Wrap callback
  logic in `try`/`except` and check `TaskResult.error` before acting.

### Diagnosis order

1. Reproduce with a minimal `read_spec(plan_path)` call — if it
   raises, the problem is the path or the plan file.
2. Inspect persisted state: `load_state(plan_path)`; check
   `completed`, `current`, `schema_version`.
3. Clear stale state and retry: `clear_state(plan_path)`.
4. Re-run with `skip_gates=True` to isolate gate failures from task
   logic. If `success` flips to `True`, the gate thresholds or scores
   are the cause — inspect `gate_details`.
5. Iterate `result.tasks` and print each failing `TaskResult`
   (`error`, `gate_score`, `gate_details`, `tests_passed`).
6. Run the related tests: `pytest -k "spec" -v`.

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic
> source of truth fed by four channels — unmatched user queries,
> telemetry error-frequency, GitHub issues, and these author-curated
> seeds — merged, deduplicated, and frequency-ranked by the FAQ
> Generator (see doc-stack D3, and this spec's
> [decisions.md](../../docs/specs/help-docs-single-source/decisions.md)
> D6). This section is **not** projected verbatim as the FAQ; it
> contributes the feature's author-curated seed questions to the
> Generator. Keep entries to genuine, feature-specific seeds — do not
> mirror the dynamic channels here.

- **Q:** What is the spec engine?
  **A:** The runtime layer that reads a decomposed plan file, executes
  each task in order, runs quality gates after each, and tracks
  progress so a run can be paused and resumed.
- **Q:** When should I use it?
  **A:** When you have a plan file with XML task blocks under
  `.claude/plans/` and want to execute those tasks with quality gates
  and approval checkpoints. If you're still brainstorming or
  decomposing, you don't need the engine yet.
- **Q:** What's the main entry point?
  **A:** Load and parse a plan — `read_spec(plan_path)`. Run the full
  pipeline programmatically — `PipelineOrchestrator(spec_path).run_all()`.
  Run with per-task approval — `await execute_with_approval(spec_path,
  on_task_complete)`.
- **Q:** How do quality gates work?
  **A:** After each task, `run_gates_for_task` evaluates the result and
  returns a `TaskResult`. `quality_gate_passed` says whether the task
  met its acceptance criteria; `gate_score` gives a numeric score;
  `severity` classifies the outcome. If `quality_gate_passed` is
  `False`, the pipeline stops unless auto-run is active
  (`SpecState.auto_run = True`).
- **Q:** Can I skip tasks or resume a partial run?
  **A:** Yes. Pass a set of task IDs to `run_all(skip_task_ids=...)` to
  exclude them. To resume, call `get_pending_tasks(tasks, state)` — it
  filters out IDs already in `SpecState.completed` — then orchestrate
  the remaining tasks.
- **Q:** How do I check whether the whole pipeline succeeded?
  **A:** Inspect the `PipelineResult`. `success` is `True` only when
  all tasks executed and passed their gates; `summary` is the
  human-readable summary; `total_cost` and `duration_ms` are available
  for observability.

## Notes & tips

- **Depend only on the public API.** `pipeline` exports
  `PipelineOrchestrator`, `PipelineResult`, `TaskResult`, and
  `read_spec`. `spec` exports `SpecState`, `clear_state`,
  `find_resumable_plans`, `format_progress_bar`, `get_pending_tasks`,
  `load_state`, `present_task_detail`, `present_task_result`,
  `present_tasks`, and `save_state`. `execute_with_approval` lives in
  `attune.spec.runner`. Private helpers can change without notice.
- **Presenter functions are pure.** `present_tasks`,
  `present_task_detail`, `present_task_result`, and
  `format_progress_bar` accept `pipeline` data types, hold no state,
  and have no coupling to the pipeline layer — safe to call anywhere.
- **Prefer `skip_task_ids` over `clear_state` for re-runs.** Clearing
  state is irreversible mid-run; skipping completed tasks preserves
  your `completed` list and keeps `total_cost` / `duration_ms`
  accurate.

## Design & extension

### Design decisions

- **State embedded in the plan file, not a sidecar.** `save_state` and
  `load_state` read and write `SpecState` as an HTML comment block
  inside the `.md` plan file rather than a separate JSON file. This
  keeps the plan and its progress co-located — the plan file is the
  single artifact needed to resume. The trade-off is that plan files
  are mutable after authoring, so the state block is versioned
  (`schema_version`) to survive format changes.
- **`skip_gates`, `skip_tests`, `skip_simplify` as constructor flags,
  not subclasses.** The three concerns are tightly coupled inside a
  single task execution; separating them into composable strategies
  would add indirection without simplifying the gate logic. The flags
  propagate transparently through `execute_with_approval`.
- **`SpecState.completed` is a list of task IDs, not a count.**
  `get_pending_tasks` filters by ID, so tasks can be skipped
  non-linearly via `skip_task_ids` in `run_all` without corrupting
  resume behavior. A simple counter could not support this.

### Extension points

- **Add a new quality-gate check:** extend
  `PipelineOrchestrator.run_gates_for_task()`. It returns a
  `TaskResult`; add fields to the `TaskResult` dataclass in
  `pipeline/models.py` if the new gate produces data callers must
  inspect.
- **Hook into task completion:** pass an `on_task_complete` callback
  to `run_all()`. It receives a `TaskResult` after each task — the
  intended integration point for custom reporting, logging, or
  approval UIs, without modifying the orchestrator.
- **Resume or skip tasks selectively:** pass `skip_task_ids: set[str]`
  to `run_all()`. Task IDs come from the `DecomposedTask` objects
  returned by `read_spec()`.
- **Add a new presenter format:** add a function alongside the
  existing presenters in `spec/presenter.py`. Presenters are pure
  functions over `DecomposedTask` and `TaskResult`.
- **Find or restore interrupted runs:** use
  `find_resumable_plans(plans_dir)` to list `SpecState` objects for
  incomplete plans, then pass `plan_path` to `execute_with_approval()`
  to resume.
