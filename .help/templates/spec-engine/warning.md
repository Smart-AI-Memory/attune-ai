---
type: warning
feature: spec-engine
depth: warning
generated_at: 2026-04-14T15:25:24.133155+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Spec Engine cautions

## What to watch for

The spec engine orchestrates task execution with quality gates and approval loops. State persistence and task filtering can cause unexpected behavior when execution is interrupted or resumed.

## Risk areas

### State file corruption during interrupted execution

The `save_state()` function writes execution state as HTML comments in plan files. If your process terminates while writing state, you may end up with malformed comments that `load_state()` cannot parse. Always check the return value of `load_state()` for `None` before assuming you have valid state.

### Task filtering creates execution gaps

`get_pending_tasks()` filters based on the `completed` list in `SpecState`, but there's no validation that completed task IDs actually exist in the current spec. If you modify a spec file after partial execution, previously completed tasks may no longer match, causing tasks to run unexpectedly or be skipped entirely.

### Quality gate bypass affects cost tracking

When you set `skip_gates=True` on `PipelineOrchestrator`, tasks still execute but gate validation is bypassed. The `TaskResult.quality_gate_passed` field will be `None`, which may break downstream logic that expects a boolean. Additionally, cost tracking continues even when gates are skipped, potentially inflating cost calculations.

### Auto-run mode ignores approval callbacks

Setting `auto_run=True` in `SpecState` causes the execution engine to bypass the approval loop entirely. If you're expecting `on_task_complete` callbacks to provide user interaction, they will still fire but won't block execution. This can lead to tasks running faster than expected monitoring systems can handle.

## How to avoid problems

1. **Validate state before resuming execution.** Always call `load_state()` and check for `None` before passing state to execution functions. Consider clearing corrupted state with `clear_state()` rather than attempting manual repairs.

2. **Use task ID sets for safer filtering.** Convert the completed task list to a set and verify that all IDs exist in your current task list before filtering. This prevents silent execution gaps when specs change between runs.

3. **Check gate results explicitly.** When processing `TaskResult` objects, test for `quality_gate_passed is None` separately from `quality_gate_passed is False`. These represent different failure modes that may need different handling.

4. **Test with interrupted execution.** Simulate process termination during state saves and task execution to verify your error handling works correctly. The `find_resumable_plans()` function can help identify plans left in inconsistent states.

## Source files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

**Tags:** `spec`, `planning`
