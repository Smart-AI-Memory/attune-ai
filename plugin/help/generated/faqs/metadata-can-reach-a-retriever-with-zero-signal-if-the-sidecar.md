---
type: faq
name: metadata-can-reach-a-retriever-with-zero-signal-if-the-sidecar
tags: [security]
source: .claude/CLAUDE.md
---

# FAQ: Why metadata can reach a retriever with zero signal if the sidecar schema doesn't match the loader's expected shape?

## Answer

attune-rag's `DirectoryCorpus` expected path-keyed `summaries.json`, but attune-help 0.5.1 shipped a feature-keyed one (`"security-audit": "..."` instead of `"concepts/tool-security-audit.md": "..."`). Result: every one of 633 corpus entries had `summary=None` at retrieval time, making the 1.5x `SUMMARY_WEIGHT` apply to zero data for months.

**How to fix:**
- Always validate that metadata actually reaches the retriever before spending time tuning retrieval coefficients — a one-line check on `sum(1 for e in corpus.entries() if e.summary)` would have caught this in minutes instead of weeks

```
DirectoryCorpus
```

## Related Topics
- **Error**: Detailed error: Metadata can reach a retriever with zero signal if
  the sidecar schema doesn't match the loader's
  expected shape
