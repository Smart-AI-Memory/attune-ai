---
description: Hook System: Attune ships hook scripts that Claude Code runs on session and tool lifecycle events.
---

# Hook System

Attune's hooks are **concrete scripts that Claude Code runs** on
session and tool lifecycle events. They live under
`attune/hooks/scripts/` (e.g. `security_guard`, `worktree_path_guard`,
`lessons_reminder`, `starter_reconciler`) and are wired to events
through the plugin's `hooks.json`.

There is no in-process Python hook API. An earlier programmatic engine
(`HookRegistry` / `HookExecutor` / `HookConfig`) was removed in
v13.0.0 — it had no caller, and its originating use-case was retired
in 9.0.0.

## Lifecycle events

| Event | When fired | Typical use |
|-------|------------|-------------|
| `SessionStart` | Session begins | Orientation banners, state restore |
| `SessionEnd` / `Stop` | Session ends | Save state, lesson reminders |
| `PreToolUse` | Before a tool runs | Policy guards (block or allow) |
| `PostToolUse` | After a tool runs | Formatting, telemetry |
| `PreCompact` | Before context compaction | Pre-compaction side effects |

Event names are the Claude Code hook names.

## The stdin / exit-code contract

Claude Code invokes each script with the event payload as JSON on
stdin. The script signals its verdict through its exit code:

- **`PreToolUse`** — exit `0` to allow the tool, exit `2` to block it.
- **`PostToolUse` / `SessionStart` / `Stop` / `PreCompact`** — exit `0`;
  the script's job is a side effect, not a verdict.

Scripts **fail open** (exit `0`) on malformed input, so a bug in a hook
never blocks the user's real tool call.

```python
import json
import sys

try:
    payload = json.load(sys.stdin)       # {"tool_name": ..., "tool_input": ...}
except (json.JSONDecodeError, ValueError):
    sys.exit(0)                          # fail open

if isinstance(payload, dict) and payload.get("tool_name") == "Bash":
    print("Bash blocked by policy", file=sys.stderr)
    sys.exit(2)                          # 2 = block
sys.exit(0)                             # 0 = allow
```

## Wiring

The plugin's `hooks.json` maps each event to the script(s) that run for
it, with a per-hook timeout. To add a hook, add a module under
`attune/hooks/scripts/` and map it to an event in `hooks.json`.

## See Also

- [Hooks — how-to](how-to/hooks.md) — task recipes
- [Hooks — architecture](architecture/hooks.md) — design and contract
- [Hooks — reference](reference/hooks.md) — event/exit-code table
- [Continuous Learning](continuous-learning.md) — pattern extraction
- [CLI Reference](reference/cli-reference.md#slash-command-system) — slash command system
