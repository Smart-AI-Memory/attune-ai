---
type: error
feature: doc-gen
depth: error
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: e72f8c7df1bc5e57a104c92b8ea7ec8a43b33084d7d1ab2add257441af45c122
status: generated
---

# Doc Gen errors

Documentation generation failures occur during the multi-stage workflow that extracts API references, generates content outlines, writes documentation, and applies final polish.

## Common error signatures

- **Workflow execution failures**: Errors from `DocumentGenerationWorkflow.execute()` when the orchestration of subagents fails
- **Context initialization errors**: Problems in `default_context()` when XML configuration is invalid or missing required fields
- **Subagent coordination failures**: Communication breakdowns between the three specialized subagents (outline-planner, content-writer, polish-reviewer)
- **Report formatting errors**: Exceptions from `format_doc_gen_report()` when result data is malformed or missing expected keys
- **Cost tracking errors**: Failures in `DocGenCostMixin` when token usage cannot be calculated or limits are exceeded

## Where errors originate

Most doc-gen failures stem from the workflow orchestration or report generation:

- `DocumentGenerationWorkflow.execute()` — Main workflow execution that coordinates all three documentation generation stages
- `format_doc_gen_report()` in `src/attune/workflows/document_gen/report_formatter.py` — Report formatting that expects specific result structure
- Individual stage mixins (`OutlineStageMixin`, `WriteStageMixin`, `PolishStageMixin`) — Stage-specific processing failures
- `DocGenCostMixin` — Token cost calculation and management errors

## How to diagnose

1. **Check the workflow stage.** The error message or traceback should indicate whether failure occurred during outline planning, content writing, or polish review. Each stage has different failure modes.

2. **Validate input paths and configuration.** Verify that the source code path exists and is readable, and that any XML configuration passed to `default_context()` contains required fields.

3. **Examine subagent coordination.** If the workflow executes but produces incomplete results, check that all three subagents (_SUBAGENT_NAMES) are responding correctly and their outputs match the expected markdown structure.

4. **Verify report data structure.** If `format_doc_gen_report()` fails, inspect the `result` dictionary to ensure it contains the sections expected by the formatting logic (Summary, Outline, Documentation, Suggestions).

5. **Check cost limits.** Review token usage through `DocGenCostMixin` to determine if generation failed due to cost constraints or calculation errors.

## Source files

- `src/attune/workflows/document_gen/**`

**Tags:** `docs`, `documentation`, `generation`
