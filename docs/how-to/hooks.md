# Hooks

## Quickstart

Read the payload, decide, exit — failing open on anything malformed:

```python
import json
import sys

try:
    payload = json.load(sys.stdin)       # {"tool_name": ..., "tool_input": ...}
except (json.JSONDecodeError, ValueError):
    sys.exit(0)                          # fail open on malformed input

if isinstance(payload, dict) and payload.get("tool_name") == "Bash":
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

**Verify:** the script exits `0` on non-JSON or non-dict stdin, and
reads fields with `.get()` (never a raising index), so a hook bug can
never block a real tool call.

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

<!-- attune-generated: source_hash=5aba5457cc740ed70cb22f0f6e950c97d47eeeac8faabd7f0a716459b548cb13 feature=hooks kind=how-to generated_at=2026-08-20 -->
