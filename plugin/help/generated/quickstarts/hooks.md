---
name: hooks
source: content/features/hooks.md
tags:
- hooks
- webhooks
- events
- automation
type: quickstart
---

# The hook system — shipped scripts that Claude Code runs on session and tool lifecycle events

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
