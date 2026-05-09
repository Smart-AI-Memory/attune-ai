---
type: faq
name: duck-typed-test-fakes-fail-isinstance-based-collectors-silently
tags: [testing, python]
source: .claude/CLAUDE.md
---

# FAQ: Why does duck-typed test fakes fail isinstance-based collectors silently?

## Answer

`collect_agent_output()` in `src/attune/workflows/agent_sdk_adapter.py` does `isinstance(message, claude_agent_sdk.AssistantMessage)`. A shape-compatible fake class (`class _FakeAssistantMessage: def __init__(self, text): self.content = [...]`) will fall through the isinstance check and leave `result_text="No results returned."` untouched — the test passes against that default answer and may appear successful.

**How to fix:**
- construct real SDK class instances in tests: `claude_agent_sdk.AssistantMessage(content=[...], model="...", parent_tool_use_id=None)` and `claude_agent_sdk.ResultMessage(subtype="success", ...)`
- Use `dataclasses.fields(Cls)` to discover the real field list

```
collect_agent_output()
```

## Related Topics
- **Error**: Detailed error: Duck-typed test fakes fail isinstance-based
  collectors silently
