---
type: quickstart
name: session-handoff-quickstart
feature: session-handoff
depth: quickstart
generated_at: 2026-07-28T03:00:44.232722+00:00
source_hash: 963aaf0dd059e464542f852a8b8c1f93be3beb0bbf89675536ba711fe6d47c66
status: generated
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
