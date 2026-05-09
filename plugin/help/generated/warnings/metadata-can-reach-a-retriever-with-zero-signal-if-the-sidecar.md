---
type: warning
name: metadata-can-reach-a-retriever-with-zero-signal-if-the-sidecar
confidence: Verified
tags: [security]
source: .claude/CLAUDE.md
---

# Warning: Metadata can reach a retriever with zero signal if
  the sidecar schema doesn't match the loader's
  expected shape

## Condition

attune-rag's `DirectoryCorpus` expected path-keyed `summaries.json`, but attune-help 0.5.1 shipped a feature-keyed one (`"security-audit": "..."` instead of `"concepts/tool-security-audit.md": "..."`)

## Risk

Validated by a prototype that replaced the sidecar schema on one feature and saw P@1 jump +40 pts (bug-predict: 36% → 76%) without changing the retriever at all

## Mitigation

1. Always validate that metadata actually reaches the retriever before spending time tuning retrieval coefficients — a one-line check on `sum(1 for e in corpus.entries() if e.summary)` would have caught this in minutes instead of weeks

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Metadata can reach a retriever with zero signal if
  the sidecar schema doesn't match the loader's
  expected shape
