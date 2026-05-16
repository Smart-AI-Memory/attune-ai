---
feature: rag-grounding
depth: task
generated_at: 2026-05-16T07:57:53.307294+00:00
source_hash: b292cc405776df72a1b9d1d8305fef86784d97ef15f9c68d9509bccecf1f865a
status: generated
---

# Work with rag grounding

Use rag grounding when you need to rag-grounded code generation — retrieves attune-help context via attune-rag, feeds citation-forced prompts to claude, emits answers with provenance.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/rag_code_gen.py

## Steps

1. **Understand the class hierarchy.**
   Read the interfaces to see how rag grounding
   is structured before extending or modifying.
   The key classes are:
   - `RagCodeGenWorkflow` in `src/attune/workflows/rag_code_gen.py` — SDK-native RAG-grounded code generation workflow.
2. **Decide whether to extend or modify.**
   If the class has subclasses, extend with a new one
   rather than changing the base. If it stands alone,
   modify directly.

3. **Make your change.**
   Follow existing patterns — naming, error handling,
   and logging style.

4. **Run the related tests.**
   Target with `pytest -k "rag-grounding"`.

## Key files

- `src/attune/workflows/rag_code_gen.py`

## Common modifications

Classes you are most likely to extend:

- `RagCodeGenWorkflow` in `src/attune/workflows/rag_code_gen.py`
