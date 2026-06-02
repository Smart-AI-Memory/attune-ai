---
type: cli-reference
name: spec-engine
tags: [spec, pipeline, claude-code]
---

# Spec Engine CLI reference

Spec-driven development with approval loops.

## Description

`spec-engine` executes spec plan files through a quality-gated pipeline. It reads a plan file containing XML task blocks, runs each task in order through `PipelineOrchestrator`, and evaluates quality gates after each task. The command supports per-task approval loops and can resume in-progress plans using saved `SpecState`.

## Usage

```
spec-engine [OPTIONS] SUBCOMMAND [ARGS]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--skip-gates` | `false` | Skip quality gate evaluation for all tasks |
| `--skip-tests` | `false` | Skip test execution for all tasks |
| `--skip-simplify` | `false` | Skip the simplification step for all tasks |
| `--help` | — | Show help and exit |

## Subcommands

### `execute-with-approval`

Execute a spec plan file with per-task approval. Calls `execute_with_approval(spec_path, on_task_complete, ...)` and pauses after each task so you can approve, redo, or auto-run remaining tasks. Respects `--skip-gates`, `--skip-tests`, and `--skip-simplify`.

**Arguments:** `SPEC_PATH` — path to the plan file.

---

### `read-spec`

Read a plan file and extract its XML task blocks. Calls `read_spec(plan_path)` and prints the list of `DecomposedTask` objects.

**Arguments:** `PLAN_PATH` — path to the plan file.

**Errors:**
- Exits non-zero with `ValueError` if `PLAN_PATH` is empty.
- Exits non-zero with `FileNotFoundError` if the file does not exist.

---

### `present-tasks`

Format all tasks from a plan as a markdown table. Calls `present_tasks(tasks, state)`. If a `SpecState` is available for the plan, completed tasks are marked accordingly.

**Arguments:** `PLAN_PATH` — path to the plan file.

---

### `present-task-detail`

Print full details for a single task. Calls `present_task_detail(task)`.

**Arguments:** `PLAN_PATH TASK_ID`

---

### `present-task-result`

Print a task's execution result with quality gate status. Calls `present_task_result(task, gate_result)`, including `gate_score`, `quality_gate_passed`, `tests_passed`, and `severity`.

**Arguments:** `PLAN_PATH TASK_ID`

---

### `format-progress-bar`

Print a visual progress indicator. Calls `format_progress_bar(completed, total)`.

**Arguments:** `COMPLETED TOTAL` — integers.

---

### `get-pending-tasks`

List tasks not yet recorded in `SpecState.completed`. Calls `get_pending_tasks(tasks, state)`.

**Arguments:** `PLAN_PATH`

---

### `load-state`

Read the `SpecState` embedded as an HTML comment in a plan file. Calls `load_state(plan_path)`. Prints nothing and exits `0` if no state is present.

**Arguments:** `PLAN_PATH`

---

### `save-state`

Write or update the `SpecState` HTML comment in a plan file. Calls `save_state(state)`. Updates `last_updated` to the current UTC timestamp.

**Arguments:** `PLAN_PATH`

---

### `clear-state`

Remove the `SpecState` HTML comment from a plan file. Calls `clear_state(plan_path)`. After clearing, the plan can be executed from the beginning.

**Arguments:** `PLAN_PATH`

---

### `find-resumable-plans`

List plan files under a directory that have incomplete execution state. Calls `find_resumable_plans(plans_dir)`. Defaults to `.claude/plans`.

**Arguments:** `[PLANS_DIR]` — directory to search (default: `.claude/plans`).

## Output

`execute-with-approval` prints a progress bar, per-task quality gate results, and a final pipeline summary:

```
[========--] 4/5 tasks

✔ task-1  add-jwt-config          gate: passed  score: 92.0  cost: $0.003
✔ task-2  token-service           gate: passed  score: 87.5  cost: $0.004
✔ task-3  auth-middleware         gate: passed  score: 81.0  cost: $0.005
✔ task-4  wire-routes             gate: passed  score: 78.3  cost: $0.004
  task-5  integration-tests       pending

Pipeline complete: 4/5 tasks executed  total_cost: $0.016  duration: 18402ms
```

`present-tasks` prints a markdown table:

```markdown
| ID  | Name                 | Status    |
|-----|----------------------|-----------|
| 1   | add-jwt-config       | completed |
| 2   | token-service        | completed |
| 3   | auth-middleware      | pending   |
```

`format-progress-bar` output:

```
[========--] 4/5 tasks
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | All subcommand operations completed successfully |
| `1` | Pipeline failure — one or more tasks did not pass quality gates (`PipelineResult.success` is `false`), a plan file was not found, or an invalid argument was supplied |

## Related commands

- `/spec` — interactive skill that drives `spec-engine` through a guided brainstorm, decompose, review, approve, and execute flow
- `attune help-docs ref-skill-spec` — full reference for spec phases, quality gate severity levels, and plan file format

<!-- attune-generated: source_hash=f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337 feature=spec-engine kind=cli-reference generated_at=2026-06-02 -->
