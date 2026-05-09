---
type: error
name: duck-typed-test-fakes-fail-isinstance-based-collectors-silently
confidence: Verified
tags: [testing, python]
source: .claude/CLAUDE.md
---

# Error: Duck-typed test fakes fail isinstance-based
  collectors silently

## Signature

Duck-typed test fakes fail isinstance-based
  collectors silently

## Root Cause

`collect_agent_output()` in `src/attune/workflows/agent_sdk_adapter.py` does `isinstance(message, claude_agent_sdk.AssistantMessage)`. A shape-compatible fake class (`class _FakeAssistantMessage: def __init__(self, text): self.content = [...]`) will fall through the isinstance check and leave `result_text="No results returned."` untouched — the test passes against that default answer and may appear successful.

## Resolution

1. construct real SDK class instances in tests: `claude_agent_sdk.AssistantMessage(content=[...], model="...", parent_tool_use_id=None)` and `claude_agent_sdk.ResultMessage(subtype="success", ...)`
2. Use `dataclasses.fields(Cls)` to discover the real field list

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Duck-typed test fakes fail isinstance-based
  collectors silently
- Task: Update test mocks and assertions
