---
type: tip
name: rag-grounding-tip
feature: rag-grounding
depth: tip
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 88333793edaf078345820f76455b27a1c759145c2e48dd64da93abf6f2d61450
status: generated
---

# Tip: Use `execute()` as your entry point into `RagCodeGenWorkflow`

Instantiate `RagCodeGenWorkflow` and call `execute(**kwargs)` directly — don't subclass it or reconstruct its internals.

**Why:** The workflow is designed around a single call boundary. Bypassing `execute()` skips the retrieval-and-citation pipeline, so generated code loses its grounding in real attune APIs.

**Tradeoff:** All customization must go through the `**kwargs` you pass to `__init__` and `execute`. If you need behavior that neither accepts, you are working outside the intended surface — and that gap is worth filing as a feature request rather than papering over with a subclass.

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
