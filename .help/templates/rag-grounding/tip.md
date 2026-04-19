---
type: tip
feature: rag-grounding
depth: tip
generated_at: 2026-04-19T18:51:40.818605+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# Tip: Use RagCodeGenWorkflow as-is, don't extend it

Use `RagCodeGenWorkflow` through composition rather than subclassing. The workflow is designed to be configured through its constructor, not extended through inheritance.

## Why

Subclassing breaks when the internal implementation changes, and you lose the benefit of the built-in citation system that prevents hallucinated attune features.

The tradeoff: you'll write a few more lines to compose workflows together, but your code stays stable across attune updates and maintains grounded responses.
