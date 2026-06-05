---
feature: cli
depth: concept
generated_at: 2026-06-05T16:32:09.109066+00:00
source_hash: 198ad869d0b029e3926d86fd51b53c7d1a800d65335cb982b9331b5ee6c9bcaa
status: generated
---

# Cli

## How it works

Command-line interface and routing.

The main building blocks are:

- **`RoutingPreference`** — User's learned routing preferences.
- **`HybridRouter`** — Routes user input to Claude Code skill invocations.

Under the hood, this feature spans 12 source
files covering:

- Hybrid CLI Router - Skills + Natural Language
- CLI command modules for attune.
- Exit-code contract for ``attune workflow run``.

## What connects to it

This feature relates to: cli, commands.

Other parts of the codebase interact with
cli through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `RoutingPreference` | User's learned routing preferences. | `src/attune/cli_router.py` |
| `HybridRouter` | Routes user input to Claude Code skill invocations. | `src/attune/cli_router.py` |
