---
type: error
name: spec-engine-error
feature: spec-engine
depth: error
generated_at: 2026-06-02T10:56:02.699564+00:00
source_hash: f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337
status: generated
---

# Spec Engine errors

Spec Engine errors fall into two categories: failures that prevent a plan from loading, and failures that occur during task execution and gate evaluation. The sections below map each error to its cause and how to resolve it.

## Common error signatures

| Exception | Message | Raised by | Cause |
|-----------|---------|-----------|-------|
| `ValueError` | `plan_path must be a non-empty string` | `read_spec()` | You passed an empty string or `None` as `plan_path` |
| `FileNotFoundError` | `Plan file not found: {path}` | `read_spec()` | The `.claude/plans/` file does not exist at the given path |
| `TaskResult.error` set | varies | `PipelineOrchestrator.run_gates_for_task()` | A quality gate failed or an exception occurred during task execution; inspect `TaskResult.error` and `TaskResult.gate_details` |
| `PipelineResult.success` is `False` | — | `PipelineOrchestrator.run_all()` | One or more tasks did not execute or did not pass gates; check `PipelineResult.summary` for a human-readable summary |

## Where errors originate

**Plan loading** — `read_spec(plan_path)` is the first call in every pipeline run. A `ValueError` here means `plan_path` is empty; a `FileNotFoundError` means the plan file is missing. Neither can proceed until you supply a valid, existing path.

**Task execution and gate evaluation** — `PipelineOrchestrator.run_gates_for_task()` evaluates quality gates for a single task and returns a `TaskResult`. When a gate fails, `TaskResult.quality_gate_passed` is `False` and `TaskResult.gate_score` holds the numeric score. When tests fail, `TaskResult.tests_passed` is `False`. When an unexpected error occurs, `TaskResult.error` contains the error string.

**Pipeline-level failure** — `PipelineOrchestrator.run_all()` aggregates all `TaskResult` objects into a `PipelineResult`. If `PipelineResult.success` is `False`, at least one task did not execute or failed a gate. Call `PipelineResult.summary` to see which tasks failed and why.

**State loading** — `load_state(plan_path)` reads execution state from the plan file and returns `None` if no state is found (not an error). If the returned `SpecState.schema_version` doesn't match the current version, the state may be stale or unreadable.

## How to diagnose

1. **Identify where in the pipeline the failure occurred.** A `ValueError` or `FileNotFoundError` from `read_spec()` means the plan never loaded. A `False` result from `PipelineResult.success` means the plan loaded but at least one task failed during execution.

2. **Inspect the failing `TaskResult`.** Iterate over `PipelineResult.tasks` and check `TaskResult.executed`, `TaskResult.quality_gate_passed`, `TaskResult.tests_passed`, and `TaskResult.error` for each task. The `TaskResult.severity` property classifies the outcome so you can quickly identify the most critical failures.

3. **Check gate details for score-based failures.** When `TaskResult.quality_gate_passed` is `False`, examine `TaskResult.gate_details` and `TaskResult.gate_score` to understand why the gate did not pass. Adjust the task implementation or re-run with `skip_gates=True` on `PipelineOrchestrator` to bypass gates temporarily.

4. **Verify state consistency before resuming.** If you're resuming a partial run, call `load_state(plan_path)` and confirm that `SpecState.completed` lists the tasks you expect. Use `get_pending_tasks(tasks, state)` to see what remains. If state looks wrong, call `clear_state(plan_path)` to reset it and re-run from the beginning.

5. **Re-run with gates or steps skipped to isolate the failure.** `PipelineOrchestrator` accepts `skip_gates=True`, `skip_tests=True`, and `skip_simplify=True`. Enabling these flags narrows which phase is producing the failure.

## Source files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

**Tags:** `spec`, `planning`
