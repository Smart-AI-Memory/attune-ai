---
type: warning
name: sdk-adapter-swallows-subagent-findings-lesson-was-wrong-adapter
confidence: Verified
tags: [security]
source: .claude/CLAUDE.md
---

# Warning: "SDK adapter swallows subagent findings" lesson was
  wrong — adapter is fine, budget cap cuts the stream
  early

## Condition

Verified with a 157-message trace of `security-audit` (max_turns=30)

## Risk

`collect_agent_output()` at `src/attune/workflows/agent_sdk_adapter.py:48-91` already captures all `AssistantMessage` TextBlocks (including from subagents — those carry `parent_tool_use_id=<task-id>`, no filter needed)

## Mitigation

1. Verified with a 157-message trace of `security-audit` (max_turns=30)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: "SDK adapter swallows subagent findings" lesson was
  wrong — adapter is fine, budget cap cuts the stream
  early
