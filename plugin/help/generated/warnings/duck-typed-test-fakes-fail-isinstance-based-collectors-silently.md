---
type: warning
name: duck-typed-test-fakes-fail-isinstance-based-collectors-silently
confidence: Verified
tags: [testing, python]
source: .claude/CLAUDE.md
---

# Warning: Duck-typed test fakes fail isinstance-based
  collectors silently

## Condition

`collect_agent_output()` in `src/attune/workflows/agent_sdk_adapter.py` does `isinstance(message, claude_agent_sdk.AssistantMessage)`

## Risk

Ignoring this guidance may cause: Duck-typed test fakes fail isinstance-based
  collectors silently

## Mitigation

1. construct real SDK class instances in tests: `claude_agent_sdk.AssistantMessage(content=[...], model="...", parent_tool_use_id=None)` and `claude_agent_sdk.ResultMessage(subtype="success", ...)`
2. Use `dataclasses.fields(Cls)` to discover the real field list

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Duck-typed test fakes fail isinstance-based
  collectors silently
