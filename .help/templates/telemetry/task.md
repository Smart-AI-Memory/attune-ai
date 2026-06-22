---
type: task
name: telemetry-task
feature: telemetry
depth: task
generated_at: 2026-06-22T10:00:48.764701+00:00
source_hash: dba935dbb81bdeff572ce1339760a554a2afb6a7b99583b95b2a4ce078fd6abc
status: generated
---

# Work with telemetry

Use the telemetry module when you need to query usage data, review cost savings, monitor agent performance, or extend the CLI with new reporting commands.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/telemetry/`

## Steps

1. **Identify the CLI command that covers your goal.**
   Each subcommand has a single responsibility. Match your goal to the function that owns it:

   | Goal | Function | File |
   |---|---|---|
   | View recent telemetry entries | `cmd_telemetry_show()` | `cli_core.py` |
   | Calculate cost savings | `cmd_telemetry_savings()` | `cli_core.py` |
   | Review prompt cache performance | `cmd_telemetry_cache_stats()` | `cli_core.py` |
   | Analyze Sonnet → Opus fallback costs | `cmd_sonnet_opus_analysis()` | `cli_analysis.py` |
   | View per-file test status | `cmd_file_test_status()` | `cli_analysis.py` |
   | View Tier 1 automation status | `cmd_tier1_status()` | `cli_automation.py` |
   | View task routing report | `cmd_task_routing_report()` | `cli_automation.py` |
   | View agent performance metrics | `cmd_agent_performance()` | `cli_automation.py` |
   | Check usage-ping opt-in status and payload | `cmd_telemetry_status()` | `cli_commands/telemetry_commands.py` |
   | Opt in to anonymous usage pinging | `cmd_telemetry_enable()` | `cli_commands/telemetry_commands.py` |
   | Opt out of anonymous usage pinging | `cmd_telemetry_disable()` | `cli_commands/telemetry_commands.py` |

2. **Read the function's docstring, parameters, and return type.**
   Confirm that the function owns the exact behavior you need before proceeding. All CLI command functions return `int` (exit code `0` on success).

3. **Run the existing telemetry tests to establish a baseline.**
   ```
   pytest -k "telemetry"
   ```
   All tests must pass before you make any changes.

4. **Edit the target function.**
   Apply your change — new logic, additional output fields, or updated filtering. Match the naming conventions, error-handling style, and logging patterns already present in that file.

5. **Register any new subcommand in the CLI entry point.**
   If you added a new `cmd_*` function for the telemetry module, wire it up in `src/attune/telemetry/__main__.py` via `main()`. For user-facing commands like the usage-ping opt-in controls, add them to `src/attune/cli_commands/telemetry_commands.py` instead (registered through `cli_minimal.py`).

6. **Run the tests again.**
   ```
   pytest -k "telemetry"
   ```

## Key files

| File | Purpose |
|---|---|
| `src/attune/telemetry/__main__.py` | CLI entry point — `main()` dispatches all subcommands |
| `src/attune/telemetry/cli_core.py` | Core telemetry display and savings commands |
| `src/attune/telemetry/cli_analysis.py` | Cost and test-status analysis commands |
| `src/attune/telemetry/cli_automation.py` | Tier 1, task routing, and agent performance commands |
| `src/attune/telemetry/usage_ping.py` | Opt-in anonymous usage sync — enable/disable, payload building, endpoint resolution |
| `src/attune/cli_commands/telemetry_commands.py` | User-facing usage-ping commands: `cmd_telemetry_enable`, `cmd_telemetry_disable`, `cmd_telemetry_status` |

## Verify your changes

Run the telemetry CLI directly and confirm your expected output appears:

```
python -m attune.telemetry <subcommand>
```

A return code of `0` and the expected report printed to stdout confirms the command succeeded. Re-run `pytest -k "telemetry"` to confirm no regressions were introduced.
