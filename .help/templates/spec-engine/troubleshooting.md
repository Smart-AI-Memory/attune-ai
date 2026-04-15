---
type: troubleshooting
feature: spec-engine
depth: troubleshooting
generated_at: 2026-04-14T15:25:44.466671+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Troubleshoot spec engine

## Before you start

The spec engine handles spec-driven development with quality gates, task execution, and state persistence. Issues typically manifest as execution failures, incorrect state tracking, or quality gate problems.

## Symptom table

| If you observe | Check |
|----------------|-------|
| Pipeline execution stops unexpectedly | Verify the XML spec format and task definitions are valid |
| Quality gates fail without clear reason | Examine `TaskResult.gate_details` and `gate_score` values |
| State persistence not working | Check if the plan file exists and is writable at `plan_path` |
| Tasks marked as completed but not executed | Compare `SpecState.completed` list against actual task IDs |
| Approval loop hangs indefinitely | Verify the `on_task_complete` callback function is properly defined |

## Step-by-step diagnosis

1. **Reproduce with minimal spec.**
   Create a simple XML spec with one task to isolate whether the issue is in the orchestrator logic or your specific spec content.

2. **Check spec state consistency.**
   Use `load_state(plan_path)` to inspect the current `SpecState`. Verify that `completed`, `current`, and `auto_run` fields match your expectations.

3. **Examine pipeline execution flow.**
   Add logging around these key functions:
   - `PipelineOrchestrator.run_all()` - Check if tasks are being filtered correctly
   - `run_gates_for_task()` - Verify quality gate execution
   - `execute_with_approval()` - Confirm approval callbacks are triggered

4. **Validate task filtering logic.**
   Use `get_pending_tasks()` manually to see which tasks the engine considers incomplete. Compare this against your expected task list.

5. **Test quality gates in isolation.**
   Call `run_gates_for_task()` directly on a single task to check if gate failures are due to the task content or the gate logic itself.

## Common fixes

- **Reset corrupted state:** Run `clear_state(plan_path)` to remove the state comment and restart execution from the beginning.

- **Fix spec path issues:** Ensure the `spec_path` argument points to a valid XML file and the directory is readable:
  ```bash
  ls -la /path/to/spec.xml
  ```

- **Handle quality gate configuration:** If gates are failing incorrectly, initialize with `skip_gates=True`:
  ```python
  orchestrator = PipelineOrchestrator(spec_path, skip_gates=True)
  ```

- **Debug approval callback errors:** Verify your callback function signature matches `TaskCallback` and handles exceptions:
  ```python
  def safe_callback(task, result):
      try:
          # your callback logic
          pass
      except Exception as e:
          print(f"Callback error: {e}")
  ```

- **Resolve resumability issues:** Use `find_resumable_plans()` to see which plans have incomplete state, then clear or fix corrupted entries.

## Source files

- `src/attune/spec/orchestrator.py` - Pipeline execution and quality gates
- `src/attune/spec/runner.py` - State management and task filtering
- `src/attune/spec/presenter.py` - Task formatting and progress display

**Tags:** `spec`, `planning`
