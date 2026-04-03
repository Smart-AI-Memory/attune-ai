---
type: warning
name: resultmessage-result-is-often-none-capture-assistantmessage
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: `ResultMessage.result` is often `None` — capture
  `AssistantMessage` text too

## Condition

All 15 SDK-native workflows only checked `ResultMessage.result` for the agent's output

## Risk

The actual analysis text lives in `AssistantMessage.content` `TextBlock` entries emitted throughout the conversation

## Mitigation

1. `collect_agent_output()` and `build_result_text()` in `agent_sdk_adapter.py` now collect from both message types, preferring `ResultMessage.result` when present and falling back to `AssistantMessage` text

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `ResultMessage.result` is often `None` — capture
  `AssistantMessage` text too
