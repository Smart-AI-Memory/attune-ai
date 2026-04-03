---
type: error
name: resultmessage-result-is-often-none-capture-assistantmessage
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: `ResultMessage.result` is often `None` — capture
  `AssistantMessage` text too

## Signature

`ResultMessage.result` is often `None` — capture
  `AssistantMessage` text too

## Root Cause

All 15 SDK-native workflows only checked `ResultMessage.result` for the agent's output. But `ResultMessage` is a metadata-only final message; its `result` field is `str | None` and frequently `None`. The actual analysis text lives in `AssistantMessage.content` `TextBlock` entries emitted throughout the conversation.

## Resolution

1. `collect_agent_output()` and `build_result_text()` in `agent_sdk_adapter.py` now collect from both message types, preferring `ResultMessage.result` when present and falling back to `AssistantMessage` text

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `ResultMessage.result` is often `None` — capture
  `AssistantMessage` text too
