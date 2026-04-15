---
type: comparison
feature: code-quality
depth: comparison
generated_at: 2026-04-14T14:41:59.529622+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Code Quality vs alternatives

## Context

The code-quality feature provides automated code review through `CodeReviewWorkflow`, which orchestrates four specialized subagents (security, quality, performance, and architecture reviewers) to analyze your codebase and generate a unified report with actionable findings.

## Feature comparison

| Aspect | CodeReviewWorkflow | Manual code review | Static analysis tools |
|--------|-------------------|-------------------|----------------------|
| **Coverage** | Multi-domain (security, quality, perf, architecture) | Domain expertise varies by reviewer | Single-domain focus |
| **Consistency** | Standardized criteria across all reviews | Varies by reviewer mood/experience | Consistent but narrow |
| **Speed** | Automated, processes entire codebase | Hours to days per review | Seconds to minutes |
| **Context awareness** | Understands code relationships and patterns | High contextual understanding | Limited to syntax/patterns |
| **Report format** | Structured markdown with priority rankings | Varies widely | Tool-specific formats |
| **Actionability** | Specific suggestions with file paths and line numbers | Quality depends on reviewer | Often generic recommendations |

## When to use CodeReviewWorkflow

Use `CodeReviewWorkflow` when you need:

- **Comprehensive analysis** across security, quality, performance, and architecture domains in a single pass
- **Consistent review standards** that don't vary based on reviewer availability or expertise
- **Structured reports** with actionable suggestions ranked by priority
- **Automated integration** into CI/CD pipelines or development workflows
- **Large codebase reviews** where manual review would be time-prohibitive

The workflow excels at identifying cross-cutting concerns that single-purpose tools might miss, such as security implications of performance optimizations or architectural decisions that impact code quality.

## When NOT to use it

Avoid `CodeReviewWorkflow` when:

- **Domain-specific expertise** is required that exceeds the subagents' capabilities (e.g., specialized compliance requirements)
- **Interactive discussion** is needed to resolve complex design decisions
- **Learning and mentorship** are primary goals — human reviewers provide irreplaceable teaching moments
- **Legacy system knowledge** is critical — the workflow cannot access institutional knowledge about why certain patterns exist
- **Real-time collaboration** is required during active development

## Recommended approach

**Use CodeReviewWorkflow as your first pass** to catch common issues and establish a baseline quality assessment, then supplement with targeted human review for complex architectural decisions and team knowledge transfer.

For most development teams, this hybrid approach provides the best balance of speed, consistency, and insight depth.

## Source files

- `src/attune/workflows/code_review.py`

**Tags:** `review`, `quality`, `bugs`
