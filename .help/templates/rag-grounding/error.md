---
type: error
feature: rag-grounding
depth: error
generated_at: 2026-04-19T18:50:42.041159+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# RAG grounding errors

RAG grounding failures occur when the RAG-grounded code generation workflow cannot retrieve relevant context, process prompts, or maintain citation requirements during code generation.

## Common error signatures

- **Import errors** — `ModuleNotFoundError` or `ImportError` when `RagCodeGenWorkflow` cannot load dependencies
- **Workflow execution errors** — Exceptions from `RagCodeGenWorkflow.execute()` when retrieval or generation steps fail
- **Configuration errors** — `ValueError` or `TypeError` when workflow initialization receives invalid parameters
- **Context retrieval errors** — Network or API failures when fetching attune-help context via attune-rag
- **Prompt processing errors** — Template or formatting failures when constructing citation-forced prompts for Claude

## Where errors originate

RAG grounding errors originate in the `RagCodeGenWorkflow` class in `src/attune/workflows/rag_code_gen.py`. Check these methods based on your error's context:

- `__init__()` — Configuration and initialization failures
- `execute()` — Runtime failures during retrieval, prompt generation, or Claude interaction

## How to diagnose

1. **Check the workflow initialization.** Verify that `RagCodeGenWorkflow.__init__()` receives valid keyword arguments. Missing or malformed configuration often causes early `ValueError` or `TypeError` exceptions.

2. **Examine the execution context.** If the error occurs in `execute()`, check whether the workflow can access the attune-rag retrieval system and whether your input parameters match the expected format.

3. **Verify context retrieval.** RAG grounding depends on retrieving relevant attune-help documentation. Connection failures, API timeouts, or malformed queries can cause network-related exceptions during the retrieval phase.

4. **Inspect prompt construction.** The workflow builds citation-forced prompts using the system prompt template (`_SYSTEM_PROMPT`). Template formatting errors or missing context can cause string processing failures.

5. **Check Claude API integration.** Generation failures may stem from API authentication issues, rate limiting, or prompt length restrictions when calling Claude with the grounded prompts.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
