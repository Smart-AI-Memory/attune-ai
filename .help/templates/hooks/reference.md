---
type: reference
name: hooks-reference
feature: hooks
depth: reference
generated_at: 2026-08-20T12:28:08.536306+00:00
source_hash: 6a74897099089de928581379ad010c61f7449b270204090c659e122d08d62c1c
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
