---
type: troubleshooting
name: cli-troubleshooting
feature: cli
depth: troubleshooting
generated_at: 2026-06-02T10:56:02.731671+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Troubleshoot cli

## Before you start

This page covers the `attune` CLI — command dispatch, argument parsing, routing user input to skills, and cost/memory/telemetry subcommands. If you hit a specific error message rather than a behavioral symptom, check the `errors/` templates first.

## Symptom table

| Symptom | Concrete check |
|---|---|
| `attune <subcommand>` exits with a non-zero code but prints nothing | Run `attune doctor` — it checks your environment and configuration and reports what is wrong |
| A cost subcommand (`costs`, `costs-today`, `costs-export`) shows no data or wrong totals | Run `attune costs` to see the full report, then `attune costs today` to narrow to today; if both show nothing, run `attune costs reset` **only if** you want to clear all data — this is irreversible |
| `attune help` returns no results or the wrong template | Confirm the template files exist under the expected `_CATEGORIES` (`errors`, `warnings`, `tips`, `references`) |
| Routing sends input to the wrong skill | Run `attune telemetry routing-stats` to see historical routing decisions, then `attune telemetry routing-check` to test a specific input against the current routing logic |
| A memory command (`remember`, `forget`, `lessons`) acts on the wrong entry | Run `attune lessons` to list all current lessons with line numbers, then use the line number with `attune forget` to target the exact entry |
| `route_user_input` returns an unexpected skill | Check the `RoutingPreference` records — specifically the `keyword`, `skill`, and `confidence` fields — by calling `HybridRouter.get_suggestions(partial)` with your input prefix |
| The CLI version does not match what you installed | Run `attune version` and compare against `get_version()` output; a mismatch points to a stale `.egg-info` or editable-install cache |

## Diagnosis steps

Work through these in order — each step is cheaper than the next.

### 1. Reproduce the failure with a minimal command

Strip the invocation to its bare required arguments and run it directly in your terminal. Confirm the failure occurs outside any wrapper script or IDE integration. For example:

```bash
attune costs
attune telemetry routing-check
attune memory recall <keyword>
```

If the failure disappears with a minimal invocation, the problem is in the calling context (environment variables, shell aliases, argument escaping), not in the CLI itself.

### 2. Run `attune doctor`

`cmd_doctor` performs built-in environment checks. Run it before inspecting any code:

```bash
attune doctor
```

Review every item it flags. Many setup and configuration issues are caught here without any further debugging.

### 3. Run `attune validate`

If `attune doctor` passes but behavior is still wrong, run:

```bash
attune validate
```

`cmd_validate` checks that the CLI's internal configuration and data files are consistent.

### 4. Check telemetry and routing state

For routing or skill-dispatch problems, use the telemetry subcommands to inspect live state before touching any code:

```bash
attune telemetry show
attune telemetry routing-stats
attune telemetry routing-check
```

For model or agent-level dispatch issues, also run:

```bash
attune telemetry models
attune telemetry agents
```

### 5. Inspect the relevant entry point

Once you have a minimal reproduction, identify which command function is failing and look at its return value. All command functions return `int` — a non-zero return signals failure. The entry points grouped by area are:

**Cost tracking:** `cmd_costs`, `cmd_costs_today`, `cmd_costs_export`, `cmd_costs_reset` in `cli_commands/cost_commands.py`

**Memory:** `cmd_remember`, `cmd_forget`, `cmd_lessons`, `cmd_memory_capture`, `cmd_memory_recall`, `cmd_memory_topics`, `cmd_memory_forget_topic` in `cli_commands/memory_commands.py`

**Telemetry:** `cmd_telemetry_show`, `cmd_telemetry_savings`, `cmd_telemetry_export`, `cmd_telemetry_routing_stats`, `cmd_telemetry_routing_check`, `cmd_telemetry_models`, `cmd_telemetry_agents`, `cmd_telemetry_signals` in `cli_commands/telemetry_commands.py`

**Routing:** `route_user_input`, `HybridRouter.route` in `attune/cli_router.py`

**Dispatch and setup:** `main`, `create_parser` in `attune/cli_minimal.py`; `cmd_setup`, `cmd_validate`, `cmd_doctor`, `cmd_features` in `cli_commands/utility_commands.py`

### 6. Run the CLI test suite

```bash
pytest -k "cli" -v
```

A failing test that covers your scenario gives you a reproducible fixture and confirms the regression boundary. If all tests pass but you still see the failure, the issue is likely environment- or state-specific — see "Common fixes" below.

## Common fixes

**Stale routing preferences**
If `HybridRouter` routes to the wrong skill, a learned `RoutingPreference` with a high `usage_count` may be overriding the default. Call `HybridRouter.learn_preference(keyword, skill, args)` to correct the mapping, which resets the association for that keyword.

**Cost data is empty after a reset**
`cmd_costs_reset` clears all cost tracking data and returns `0` on success. If you ran it unintentionally, the data cannot be recovered — cost tracking restarts from the next recorded event.

**Wrong provider active**
If commands behave unexpectedly due to model selection, check the active provider:

```bash
attune provider show
```

To change it:

```bash
attune provider set <provider-name>
```

This change affects all subsequent CLI invocations and is outside the CLI code itself — it modifies persisted provider configuration.

**Dependency version mismatch**
A dependency upgrade can silently change routing or parsing behavior. Confirm installed versions match your lockfile:

```bash
pip show attune
```

For editable installs, a stale build cache can cause `get_version()` and `attune version` to disagree. Reinstall with:

```bash
pip install -e . --no-build-isolation
```

**`is_slash_command` returning unexpected results**
If input that starts with `/` is not being routed as a slash command, confirm you are passing the raw user string — not a pre-processed or stripped version — to `is_slash_command(text)` or `route_user_input(user_input, context)`.

## Source files

- `src/attune/cli_minimal.py`
- `src/attune/cli_router.py`
- `src/attune/cli_commands/cost_commands.py`
- `src/attune/cli_commands/help_commands.py`
- `src/attune/cli_commands/memory_commands.py`
- `src/attune/cli_commands/provider_commands.py`
- `src/attune/cli_commands/telemetry_commands.py`
- `src/attune/cli_commands/utility_commands.py`
- `src/attune/cli_commands/workflow_commands.py`

**Tags:** `cli`, `commands`
