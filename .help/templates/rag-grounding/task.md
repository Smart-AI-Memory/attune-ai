---
type: task
name: rag-grounding-task
feature: rag-grounding
depth: task
generated_at: 2026-06-02T10:56:02.679193+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# Generate grounded code with RAG

Use `RagCodeGenWorkflow` when you need to generate code that cites real attune APIs, workflow names, and CLI commands — retrieved from attune-help context and verified against actual source documentation.

## Prerequisites

- Read access to `src/attune/workflows/rag_code_gen.py`
- A Python environment where you can import from `workflows.rag_code_gen`

## Instantiate and execute the workflow

1. **Import `RagCodeGenWorkflow`.**
   Add the following import to your module:

   ```python
   from workflows.rag_code_gen import RagCodeGenWorkflow
   ```

2. **Instantiate the workflow.**
   Pass any configuration as keyword arguments to `__init__`:

   ```python
   workflow = RagCodeGenWorkflow(**your_kwargs)
   ```

3. **Call `execute` to run the workflow.**
   Pass your generation parameters as keyword arguments. The method returns a `WorkflowResult`:

   ```python
   result = workflow.execute(**your_kwargs)
   ```

4. **Inspect the result for provenance.**
   The `WorkflowResult` includes citations sourced from retrieved attune-help passages. Verify that any referenced APIs, workflow names, and CLI commands appear in those citations — the workflow is designed never to invent attune features.

5. **Run the related tests** to confirm your usage is correct:

   ```shell
   pytest -k "rag-grounding"
   ```

## Verify success

Your call succeeded when `execute` returns a `WorkflowResult` without raising an exception and the result contains citations that trace back to real attune-help source files. If the output references an attune feature that does not appear in the cited passages, the grounding has failed and you should review the context retrieval step.

## Key files

- `src/attune/workflows/rag_code_gen.py` — defines `RagCodeGenWorkflow` and its `execute` method
