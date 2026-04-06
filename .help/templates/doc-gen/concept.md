---
feature: doc-gen
depth: concept
generated_at: 2026-04-06T04:28:11.277603+00:00
source_hash: 444c6caa95ffb8aba3f6ccaa58d9ed8e39b6778803e88559314abcc374802863
status: generated
---

# Doc Gen

## How it works

Generate documentation from source code through API reference extraction, chunked processing, and multi-stage workflow management.

The main building blocks are:

- **`APIReferenceMixin`** — Extracts API references and generates documentation from source code.
- **`ChunkedGenerationMixin`** — Processes large documentation tasks in manageable chunks with progress display.
- **`DocGenCostMixin`** — Tracks and manages costs associated with documentation generation operations.
- **`OutlineStageMixin`** — Generates initial documentation outlines and structure.
- **`PolishStageMixin`** — Performs final review and refinement of generated documentation.

Under the hood, this feature spans 20 source
files covering:

- API reference extraction from source code
- Chunked processing of large documentation sets
- Configuration management for generation workflows
- Cost tracking and budget management

## What connects to it

This feature relates to: docs, documentation, generation.

Other parts of the codebase interact with
doc gen through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `APIReferenceMixin` | Extracts API references and generates documentation from source code. | `src/attune/workflows/document_gen/api_reference.py` |
| `ChunkedGenerationMixin` | Processes large documentation tasks in manageable chunks with progress display. | `src/attune/workflows/document_gen/chunked_generation.py` |
| `DocGenCostMixin` | Tracks and manages costs associated with documentation generation operations. | `src/attune/workflows/document_gen/cost_management.py` |
| `OutlineStageMixin` | Generates initial documentation outlines and structure. | `src/attune/workflows/document_gen/outline_stage.py` |
| `PolishStageMixin` | Performs final review and refinement of generated documentation. | `src/attune/workflows/document_gen/polish_stage.py` |
