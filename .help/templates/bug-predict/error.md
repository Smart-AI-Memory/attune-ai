---
type: error
name: bug-predict-error
feature: bug-predict
depth: error
generated_at: 2026-05-16T06:19:45.779515+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Bug Predict errors

## Common error signatures

Errors in bug predict fall into three categories: failures during subagent orchestration, failures formatting the final report, and failures at the CLI entry point.

- **Path not found or unreadable** — `main()` receives a path argument that doesn't exist or can't be traversed. Typically surfaces as an `OSError` or `FileNotFoundError` before any subagent runs.
- **Malformed subagent output** — one of the three subagents (`pattern-scanner`, `risk-correlator`, or `prevention-advisor`) returns output that `format_bug_predict_report()` cannot parse into the expected `## Summary / ## Bugs / ## Suggestions` structure. Often raises a `KeyError` or `ValueError` on the `result` dict.
- **Synthesis failure in `BugPredictionWorkflow.execute()`** — the orchestrator fails to merge subagent findings into a unified report, usually because a subagent timed out or returned an empty result.

## Where errors originate

- **`format_bug_predict_report(result, input_data)`** — converts the raw `result` dict from `BugPredictionWorkflow.execute()` into human-readable markdown. If `result` is missing expected keys (for example, no `bugs` list or no `summary` field), this function raises before anything is printed.
- **`main()`** — the CLI entry point that parses arguments, invokes `BugPredictionWorkflow`, and calls `format_bug_predict_report()`. Errors here include bad argument values and unhandled exceptions from the workflow layer.

## How to diagnose

1. **Identify which layer failed.** Check whether the traceback points to `bug_predict_report.py` (formatting or CLI) or `bug_predict.py` (orchestration and subagent coordination). The fix differs depending on the layer.

2. **Inspect the `result` dict before formatting.** If `format_bug_predict_report()` is raising, add a temporary `print(result)` or `logger.debug(result)` call just before it's invoked. Confirm that the dict contains `summary`, `bugs`, and `suggestions` keys — missing keys mean a subagent returned incomplete output.

3. **Check which subagent stalled or failed.** `BugPredictionWorkflow` coordinates `pattern-scanner`, `risk-correlator`, and `prevention-advisor`. If one subagent produced no output, the synthesis step has nothing to merge. Look for empty sections in the raw result or log lines indicating which subagent completed.

4. **Verify the scan path.** Run with the exact path you passed to `/bug-predict` and confirm it exists and is readable. An unresolvable path causes an early exit before any pattern detection runs — the report will be empty rather than partial.

5. **Check false-positive suppression isn't hiding real findings.** If the report returns zero findings on a path you expect to have results, confirm the scanned files don't match `_SCANNER_TEST_PATTERNS` (`test_bug_predict`, `test_scanner`, `test_security_scan`) and that broad exceptions aren't marked with `# INTENTIONAL:` or `# noqa: BLE001`, which the scanner suppresses by design.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_report.py`

**Tags:** `bugs`, `prediction`, `scanning`
