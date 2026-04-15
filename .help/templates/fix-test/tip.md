---
type: tip
feature: fix-test
depth: tip
generated_at: 2026-04-14T14:58:00.827179+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# Use TestLifecycleManager for event-driven test maintenance

Start with `TestLifecycleManager` when files change in your project—it automatically queues appropriate test actions based on what happened to each file.

## Why this matters

Setting up event handlers once is faster than manually tracking which tests need updates every time you modify source code.

## How to use it

Initialize the manager with your project root and call the appropriate handler:

```python
manager = TestLifecycleManager(project_root="/path/to/project")

# When a file is created, modified, or deleted
task = manager.on_file_created("src/new_module.py")
task = manager.on_file_modified("src/existing_module.py")
task = manager.on_file_deleted("src/old_module.py")

# Process queued tasks
result = manager.process_queue(max_tasks=5)
```

## The tradeoff

The manager queues tasks instead of running them immediately—you get control over when test maintenance happens, but you must remember to process the queue.
