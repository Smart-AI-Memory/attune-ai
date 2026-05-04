---
type: task
feature: bug-predict
depth: task
generated_at: 2026-05-04T02:26:31.028318+00:00
source_hash: 1686df43f96bd1cdf341101bfab34ee6e5f7f50c3733daf08c8827b94e8a7fef
status: generated
---

# Work with bug predict

Use bug predict when you need to modify how the bug prediction workflow scans code patterns, formats reports, or handles the CLI interface.

## Prerequisites

- Access to the project source code
- Understanding of the BugPredictionWorkflow's three-subagent architecture

## Identify the component to modify

The bug prediction system has three main parts:

- **BugPredictionWorkflow** in `src/attune/workflows/bug_predict.py` — Orchestrates pattern-scanner, risk-correlator, and prevention-advisor subagents
- **format_bug_predict_report()** in `src/attune/workflows/bug_predict_report.py` — Converts raw analysis into human-readable reports
- **main()** in `src/attune/workflows/bug_predict_report.py` — Handles CLI invocation and parameter parsing

Read the docstring and parameters for your target function to confirm it owns the behavior you want to change.

## Modify the workflow orchestration

To change how subagents coordinate or what analysis they perform:

1. Open `src/attune/workflows/bug_predict.py`
2. Locate the `BugPredictionWorkflow` class
3. Review `_SUBAGENT_NAMES` and `_TASK_PROMPT_TEMPLATE` constants to understand the current structure
4. Modify the `execute()` method to adjust subagent coordination
5. Update `_SYSTEM_PROMPT` if you change the orchestrator's role

## Modify report formatting

To change how results display to users:

1. Open `src/attune/workflows/bug_predict_report.py`
2. Find the `format_bug_predict_report()` function
3. Adjust the markdown structure, severity groupings, or file path formatting
4. Test with sample input data to verify output readability

## Modify CLI behavior

To change command-line parameters or entry point logic:

1. Locate the `main()` function in `src/attune/workflows/bug_predict_report.py`
2. Update argument parsing, path validation, or error handling
3. Ensure changes align with the `/bug-predict` skill interface

## Validate your changes

Run targeted tests to catch regressions:

```bash
pytest -k "bug_predict"
```

Test with a real codebase to verify the workflow produces useful results and reports format correctly.
