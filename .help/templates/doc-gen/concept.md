---
type: concept
feature: doc-gen
depth: concept
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: e72f8c7df1bc5e57a104c92b8ea7ec8a43b33084d7d1ab2add257441af45c122
status: generated
---

# Doc Gen

Doc Gen creates comprehensive documentation by analyzing your source code and coordinating three specialized AI agents to produce structured, accurate docs that reflect your actual codebase.

## Three-stage generation process

Doc Gen uses a pipeline approach where each stage handles a specific aspect of documentation creation:

| Stage | Agent | Responsibility |
|-------|-------|----------------|
| **Outline** | outline-planner | Scans codebase structure and creates documentation hierarchy |
| **Write** | content-writer | Generates detailed content with code examples and API references |
| **Polish** | polish-reviewer | Reviews and refines the final output for clarity and consistency |

The `DocumentGenerationWorkflow` orchestrates these agents, ensuring each focuses on its domain while producing a cohesive final document.

## Chunked processing for large codebases

When documenting complex projects, Doc Gen breaks the work into manageable chunks to avoid overwhelming the AI agents:

- **`ChunkedGenerationMixin`** splits large codebases into logical units
- **`APIReferenceMixin`** extracts function signatures, class hierarchies, and type hints
- **`DocGenCostMixin`** tracks token usage across all stages to manage API costs

This approach ensures that even extensive codebases get thorough documentation without hitting token limits or generating superficial coverage.

## Output structure

Every Doc Gen run produces a structured markdown document with four consistent sections:

- **Summary**: A 2-3 sentence overview of the documented codebase and its purpose
- **Outline**: The documentation structure listing modules, APIs, and example sections
- **Documentation**: Full content with code examples and API references for each section
- **Suggestions**: Recommendations for improving documentation coverage and organization

## When to use Doc Gen

Run Doc Gen when you need comprehensive documentation that accurately reflects your current codebase structure. Unlike manually written docs that drift from the code, Doc Gen reads the actual source files and generates content based on what's really there — function signatures, module exports, class hierarchies, and import relationships.
