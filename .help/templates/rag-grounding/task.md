---
type: task
feature: rag-grounding
depth: task
generated_at: 2026-05-04T02:41:40.818285+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# Work with rag grounding

Use the RAG-grounded code generation workflow when you need to generate code and explanations backed by verified attune ecosystem documentation.

## Prerequisites

- Access to the project source code
- Familiarity with `src/attune/workflows/rag_code_gen.py`
- Understanding of RAG (Retrieval-Augmented Generation) concepts

## Steps

1. **Import the workflow class.**
   ```python
   from attune.workflows.rag_code_gen import RagCodeGenWorkflow
   ```

2. **Initialize the workflow.**
   Create a new instance with any required configuration:
   ```python
   workflow = RagCodeGenWorkflow()
   ```

3. **Prepare your query parameters.**
   Set up the execution parameters for your code generation request:
   ```python
   params = {
       "query": "your code generation request",
       # Add other parameters as needed
   }
   ```

4. **Execute the workflow.**
   Run the workflow with your parameters:
   ```python
   result = workflow.execute(**params)
   ```

5. **Extract the results.**
   Access the generated code and supporting documentation:
   ```python
   generated_code = result.code
   explanations = result.explanations
   source_citations = result.citations
   ```

## Verify success

The workflow succeeds when:
- `result.code` contains valid, executable code
- `result.citations` includes references to source documentation
- The generated code follows attune ecosystem patterns and APIs

## Key files

- `src/attune/workflows/rag_code_gen.py` — Main workflow implementation
