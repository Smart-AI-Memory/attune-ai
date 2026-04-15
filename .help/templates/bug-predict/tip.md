---
type: tip
feature: bug-predict
depth: tip
generated_at: 2026-04-14T14:48:52.930870+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Tip: working effectively with bug predict

## Context

Predict likely bug locations based on code patterns and complexity.

## Recommendations

1. **Start with `format_bug_predict_report()` for readable output.** The raw `WorkflowResult` from `BugPredictionWorkflow.execute()` contains structured data that's hard to parse visually — the formatter converts it to organized markdown with severity levels and file paths.

2. **Use the CLI entry point for exploration.** Call `main()` to run bug prediction interactively before integrating the workflow into larger systems — it handles argument parsing and report formatting automatically.

3. **Run tests with `pytest -k "test_bug_predict"` before changes.** The bug prediction workflow coordinates three subagents (pattern-scanner, risk-correlator, prevention-advisor), so integration issues are common when modifying the orchestration logic.

## Why this matters

Bug prediction generates complex structured output that requires careful interpretation. Starting with the formatted report helps you understand what the workflow produces before you try to consume the raw results programmatically.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_*.py`

**Tags:** `bugs`, `prediction`, `scanning`
