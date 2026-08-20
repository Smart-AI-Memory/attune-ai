---
feature: hooks
summary: The hook system — shipped scripts that Claude Code runs on session and tool lifecycle events
tags: [hooks, events, automation, lifecycle]
source_globs:
  - src/attune/hooks/**
nav:
  help: hooks
  mkdocs:
    how-to: how-to/hooks
    architecture: architecture/hooks
    reference: reference/hooks
---

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

## Quickstart

Read the payload, decide, exit. A minimal `PreToolUse` guard:

```python
import json
import sys

payload = json.load(sys.stdin)          # {"tool_name": ..., "tool_input": ...}
if payload.get("tool_name") == "Bash":
    print("Bash blocked by policy", file=sys.stderr)
    sys.exit(2)                          # 2 = block
sys.exit(0)                             # 0 = allow
```

## Tasks

### Read the event payload safely

```python
import json
import sys

try:
    payload = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)                          # fail open — never block on bad input

if not isinstance(payload, dict):
    sys.exit(0)

tool_name = payload.get("tool_name", "")
```

**Verify:** the script exits `0` on any malformed stdin (non-JSON,
non-dict, wrong-typed fields) so a hook bug can never block a real
tool call.

### Block a tool from a PreToolUse hook

```python
import json
import sys

payload = json.load(sys.stdin)
if payload.get("tool_name") == "Write" and "/etc/" in str(
    payload.get("tool_input", {}).get("file_path", "")
):
    print("refusing to write under /etc", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
```

**Verify:** exit `2` blocks the tool and Claude Code surfaces the
stderr message; exit `0` lets it proceed.

## Reference

| Event | Exit contract | Typical use |
|-------|---------------|-------------|
| `PreToolUse` | `0` allow / `2` block | policy guards (`security_guard`, `worktree_path_guard`) |
| `PostToolUse` | `0` | formatting, telemetry |
| `SessionStart` | `0` | orientation banners (`starter_reconciler`) |
| `SessionEnd` / `Stop` | `0` | stash notes, lesson reminders |
| `PreCompact` | `0` | pre-compaction side effects |

Wiring: the plugin's `hooks.json` maps events → scripts under
`attune/hooks/scripts/`, each with a timeout.

## Comparison

| | attune bundled scripts | ad-hoc project hook |
|--|------------------------|---------------------|
| Define | module in `attune/hooks/scripts/` | any executable |
| Wire | plugin `hooks.json` | your `settings.json` hooks |
| Run | invoked by Claude Code | invoked by Claude Code |

Both are Claude Code hooks over the same stdin/exit-code contract;
attune's ship with the plugin and are maintained in-tree.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| Hook blocks a real tool on odd input | script raised / exited non-zero on malformed stdin | parse defensively and exit `0` on any non-dict / non-JSON payload | high |
| Tool not blocked when it should be | wrong exit code (only `2` blocks a `PreToolUse`) | `sys.exit(2)` to block | high |
| Banner or side effect missing | script exceeded its `hooks.json` timeout and was killed | keep the script fast; move slow work off the critical path | medium |
| Hook never fires | event not wired in `hooks.json`, or wrong event name | check the mapping and the Claude Code event name | medium |

### Risk areas

- **Fail open.** A `PreToolUse` guard must exit `0` on malformed input,
  never crash — a crashing guard silently stops blocking.
- **Only `2` blocks.** Any other exit code from a `PreToolUse` hook
  lets the tool through.
- **Timeouts are real.** A script slower than its `hooks.json` timeout
  is killed and its effect is lost.

### Diagnosis order

1. Is the event wired to the script in `hooks.json`?
2. What exit code does the script return for this payload?
3. Does it fail open on malformed stdin?
4. Is it finishing inside its timeout?

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** Author-curated seeds, merged
> by the FAQ Generator with live signals. Not projected verbatim.

- **Q:** Where are the hooks the plugin actually runs?
  **A:** Under `attune/hooks/scripts/` (e.g. `security_guard`,
  `worktree_path_guard`, `lessons_reminder`), wired via the plugin's
  `hooks.json`.
- **Q:** How does a hook block a tool?
  **A:** A `PreToolUse` script exits `2` to block and `0` to allow.
- **Q:** Is there a Python API to register hooks in-process?
  **A:** No — that engine was removed in v13.0.0. Attune ships hook
  scripts and lets Claude Code fire them.
- **Q:** What happens on malformed input?
  **A:** Scripts fail open (exit `0`) so a hook bug never blocks a real
  tool call.

## Notes & tips

- **Fail open on bad input.** Exit `0` on any non-JSON / non-dict
  stdin; only a deliberate policy decision should exit `2`.
- **Only `2` blocks.** Every other exit code allows the tool.
- **Keep hooks fast.** They run on the critical path under a timeout.
- **One event name space.** The event names (`PreToolUse`, …) are the
  Claude Code names.

## Design & extension

### Design decisions

- **Scripts, not an API.** Attune ships concrete hook scripts and
  registers them with Claude Code, rather than exposing an in-process
  hook engine.
- **Fail open.** Guards default to allowing the tool on any input they
  can't parse, so a hook defect degrades to a no-op instead of a block.
- **Bounded by timeout.** Each hook runs under a `hooks.json` timeout on
  the critical path.

### Extension points

- **Ship a script:** add a module under `attune/hooks/scripts/` and map
  it to an event in the plugin's `hooks.json`.
- **Guard a tool:** a `PreToolUse` script that exits `2` on the
  disallowed case and `0` otherwise.
- **React to a session:** a `SessionStart` / `Stop` script that performs
  its side effect and exits `0`.
