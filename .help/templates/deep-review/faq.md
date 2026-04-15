---
type: faq
feature: deep-review
depth: faq
generated_at: 2026-04-14T14:55:01.503111+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Deep Review FAQ

## What is deep review?

A multi-pass code review system that analyzes your codebase using three specialized reviewers: security, quality, and test gap analysis. Each reviewer examines the code independently, then their findings are synthesized into a consolidated report.

## When should I use deep review?

Use deep review when you want comprehensive feedback on a codebase before major releases, merges, or deployments. It's particularly useful for catching issues that single-pass reviews might miss, since each subagent focuses on a specific domain.

## How does it work?

Deep review coordinates three specialized subagents:
- **security-reviewer**: Identifies security vulnerabilities and risks
- **quality-reviewer**: Analyzes code quality, maintainability, and best practices
- **test-gap-reviewer**: Finds missing test coverage and testing opportunities

The workflow produces a consolidated report with an overall health score, findings organized by severity, and actionable next steps.

## What's the main entry point?

Use the `DeepReviewAgentSDKWorkflow` class from `src/attune/workflows/deep_review.py`. Instantiate it and call the `execute()` method with your codebase path.

## How do I debug issues?

First, run the tests: `pytest -k "deep-review" -v`. If tests pass but your code fails, add `logger.debug` statements at suspected failure points and re-run with logging enabled. Check the troubleshooting page for common failure modes.

## Where are the source files?

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`
