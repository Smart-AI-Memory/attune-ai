---
type: faq
name: provenance-citation-records-usually-store-short-previews-not
tags: [packaging, python]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about provenance/citation records usually store short previews, not full content — preserve the exact context separately when downstream evaluators need it?

## Answer

`attune_rag.provenance.CitedSource.excerpt` caps at 200 chars. A faithfulness judge fed `.excerpt` would score answers against truncated passages and mis-flag supported claims as unsupported.

**How to fix:**
- add a `context: str` field on the pipeline result dataclass (`RagResult.context` in this case) so downstream consumers get the *exact* passage block the generator saw

```
attune_rag.provenance.CitedSource.excerpt
```

## Related Topics
- **Error**: Detailed error: Provenance/citation records usually store short
  previews, not full content — preserve the exact context
  separately when downstream evaluators need it
