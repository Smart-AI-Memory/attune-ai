---
type: task
feature: spec-engine
depth: task
generated_at: 2026-04-14T15:24:40.703800+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Work with spec engine

Use the spec engine when you need to run automated task pipelines with human approval gates and persistent execution state.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/spec/`

## Execute a spec with approval loop

1. **Import the execution function.**
   ```python
   from attune.spec.runner import execute_with_approval
   ```

2. **Run your spec file.**
   ```python
   result = execute_with_approval(
       spec_path="path/to/your/spec.xml",
       on_task_complete=my_callback_function,
       skip_gates=False,  # Set to True to bypass quality gates
       skip_tests=False   # Set to True to skip test execution
   )
   ```

3. **Verify execution completed.**
   Check `result.success` returns `True` and `result.summary` shows all tasks passed their quality gates.

## Resume interrupted execution

1. **Find resumable plans.**
   ```python
   from attune.spec.state import find_resumable_plans

   resumable = find_resumable_plans("path/to/plans")
   ```

2. **Load existing state.**
   ```python
   from attune.spec.state import load_state

   state = load_state(plan_path)
   if state:
       print(f"Plan has {len(state.completed)} completed tasks")
   ```

3. **Continue from where you left off.**
   Re-run `execute_with_approval()` with the same spec path. The engine automatically skips completed tasks.

## Format task information for display

1. **Present all tasks in a table.**
   ```python
   from attune.spec.presenter import present_tasks

   markdown_table = present_tasks(tasks, state)
   print(markdown_table)
   ```

2. **Show detailed task information.**
   ```python
   from attune.spec.presenter import present_task_detail

   detail = present_task_detail(single_task)
   print(detail)
   ```

3. **Display execution results.**
   ```python
   from attune.spec.presenter import present_task_result

   result_summary = present_task_result(task, gate_result)
   print(result_summary)
   ```

## Run quality gates independently

1. **Create a pipeline orchestrator.**
   ```python
   from attune.spec.pipeline import PipelineOrchestrator

   orchestrator = PipelineOrchestrator(
       spec_path="your_spec.xml",
       skip_gates=False,
       skip_tests=False
   )
   ```

2. **Execute quality gates for a specific task.**
   ```python
   gate_result = orchestrator.run_gates_for_task(decomposed_task)
   print(f"Gate passed: {gate_result.quality_gate_passed}")
   ```

3. **Check the gate severity.**
   Use `gate_result.severity` to determine if issues require attention before proceeding.

## Verify success

Your spec execution succeeded when:
- `PipelineResult.success` returns `True`
- All `TaskResult.quality_gate_passed` values are `True` or `None`
- No `TaskResult.error` fields contain error messages
