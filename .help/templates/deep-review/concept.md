---
type: concept
feature: deep-review
depth: concept
generated_at: 2026-04-14T14:53:54.865821+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Deep Review

The deep review feature orchestrates three specialized AI subagents to analyze code from different perspectives: security vulnerabilities, code quality issues, and test coverage gaps.

## Review process structure

The `DeepReviewAgentSDKWorkflow` coordinates three independent subagents that examine your codebase simultaneously:

- **security-reviewer** — Identifies potential security vulnerabilities and unsafe patterns
- **quality-reviewer** — Evaluates code maintainability, performance, and best practices
- **test-gap-reviewer** — Analyzes test coverage and suggests missing test scenarios

After all subagents complete their analysis, the workflow synthesizes their findings into a consolidated report with severity rankings and actionable recommendations.

## Output format

The deep review generates a structured report containing:

- **Summary** — Overall code health score (0-100) with finding counts by severity
- **Security** — Security findings ordered by risk level
- **Quality** — Code quality issues ordered by impact
- **Test Gaps** — Missing test coverage ordered by priority
- **Suggestions** — Top 5-10 actionable improvements with specific file references

Each finding includes file paths and line numbers to help you locate and address issues efficiently.

## Integration points

| Interface | Purpose | File |
|-----------|---------|------|
| `DeepReviewAgentSDKWorkflow` | Coordinates multi-agent code analysis workflow | `src/attune/workflows/deep_review.py` |
