---
type: faq
feature: code-quality
depth: faq
generated_at: 2026-04-14T14:41:31.768858+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Code Quality FAQ

## What does the code quality feature do?

It performs comprehensive code reviews using four specialized AI subagents that analyze security, quality, performance, and architecture issues in your codebase.

## When should I use the CodeReviewWorkflow?

Use it when you need an automated, multi-perspective code review that goes beyond basic linting. It's especially helpful for reviewing pull requests, auditing legacy code, or getting a second opinion on complex changes.

## How do I run a code review?

Create a `CodeReviewWorkflow` instance and call its `execute()` method with the path to your code:

```python
workflow = CodeReviewWorkflow()
result = workflow.execute(path="path/to/your/code")
```

## What do I get back from the workflow?

You get a structured report with:
- Overall code health score (0-100)
- Executive summary
- Findings from each specialized reviewer (security, quality, performance, architecture)
- Prioritized suggestions for improvement

## Which subagents analyze my code?

Four specialized reviewers examine different aspects:
- `security-reviewer` - identifies security vulnerabilities
- `quality-reviewer` - catches bugs and style issues
- `perf-reviewer` - spots performance bottlenecks
- `architect-reviewer` - evaluates structural design

## How do I debug workflow issues?

First, run the tests: `pytest -k "code-quality" -v`. If tests pass but your code fails, add debug logging at the suspected failure point and check the troubleshooting page for common issues.

## Where is the source code?

The main workflow is in `src/attune/workflows/code_review.py`. Supporting files follow the pattern `src/attune/workflows/code_review_*.py`.

**Tags:** `review`, `quality`, `bugs`
