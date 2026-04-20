---
type: warning
feature: rag-grounding
depth: warning
generated_at: 2026-04-19T18:50:54.599261+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# RAG grounding cautions

## What to watch for

RAG-grounded code generation retrieves attune-help context via attune-rag, feeds citation-forced prompts to Claude, and emits answers with provenance. The system's accuracy depends on proper context retrieval and citation enforcement.

## Risk areas

### Context retrieval failures produce hallucinated APIs

When `RagCodeGenWorkflow` cannot retrieve relevant context, the underlying language model fills gaps with plausible-sounding but nonexistent attune features. You'll see method names, CLI commands, or workflow classes that don't exist in the actual codebase.

**Mitigation:** Validate all generated code references against the actual attune API documentation before using them.

### Citation enforcement bypassed by clever prompting

The `_SYSTEM_PROMPT` instructs Claude to "never invent attune features," but sufficiently creative input prompts can override this constraint. User prompts that begin with "ignore previous instructions" or similar jailbreaking patterns can compromise citation discipline.

**Mitigation:** Sanitize user inputs and monitor generated outputs for invented APIs that don't appear in the retrieved context.

### Stale context leads to deprecated API usage

RAG retrieval pulls from indexed documentation that may lag behind rapid API changes. Generated code might reference methods or parameters that were recently deprecated or removed.

**Mitigation:** Keep your attune-rag index synchronized with the latest codebase, especially after major releases.

### Workflow state pollution between executions

`RagCodeGenWorkflow.execute()` may retain state from previous invocations if not properly reset. This can cause context bleeding where one generation request influences subsequent ones.

**Mitigation:** Create fresh workflow instances for each generation request, or verify that `execute()` properly cleans up internal state.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
