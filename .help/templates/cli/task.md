---
type: task
name: cli-task
feature: cli
depth: task
generated_at: 2026-06-04T23:39:47.639055+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# Work with the attune CLI

Use the attune CLI when you need to run workflows, manage costs, interact with memory, or extend routing behavior from the command line.

## Prerequisites

- Access to the project source code
- Python environment with `attune` installed
- Familiarity with `src/attune/cli_minimal.py` as the main entry point

## Run a built-in CLI command

1. **Start with `main()`** in `attune.cli_minimal`. Call it directly in tests or scripts, or let the installed `attune` entry point invoke it. It accepts an optional `argv: list[str]` and returns an integer exit code.

2. **Choose the command group that matches your goal:**

   | Goal | Function | Module |
   |---|---|---|
   | Show cost report | `cmd_costs()` | `cli_commands.cost_commands` |
   | Show today's costs | `cmd_costs_today()` | `cli_commands.cost_commands` |
   | Export cost data | `cmd_costs_export()` | `cli_commands.cost_commands` |
   | Clear cost data | `cmd_costs_reset()` | `cli_commands.cost_commands` |
   | Browse help templates | `cmd_help()` | `cli_commands.help_commands` |
   | Save a lesson | `cmd_remember()` | `cli_commands.memory_commands` |
   | Remove a lesson | `cmd_forget()` | `cli_commands.memory_commands` |
   | List lessons | `cmd_lessons()` | `cli_commands.memory_commands` |
   | Save to cross-session memory | `cmd_memory_capture()` | `cli_commands.memory_commands` |
   | Recall from memory | `cmd_memory_recall()` | `cli_commands.memory_commands` |
   | List memory topics | `cmd_memory_topics()` | `cli_commands.memory_commands` |
   | Forget a memory topic | `cmd_memory_forget_topic()` | `cli_commands.memory_commands` |
   | List workflows | `cmd_workflow_list()` | `cli_commands.workflow_commands` |
   | Run a workflow | `cmd_workflow_run()` | `cli_commands.workflow_commands` |
   | Check setup | `cmd_doctor()` | `cli_commands.utility_commands` |

3. **Call the function**, passing a populated `argparse.Namespace` object. Each function returns an integer exit code.

## Run a workflow with an exit code contract

Use `run_workflow_with_exit_code()` from `cli_commands._exit_codes` when you need to execute a workflow class and map its result to a standard exit code.

1. **Import the function:**

   ```python
   from cli_commands._exit_codes import run_workflow_with_exit_code
   ```

2. **Call it with the required arguments:**

   ```python
   exit_code = run_workflow_with_exit_code(
       workflow_cls=MyWorkflow,
       input_data={"key": "value"},
       name="my-workflow",
       json_mode=False,
       print_result=print,
   )
   ```

   - `workflow_cls` — the workflow class to instantiate and execute
   - `input_data` — a `dict[str, Any]` passed to the workflow
   - `name` — a display name used in output
   - `json_mode` — set to `True` to emit JSON output instead of formatted text
   - `print_result` — a callable that receives the workflow result for display

3. **Check the return value.** The function returns an integer exit code. Pass it to `sys.exit()` if you are running from a script.

## Route user input with `HybridRouter`

Use `HybridRouter` from `attune.cli_router` when you need to map free-text user input to a skill invocation, or when you want to teach the router a new keyword preference.

1. **Instantiate the router:**

   ```python
   from attune.cli_router import HybridRouter

   router = HybridRouter()  # uses default preferences path
   ```

   Pass `preferences_path` to load or persist routing preferences from a specific file.

2. **Route an input string:**

   ```python
   result = router.route("show me today's costs")
   ```

   `route()` returns a `dict[str, Any]` describing the matched skill and arguments.

3. **Teach the router a new preference:**

   ```python
   router.learn_preference(keyword="costs", skill="cost_report", args="--today")
   ```

   This creates a `RoutingPreference` with `keyword`, `skill`, and optional `args`. The router increments `usage_count` and tracks `confidence` as the preference is used.

4. **Get autocomplete suggestions** for a partial input string:

   ```python
   suggestions = router.get_suggestions("cos")
   ```

   Returns a `list[str]` of matching completions.

## Check whether input is a slash command

Call `is_slash_command(text)` from `attune.cli_router` before routing if you need to handle slash commands (`/help`, `/forget`, etc.) separately from natural-language input:

```python
from attune.cli_router import is_slash_command

if is_slash_command(user_input):
    # handle as slash command
```

## Key files

| File | Purpose |
|---|---|
| `src/attune/cli_minimal.py` | Entry point — `main()`, `create_parser()`, `get_version()` |
| `src/attune/cli_router.py` | `HybridRouter`, `RoutingPreference`, `route_user_input()` |
| `src/attune/cli_commands/cost_commands.py` | Cost reporting and export commands |
| `src/attune/cli_commands/memory_commands.py` | Lesson and memory commands |
| `src/attune/cli_commands/workflow_commands.py` | Workflow list, info, and run commands |
| `src/attune/cli_commands/utility_commands.py` | Setup, validate, version, features, doctor |
| `src/attune/cli_commands/_exit_codes.py` | Exit code contract for workflow execution |

## Verify the task worked

- **CLI commands** return `0` on success. A non-zero return value indicates an error. Check the printed output against the expected report or confirmation message.
- **`run_workflow_with_exit_code()`** returns `0` on a successful workflow run. Capture the return value and assert it equals `0` in tests.
- **`router.route()`** returns a non-empty dict. Inspect the returned dict to confirm the expected skill name is present.
- **`router.learn_preference()`** takes effect immediately. Call `router.get_suggestions(keyword)` afterward and confirm the keyword appears in the results.
