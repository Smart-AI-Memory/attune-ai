---
type: task
feature: rag-grounding
depth: task
generated_at: 2026-04-19T18:50:29.164063+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# Work with rag grounding

Use rag grounding when you need code generation that cites real attune features and patterns rather than hallucinating APIs or workflows.

## Prerequisites

- Access to the project source code
- Familiarity with `src/attune/workflows/rag_code_gen.py`

## Steps

1. **Import the workflow class.**
   ```python
   from attune.workflows.rag_code_gen import RagCodeGenWorkflow
   ```

2. **Initialize the workflow.**
   Create an instance with any required configuration:
   ```python
   workflow = RagCodeGenWorkflow()
   ```

3. **Execute code generation.**
   Call the workflow with your specific requirements:
   ```python
   result = workflow.execute(**kwargs)
   ```
   The workflow retrieves relevant context from attune-help via attune-rag, then sends citation-enforced prompts to Claude.

4. **Extract generated code and provenance.**
   The `WorkflowResult` contains both the generated code and source citations showing which attune features informed the response.

## Verify success

Check that the generated code includes citations to real attune files and features rather than invented APIs. The system prompt enforces this: "Never invent attune features. When referencing a pattern, note the source file it came from."

## Key files

- `src/attune/workflows/rag_code_gen.py` — Contains `RagCodeGenWorkflow` class
