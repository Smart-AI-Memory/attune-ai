---
type: quickstart
feature: spec-engine
depth: quickstart
generated_at: 2026-04-14T15:26:13.006376+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Run a spec-driven development pipeline

Execute a development plan with automatic quality gates and approval steps.

```python
from attune.spec.orchestrator import PipelineOrchestrator

# Run all tasks from your spec file
orchestrator = PipelineOrchestrator("path/to/your/spec.xml")
result = orchestrator.run_all()
print(f"Pipeline completed: {result.success}")
print(result.summary)
```

Expected output:
```
Pipeline completed: True
Executed 5 tasks successfully. All quality gates passed. Total cost: $0.23
```

## Run your first pipeline

1. **Create a pipeline orchestrator** with your XML spec file:
   ```python
   orchestrator = PipelineOrchestrator("./plans/my_feature.xml")
   ```

2. **Execute all tasks** in the specification:
   ```python
   result = orchestrator.run_all()
   ```

3. **Check the results** to see which tasks passed quality gates:
   ```python
   for task in result.tasks:
       print(f"{task.task_name}: {'✓' if task.quality_gate_passed else '✗'}")
   ```

## View pipeline progress

Track execution state and resume interrupted pipelines:

```python
from attune.spec.runner import find_resumable_plans, execute_with_approval

# Find plans you can resume
resumable = find_resumable_plans()
for state in resumable:
    print(f"Plan: {state.plan_path}, Progress: {len(state.completed)} tasks done")

# Run with manual approval for each task
result = execute_with_approval("./plans/my_feature.xml",
                             on_task_complete=lambda task: input("Continue? (y/n): ") == "y")
```

**Next:** Create your first XML specification file to define development tasks and quality gates.
