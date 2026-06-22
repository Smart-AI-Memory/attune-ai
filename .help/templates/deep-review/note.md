---
type: note
name: deep-review-note
feature: deep-review
depth: note
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 0166eb83fb8436c203cdd073439a7339645f40e53cdfe39db4fbed0559eac81d
status: generated
---

# Note: Deep Review

## Context

Deep Review is a multi-pass code review workflow implemented in `src/attune/workflows/deep_review.py`. It coordinates three specialized subagents — `security-reviewer`, `quality-reviewer`, and `test-gap-reviewer` — each analyzing the codebase independently before an orchestrator synthesizes their findings into a single consolidated report.

## How it works

`DeepReviewAgentSDKWorkflow.execute()` accepts a `path` argument pointing to the directory or file under review. Internally, the workflow uses a fixed system prompt that instructs the orchestrating agent to "cite file paths and line numbers" and remain "thorough but concise." The task prompt template drives the subagents to report findings by severity and priority, then assembles results into five sections: **Summary**, **Security**, **Quality**, **Test Gaps**, and **Suggestions**.

The Summary section includes an overall code health score (0–100) and finding counts by severity. The Suggestions section surfaces the top 5–10 actionable next steps ordered by impact, each tied back to a specific finding.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`, `comprehensive-review`
