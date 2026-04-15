---
type: note
feature: code-quality
depth: note
generated_at: 2026-04-14T14:41:52.697669+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Note: code quality

## Context

The code quality feature provides automated code review through a multi-agent workflow that examines codebases for style issues, potential bugs, and structural problems.

## Implementation

The feature centers on `CodeReviewWorkflow`, an SDK-native workflow that coordinates four specialized subagents to analyze different aspects of code quality:

- **security-reviewer** — Identifies security vulnerabilities and risks
- **quality-reviewer** — Checks code style, maintainability, and best practices
- **perf-reviewer** — Analyzes performance bottlenecks and optimization opportunities
- **architect-reviewer** — Evaluates structural design and architectural patterns

The workflow produces a unified report with an overall health score (0-100) and structured findings across all review domains. Each subagent focuses on its specialized area and reports findings with specific file paths and line numbers when possible.

The orchestration follows a template-driven approach where subagents complete their analysis independently, then their findings are synthesized into sections for Summary, Security, Quality, Performance, Architecture, and prioritized Suggestions.

## Source files

- `src/attune/workflows/code_review.py`

**Tags:** `review`, `quality`, `bugs`
