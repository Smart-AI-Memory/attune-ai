---
feature: doc-gen
depth: reference
generated_at: 2026-04-13T16:54:59.269438+00:00
source_hash: 67aadd029bbf773d9f478a4d4c750e25344dc6b0bd9e1edadbcf5151d83f3bff
status: generated
---

# Doc Gen reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `APIReferenceMixin` | Extracts and generates API reference documentation from source code. | `src/attune/workflows/document_gen/api_reference.py` |
| `ChunkedGenerationMixin` | Processes large documentation tasks in manageable chunks with progress tracking. | `src/attune/workflows/document_gen/chunked_generation.py` |
| `DocGenCostMixin` | Tracks and manages API costs during documentation generation. | `src/attune/workflows/document_gen/cost_management.py` |
| `OutlineStageMixin` | Creates structured outlines for documentation before content generation. | `src/attune/workflows/document_gen/outline_stage.py` |
| `PolishStageMixin` | Reviews and refines generated documentation for final output. | `src/attune/workflows/document_gen/polish_stage.py` |
| `DocumentGenerationWorkflow` | Orchestrates the complete documentation generation process from source code to finished docs. | `src/attune/workflows/document_gen/workflow.py` |
| `WriteStageMixin` | Generates documentation content based on source code analysis and outlines. | `src/attune/workflows/document_gen/write_stage.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `format_doc_gen_report()` | Formats documentation generation results into readable progress and summary reports. | `src/attune/workflows/document_gen/report_formatter.py` |

## Source files

- `src/attune/workflows/document_gen/**`

## Tags

`docs`, `documentation`, `generation`
