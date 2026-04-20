---
type: troubleshooting
feature: rag-grounding
depth: troubleshooting
generated_at: 2026-04-19T18:51:06.004110+00:00
source_hash: 2b43bd46a0867ccd82e17c74e483eb64489f056eec8c96f498bd15452d8e7696
status: generated
---

# Troubleshoot RAG grounding

## Before you start

RAG grounding retrieves relevant context from attune-help documentation, then feeds that context to Claude with citation requirements to generate answers with provenance. When this workflow fails, the problem typically occurs in retrieval (empty or irrelevant context) or generation (hallucinated features despite grounding).

## Symptom table

| If you observe | Check |
|----------------|-------|
| Generated code references non-existent attune features | `RagCodeGenWorkflow.execute()` return value for empty context or verify the system prompt includes `_SYSTEM_PROMPT` |
| Empty or "I don't know" responses | Log the retrieved context passed to `RagCodeGenWorkflow.__init__()` and confirm documents match your query |
| Python exceptions during generation | Traceback points to the failing line in `RagCodeGenWorkflow.execute()` |
| Workflow runs but produces wrong code patterns | Compare retrieved context against expected source files — retrieval may be pulling irrelevant documentation |

## Step-by-step diagnosis

1. **Verify the workflow initializes correctly.**
   Create a minimal `RagCodeGenWorkflow` instance with logging enabled:
   ```python
   from attune.workflows.rag_code_gen import RagCodeGenWorkflow
   workflow = RagCodeGenWorkflow()
   ```
   If this throws an exception, the issue is in initialization, not execution.

2. **Inspect the retrieved context.**
   Before calling `execute()`, log what context the RAG system retrieved. Empty context means the retrieval step failed; irrelevant context means your query needs refinement.

3. **Check the system prompt application.**
   The workflow uses `_SYSTEM_PROMPT` to force citations and prevent hallucination. Verify this prompt reaches Claude by examining the full request payload in debug logs.

4. **Test with known-good queries.**
   Run the workflow with queries that should retrieve obvious documentation (like "how to create a task template"). If these fail, the problem is in the workflow itself, not your specific use case.

## Common fixes

- **No retrieved context**: The RAG system found no relevant documentation. Broaden your query terms or check that the documentation index includes the topics you're asking about.

- **Hallucinated attune features**: The system prompt isn't properly constraining generation. Verify that `_SYSTEM_PROMPT` is applied and contains the text "Never invent attune features."

- **Initialization errors**: Missing dependencies or configuration. Run `pip show attune` to confirm the package is installed and `RagCodeGenWorkflow` is importable.

- **Slow or hanging execution**: The underlying Claude API may be rate-limited or unavailable. Add timeouts to your `execute()` calls and check API status.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
