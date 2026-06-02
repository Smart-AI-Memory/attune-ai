---
type: warning
name: rag-grounding-warning
feature: rag-grounding
depth: warning
generated_at: 2026-06-02T10:56:02.700632+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# RAG Grounding Cautions

`RagCodeGenWorkflow` retrieves attune-help context, feeds citation-forced prompts to Claude, and returns answers with provenance. Because the workflow couples retrieval, prompting, and code generation in a single call chain, a misstep in any one layer can silently degrade faithfulness without raising an exception.

## Risk areas

### Hallucinated attune features in generated code

The system prompt instructs the model never to invent attune features, but that guarantee depends on the retrieved context actually covering the topic being asked about. If the RAG retrieval returns thin or off-topic passages, the model may fill gaps with plausible-sounding but non-existent API names, workflow names, or CLI commands. The generated code compiles and looks reasonable — there is no runtime signal that anything is wrong.

**Mitigation:** Review generated code against the public API before using it. Any class, method, or CLI flag not present in the attune public API surface should be treated as a hallucination.

### Prompt-injection via retrieved passages

The system prompt explicitly guards against instructions embedded in `<passage>...</passage>` content — text that appears to be a directive or attempts to break out of the wrapping is treated as documentation, not as a command. However, this boundary is only as strong as the retrieval pipeline's ability to keep adversarial content out of the context window in the first place.

**Mitigation:** Treat the passage content fed to `RagCodeGenWorkflow.execute()` as untrusted input. Do not retrieve passages from sources you do not control without reviewing them first.

### `**kwargs` interfaces obscure required inputs

Both `RagCodeGenWorkflow.__init__` and `RagCodeGenWorkflow.execute` accept `**kwargs`. This means missing or misspelled arguments fail silently or produce degraded output rather than a `TypeError`. You will not get an error if you omit a required retrieval parameter — you will get a response grounded in no context at all.

**Mitigation:** Check the `WorkflowResult` returned by `execute` for provenance and citation fields before trusting the output. An empty or missing citation set is a signal that the retrieval step did not receive the inputs it needed.

### Private helpers can change without notice

The `_SYSTEM_PROMPT` constant and any other underscore-prefixed names in `rag_code_gen` are internal implementation details. If you copy or override `_SYSTEM_PROMPT` to customize behavior, your copy will silently diverge from the upstream prompt — including any future security or faithfulness fixes applied to it.

**Mitigation:** Depend only on `RagCodeGenWorkflow` and `execute` from the public API. If you need to customize prompting behavior, pass parameters through `execute(**kwargs)` rather than patching internal constants.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
