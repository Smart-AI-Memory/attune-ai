---
type: reference
name: hooks-reference
feature: hooks
depth: reference
generated_at: 2026-08-20T13:06:14.232086+00:00
source_hash: 5aba5457cc740ed70cb22f0f6e950c97d47eeeac8faabd7f0a716459b548cb13
status: generated
---

# The hook system — shipped scripts that Claude Code runs on session and tool lifecycle events

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
