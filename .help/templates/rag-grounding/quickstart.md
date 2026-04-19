---
type: quickstart
feature: rag-grounding
depth: quickstart
generated_at: 2026-04-19T18:51:32.292487+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# Quickstart: RAG-Grounded Code Generation

Create a workflow that generates code and explanations grounded in real attune documentation and APIs.

```python
from attune.workflows.rag_code_gen import RagCodeGenWorkflow

workflow = RagCodeGenWorkflow()
result = workflow.execute(query="How do I create a template?")
print(result)
```

## Step 1: Import and instantiate the workflow

```python
from attune.workflows.rag_code_gen import RagCodeGenWorkflow

workflow = RagCodeGenWorkflow()
```

The workflow connects to attune-rag for context retrieval and uses Claude for generation.

## Step 2: Execute with your query

```python
result = workflow.execute(query="How do I create a template?")
```

The workflow retrieves relevant context from attune-help and generates a response that cites real APIs and workflow names.

## Step 3: Examine the grounded output

```python
print(result)
```

You'll see code examples with citations to actual source files and APIs. The system prompt ensures Claude never invents attune features.

## What you just did

- Set up RAG-grounded code generation that pulls from real attune documentation
- Generated responses that cite actual APIs and patterns with source provenance
- Created a workflow that prevents hallucination by grounding answers in retrieved context

## Next:

Say **"how does RAG grounding work?"** to understand the retrieval and citation mechanism in detail.
