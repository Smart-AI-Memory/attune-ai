---
type: tip
name: cli-tip
feature: cli
depth: tip
generated_at: 2026-06-10T07:07:04.669242+00:00
source_hash: 5b5c949846a62732ae6954c6682e1c7a924430b6ac1efcd58027d681df89d386
status: generated
---

# Tip: working effectively with cli

Use `cmd_doctor` and `cmd_validate` to catch configuration problems before they surface as confusing exit codes at runtime.

**Why:** `run_workflow_with_exit_code()` returns a contract exit code — if the environment or configuration is broken, you get a non-zero exit with little context. Running `cmd_doctor` and `cmd_validate` first gives you a human-readable diagnosis before you invoke any workflow.

**Tradeoff:** Both commands make live checks against your environment, so they add a small startup cost. Skip them in CI once your environment is known-good and you want deterministic timing.

## Where this applies

The exit-code contract flows through `run_workflow_with_exit_code()` in `cli_commands._exit_codes`. Every `cmd_workflow_*` command — `cmd_workflow_list`, `cmd_workflow_info`, and `cmd_workflow_run` — ultimately relies on this contract, so a misconfigured environment fails there, not at the command that triggered the workflow.

## Quick reference

| Command | What it checks |
|---|---|
| `cmd_doctor` | Environment health and dependencies |
| `cmd_validate` | Configuration correctness |
| `cmd_workflow_run` | Runs a workflow; returns the contract exit code |
| `cmd_provider_show` / `cmd_provider_set` | Active model provider — a common source of non-zero exits |

**Source files:** `attune.cli_minimal`, `attune.cli_router`, `cli_commands.utility_commands`, `cli_commands.workflow_commands`

**Tags:** `cli`, `commands`
