---
type: warning
name: fastembed-is-the-local-embeddings-path-that-passes-a-50mb
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: `fastembed` is the local-embeddings path that passes
  a <50MB install gate

## Condition

When `sentence-transformers` (420MB via `torch`) fails an install-size gate, don't jump to hosted embeddings

## Risk

When `sentence-transformers` (420MB via `torch`) fails an install-size gate, don't jump to hosted embeddings

## Mitigation

1. When `sentence-transformers` (420MB via `torch`) fails an install-size gate, don't jump to hosted embeddings

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `fastembed` is the local-embeddings path that passes
  a <50MB install gate
