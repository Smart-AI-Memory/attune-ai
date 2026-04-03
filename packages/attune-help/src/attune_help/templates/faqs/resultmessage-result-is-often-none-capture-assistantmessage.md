---
type: faq
name: resultmessage-result-is-often-none-capture-assistantmessage
source: .claude/CLAUDE.md
---

# FAQ: What should I know about resultMessage.result is often None — capture AssistantMessage text too?

## Answer

All 15 SDK-native workflows only checked `ResultMessage.result` for the agent's output. But `ResultMessage` is a metadata-only final message; its `result` field is `str | None` and frequently `None`.

**How to fix:**
- `collect_agent_output()` and `build_result_text()` in `agent_sdk_adapter.py` now collect from both message types, preferring `ResultMessage.result` when present and falling back to `AssistantMessage` text

```
ResultMessage.result
```

## Related Topics
- **Error**: Detailed error: `ResultMessage.result` is often `None` — capture
  `AssistantMessage` text too
