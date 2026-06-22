---
type: troubleshooting
feature: doc-gen
depth: troubleshooting
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: e72f8c7df1bc5e57a104c92b8ea7ec8a43b33084d7d1ab2add257441af45c122
status: generated
---

# Troubleshoot doc gen

## Before you start

The doc-gen feature generates comprehensive documentation from source code by orchestrating three specialized subagents: outline-planner, content-writer, and polish-reviewer. The workflow extracts API references, creates structured documentation, and manages generation costs through chunked operations.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `DocumentGenerationWorkflow.execute()` raises exception | Python traceback for the exact failure point in the workflow execution |
| Empty or malformed documentation output | Return value from `format_doc_gen_report()` and the `result` dict it processes |
| Missing API references | `APIReferenceMixin` extraction methods and source code docstring availability |
| Incomplete documentation sections | Output from outline-planner, content-writer, and polish-reviewer subagents |
| High token costs or timeouts | `DocGenCostMixin` cost tracking and chunked operation boundaries |

## Step-by-step diagnosis

1. **Reproduce with minimal workflow execution.**
   Create a simple test case calling `DocumentGenerationWorkflow.execute()` with just the required arguments. Verify the failure occurs without external dependencies or complex input data.

2. **Check subagent coordination.**
   Enable debug logging and examine the output from each of the three subagents (`_SUBAGENT_NAMES`). The workflow depends on structured markdown output from outline-planner, content-writer, and polish-reviewer working in sequence.

3. **Verify source code accessibility.**
   Confirm that the target codebase path exists and contains readable Python files. The `APIReferenceMixin` requires valid source files to extract docstrings and API information.

4. **Inspect workflow context and configuration.**
   Check the `WorkflowContext` returned by `default_context()` and any XML configuration passed in. Verify that all required workflow stages (outline, write, polish) are properly configured.

5. **Test report formatting independently.**
   Call `format_doc_gen_report()` directly with known good input data to isolate whether the issue is in generation or formatting.

## Common fixes

- **Fix missing or malformed docstrings.** The API reference extraction fails silently when source files lack proper docstrings. Add docstrings to classes and functions in the target codebase.

- **Adjust chunked operation limits.** If you encounter memory issues or timeouts, modify the chunking parameters in `ChunkedGenerationMixin` to process smaller code segments.

- **Resolve subagent communication failures.** Check that the `_SYSTEM_PROMPT` and `_TASK_PROMPT_TEMPLATE` are properly formatting the coordination messages between subagents. Verify the expected markdown structure is being produced.

- **Update workflow configuration.** If the workflow hangs or produces unexpected results, regenerate the default context with `DocumentGenerationWorkflow.default_context()` to ensure proper stage configuration.

- **Clear cost tracking state.** The `DocGenCostMixin` maintains token cost state that can become stale. Reset cost tracking if you see incorrect billing or quota errors.

## Source files

- `src/attune/workflows/document_gen/`

**Tags:** `docs`, `documentation`, `generation`
