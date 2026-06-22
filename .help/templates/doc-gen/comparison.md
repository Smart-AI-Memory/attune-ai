---
type: comparison
feature: doc-gen
depth: comparison
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: e72f8c7df1bc5e57a104c92b8ea7ec8a43b33084d7d1ab2add257441af45c122
status: generated
---

# Doc gen vs alternatives

## Context

The doc gen workflow creates comprehensive documentation by orchestrating three specialized AI agents: an outline planner, content writer, and polish reviewer. It analyzes source code to extract API references, generate structured content, and produce human-readable reports.

## Feature comparison

| Feature | Doc gen workflow | Manual documentation | Single-pass generators |
|---------|------------------|---------------------|----------------------|
| **Structure** | Three-stage pipeline (outline → write → polish) | Fully manual | Single AI call |
| **Cost management** | Built-in token tracking and budgeting | No cost tracking | No cost oversight |
| **Chunked processing** | Handles large codebases via chunking | Manual file splitting | Often fails on large inputs |
| **API extraction** | Automatic docstring and signature parsing | Manual API documentation | Basic code scanning |
| **Quality control** | Dedicated polish/review stage | Developer review only | No built-in review |
| **Output format** | Structured markdown with citations | Varies by author | Usually plain text |

## Use doc gen when

- You need comprehensive documentation for a medium-to-large codebase (the chunking handles projects that exceed token limits)
- Cost visibility matters — the `DocGenCostMixin` tracks token usage across all three stages
- You want structured output with file path citations rather than generic descriptions
- Your codebase has substantial API surface area that benefits from automated extraction
- Quality matters more than speed — the three-stage pipeline produces more thorough results than single-pass tools

## Don't use doc gen when

- You need real-time documentation updates — the workflow is designed for periodic comprehensive generation, not continuous integration
- You're documenting a single small file — the orchestration overhead isn't worth it
- You need non-markdown output formats — the workflow targets structured markdown specifically
- Your codebase lacks docstrings or clear structure — garbage in, garbage out applies
- You're prototyping and need quick iteration — the three-stage process prioritizes thoroughness over speed

## Alternative approaches

**Manual documentation**: Full control but no automation benefits. Choose this for highly specialized content where AI assistance adds little value.

**Docstring-only tools**: Tools that extract existing docstrings without generating new content. Faster but limited to what developers already wrote.

**IDE documentation features**: Real-time tooltips and inline help. Complements but doesn't replace comprehensive documentation generation.

**Single-pass AI generators**: Simpler but less structured. Consider for quick documentation tasks where the three-stage quality improvement isn't needed.

## Recommendation

Use doc gen as your primary documentation generator if you have a substantial codebase (10+ files) and care about output quality. The three-stage approach and built-in cost management make it suitable for regular documentation updates in professional projects. For smaller codebases or quick prototypes, simpler alternatives may be more efficient.

## Source files

- `src/attune/workflows/document_gen/**`

**Tags:** `docs`, `documentation`, `generation`
