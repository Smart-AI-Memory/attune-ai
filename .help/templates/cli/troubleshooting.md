---
type: troubleshooting
name: cli-troubleshooting
feature: cli
depth: troubleshooting
generated_at: 2026-06-04T23:39:47.655698+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# Troubleshoot cli

## Before you start

This page covers the command-line interface and routing layer, including workflow execution, cost tracking, memory commands, telemetry, and provider management. All entry points are in `src/attune/cli_minimal.py`, `src/attune/cli_router.py`, and the modules under `src/attune/cli_commands/`.

## Symptom table

| If you observe | Check |
|----------------|-------|
| A command exits with an unexpected code | Run the command again with `attune doctor` to verify your environment, then check the return value from the relevant `cmd_*` function — each returns an `int` exit code |
| `attune workflow run` exits with the wrong code | Confirm `run_workflow_with_exit_code()` received the correct `input_data` dict and that the workflow class is registered — the function is the sole exit-code contract for workflow execution |
| A cost command (`costs`, `costs-today`, `costs-export`, `costs-reset`) shows no data or wrong totals | Check whether `cmd_costs_reset` was called recently — it clears all tracking data and always returns `0`, so it gives no warning on success |
| Routing sends input to the wrong skill | Inspect learned preferences with `HybridRouter.get_suggestions(partial)` and check stored `RoutingPreference` entries — look at the `confidence` and `usage_count` fields for stale or low-confidence entries |
| A slash command is not recognized | Call `is_slash_command(text)` directly to confirm the text is detected as a slash command before routing |
| `attune help` returns nothing or the wrong template | Run `cmd_validate` first to confirm the help system's template store is intact |
| A memory command (`remember`, `forget`, `lessons`, etc.) silently does nothing | Verify the `args` namespace passed to the command contains all required fields — these commands fail quietly when the namespace is incomplete |

## Diagnose the problem

Work through these steps from cheapest to most expensive. Stop when you find the cause.

### 1. Check your environment first

```bash
attune doctor
attune version
attune features
```

`cmd_doctor` checks the runtime environment. `cmd_version` confirms the installed build. `cmd_features` lists which capabilities are active. If any of these fail, fix the environment before investigating further.

### 2. Run setup if this is a fresh install

```bash
attune setup
```

`cmd_setup` initializes configuration that several commands depend on. Missing configuration is a common cause of silent failures in memory and provider commands.

### 3. Validate your configuration

```bash
attune validate
```

`cmd_validate` surfaces configuration problems that would otherwise cause commands to fail with misleading errors.

### 4. Reproduce with a minimal invocation

Strip the failing command to its required arguments and run it in isolation. For workflow failures, confirm that `run_workflow_with_exit_code()` is receiving the expected `workflow_cls`, `input_data`, `name`, and `json_mode` values.

### 5. Check routing behavior

If the wrong skill is being invoked, inspect the router directly:

```python
from attune.cli_router import HybridRouter, route_user_input

router = HybridRouter()
result = router.route("your input here")
print(result)

# Check what suggestions exist for a partial keyword
print(router.get_suggestions("your"))
```

A `RoutingPreference` with a low `confidence` value or high `usage_count` for the wrong skill may be overriding the expected route. Use `router.learn_preference(keyword, skill, args)` to correct it.

### 6. Run the CLI tests

```bash
pytest -k "cli" -v
```

If a test covers the failing path, its fixtures show you exactly what inputs the command expects.

## Common fixes

**Wrong exit code from `attune workflow run`**
`run_workflow_with_exit_code()` owns the exit-code contract. If the exit code is wrong, check that `workflow_cls` is the correct class (not a base class or an unrelated subclass) and that `input_data` matches the workflow's expected schema.

**Cost data missing after a reset**
`cmd_costs_reset` clears all cost tracking data and returns `0` unconditionally. If data disappeared unexpectedly, check whether `cmd_costs_reset` was invoked programmatically — for example, in a test teardown or automation script.

**Memory commands do nothing**
`cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, and `cmd_memory_forget_topic` all accept an `argparse.Namespace`. If the required attributes are absent from the namespace, the commands typically return without writing or reading anything. Reconstruct the namespace from `create_parser()` to ensure it contains the expected fields:

```python
from attune.cli_minimal import create_parser
parser = create_parser()
args = parser.parse_args(["remember", "your lesson here"])
```

**Provider commands have no effect**
`cmd_provider_show` and `cmd_provider_set` read and write provider configuration. If `cmd_provider_set` appears to succeed but `cmd_provider_show` still shows the old value, the configuration file path may differ between invocations (for example, a virtualenv versus a global install). Run `attune doctor` to confirm which configuration file is active.

**Routing picks the wrong skill every time**
A `RoutingPreference` entry with a high `usage_count` and a mismatched `skill` will consistently win over correct routes. Correct it with:

```python
router.learn_preference(keyword="the-keyword", skill="correct-skill")
```

This overwrites the stored preference for that keyword.

**Dependency version mismatch**
If a command worked previously without any code change, confirm that a dependency upgrade did not change behavior:

```bash
pip show attune
```

This fix requires a change outside the CLI itself — pin or roll back the dependency in your environment.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
