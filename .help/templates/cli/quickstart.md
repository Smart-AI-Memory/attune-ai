---
type: quickstart
name: cli-quickstart
feature: cli
depth: quickstart
generated_at: 2026-06-10T07:07:04.666709+00:00
source_hash: 5b5c949846a62732ae6954c6682e1c7a924430b6ac1efcd58027d681df89d386
status: generated
---

# Quickstart: CLI and Routing

Run your first attune command and confirm the CLI is working.

```bash
attune --help
```

You should see the top-level command listing. If you do, the CLI is installed and ready.

## Step 1: Confirm your version

```bash
attune version
```

Expected output:

```
attune <version string>
```

This calls `cmd_version` and verifies the entry point resolves correctly.

## Step 2: Run setup

```bash
attune setup
```

`cmd_setup` walks you through the minimum configuration needed before running workflows or using memory commands.

## Step 3: List available workflows

```bash
attune workflow list
```

`cmd_workflow_list` prints every registered workflow by name. Pick one from the output to use in the next step.

## Step 4: Run a workflow

```bash
attune workflow run <workflow-name>
```

`cmd_workflow_run` executes the workflow and exits with a contract exit code from `run_workflow_with_exit_code`. Exit code `0` means success.

Expected output:

```
Running <workflow-name>...
Result: { ... }
Exit code: 0
```

## Step 5: Check today's costs

```bash
attune costs today
```

`cmd_costs_today` prints a cost summary for the current session, confirming that telemetry is recording correctly.

## What you just did

- Verified the CLI entry point with `attune --help`
- Confirmed your installed version with `cmd_version`
- Configured attune with `cmd_setup`
- Listed and ran a workflow via `cmd_workflow_list` and `cmd_workflow_run`
- Checked cost tracking with `cmd_costs_today`

**Next:** Run `attune doctor` (`cmd_doctor`) to validate your full environment and surface any configuration issues before going further.
