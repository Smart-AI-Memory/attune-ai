---
type: task
name: rag-grounding-task
feature: rag-grounding
depth: task
generated_at: 2026-05-21T03:20:54.619948+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# Work with rag grounding

Use rag grounding when you need to generate code backed by verified documentation — it retrieves attune-help context and forces Claude to cite real APIs and patterns rather than hallucinating features.

## Prerequisites

- Access to the project source code
- Familiarity with `src/attune/workflows/rag_code_gen.py`

## Configure the workflow

1. **Import the RagCodeGenWorkflow class:**
   ```python
   from attune.workflows.rag_code_gen import RagCodeGenWorkflow
   ```

2. **Initialize the workflow:**
   ```python
   workflow = RagCodeGenWorkflow(**kwargs)
   ```

3. **Execute with your requirements:**
   ```python
   result = workflow.execute(**kwargs)
   ```

## Extend the workflow behavior

1. **Review the base RagCodeGenWorkflow class** in `src/attune/workflows/rag_code_gen.py` to understand the existing citation and grounding mechanisms.

2. **Create a subclass for custom behavior:**
   ```python
   class CustomRagCodeGenWorkflow(RagCodeGenWorkflow):
       def execute(self, **kwargs):
           # Your custom logic here
           return super().execute(**kwargs)
   ```

3. **Preserve the citation system** — the workflow includes a `_SYSTEM_PROMPT` that enforces grounding in real attune documentation and prevents feature hallucination.

## Verify the grounding works

Run your workflow and confirm that:
- Generated code references actual attune APIs from the retrieved context
- Citations include source file references
- No invented features appear in the output

The workflow should return a `WorkflowResult` containing grounded code with proper provenance tracking.
