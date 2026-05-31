---
feature: cli
depth: concept
generated_at: 2026-05-31T20:54:22.256716+00:00
source_hash: f096af83524c307f70d1109f65025c4a3be1b73400f30f51bb9cdba973c59aa6
status: generated
---

# Cli

## How it works

Command-line interface and routing.

The main building blocks are:

- **`RoutingPreference`** — User's learned routing preferences.
- **`HybridRouter`** — Routes user input to Claude Code skill invocations.

Under the hood, this feature spans 10 source
files covering:

- Hybrid CLI Router - Skills + Natural Language
- CLI command modules for attune.
- CLI commands for cost tracking.

## What connects to it

This feature relates to: cli, commands.

Other parts of the codebase interact with
cli through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `RoutingPreference` | User's learned routing preferences. | `src/attune/cli_router.py` |
| `HybridRouter` | Routes user input to Claude Code skill invocations. | `src/attune/cli_router.py` |
