---
type: error
name: forced-anthropic-tool-use-is-the-cleanest-path-to-guaranteed
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Forced Anthropic tool-use is the cleanest path to
  guaranteed-schema JSON from Claude

## Signature

Forced Anthropic tool-use is the cleanest path to
  guaranteed-schema JSON from Claude

## Root Cause

`tools=[{... schema...}], tool_choice={"type": "tool", "name": "..."}` forces the model to call the named tool; the `tool_use` block's `input` field is guaranteed to match `input_schema` — no regex extraction, no code-fence stripping, no JSON-parse fallbacks. Used in `attune_rag.eval.faithfulness.FaithfulnessJudge`. Extraction helper: walk `response.content`, pick the block with `type == "tool_use"`, read `.input`. Raise if no tool-use block is present (indicates a capability/version mismatch, not a parse error).

## Resolution

1. Used in `attune_rag.eval.faithfulness.FaithfulnessJudge`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Forced Anthropic tool-use is the cleanest path to
  guaranteed-schema JSON from Claude
