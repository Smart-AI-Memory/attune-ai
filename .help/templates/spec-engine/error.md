---
type: error
name: spec-engine-error
feature: spec-engine
depth: error
generated_at: 2026-08-02T18:41:59.170606+00:00
source_hash: 0a9f094d0c1cb1edca272a7412ba50c3a59e4336596eb0a901aff5e6fc3b2d4b
status: generated
---

# Spec Ladders — goal-driven spec development with approval loops

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
  exception in the callback stops the run at that task. Run via
  `execute_with_approval` (the `spec` layer) and state is saved with
  that task marked `current` before the callback fires, so resuming
  re-runs it; bare `run_all` does no state-saving of its own. Wrap
  callback logic in `try`/`except` and check `TaskResult.error` before
  acting.

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
