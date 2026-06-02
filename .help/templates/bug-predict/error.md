---
type: error
name: bug-predict-error
feature: bug-predict
depth: error
generated_at: 2026-06-02T10:56:02.674663+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Bug Predict errors

## Common error signatures

Errors in bug predict fall into three categories: failures during workflow execution, failures during report formatting, and failures in the subagent coordination layer.

**Workflow execution (`BugPredictionWorkflow.execute`)**

- `ValueError` — the `path` argument in the task prompt template is missing or resolves to a location the orchestrator cannot access.
- `RuntimeError` — one or more of the three subagents (`pattern-scanner`, `risk-correlator`, `prevention-advisor`) did not return a result before the workflow completed.

**Report formatting (`format_bug_predict_report`)**

- `KeyError` — `result` or `input_data` is missing a field the formatter expects (for example, `severity`, `findings`, or `risk_score`).
- `TypeError` — `result` or `input_data` was passed as `None` or an unexpected type instead of `dict`.

**CLI entry point (`main`)**

- `SystemExit` with a non-zero code — the path argument was not supplied or could not be resolved before `BugPredictionWorkflow` was instantiated.

## Where errors originate

- `BugPredictionWorkflow.__init__` in `workflows/bug_predict.py` — validates constructor arguments, including `system_prompt_suffix`, before the workflow starts. A bad value here prevents any scanning from running.
- `BugPredictionWorkflow.execute` in `workflows/bug_predict.py` — coordinates `pattern-scanner`, `risk-correlator`, and `prevention-advisor`. If subagent synthesis fails, the error surfaces here as a `WorkflowResult` with no findings or as an unhandled exception.
- `format_bug_predict_report` in `workflows/bug_predict_report.py` — converts the raw `result` dict and `input_data` dict into the human-readable report. Malformed or incomplete dicts from a partial `execute` run will cause this function to fail.
- `main` in `workflows/bug_predict_report.py` — the CLI entry point. Errors here typically mean the workflow never ran, not that it ran and produced bad output.

## How to diagnose

1. **Identify which layer failed.** Check whether the traceback points to `bug_predict.py` (workflow or subagent coordination) or `bug_predict_report.py` (formatting or CLI). The fix differs by layer.

2. **Check the `result` dict shape.** If the error is a `KeyError` or `TypeError` inside `format_bug_predict_report`, inspect the `WorkflowResult` returned by `execute`. A partial run — for example, one where `risk-correlator` or `prevention-advisor` did not finish — produces an incomplete dict that the formatter cannot process.

3. **Check the path argument.** `_TASK_PROMPT_TEMPLATE` requires a `{path}` value. If `execute` was called without a resolvable path, the orchestrator prompt is malformed and all three subagents receive bad input. Confirm the path exists before calling `execute`.

4. **Inspect false-positive filter state.** If the scan runs but returns no findings on code you expect to be flagged, check whether the matched lines contain any `_INTENTIONAL_KEYWORDS` (`fallback`, `ignore`, `optional`, `best effort`, `graceful`, `intentional`) or a `# INTENTIONAL:` / `# noqa: BLE001` marker, which the scanner suppresses automatically.

5. **Verify test files are not contaminating results.** Files matching `_SCANNER_TEST_PATTERNS` (`test_bug_predict`, `test_scanner`, `test_security_scan`) are excluded from scanning. If your production code path shares a name with one of these patterns, it will be silently skipped.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_report.py`

**Tags:** `bugs`, `prediction`, `scanning`
