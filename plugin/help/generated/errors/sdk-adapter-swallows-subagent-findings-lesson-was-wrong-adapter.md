---
type: error
name: sdk-adapter-swallows-subagent-findings-lesson-was-wrong-adapter
confidence: Verified
tags: [security]
source: .claude/CLAUDE.md
---

# Error: "SDK adapter swallows subagent findings" lesson was
  wrong — adapter is fine, budget cap cuts the stream
  early

## Signature

"SDK adapter swallows subagent findings" lesson was
  wrong — adapter is fine, budget cap cuts the stream
  early

## Root Cause

Verified with a 157-message trace of `security-audit` (max_turns=30). `collect_agent_output()` at `src/attune/workflows/agent_sdk_adapter.py:48-91` already captures all `AssistantMessage` TextBlocks (including from subagents — those carry `parent_tool_use_id=<task-id>`, no filter needed). The real issue: with 4-5 Opus subagents spawned in parallel, the stream ends with `ResultMessage(result=None, num_turns=2, is_error=False)` — looks clean but is actually silent early termination at the `max_budget_usd` cap (was $2.00 for "standard" depth; bumped to $10.00 in the fix). Subagents were still exploring (emitting `ToolUseBlock`, not terminal `TextBlock`) when the stream was cut, so the orchestrator never received their findings to synthesize. Fix is in workflow config (budgets), not the adapter: raise `max_budget_usd` for multi-subagent workflows, or set `ATTUNE_MAX_BUDGET_USD=0` to disable caps, or restructure to run fewer/cheaper subagents.

## Resolution

1. Verified with a 157-message trace of `security-audit` (max_turns=30)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: "SDK adapter swallows subagent findings" lesson was
  wrong — adapter is fine, budget cap cuts the stream
  early
- Tip: Best practice: "SDK adapter swallows subagent findings" lesson was
  wrong — adapter is fine, budget cap cuts the stream
  early
