---
feature: plugin
depth: concept
generated_at: 2026-06-03T02:46:55.572515+00:00
source_hash: 57b8e505bab7ccba5ff519e5f59111f1ef50f2e629841d8c034de4c1391df086
status: generated
---

# Plugin

## How it works

Claude Code plugin — skills, hooks, commands, and MCP config.

The main building blocks are:

- **`SpecInfo`** — One in-flight spec discovered under a workspace root.
- **`GitState`** — Snapshot of the worktree's git state at hook fire time.

Under the hood, this feature spans 964 source
files covering:

- CLI wrapper for the ``/handoff`` slash command.
- Resume-prompt builder — single source of truth for the format.
- Shared state-discovery helpers for session-continuity hooks.

## What connects to it

This feature relates to: plugin, claude-code.

Other parts of the codebase interact with
plugin through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `SpecInfo` | One in-flight spec discovered under a workspace root. | `plugin/hooks/_state.py` |
| `GitState` | Snapshot of the worktree's git state at hook fire time. | `plugin/hooks/_state.py` |
