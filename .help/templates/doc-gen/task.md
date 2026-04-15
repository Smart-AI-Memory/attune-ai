---
type: task
feature: doc-gen
depth: task
generated_at: 2026-04-14T14:45:26.816629+00:00
source_hash: 67aadd029bbf773d9f478a4d4c750e25344dc6b0bd9e1edadbcf5151d83f3bff
status: generated
---

# Work with doc gen

Use doc gen when you need to automatically generate documentation from your source code, including API references, module overviews, and structured documentation with examples.

## Prerequisites

- Access to the project source code
- The codebase path you want to document

## Generate documentation

1. **Import the workflow class.**
   ```python
   from attune.workflows.document_gen import DocumentGenerationWorkflow
   ```

2. **Create a workflow instance.**
   ```python
   workflow = DocumentGenerationWorkflow()
   ```

3. **Execute the generation.**
   ```python
   result = workflow.execute(path="/path/to/your/codebase")
   ```

4. **Format the output.**
   ```python
   from attune.workflows.document_gen import format_doc_gen_report

   report = format_doc_gen_report(result.data, {"path": "/path/to/your/codebase"})
   print(report)
   ```

## Verify success

The workflow succeeds when:
- The result contains sections for Summary, Outline, Documentation, and Suggestions
- API references are extracted and formatted as markdown
- Code examples are included where applicable
- File paths are cited when referencing source code

## Configure generation stages

The workflow operates in three specialized stages that you can customize:

- **Outline stage**: Plans the documentation structure
- **Write stage**: Generates the actual content with examples
- **Polish stage**: Reviews and refines the final output

Each stage uses dedicated subagents (outline-planner, content-writer, polish-reviewer) to ensure comprehensive coverage.

## Key files

- `src/attune/workflows/document_gen/workflow.py` — Main DocumentGenerationWorkflow class
- `src/attune/workflows/document_gen/report_formatter.py` — Output formatting utilities
- `src/attune/workflows/document_gen/mixins/` — Stage-specific generation logic
