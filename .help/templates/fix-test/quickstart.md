---
type: quickstart
feature: fix-test
depth: quickstart
generated_at: 2026-04-14T14:57:50.585458+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Quickstart: fix-test

Track and manage failing tests across your project. The fix-test feature automatically identifies files that need test attention and queues maintenance tasks.

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

## Set up automated test lifecycle management

1. **Initialize the test lifecycle manager**
   ```python
   from attune.workflows.test_lifecycle import TestLifecycleManager

   manager = TestLifecycleManager(project_root=".", auto_execute=True)
   ```

2. **Process file changes to queue test tasks**
   ```python
   # When files change, automatically queue maintenance tasks
   tasks = manager.on_files_changed(["src/updated_file.py", "src/new_file.py"])
   print(f"Queued {len(tasks)} test maintenance tasks")
   ```

3. **Execute queued maintenance**
   ```python
   # Process pending test maintenance tasks
   results = manager.process_queue(max_tasks=5)
   print(f"Completed: {results['completed_count']}")
   print(f"Failed: {results['failed_count']}")
   ```

## Next steps

Run `manager.get_test_health_summary()` to see an overview of your project's test coverage and identify the highest-priority areas for improvement.
