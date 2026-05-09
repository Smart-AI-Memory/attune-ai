---
type: error
name: fastembed-is-the-local-embeddings-path-that-passes-a-50mb
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: `fastembed` is the local-embeddings path that passes
  a <50MB install gate

## Signature

`fastembed` is the local-embeddings path that passes
  a <50MB install gate

## Root Cause

When `sentence-transformers` (420MB via `torch`) fails an install-size gate, don't jump to hosted embeddings. `fastembed` (Qdrant) ships ONNX-runtime-based MiniLM embeddings at ~35MB total install, no `torch`, no network at runtime once the ONNX model is downloaded at install time. Quality is comparable to sentence-transformers for retrieval and well-suited to local-corpus use cases. Consider it before reaching for hosted providers.

## Resolution

1. When `sentence-transformers` (420MB via `torch`) fails an install-size gate, don't jump to hosted embeddings

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `fastembed` is the local-embeddings path that passes
  a <50MB install gate
- Tip: Best practice: `fastembed` is the local-embeddings path that passes
  a <50MB install gate
