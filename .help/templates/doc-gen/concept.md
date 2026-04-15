---
type: concept
feature: doc-gen
depth: concept
generated_at: 2026-04-14T14:45:17.483499+00:00
source_hash: 67aadd029bbf773d9f478a4d4c750e25344dc6b0bd9e1edadbcf5151d83f3bff
status: generated
---

# Doc Gen

Doc-gen is an automated documentation generation system that transforms source code into comprehensive markdown documentation using a three-stage AI workflow.

## Architecture

The system orchestrates three specialized subagents — outline-planner, content-writer, and polish-reviewer — through the `DocumentGenerationWorkflow` class. Each subagent focuses on a specific aspect of documentation creation:

- **Outline-planner** structures the documentation hierarchy and identifies key modules and APIs
- **Content-writer** generates detailed content with code examples and API references
- **Polish-reviewer** performs final review and quality improvements

The workflow synthesizes outputs from all three subagents into a single structured document with Summary, Outline, Documentation, and Suggestions sections.

## Stage-specific capabilities

The system implements each documentation stage through dedicated mixins:

- **`OutlineStageMixin`** — Plans documentation structure and identifies content sections
- **`WriteStageMixin`** — Generates detailed content with code examples and API documentation
- **`PolishStageMixin`** — Reviews and refines the final documentation for clarity and completeness

Supporting mixins handle cross-cutting concerns:

- **`APIReferenceMixin`** — Extracts and formats API documentation from source code
- **`ChunkedGenerationMixin`** — Processes large codebases in manageable chunks to avoid token limits
- **`DocGenCostMixin`** — Tracks and manages API costs during generation

## Output format

Generated documentation follows a standardized structure that you can customize through the workflow configuration. The `format_doc_gen_report` function transforms raw generation results into human-readable reports, making it easy to review what was generated and identify any issues.
