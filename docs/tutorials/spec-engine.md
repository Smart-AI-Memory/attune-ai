# Tutorial: Build a Spec Engine Pipeline Runner

This tutorial walks you through the spec engine's Python API from first import to a verified `PipelineResult`. When you finish, you'll have a working script that reads a plan file, runs every task through quality gates, tracks progress with a visual bar, and prints a pass/fail summary — enough to understand how the pieces fit together before you use them in a real project.

## Prerequisites

- Python 3.10 or newer
- The project installed in your environment
- A plan file saved at `.claude/plans/` (the spec skill produces these — see the [Spec-Driven Development concept](concepts/tool-spec.md) if you haven't created one yet)

## What you will build

A self-contained Python script, `run_pipeline.py`, that:

1. Reads task definitions from a plan file
2. Shows a formatted task table before execution
3. Runs all tasks through `PipelineOrchestrator`, printing a progress bar after each one completes
4. Exits with a human-readable summary and a non-zero code if any gate failed

---

## Step 1 — Import the public API

The spec engine exposes everything you need through two packages. Open a new file called `run_pipeline.py` and add these imports:

```python
from pipeline import PipelineOrchestrator, PipelineResult, TaskResult, read_spec
from spec import present_tasks, present_task_result, format_progress_bar, load_state
```

Both `pipeline` and `spec` are top-level packages — drop the `src.` prefix that appears in the source tree. Keeping these two imports separate reflects how the packages divide responsibility: `pipeline` owns execution, `spec` owns presentation and state.

**Verify:** Run `python -c "from pipeline import read_spec; print('ok')"`. You should see `ok` with no import errors.

---

## Step 2 — Read the plan file

`read_spec` parses your plan file and returns a list of `DecomposedTask` objects — one per XML task block in the file. This is the data structure every other function in the engine consumes.

```python
PLAN_PATH = ".claude/plans/my-feature.md"

tasks = read_spec(PLAN_PATH)
print(f"Found {len(tasks)} tasks")
```

`read_spec` raises `FileNotFoundError` if the path doesn't exist and `ValueError` if you pass an empty string, so bad inputs fail loudly rather than silently.

**Verify:** The printed count should match the number of task blocks in your plan file. If you see `0`, open the plan and confirm it contains XML task blocks.

---

## Step 3 — Display the task table before running

Before any code executes, show yourself (or your user) what is about to run. `present_tasks` formats the task list as a markdown table; passing the current `SpecState` marks already-completed tasks, which matters if you're resuming a partial run.

```python
state = load_state(PLAN_PATH)   # returns None if no prior run exists
print(present_tasks(tasks, state))
```

This step is why spec-driven development separates reading from executing: you can inspect the full plan before committing to a run.

**Verify:** You should see a markdown table with one row per task. If `state` is not `None`, tasks listed in `state.completed` will be marked accordingly.

---

## Step 4 — Define a progress callback

`run_all` accepts an optional `on_task_complete` callback that fires after each task finishes. Use it to print a progress bar and the gate result for every completed task:

```python
completed_count = 0

def on_task_complete(task, task_result: TaskResult) -> None:
    global completed_count
    completed_count += 1
    print(format_progress_bar(completed_count, len(tasks)))
    print(present_task_result(task, task_result))
```

`format_progress_bar` takes two integers — completed and total — so it always reflects the live run state rather than a snapshot. `present_task_result` renders the quality gate outcome, including `task_result.gate_score` and `task_result.severity`, without you having to format those fields manually.

**Verify:** This is a function definition — nothing runs yet. Move on to Step 5 to wire it in.

---

## Step 5 — Run the pipeline

Construct `PipelineOrchestrator` with your plan path and call `run_all`, passing the callback you defined above:

```python
orchestrator = PipelineOrchestrator(PLAN_PATH)
result: PipelineResult = orchestrator.run_all(on_task_complete=on_task_complete)
```

`PipelineOrchestrator.__init__` also accepts `skip_gates`, `skip_tests`, and `skip_simplify` keyword arguments if you want a faster feedback loop during development — but run with gates enabled first so you understand what the defaults do.

**Verify:** As the run proceeds, your terminal should show a growing progress bar and one result block per task. If a task raises an error, `TaskResult.error` will be non-`None` and the progress bar will still advance.

---

## Step 6 — Print the summary and exit

`PipelineResult.summary` is a human-readable string that covers all tasks and the total cost. `PipelineResult.success` is `True` only when every task executed and every quality gate passed.

```python
print(result.summary())

if not result.success():
    raise SystemExit(1)
```

Exiting with a non-zero code lets CI systems treat a failed gate as a build failure automatically.

**Verify:** A fully passing run prints the summary and exits with code `0`. Run `echo $?` (or `echo %ERRORLEVEL%` on Windows) immediately after to confirm.

---

## Complete script

```python
from pipeline import PipelineOrchestrator, PipelineResult, TaskResult, read_spec
from spec import present_tasks, present_task_result, format_progress_bar, load_state

PLAN_PATH = ".claude/plans/my-feature.md"

tasks = read_spec(PLAN_PATH)
print(f"Found {len(tasks)} tasks")

state = load_state(PLAN_PATH)
print(present_tasks(tasks, state))

completed_count = 0

def on_task_complete(task, task_result: TaskResult) -> None:
    global completed_count
    completed_count += 1
    print(format_progress_bar(completed_count, len(tasks)))
    print(present_task_result(task, task_result))

orchestrator = PipelineOrchestrator(PLAN_PATH)
result: PipelineResult = orchestrator.run_all(on_task_complete=on_task_complete)

print(result.summary())

if not result.success():
    raise SystemExit(1)
```

---

## What you learned

- **Step 1–2:** `read_spec` is the entry point that converts a plan file into `DecomposedTask` objects. Every other API in the engine takes those objects as input, which is why reading comes first.
- **Step 3:** `present_tasks` and `load_state` let you inspect the plan and any prior run state before committing to execution — the separation between reading and running is intentional.
- **Step 4:** The `on_task_complete` callback is the hook where `format_progress_bar` and `present_task_result` belong, because they are per-task concerns, not pipeline-level ones.
- **Step 5:** `PipelineOrchestrator` owns the execution loop. Its `skip_gates`, `skip_tests`, and `skip_simplify` flags let you trade thoroughness for speed, but you should understand the default (all enabled) before reaching for them.
- **Step 6:** `PipelineResult.success` and `PipelineResult.summary` give you the two things a caller needs: a boolean for control flow and a string for humans.

## Next steps

Now that you can run a pipeline programmatically, read the `execute_with_approval` reference in `spec.runner` to see how the interactive approval loop wraps the same orchestrator — it adds per-task human confirmation on top of exactly the machinery you just built.

<!-- attune-generated: source_hash=f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337 feature=spec-engine kind=tutorial generated_at=2026-06-02 -->

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 26 (code fence) | error | `from pipeline import …` — module not importable |
| Line 26 (code fence) | error | `from spec import …` — module not importable |
| Line 9 | error | `[Spec-Driven Development concept](concepts/tool-spec.md)` — target does not exist |
| Line 44 (python fence) | error | Name "read_spec" is not defined  [name-defined] |
| Line 59 (python fence) | error | Name "load_state" is not defined  [name-defined] |
| Line 59 (python fence) | error | Name "PLAN_PATH" is not defined  [name-defined] |
| Line 60 (python fence) | error | Name "present_tasks" is not defined  [name-defined] |
| Line 60 (python fence) | error | Name "tasks" is not defined  [name-defined] |
| Line 76 (python fence) | error | Function is missing a type annotation for one or more arguments  [no-untyped-def] |
| Line 76 (python fence) | error | Name "TaskResult" is not defined  [name-defined] |
| Line 79 (python fence) | error | Name "format_progress_bar" is not defined  [name-defined] |
| Line 79 (python fence) | error | Name "tasks" is not defined  [name-defined] |
| Line 80 (python fence) | error | Name "present_task_result" is not defined  [name-defined] |
| Line 94 (python fence) | error | Name "PipelineOrchestrator" is not defined  [name-defined] |
| Line 94 (python fence) | error | Name "PLAN_PATH" is not defined  [name-defined] |
| Line 95 (python fence) | error | Name "PipelineResult" is not defined  [name-defined] |
| Line 95 (python fence) | error | Name "on_task_complete" is not defined  [name-defined] |
| Line 109 (python fence) | error | Name "result" is not defined  [name-defined] |
| Line 111 (python fence) | error | Name "result" is not defined  [name-defined] |
| Line 137 (python fence) | error | Function is missing a type annotation for one or more arguments  [no-untyped-def] |
