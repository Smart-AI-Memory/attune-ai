---
type: concept
name: hooks-concept
feature: hooks
depth: concept
generated_at: 2026-08-20T12:28:08.536306+00:00
source_hash: 6a74897099089de928581379ad010c61f7449b270204090c659e122d08d62c1c
status: generated
---

# The hook system — shipped scripts that Claude Code runs on session and tool lifecycle events

## Overview

Attune's hooks are **concrete scripts that Claude Code runs** on
session and tool lifecycle events. They live under
`attune/hooks/scripts/` (e.g. `security_guard`, `worktree_path_guard`,
`lessons_reminder`, `starter_reconciler`) and are wired to events
through the plugin's `hooks.json`. Claude Code invokes each script over
a **stdin-JSON / exit-code contract** — the script reads an event
payload on stdin and signals its verdict through its exit code.

There is no in-process Python hook API: attune registers its scripts
with Claude Code and lets Claude Code fire them. (An earlier
programmatic engine — `HookRegistry` / `HookExecutor` / `HookConfig` —
was removed in v13.0.0; it had no caller, and its originating use-case
was retired in 9.0.0.)

## Concepts

### Lifecycle events

Claude Code fires hooks at named lifecycle points — `PreToolUse`,
`PostToolUse`, `SessionStart`, `SessionEnd`, `PreCompact`, and `Stop`.
Each event carries a JSON payload (for tool events, `tool_name` and
`tool_input`).

### The stdin / exit-code contract

A hook script reads the event JSON from stdin and exits:

- **`PreToolUse`** — exit `0` to allow the tool, exit `2` to block it.
  A non-blocking script that only observes should still exit `0`.
- **`PostToolUse` / `SessionStart` / `Stop`** — exit `0`; the script's
  job is a side effect (a banner, a stashed note, a telemetry write),
  not a verdict.

Scripts fail **open** (exit `0`) on malformed input so a bug in a hook
never blocks the user's real tool call.

### Where the scripts live

Every hook is a module under `attune/hooks/scripts/`. The plugin's
`hooks.json` maps each event to the script(s) that run for it, along
with a per-hook timeout.
