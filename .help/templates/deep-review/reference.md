---
type: reference
name: deep-review-reference
feature: deep-review
depth: reference
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 0166eb83fb8436c203cdd073439a7339645f40e53cdfe39db4fbed0559eac81d
status: generated
---

# Deep Review reference

Multi-pass deep code review: security, quality, and test gap analysis with prioritized findings.

## Classes

| Class | Description |
|-------|-------------|
| `DeepReviewAgentSDKWorkflow` | Orchestrates a multi-pass deep code review using Claude Agent SDK subagents: `security-reviewer`, `quality-reviewer`, and `test-gap-reviewer`. |

### `DeepReviewAgentSDKWorkflow`

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `execute` | `**kwargs: Any` | `WorkflowResult` | Runs the three specialized subagents and synthesizes their findings into a consolidated review report. |

## Subagents

The workflow coordinates three subagents. Each reports findings independently; the orchestrator then synthesizes results into a single report.

| Name | Domain |
|------|--------|
| `security-reviewer` | Security vulnerabilities and risk findings |
| `quality-reviewer` | Code quality findings |
| `test-gap-reviewer` | Test coverage gaps |

## Consolidated report structure

The synthesized output contains the following sections:

| Section | Content |
|---------|---------|
| `## Summary` | Overall code health score (0–100), a 2–3 sentence executive summary, and finding counts by severity. |
| `## Security` | Findings from the security reviewer, ordered by severity. |
| `## Quality` | Findings from the quality reviewer, ordered by severity. |
| `## Test Gaps` | Findings from the test gap reviewer, ordered by priority. |
| `## Suggestions` | Top 5–10 actionable next steps ordered by impact, each referencing the specific finding it addresses. |

## Source files

- `src/attune/workflows/deep_review.py`

## Tags

`review`, `security`, `quality`, `tests`, `comprehensive-review`
