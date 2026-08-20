---
type: quickstart
name: hooks-quickstart
feature: hooks
depth: quickstart
generated_at: 2026-08-20T12:28:08.536306+00:00
source_hash: 6a74897099089de928581379ad010c61f7449b270204090c659e122d08d62c1c
status: generated
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
