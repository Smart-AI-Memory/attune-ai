---
type: faq
name: forced-anthropic-tool-use-is-the-cleanest-path-to-guaranteed
source: .claude/CLAUDE.md
---

# FAQ: What should I know about forced Anthropic tool-use is the cleanest path to guaranteed-schema JSON from Claude?

## Answer

`tools=[{... schema...}], tool_choice={"type": "tool", "name": "..."}` forces the model to call the named tool; the `tool_use` block's `input` field is guaranteed to match `input_schema` — no regex extraction, no code-fence stripping, no JSON-parse fallbacks. Extraction helper: walk `response.content`, pick the block with `type == "tool_use"`, read `.input`.

**How to fix:**
- Used in `attune_rag.eval.faithfulness.FaithfulnessJudge`

```
tools=[{... schema...}], tool_choice={"type": "tool", "name": "..."}
```

## Related Topics
- **Error**: Detailed error: Forced Anthropic tool-use is the cleanest path to
  guaranteed-schema JSON from Claude
