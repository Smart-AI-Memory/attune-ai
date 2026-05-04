---
type: task
feature: hooks
depth: task
generated_at: 2026-05-04T02:43:15.171329+00:00
source_hash: ee7c91a1c6d86f5cfe8cb471894be8631647c9e853782d701bb219ccfe3deaf4
status: generated
---

# Work with hooks

Use the hooks system when you need to respond to events in the Attune AI lifecycle, such as evaluating sessions for learning potential or initializing projects.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/hooks/

## Configure hook events

1. **Load your hook configuration.**
   Create a `HookConfig` instance to define which hooks fire for which events:
   ```python
   from attune.hooks import HookConfig
   config = HookConfig.from_yaml("path/to/hooks.yaml")
   ```

2. **Register hooks for specific events.**
   Add hooks to respond to Attune AI lifecycle events:
   ```python
   config.add_hook(
       event=HookEvent.SESSION_START,
       hook=HookDefinition(
           type=HookType.PYTHON,
           action="evaluate_session",
           config={"threshold": 0.8}
       )
   )
   ```

3. **Set up the hook registry.**
   Initialize the registry with your configuration:
   ```python
   from attune.hooks import HookRegistry
   registry = HookRegistry(config=config)
   ```

## Execute hooks programmatically

1. **Fire hooks for an event.**
   Trigger all matching hooks for a specific lifecycle event:
   ```python
   context = {"session_id": "abc123", "user_id": "user456"}
   results = registry.fire_sync(HookEvent.SESSION_END, context)
   ```

2. **Use built-in evaluation scripts.**
   Run the session evaluation hook directly:
   ```python
   from attune.hooks.scripts.evaluate_session import run_evaluate_session
   result = run_evaluate_session({"session_data": session})
   ```

3. **Check project initialization status.**
   Verify if Attune AI is set up in your project:
   ```python
   from attune.hooks.scripts.first_time_init import is_initialized, get_project_root
   project_root = get_project_root()
   if not is_initialized(project_root):
       # Initialize project
   ```

## Create custom hook handlers

1. **Define a Python handler function.**
   Write a function that accepts context and returns results:
   ```python
   def custom_learning_handler(context: dict) -> dict:
       session_id = context.get("session_id")
       # Process learning data
       return {"status": "processed", "insights": insights}
   ```

2. **Register your handler.**
   Add it to the registry with an event matcher:
   ```python
   registry.register(
       event=HookEvent.LEARNING_UPDATE,
       handler=custom_learning_handler,
       description="Process learning insights",
       priority=10
   )
   ```

3. **Test your hook.**
   Verify it fires correctly:
   ```python
   test_context = {"session_id": "test123"}
   results = registry.fire_sync(HookEvent.LEARNING_UPDATE, test_context)
   assert results[0]["status"] == "processed"
   ```

## Monitor hook execution

1. **Enable execution logging.**
   Track hook performance and results:
   ```python
   # Check execution history
   log = registry.get_execution_log(limit=50)
   for entry in log:
       print(f"Hook {entry['hook_id']} took {entry['duration_ms']}ms")
   ```

2. **View hook statistics.**
   Get metrics on hook usage:
   ```python
   stats = registry.get_stats()
   print(f"Total hooks: {stats['total_hooks']}")
   print(f"Executions: {stats['total_executions']}")
   ```

## Verification

Your hooks are working correctly when:
- `registry.fire_sync()` returns expected results without errors
- Hook execution logs show your handlers running at the right events
- Built-in evaluation scripts like `run_evaluate_session()` complete successfully
- Project initialization checks return the correct status for your environment
