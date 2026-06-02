---
type: warning
name: spec-engine-warning
feature: spec-engine
depth: warning
generated_at: 2026-06-02T10:56:02.708405+00:00
source_hash: f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337
status: generated
---

# Spec Engine cautions

## What to watch for

The spec engine manages long-running, stateful plan execution — tasks write to disk, quality gates gate forward progress, and approval loops depend on state surviving across sessions. Mistakes here tend to surface late: a corrupted state file, a silently skipped gate, or a resume that replays already-completed work.

## Risk areas

### Resuming a plan re-runs tasks if state is out of sync

`get_pending_tasks` filters completed tasks by comparing `task_id` values in `SpecState.completed` against the task list from `read_spec`. If the plan file changes between sessions — for example, task IDs are renumbered or reordered — previously completed tasks may appear pending again and execute a second time.

**Mitigation:** Treat plan files as append-only once execution has started. If you must edit a plan mid-run, call `clear_state` to reset progress rather than letting `get_pending_tasks` infer a stale completion list.

### `skip_gates`, `skip_tests`, and `skip_simplify` silently lower quality guarantees

`PipelineOrchestrator.__init__` accepts `skip_gates`, `skip_tests`, and `skip_simplify` flags, and `execute_with_approval` exposes the same three. Passing any of these sets fields on `TaskResult` — `quality_gate_passed`, `tests_passed`, and `simplified` — to `None` or `False` rather than raising an error. `PipelineResult.success` still returns `True` if all tasks executed, even when gates were skipped.

**Mitigation:** After any run that uses skip flags, inspect `TaskResult.quality_gate_passed`, `TaskResult.tests_passed`, and `TaskResult.gate_score` explicitly rather than relying solely on `PipelineResult.success`.

### `read_spec` raises on missing or malformed plan files — not on empty task lists

`read_spec` raises `FileNotFoundError` when the plan file is absent and `ValueError` when `plan_path` is empty. However, a valid file that contains no parseable XML task blocks returns an empty list without any warning. Downstream, `PipelineOrchestrator.run_all` and `get_pending_tasks` both accept an empty task list and complete silently.

**Mitigation:** Check that `read_spec` returns a non-empty list before passing it to orchestration logic. If you expect tasks and receive an empty list, inspect the plan file for malformed or missing XML task blocks.

### State is stored as an HTML comment inside the plan file itself

`save_state` and `load_state` read and write `SpecState` as an embedded comment in the plan file at `plan_path`. If your editor, formatter, or version control workflow strips HTML comments, the state comment disappears and `load_state` returns `None`. The next call to `get_pending_tasks` then treats every task as pending.

**Mitigation:** Verify that tooling in your workflow preserves HTML comments in `.md` files. After a `save_state` call, confirm the comment is present before closing the file. Use `find_resumable_plans` to check which plans have recoverable state before attempting a resume.

### `on_task_complete` callback errors abort the pipeline

Both `run_all` and `execute_with_approval` accept an `on_task_complete` callback. If the callback raises an unhandled exception, the pipeline stops at that task. The `SpecState` written by `save_state` at that point marks the task as `current` rather than completed, so resuming re-runs the task that triggered the failure.

**Mitigation:** Wrap callback logic in a try/except and handle errors explicitly. Check `TaskResult.error` inside the callback before taking any action that could fail.

## How to avoid problems

1. **Validate task IDs before editing a live plan.** Before changing a plan file that has an active state, read `SpecState.completed` via `load_state` and confirm that none of the IDs you're modifying appear there.

2. **Use `TaskResult` fields, not just `PipelineResult.success`, to audit gate outcomes.** Check `quality_gate_passed`, `tests_passed`, `gate_score`, and `severity` on each `TaskResult` in `PipelineResult.tasks` when correctness matters more than whether the run completed.

3. **Depend only on the public API.** The public surfaces are `PipelineOrchestrator`, `PipelineResult`, `TaskResult`, and `read_spec` from `pipeline`, and `SpecState`, `clear_state`, `find_resumable_plans`, `format_progress_bar`, `get_pending_tasks`, `load_state`, `present_task_detail`, `present_task_result`, `present_tasks`, and `save_state` from `spec`. Private helpers can change without notice.

## Source files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

**Tags:** `spec`, `planning`
