---
type: faq
feature: doc-gen
depth: faq
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: e72f8c7df1bc5e57a104c92b8ea7ec8a43b33084d7d1ab2add257441af45c122
status: generated
---

# Doc Gen FAQ

## What is doc gen?

Doc gen automatically generates documentation from your source code, including API references, README sections, and other developer documentation.

## When should I use it?

Use doc gen when you need to create or update documentation for a codebase. It's particularly useful for generating API documentation from docstrings, creating structured README content, and maintaining up-to-date reference materials as your code evolves.

## What's the main entry point?

Start with the `DocumentGenerationWorkflow` class, which orchestrates the entire documentation generation process. You can also use `format_doc_gen_report()` to format the generated output into a human-readable report.

The workflow operates in three stages: outline planning, content writing, and final polish review.

## How do I control costs?

Doc gen includes built-in cost management through the `DocGenCostMixin`. The workflow tracks token usage across all generation stages and provides cost estimates before processing large codebases.

## Can I generate documentation in chunks?

Yes, use the `ChunkedGenerationMixin` to process large codebases in smaller pieces. This prevents memory issues and allows you to generate documentation incrementally.

## How do I debug it?

Run `pytest -k "doc-gen" -v` first to check if the basic functionality works. If tests pass but your code fails, add debug logging at the failure point and check the workflow stages (outline, write, polish) individually.

## Where are the source files?

- `src/attune/workflows/document_gen/**`

**Tags:** `docs`, `documentation`, `generation`
