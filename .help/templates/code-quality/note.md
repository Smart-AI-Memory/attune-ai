---
type: note
feature: code-quality
depth: note
generated_at: 2026-04-19T18:47:09.607556+00:00
source_hash: 44a3613be3cabe60572ba20a4d4a482a2b2727856106c44e43c6eafd7e2cc42e
status: generated
---

# Note: code quality

## Context

The code quality feature provides unified code review across style, correctness, bugs, and architecture through a single coordinated workflow.

## Implementation

The feature centers on `CodeReviewWorkflow`, which orchestrates four specialized subagents to analyze different aspects of code health:

- **security-reviewer** — Scans for security vulnerabilities
- **quality-reviewer** — Checks style, formatting, and code correctness
- **perf-reviewer** — Identifies performance bottlenecks
- **architect-reviewer** — Evaluates structural design and coupling

The workflow synthesizes findings from all four subagents into a unified report with an overall health score (0-100) and actionable recommendations prioritized by impact.

This architecture allows the `/code-quality` skill to provide comprehensive analysis in a single pass rather than requiring users to run separate tools for linting, security scanning, performance analysis, and architectural review.

## Source files

- `src/attune/workflows/code_review.py`
- `src/attune/workflows/code_review_*.py`

**Tags:** `review`, `quality`, `bugs`
