---
type: error
feature: spec-engine
depth: error
generated_at: 2026-04-14T15:25:11.257427+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Spec Engine errors

Failures that occur during spec execution, task presentation, and pipeline orchestration in Attune AI's spec-driven development workflow.

## Common error signatures

- **FileNotFoundError** when loading spec files or accessing plan paths that don't exist
- **ValueError** from malformed XML specs or invalid task configurations
- **TypeError** when task callback functions don't match the expected `TaskCallback` signature
- **AttributeError** when accessing properties on incomplete `TaskResult` or `PipelineResult` objects
- **KeyError** when referencing task IDs that don't exist in the current spec
- **OSError** during state persistence operations when plan files can't be written

## Where errors originate

Most spec engine failures occur at these key execution points:

- **`PipelineOrchestrator.run_all()`** — Task execution and quality gate validation
- **`execute_with_approval()`** — Interactive approval loop and callback invocation
- **`load_state()` and `save_state()`** — HTML comment parsing and file I/O for state persistence
- **`present_tasks()` and `present_task_detail()`** — Markdown formatting when task data is incomplete
- **`run_gates_for_task()`** — Quality gate evaluation and scoring

## How to diagnose

1. **Check the spec file path.** Many failures stem from missing or inaccessible XML spec files. Verify that `spec_path` exists and contains valid task definitions.

2. **Validate task callback signatures.** If using `on_task_complete` callbacks, ensure they accept the expected parameters. Mismatched signatures cause `TypeError` during task execution.

3. **Examine quality gate results.** When `TaskResult.quality_gate_passed` is `None` or tasks fail unexpectedly, check `gate_details` and `error` fields for specific failure reasons.

4. **Inspect state persistence.** If resumption fails, check that plan files are writable and contain valid HTML comments. Malformed state comments cause parsing errors during `load_state()`.

5. **Review task dependencies.** Tasks may fail if their prerequisites haven't completed. Use `get_pending_tasks()` to verify execution order matches spec requirements.

## Source files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

**Tags:** `spec`, `planning`
