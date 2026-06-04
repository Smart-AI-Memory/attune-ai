---
type: quickstart
name: cli-quickstart
feature: cli
depth: quickstart
generated_at: 2026-06-04T23:39:47.660441+00:00
source_hash: 4b177dd28a8ce19bb06606b9ae39e4fe255d7f2fe854f3376d3330f151f3ffac
status: generated
---

# Quickstart: attune CLI

Run your first attune command and confirm the CLI is working.

```bash
attune version
```

You should see the current version string printed to stdout and the process exit with code `0`.

## Prerequisites

- attune is installed and available on your `PATH`
- You have access to the source under `src/attune/`

## Step 1: Verify your setup

Run the built-in doctor command to confirm all dependencies and configuration are in order:

```bash
attune doctor
```

A passing check prints a status line for each component. Fix any failures before continuing.

## Step 2: List available workflows

```bash
attune workflow list
```

This calls `cmd_workflow_list` and prints every registered workflow by name.

## Step 3: Run a workflow

Pick a workflow name from the previous output and run it:

```bash
attune workflow run <workflow-name>
```

`attune workflow run` calls `run_workflow_with_exit_code()` internally. Exit code `0` means success; any non-zero value signals a contract failure.

## Step 4: Check today's costs

```bash
attune costs today
```

This calls `cmd_costs_today` and prints a summary of token spend for the current day. A zero-spend summary is a valid, successful result.

**Expected output:**

```
Today's cost summary
  Requests : 1
  Tokens   : 312
  Cost     : $0.0004
```

## Next:

Run `attune help` to open the interactive help browser and find commands for memory, telemetry, and provider configuration.
