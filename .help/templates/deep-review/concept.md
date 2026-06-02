---
type: concept
name: deep-review-concept
feature: deep-review
depth: concept
generated_at: 2026-06-02T10:54:11.428956+00:00
source_hash: e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4
status: generated
---

# Deep Review

`DeepReviewAgentSDKWorkflow` is a multi-pass code review workflow that dispatches three specialized subagents in parallel and consolidates their findings into a single structured report.

## How the review works

A single call to `DeepReviewAgentSDKWorkflow.execute()` coordinates three subagents, each focused on a distinct domain:

| Subagent | Domain |
|---|---|
| `security-reviewer` | Vulnerabilities and security risk |
| `quality-reviewer` | Code structure, style, and maintainability |
| `test-gap-reviewer` | Missing or insufficient test coverage |

Each subagent reports independently. After all three finish, the orchestrator synthesizes their findings into a consolidated report with five sections: **Summary**, **Security**, **Quality**, **Test Gaps**, and **Suggestions**.

The Summary section includes an overall code health score from 0–100, a short executive summary, and finding counts by severity. The Suggestions section closes the report with the top 5–10 actionable next steps, each linked back to the specific finding it addresses.

## When to use it

Deep review is suited for situations where a quick diff scan is not enough — for example, before merging a large refactor, auditing a module you didn't write, or establishing a health baseline for a legacy codebase. Because the three subagents run over the same codebase independently, findings that appear across multiple domains (say, an untested function that also has a security smell) surface in both the relevant section and the Suggestions rollup.

## The consolidated report as a mental model

Think of `DeepReviewAgentSDKWorkflow` as a review committee rather than a single reviewer. The orchestrator acts as chair: it hands the same codebase path to each specialist, waits for their independent reports, then writes the meeting minutes. You get one artifact instead of three, with severity ordering within each section so the most critical findings appear first.
