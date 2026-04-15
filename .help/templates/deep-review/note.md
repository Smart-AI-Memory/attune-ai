---
type: note
feature: deep-review
depth: note
generated_at: 2026-04-14T14:55:24.294865+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Note: deep review

## Context

Deep Review provides multi-pass code analysis through three specialized subagents that examine security vulnerabilities, code quality issues, and test coverage gaps.

## How it works

The `DeepReviewAgentSDKWorkflow` orchestrates three Claude Agent SDK subagents that run independently:

- **security-reviewer** — Identifies security vulnerabilities and potential attack vectors
- **quality-reviewer** — Analyzes code maintainability, performance, and best practices
- **test-gap-reviewer** — Evaluates test coverage and identifies missing test scenarios

After all subagents complete their analysis, the workflow synthesizes their findings into a consolidated report with sections for Summary, Security, Quality, Test Gaps, and actionable Suggestions ranked by impact.

## Output format

The consolidated report includes:
- Overall code health score (0-100) with finding counts by severity
- Security findings ordered by severity level
- Quality findings ordered by severity level
- Test gaps ordered by priority
- Top 5-10 actionable suggestions with specific file and line references

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`
