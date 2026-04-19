---
type: troubleshooting
feature: rag-grounding
depth: troubleshooting
generated_at: 2026-04-19T06:52:01.664369+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# Troubleshoot RAG grounding

## Before you start

RAG grounding retrieves context from attune-help via attune-rag, then feeds citation-enforced prompts to Claude to generate code with verifiable provenance. The system prevents hallucination by grounding responses in real attune APIs and workflows.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `RagCodeGenWorkflow.execute()` throws exceptions | Python traceback for the exact file and line where the error occurs |
| Generated code references non-existent attune features | The retrieved RAG context - verify it contains accurate API documentation |
| Missing citations in output | The `_SYSTEM_PROMPT` enforcement - check if Claude is receiving the grounding instructions |
| Workflow returns empty `WorkflowResult` | The `execute()` method's return path and any early exit conditions |

## Step-by-step diagnosis

1. **Create a minimal reproduction case.**
   Strip your `RagCodeGenWorkflow` call down to only required arguments. Initialize the workflow with basic parameters and call `execute()` to confirm the issue persists without surrounding application logic.

2. **Check RAG context retrieval.**
   Before investigating the code generation, verify that attune-rag is returning relevant context. The quality of generated code depends entirely on the retrieved documentation being accurate and complete.

3. **Enable debug logging.**
   Set your logging level to `DEBUG` and re-run the workflow. Look for log entries that show the retrieved context, the assembled prompt sent to Claude, and any intermediate processing steps.

4. **Inspect the `RagCodeGenWorkflow` class.**
   Review the workflow implementation in `src/attune/workflows/rag_code_gen.py`. Check the `__init__` method for proper initialization and the `execute()` method for the core logic flow.

## Common fixes

- **Verify RAG dependencies.** Ensure attune-rag is properly installed and configured. Run `pip show attune-rag` to confirm the version and check that any required API keys or endpoints are accessible.

- **Clear stale context cache.** If the workflow previously worked but now generates outdated code, clear any cached RAG results or restart services that might be serving stale documentation.

- **Update the system prompt.** If citations are missing, verify that the `_SYSTEM_PROMPT` constant is being used correctly: "You generate code and explanations grounded in the attune ecosystem. Use the provided context to cite real APIs, workflow names, and CLI commands. Never invent attune features."

- **Check Claude API access.** Verify your Claude API credentials and rate limits. Network issues or authentication failures can cause silent failures in the generation pipeline.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
