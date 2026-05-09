---
type: faq
name: changing-the-citation-anchor-format-can-silently-regress-llm
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about changing the citation-anchor format can silently regress LLM citation fidelity even when the instructions are "equivalent"?

## Answer

initial attune-rag 0.1.5 implementation replaced `[P1] source: <path>` headers with an XML `id="P1"` attribute on a `<passage>` sentinel tag, and updated the prompt instruction from "citation marker pointing at the passages" to "pointing at the `id` attribute of the passage(s)". The A/B sweep regressed citation faithfulness from 1.00 to 0.97 and query-bucket hallucination rate from 6.7% to 33.3%.

```
[P1] source: <path>
```

## Related Topics
- **Error**: Detailed error: Changing the citation-anchor format can silently
  regress LLM citation fidelity even when the
  instructions are "equivalent"
