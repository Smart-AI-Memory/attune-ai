---
feature: doc-gen
depth: concept
generated_at: 2026-04-13T16:54:43.133218+00:00
source_hash: 67aadd029bbf773d9f478a4d4c750e25344dc6b0bd9e1edadbcf5151d83f3bff
status: generated
---

# Doc Gen

## How it works

Generate documentation from source code through a three-stage workflow that extracts API references, creates content outlines, writes documentation, and polishes the final output.

The main building blocks are:

- **`DocumentGenerationWorkflow`** — Creates new documentation from source code with automated extraction and generation.
- **`APIReferenceMixin`** — Extracts API references and generates documentation for classes, functions, and modules.
- **`OutlineStageMixin`** — Creates structured outlines for documentation content.
- **`WriteStageMixin`** — Generates the actual documentation content from outlines.
- **`PolishStageMixin`** — Reviews and refines the generated documentation for quality and consistency.

Under the hood, this feature spans 10 source
files covering:

- Document Generation API Reference Extraction.
- Document Generation Chunked Operations.
- Document Generation Configuration.

## What connects to it

This feature relates to: docs, documentation, generation.

Other parts of the codebase interact with
doc gen through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `APIReferenceMixin` | Extracts API references and generates documentation for classes, functions, and modules. | `src/attune/workflows/document_gen/api_reference.py` |
| `ChunkedGenerationMixin` | Splits large documentation tasks into manageable chunks with progress tracking. | `src/attune/workflows/document_gen/chunked_generation.py` |
| `DocGenCostMixin` | Tracks and manages costs associated with AI-powered documentation generation. | `src/attune/workflows/document_gen/cost_management.py` |
| `OutlineStageMixin` | Creates structured outlines for documentation content. | `src/attune/workflows/document_gen/outline_stage.py` |
| `PolishStageMixin` | Reviews and refines generated documentation for quality and consistency. | `src/attune/workflows/document_gen/polish_stage.py` |
