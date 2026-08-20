---
type: quickstart
name: hooks-quickstart
feature: hooks
depth: quickstart
generated_at: 2026-08-20T13:06:14.232086+00:00
source_hash: 5aba5457cc740ed70cb22f0f6e950c97d47eeeac8faabd7f0a716459b548cb13
status: generated
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
