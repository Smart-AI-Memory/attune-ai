---
type: warning
feature: doc-gen
depth: warning
generated_at: 2026-04-14T14:45:57.643752+00:00
source_hash: 67aadd029bbf773d9f478a4d4c750e25344dc6b0bd9e1edadbcf5151d83f3bff
status: generated
---

# Doc Gen cautions

## What to watch for

The document generation workflow orchestrates three specialized subagents to create comprehensive documentation from source code. The most significant risks involve cost management during chunked operations and stage coordination failures.

## Risk areas

**Cost overruns in chunked operations.** The `ChunkedGenerationMixin` processes large codebases in segments, but token consumption can escalate quickly across the outline, write, and polish stages. Each subagent (`outline-planner`, `content-writer`, `polish-reviewer`) operates independently and doesn't share token budgets, making it difficult to predict total costs upfront.

**Stage dependencies breaking silently.** The workflow executes three distinct stages where each depends on output from the previous stage. If the outline planner produces malformed structure data, the content writer may generate incomplete sections, and the polish reviewer will work with inconsistent input. These failures often propagate without clear error messages.

**API reference extraction inconsistencies.** The `APIReferenceMixin` extracts docstrings and function signatures, but it can miss dynamically defined methods, inherited behavior from complex class hierarchies, or modules with conditional imports. The generated documentation may appear complete while missing critical API details.

**Report formatting edge cases.** The `format_doc_gen_report()` function structures the final output, but it assumes specific keys exist in the result dictionary. When subagents return unexpected data structures or partial results, the formatter can produce truncated reports without indicating what content was dropped.

## How to avoid problems

**Set explicit cost limits before starting.** Use the `DocGenCostMixin` to establish token budgets for each stage rather than relying on default limits. Monitor consumption during the outline phase since it determines the scope for subsequent stages.

**Validate stage outputs immediately.** Check that each stage produces the expected data structure before proceeding to the next. The outline stage should return structured markdown with clear section headers, and the write stage should populate all outlined sections.

**Test API extraction on your specific codebase patterns.** Run the workflow on a small subset of your code first to identify whether the extraction logic handles your project's inheritance patterns, dynamic imports, and documentation styles correctly.

**Verify complete report generation.** After workflow execution, check that the final report contains all four expected sections (Summary, Outline, Documentation, Suggestions) and that no placeholder text remains from incomplete processing.

## Source files

- `src/attune/workflows/document_gen/**`

**Tags:** `docs`, `documentation`, `generation`
