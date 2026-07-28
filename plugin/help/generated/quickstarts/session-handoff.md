---
name: session-handoff
source: content/features/session-handoff.md
tags:
- handoff
- collaboration
- multi-llm
- memory
type: quickstart
---

# Cross-provider session handoff — verified packet create/resume so any agent can pick up a branch mid-flight

## Quickstart

From any MCP client with the attune server connected, on the branch
you want to hand off:

```json
{
  "tool": "handoff_create",
  "arguments": {
    "goal": "Ship the retry-loop fix with a regression test",
    "next_action": "Run the failing test, then re-run the full suite",
    "provider": "claude-code"
  }
}
```

The receiving session — any provider — resumes with no arguments
(defaults to the current branch):

```json
{ "tool": "handoff_resume", "arguments": {} }
```

Or from Python:

```python
from attune.handoff import handoff_create, handoff_resume

created = handoff_create(".", goal="Ship the retry-loop fix", provider="claude-code")
report = handoff_resume(".")
print(report["warnings"], report["asserted"]["goal"])
```
