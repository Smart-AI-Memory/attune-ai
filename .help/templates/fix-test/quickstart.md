---
type: quickstart
feature: fix-test
depth: quickstart
generated_at: 2026-06-22T10:21:37.523920+00:00
source_hash: 26d8af3fe4cef200ee3e0528559c0e39b2bd3756956371d1e78427e02cb6385b
status: generated
---

# Quickstart: fix-test

Track and manage failing tests across your project. The fix-test feature identifies files that need test attention and turns changes into a prioritized maintenance plan.

```python
from attune.workflows.test_runner import get_files_needing_tests

# Find files that need test fixes
files_needing_attention = get_files_needing_tests(failed_only=True)
for record in files_needing_attention:
    print(f"File: {record.source_file}")
    print(f"Status: {record.status}")
```

Expected output:
```
File: src/my_module.py
Status: test_failed
File: src/another_module.py
Status: no_tests
```

## Build a test maintenance plan

1. **Create the workflow**
   ```python
   from attune.workflows.test_maintenance import TestMaintenanceWorkflow

   workflow = TestMaintenanceWorkflow()
   ```

2. **React to a change, or build a full plan**
   ```python
   # Per-file: returns a TestPlanItem | None
   item = workflow.on_file_modified("src/updated_file.py")

   # Or a full plan for the project
   plan = workflow.run({})
   print(f"Planned {len(plan.items)} test maintenance items")
   ```

3. **Act on the safe subset**
   ```python
   safe = plan.get_auto_executable_items()
   print(f"{len(safe)} items can run automatically")
   ```

## Next steps

Run `workflow.get_test_health_summary()` to see an overview of your project's test coverage and identify the highest-priority areas for improvement.
