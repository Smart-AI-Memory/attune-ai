---
type: faq
name: sdk-adapter-swallows-subagent-findings-lesson-was-wrong-adapter
tags: [security]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about "SDK adapter swallows subagent findings" lesson was wrong — adapter is fine, budget cap cuts the stream early?

## Answer

Verified with a 157-message trace of `security-audit` (max_turns=30). `collect_agent_output()` at `src/attune/workflows/agent_sdk_adapter.py:48-91` already captures all `AssistantMessage` TextBlocks (including from subagents — those carry `parent_tool_use_id=<task-id>`, no filter needed).

```
security-audit
```

## Related Topics
- **Error**: Detailed error: "SDK adapter swallows subagent findings" lesson was
  wrong — adapter is fine, budget cap cuts the stream
  early
