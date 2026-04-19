---
type: tip
feature: rag-grounding
depth: tip
generated_at: 2026-04-19T06:52:33.786530+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# Use RagCodeGenWorkflow for citation-backed code generation

## Recommendation

Use `RagCodeGenWorkflow` when you need generated code that references real attune APIs and patterns. This workflow retrieves relevant documentation context and forces the LLM to cite actual source files rather than hallucinating features.

## Why

The system prompt explicitly prohibits inventing attune capabilities and requires citing source files, which prevents the common problem of generated code using non-existent APIs.

## Usage

```python
workflow = RagCodeGenWorkflow(**config)
result = workflow.execute(query="How do I implement a custom validator?")
```

The workflow handles the RAG retrieval and prompt engineering automatically — you focus on crafting good queries.

## Tradeoff

Generation is slower than direct LLM calls because it includes a retrieval step, but the accuracy gain typically justifies the latency cost for production code.

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
