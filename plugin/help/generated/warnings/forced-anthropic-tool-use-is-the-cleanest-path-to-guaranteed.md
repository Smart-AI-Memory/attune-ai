---
type: warning
name: forced-anthropic-tool-use-is-the-cleanest-path-to-guaranteed
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: Forced Anthropic tool-use is the cleanest path to
  guaranteed-schema JSON from Claude

## Condition

`tools=[{... schema...}], tool_choice={"type": "tool", "name": "..."}` forces the model to call the named tool; the `tool_use` block's `input` field is guaranteed to match `input_schema` — no regex extraction, no code-fence stripping, no JSON-parse fallbacks

## Risk

`tools=[{... schema...}], tool_choice={"type": "tool", "name": "..."}` forces the model to call the named tool; the `tool_use` block's `input` field is guaranteed to match `input_schema` — no regex extraction, no code-fence stripping, no JSON-parse fallbacks

## Mitigation

1. Used in `attune_rag.eval.faithfulness.FaithfulnessJudge`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Forced Anthropic tool-use is the cleanest path to
  guaranteed-schema JSON from Claude
