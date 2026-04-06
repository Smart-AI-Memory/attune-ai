---
feature: cli
depth: concept
generated_at: 2026-04-06T04:33:09.132823+00:00
source_hash: 60d629c5d9c90360ec0e4d695e0e6548b4a7742f1575ea77863085ed35e3a4ef
status: generated
---

# CLI

## How it works

Command-line interface that combines traditional commands with natural language routing to AI skills.

The main building blocks are:

- **`RoutingPreference`** — Stores user's learned routing preferences for intelligent command handling.
- **`HybridRouter`** — Routes user input between traditional CLI commands and Claude Code skill invocations.

Under the hood, this feature spans 158 source
files covering:

- Hybrid CLI router that handles both structured commands and natural language
- CLI command modules for core Attune functionality
- Cost tracking commands for monitoring API usage

## What connects to it

This feature relates to: cli, commands.

Other parts of the codebase interact with
cli through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `RoutingPreference` | Stores user's learned routing preferences for intelligent command handling. | `src/attune/cli_router.py` |
| `HybridRouter` | Routes user input between traditional CLI commands and Claude Code skill invocations. | `src/attune/cli_router.py` |
