---
type: faq
feature: bug-predict
depth: faq
generated_at: 2026-04-14T14:48:34.434172+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Bug Predict FAQ

## What is bug predict?

Bug predict analyzes your codebase to identify potential bug hotspots using pattern detection, risk correlation, and prevention strategies.

## When should I use bug predict?

Use bug predict when you want to proactively identify areas of your code that are likely to contain bugs before they manifest in production. It's particularly useful during code reviews, before major releases, or when working with legacy codebases.

## How do I run bug predict?

You can run bug predict from the command line using the `main()` function, or programmatically by creating a `BugPredictionWorkflow` instance and calling its `execute()` method.

## What does the output look like?

Bug predict generates a structured report with three main sections:
- **Summary**: Overall risk score (0-100) and executive summary of predicted bug hotspots
- **Bugs**: Predicted bugs organized by severity (HIGH, MEDIUM, LOW) with file paths and line numbers
- **Suggestions**: Actionable prevention strategies and refactoring advice

## How accurate are the predictions?

Bug predict uses three specialized subagents (pattern-scanner, risk-correlator, and prevention-advisor) to analyze your code from different angles. While it can't guarantee bugs will occur, it identifies patterns commonly associated with problematic code.

## Can I customize the analysis?

Yes, you can configure the `BugPredictionWorkflow` by passing keyword arguments to its `__init__` method. The workflow will adapt its analysis based on your specific codebase characteristics.

## How do I debug issues with bug predict?

Run the related tests first with `pytest -k "test_bug_predict or test_scanner" -v`. If tests pass but you're still having issues, add debug logging at suspected failure points and check that your input data matches the expected format.

## Where are the source files?

The bug predict feature is implemented across these files:
- `src/attune/workflows/bug_predict.py` — Main workflow class
- `src/attune/workflows/bug_predict_report.py` — Report formatting and CLI entry point

**Tags:** `bugs`, `prediction`, `scanning`
