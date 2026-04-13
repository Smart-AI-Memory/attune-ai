---
feature: cli
depth: concept
generated_at: 2026-04-13T16:59:36.754504+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# CLI

## How it works

Command-line interface that combines traditional commands with natural language routing to AI skills.

The main building blocks are:

- **`RoutingPreference`** — Stores user's learned routing preferences for hybrid command interpretation.
- **`HybridRouter`** — Routes user input between structured CLI commands and Claude Code skill invocations.

Under the hood, this feature spans 10 source
files covering:

- Hybrid CLI router that handles both skills and natural language
- Core CLI command modules for the Attune platform
- Cost tracking commands for monitoring API usage

## What connects to it

This feature relates to: cli, commands.

Other parts of the codebase interact with
cli through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `RoutingPreference` | Stores user's learned routing preferences for hybrid command interpretation. | `src/attune/cli_router.py` |
| `HybridRouter` | Routes user input between structured CLI commands and Claude Code skill invocations. | `src/attune/cli_router.py` |
