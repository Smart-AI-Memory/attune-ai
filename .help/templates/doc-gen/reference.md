---
feature: doc-gen
depth: reference
generated_at: 2026-04-06T04:28:26.453959+00:00
source_hash: 444c6caa95ffb8aba3f6ccaa58d9ed8e39b6778803e88559314abcc374802863
status: generated
---

# Doc Gen reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `APIReferenceMixin` | Extracts and generates API reference documentation from source code. | `src/attune/workflows/document_gen/api_reference.py` |
| `ChunkedGenerationMixin` | Processes large documentation tasks in smaller, manageable chunks with progress display. | `src/attune/workflows/document_gen/chunked_generation.py` |
| `DocGenCostMixin` | Tracks and manages API costs during document generation workflows. | `src/attune/workflows/document_gen/cost_management.py` |
| `OutlineStageMixin` | Creates structured document outlines from source code analysis. | `src/attune/workflows/document_gen/outline_stage.py` |
| `PolishStageMixin` | Reviews and refines generated documentation in the final workflow stage. | `src/attune/workflows/document_gen/polish_stage.py` |
| `DocumentGenerationWorkflow` | Orchestrates the complete process of creating documentation from source code. | `src/attune/workflows/document_gen/workflow.py` |
| `WriteStageMixin` | Generates documentation content from analyzed source code and outlines. | `src/attune/workflows/document_gen/write_stage.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `format_doc_gen_report()` | Converts document generation results into readable summary reports. | `src/attune/workflows/document_gen/report_formatter.py` |


## Source files

- `src/attune/workflows/document_gen/**`

## Tags

`docs`, `documentation`, `generation`
