---
type: error
name: metadata-can-reach-a-retriever-with-zero-signal-if-the-sidecar
confidence: Verified
tags: [security]
source: .claude/CLAUDE.md
---

# Error: Metadata can reach a retriever with zero signal if
  the sidecar schema doesn't match the loader's
  expected shape

## Signature

Metadata can reach a retriever with zero signal if
  the sidecar schema doesn't match the loader's
  expected shape

## Root Cause

attune-rag's `DirectoryCorpus` expected path-keyed `summaries.json`, but attune-help 0.5.1 shipped a feature-keyed one (`"security-audit": "..."` instead of `"concepts/tool-security-audit.md": "..."`). Result: every one of 633 corpus entries had `summary=None` at retrieval time, making the 1.5x `SUMMARY_WEIGHT` apply to zero data for months. Always validate that metadata actually reaches the retriever before spending time tuning retrieval coefficients — a one-line check on `sum(1 for e in corpus.entries() if e.summary)` would have caught this in minutes instead of weeks. Validated by a prototype that replaced the sidecar schema on one feature and saw P@1 jump +40 pts (bug-predict: 36% → 76%) without changing the retriever at all.

## Resolution

1. Always validate that metadata actually reaches the retriever before spending time tuning retrieval coefficients — a one-line check on `sum(1 for e in corpus.entries() if e.summary)` would have caught this in minutes instead of weeks

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Metadata can reach a retriever with zero signal if
  the sidecar schema doesn't match the loader's
  expected shape
