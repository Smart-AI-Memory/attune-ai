---
type: note
name: deep-review-note
feature: deep-review
depth: note
generated_at: 2026-06-02T10:54:11.466157+00:00
source_hash: e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4
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
