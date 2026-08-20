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
