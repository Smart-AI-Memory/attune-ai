---
feature: plugin
depth: concept
generated_at: 2026-05-17T18:27:08.904228+00:00
source_hash: 7c317f125965385a2a8e8ed6605ef6bd454625bc8fded43149d47d64438b73b0
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
