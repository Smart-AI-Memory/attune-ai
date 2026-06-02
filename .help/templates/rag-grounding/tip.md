---
type: tip
name: rag-grounding-tip
feature: rag-grounding
depth: tip
generated_at: 2026-06-02T10:56:02.717692+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# Tip: Use `execute()` as your entry point into `RagCodeGenWorkflow`

Instantiate `RagCodeGenWorkflow` and call `execute(**kwargs)` directly — don't subclass it or reconstruct its internals.

**Why:** The workflow is designed around a single call boundary. Bypassing `execute()` skips the retrieval-and-citation pipeline, so generated code loses its grounding in real attune APIs.

**Tradeoff:** All customization must go through the `**kwargs` you pass to `__init__` and `execute`. If you need behavior that neither accepts, you are working outside the intended surface — and that gap is worth filing as a feature request rather than papering over with a subclass.

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
