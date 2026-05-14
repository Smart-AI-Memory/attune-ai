---
feature: plugin
depth: concept
generated_at: 2026-05-14T00:09:29.490567+00:00
source_hash: dad4ff4d931be93483178512f305df4124786c91adacb4cc3420e7e53450f49d
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
