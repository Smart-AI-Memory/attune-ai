---
type: faq
name: fastembed-is-the-local-embeddings-path-that-passes-a-50mb
source: .claude/CLAUDE.md
---

# FAQ: How do I handle fastembed is the local-embeddings path that passes a <50MB install gate?

## Answer

When `sentence-transformers` (420MB via `torch`) fails an install-size gate, don't jump to hosted embeddings. `fastembed` (Qdrant) ships ONNX-runtime-based MiniLM embeddings at ~35MB total install, no `torch`, no network at runtime once the ONNX model is downloaded at install time.

```
sentence-transformers
```

## Related Topics
- **Error**: Detailed error: `fastembed` is the local-embeddings path that passes
  a <50MB install gate
