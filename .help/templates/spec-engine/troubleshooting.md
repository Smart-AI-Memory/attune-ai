---
type: troubleshooting
name: spec-engine-troubleshooting
feature: spec-engine
depth: troubleshooting
generated_at: 2026-06-02T10:56:02.711703+00:00
source_hash: f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337
status: generated
---

# Troubleshoot spec engine

## Before you start

The spec engine coordinates plan parsing, task execution, quality gates, and state persistence. Failures usually fall into one of three areas: a plan file that can't be read or parsed, a `SpecState` that is missing or corrupt, or a `TaskResult` that signals a quality-gate failure. Identify which area is affected before diving into code.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `FileNotFoundError: Plan file not found` | Verify the path passed to `read_spec(plan_path)` or `PipelineOrchestrator(spec_path)` exists and is non-empty. |
| `ValueError: plan_path must be a non-empty string` | You passed an empty string or `None` as `spec_path`/`plan_path`. Confirm the calling code resolves the path before passing it. |
| `PipelineResult.success` is `False` | Iterate `PipelineResult.tasks` and check each `TaskResult.error`, `TaskResult.quality_gate_passed`, and `TaskResult.tests_passed` to find which task failed and why. |
| A task never appears in the output | Call `read_spec(plan_path)` directly and inspect the returned list. If the task is missing, the XML task block in the plan file is malformed or absent. |
| Execution resumes from the wrong task | Call `load_state(plan_path)` and inspect `SpecState.completed` and `SpecState.current`. If stale, call `clear_state(plan_path)` to reset. |
| `get_pending_tasks` returns an empty list unexpectedly | `SpecState.completed` already contains all task IDs. Either the state is stale or the plan was previously finished. Call `clear_state(plan_path)` to start fresh. |
| Quality gate always passes when it shouldn't | Check whether `skip_gates=True` was passed to `PipelineOrchestrator` or `execute_with_approval`. Remove that flag to re-enable gates. |
| `TaskResult.severity` returns an unexpected level | Inspect `TaskResult.gate_score` and `TaskResult.gate_details` to see the raw values driving the classification. |
| No resumable plans found | Call `find_resumable_plans()` (default search path: `.claude/plans`). If it returns an empty list, no `.state.json` files exist in that directory. |

## Step-by-step diagnosis

Follow these steps in order — earlier steps are cheaper and resolve most issues without deeper investigation.

1. **Reproduce the failure with a minimal call.**
   Strip the invocation to its required arguments and confirm the failure is repeatable:

   ```python
   from attune.pipeline import read_spec
   tasks = read_spec("path/to/your-plan.md")
   print(tasks)
   ```

   If `read_spec` raises, the problem is in the plan file or the path. If it returns an unexpected list, the XML task blocks in the file need inspection.

2. **Inspect the state file.**
   Before running the pipeline, check what state is persisted:

   ```python
   from attune.spec import load_state
   state = load_state("path/to/your-plan.md")
   print(state)  # None means no state exists
   if state:
       print(state.to_dict())
   ```

   Look at `state.completed`, `state.current`, and `state.schema_version`. A mismatched `schema_version` or a `completed` list that includes tasks you expect to re-run indicates stale state.

3. **Clear stale state and retry.**
   If step 2 reveals stale or corrupt state, reset it:

   ```python
   from attune.spec import clear_state
   clear_state("path/to/your-plan.md")
   ```

   Then re-run the pipeline. This is the fix for most "wrong task order" and "pending tasks list is empty" issues.

4. **Run the pipeline with gates disabled to isolate gate failures.**
   If tasks execute but quality gates block progress unexpectedly, run with `skip_gates=True` to confirm the task logic itself works:

   ```python
   from attune.pipeline import PipelineOrchestrator
   orch = PipelineOrchestrator("path/to/your-plan.md", skip_gates=True)
   result = orch.run_all()
   print(result.summary())
   ```

   If `result.success` is `True` with gates skipped but `False` with gates enabled, the gate thresholds or the `gate_score` values on failing tasks are the root cause. Re-enable gates and inspect `TaskResult.gate_details` for each failing task.

5. **Examine per-task results.**
   Iterate the `PipelineResult.tasks` list and print each `TaskResult` to pinpoint which task failed:

   ```python
   for task_result in result.tasks:
       if not task_result.quality_gate_passed or task_result.error:
           print(task_result.task_id, task_result.task_name)
           print("error:", task_result.error)
           print("score:", task_result.gate_score)
           print("details:", task_result.gate_details)
           print("tests_passed:", task_result.tests_passed)
   ```

6. **Run related tests.**
   Confirm which test cases pass against your current code:

   ```
   pytest -k "spec" -v
   ```

   A failing test that exercises the broken path gives you a reproducible harness and can confirm when your fix is correct.

## Common fixes

- **Missing or mistyped plan path.**
  `read_spec` raises `FileNotFoundError` or `ValueError` when `plan_path` is wrong. Always resolve the path before passing it:

  ```python
  import os
  plan_path = os.path.abspath("path/to/your-plan.md")
  tasks = read_spec(plan_path)
  ```

- **Stale `SpecState` blocking re-execution.**
  If a plan was previously completed or interrupted mid-run, the state file records those task IDs in `SpecState.completed`. Reset with:

  ```python
  from attune.spec import clear_state
  clear_state("path/to/your-plan.md")
  ```

  This removes the embedded state comment from the plan file. The next run starts from the first task.

- **Quality gates skipped unintentionally.**
  If `skip_gates=True` was passed to `PipelineOrchestrator` or `execute_with_approval` during development and left in, gate failures will never surface. Remove the flag:

  ```python
  # Before (gates disabled):
  orch = PipelineOrchestrator(spec_path, skip_gates=True)

  # After (gates enabled):
  orch = PipelineOrchestrator(spec_path)
  ```

- **Skipping specific tasks unintentionally.**
  If `run_all` was called with a non-empty `skip_task_ids` set, those tasks are silently omitted from the run. Confirm the set is correct or pass `None` to run all tasks:

  ```python
  result = orch.run_all(skip_task_ids=None)
  ```

- **XML task blocks missing from the plan file.**
  `read_spec` returns an empty list if the plan file contains no parseable XML task blocks. Open the plan file and confirm the task blocks are present and well-formed. The plan file lives at the path under `.claude/plans/` recorded in `SpecState.plan_path`.

- **Dependency version drift.**
  If behavior changed without a code edit, confirm your environment matches expectations:

  ```
  pip show attune
  ```

  Note that this check requires access to your local environment and is outside the spec engine itself.

## Source files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

**Tags:** `spec`, `planning`
