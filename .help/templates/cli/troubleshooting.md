---
type: troubleshooting
name: cli-troubleshooting
feature: cli
depth: troubleshooting
generated_at: 2026-06-10T07:07:04.661741+00:00
source_hash: 5b5c949846a62732ae6954c6682e1c7a924430b6ac1efcd58027d681df89d386
status: generated
---

# Troubleshoot cli

## Before you start

This page covers the `attune` CLI — command dispatch, workflow execution, routing, memory, cost tracking, and telemetry commands. The entry point is `main()` in `attune.cli_minimal`. Routing goes through `attune.cli_router`.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `attune <command>` exits with a non-zero code | Run `attune doctor` — it reports environment and configuration problems directly |
| A workflow command returns unexpectedly | Confirm the exit contract: `run_workflow_with_exit_code()` returns an `int`; check whether your caller is comparing against the correct value |
| `attune help` produces no output or errors | Verify `cmd_help()` can resolve the requested template category — valid categories are `errors`, `warnings`, `tips`, `references` |
| Routing sends input to the wrong skill | Check learned preferences with `HybridRouter.get_suggestions(partial)` and inspect the stored `RoutingPreference` fields (`keyword`, `skill`, `confidence`) |
| A slash command is not recognised | Call `is_slash_command(text)` on the raw input to confirm the text is being identified as a slash command before routing |
| Memory commands silently do nothing | Confirm the Redis-backed memory beta header `context-management-2025-06-27` is available in your environment; `cmd_memory_recall()` will return nothing if the store is unreachable |
| Cost data is missing or stale | Run `attune costs` (`cmd_costs`) then `attune costs today` (`cmd_costs_today`) to narrow the scope; if both are empty, run `attune costs reset` only as a last resort — it calls `cmd_costs_reset()`, which always returns `0` and clears all tracking data |
| `attune validate` fails after a config change | Run `cmd_validate()` directly and read the full output before assuming a code bug |

## Diagnosis steps

Work through these in order — each step is cheaper than the one that follows.

### 1. Run `attune doctor`

`cmd_doctor()` is the fastest first check. It inspects the environment and prints actionable output without modifying state:

```
attune doctor
```

Fix anything it reports before continuing.

### 2. Reproduce with a minimal invocation

Strip the call to its required arguments. If you are running a workflow, pass only the mandatory `input_data` keys to `run_workflow_with_exit_code()` and confirm the failure still occurs without additional context.

### 3. Check the version and feature flags

```
attune version
attune features
```

`cmd_version()` prints the value returned by `get_version()`. `cmd_features()` lists which features are active. A silent failure after an upgrade is often a disabled feature or a changed default model (`claude-sonnet-4-6`).

### 4. Inspect routing behaviour

If the wrong command is being dispatched, use `route_user_input()` directly to see what `HybridRouter.route()` resolves:

```python
from attune.cli_router import route_user_input
result = route_user_input("your input here")
print(result)
```

If a keyword is being routed incorrectly, check the `RoutingPreference` for that keyword — pay attention to the `confidence` and `usage_count` fields. You can correct a bad preference with:

```python
from attune.cli_router import HybridRouter
router = HybridRouter()
router.learn_preference(keyword="your-keyword", skill="correct-skill", args="")
```

### 5. Run the related tests

```
pytest -k "cli" -v
```

If a test covers the failing path, its fixtures show you the expected inputs and outputs. A failing test here points directly at a regression.

### 6. Enable debug logging

If the steps above haven't located the problem, bump Python's log level to `DEBUG` and re-run the failing command. Look for the first log line that deviates from the expected flow — that line identifies the offending module in `attune.cli_commands`.

## Common fixes

**Wrong exit code handling**
`run_workflow_with_exit_code()` always returns an `int`. If your script treats a non-zero return as a crash rather than a workflow-defined outcome, wrap the call and check the value explicitly:

```python
exit_code = run_workflow_with_exit_code(MyWorkflow, data, name="my-workflow", json_mode=False, print_result=print)
if exit_code != 0:
    # handle non-zero outcome
```

**Bad routing preference overriding the correct skill**
A `RoutingPreference` with high `usage_count` but low `confidence` can silently win. Reset it:

```python
router = HybridRouter()
router.learn_preference(keyword="bad-keyword", skill="correct-skill", args="")
```

**Provider not set**
If commands that call a model fail immediately, run:

```
attune provider show   # calls cmd_provider_show()
attune provider set    # calls cmd_provider_set()
```

**Stale cost data after a reset**
`cmd_costs_reset()` always returns `0` and cannot be undone. Export first:

```
attune costs export    # cmd_costs_export() writes data to a file
attune costs reset     # cmd_costs_reset() then clears all data
```

**Memory commands require the beta header**
`cmd_memory_agent()`, `cmd_memory_capture()`, `cmd_memory_recall()`, and related commands depend on the Redis-backed memory tool gated behind the `context-management-2025-06-27` beta. If these commands silently do nothing, the beta is not enabled in your environment — this requires a configuration change outside the CLI itself.

**Dependency version drift**
A dependency upgrade can change behaviour without a code change. Confirm installed versions:

```
pip show anthropic
```

Then compare against the version the project expects.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/**`

**Tags:** `cli`, `commands`
