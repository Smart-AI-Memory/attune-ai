---
type: note
feature: doc-gen
depth: note
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: e72f8c7df1bc5e57a104c92b8ea7ec8a43b33084d7d1ab2add257441af45c122
status: generated
---

# Note: doc gen

## Context

The doc-gen feature generates documentation from source code, including docstrings, README sections, and API references. It uses a three-stage workflow with specialized subagents for planning, writing, and polishing documentation.

## Architecture

The doc-gen package implements a multi-stage workflow through mixins and a central orchestrator:

**Core workflow:**
- `DocumentGenerationWorkflow` orchestrates three specialized subagents: outline-planner, content-writer, and polish-reviewer
- Each subagent focuses on a specific domain and produces structured markdown output
- The workflow synthesizes subagent output into a single document with Summary, Outline, Documentation, and Suggestions sections

**Stage mixins:**
- `OutlineStageMixin` — handles documentation structure planning
- `WriteStageMixin` — generates content with code examples and API references
- `PolishStageMixin` — performs final review and refinement

**Support mixins:**
- `APIReferenceMixin` — extracts and formats API documentation from source code
- `ChunkedGenerationMixin` — breaks large generation tasks into manageable chunks with progress display
- `DocGenCostMixin` — tracks and manages API costs during generation

**Utilities:**
- `format_doc_gen_report()` — converts workflow results into human-readable reports

The workflow operates on codebases at specified paths, analyzing source files to produce comprehensive documentation that covers modules, APIs, and usage examples.

## Source files

- `src/attune/workflows/document_gen/**`

**Tags:** `docs`, `documentation`, `generation`
