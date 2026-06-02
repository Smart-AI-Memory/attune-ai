---
type: troubleshooting
name: bug-predict-troubleshooting
feature: bug-predict
depth: troubleshooting
generated_at: 2026-06-02T10:56:02.687232+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Troubleshoot bug predict

## Before you start

Bug prediction scans your codebase for patterns that historically cause production incidents — `dangerous_eval`, `broad_exception`, and `incomplete_code` — and returns a risk report scored 0–100. The workflow coordinates three subagents (`pattern-scanner`, `risk-correlator`, `prevention-advisor`) and formats output through `format_bug_predict_report()`. Failures can occur at the workflow, subagent, or report-formatting layer.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `BugPredictionWorkflow.execute()` raises an exception | Read the full traceback — it names the file and line. Check whether the `path` argument resolves to a real directory before calling `execute()`. |
| The report is empty or shows 0 findings on a path that should have issues | Confirm the scanned path contains `.py` files. If it does, check whether all findings are being suppressed by the false-positive filter (look for `# INTENTIONAL:`, `# noqa: BLE001`, or `_INTENTIONAL_KEYWORDS` matches). |
| `format_bug_predict_report()` returns garbled or incomplete output | Verify that the `result` dict passed to `format_bug_predict_report(result, input_data)` is the unmodified return value of `execute()`. A partial or manually constructed dict can omit required keys. |
| The CLI entry point (`main()`) exits without output | Run with a path argument and check stderr for an error message. `main()` is the CLI entry point — it does not return a value, so silent exit usually means the path was not found or was empty. |
| Risk score is unexpectedly low despite known risky patterns | Check whether the flagged files match any of the test-file patterns (`test_bug_predict`, `test_scanner`, `test_security_scan`). Test files are excluded from scoring. |
| Behavior differs between two runs on the same code | Look for environment drift: changed files, a dependency upgrade, or a different working directory affecting relative path resolution. |

## Step-by-step diagnosis

Work from cheapest to most invasive. Stop as soon as you find the cause.

1. **Reproduce against a minimal path.**
   Call `/bug-predict` on a single file you control — for example, a file you know contains a bare `except:`. If the expected finding appears, the scanner is working and the issue is specific to your target path or environment.

   ```
   /bug-predict src/api/webhook.py
   ```

2. **Verify the path is reachable.**
   Relative paths resolve from the working directory at the time `execute()` is called. Print or log the resolved path before passing it to `BugPredictionWorkflow.execute()` to rule out a working-directory mismatch.

3. **Check false-positive suppression.**
   If findings disappear unexpectedly, review the code under scan for any of the suppression markers the scanner honors:
   - `# INTENTIONAL:` comments on broad-exception blocks
   - `# noqa: BLE001` markers
   - Keywords from `_INTENTIONAL_KEYWORDS`: `fallback`, `ignore`, `optional`, `best effort`, `graceful`, `intentional`

   These are intentional suppressions — remove the marker if the suppression is wrong, not the pattern check.

4. **Run the related test suite.**
   ```
   pytest -k "bug_predict" -v
   ```
   If a test exercises the failing path, its fixtures show you the expected input shape for `BugPredictionWorkflow` and `format_bug_predict_report()`.

5. **Inspect `format_bug_predict_report()` inputs directly.**
   If the report output is wrong but `execute()` succeeds, call `format_bug_predict_report(result, input_data)` in isolation with the raw `result` dict to confirm the formatting layer is the source. A malformed `result` dict is the most common cause of garbled report output.

6. **Check subagent completion.**
   `BugPredictionWorkflow` coordinates three subagents: `pattern-scanner`, `risk-correlator`, and `prevention-advisor`. If the returned report is missing a section (Summary, Bugs, or Suggestions), one subagent likely did not complete. Look for timeout or error signals in the `WorkflowResult` before the report is formatted.

## Common fixes

- **Path does not exist or is empty.**
  Pass an absolute path or confirm your working directory before calling `execute()`:
  ```python
  import os
  from workflows.bug_predict import BugPredictionWorkflow

  wf = BugPredictionWorkflow()
  result = wf.execute(path=os.path.abspath("src/"))
  ```

- **All findings suppressed by false-positive filter.**
  If every match in a file carries a suppression marker and the suppression is wrong, remove the marker from the source file. Do not disable the filter globally — it exists to reduce noise from safe patterns like `regex.exec()` and test fixture strings.

- **`format_bug_predict_report()` receives a partial dict.**
  Always pass the unmodified return value of `execute()` as the `result` argument:
  ```python
  from workflows.bug_predict_report import format_bug_predict_report

  report = format_bug_predict_report(result=wf.execute(path="src/"), input_data={"path": "src/"})
  ```

- **Dependency version mismatch.**
  A dependency upgrade can change pattern-matching behavior. Run `pip show <dep>` to confirm installed versions match your lockfile. This is a change outside the feature itself — align your environment before rerunning.

- **Test files excluded from results.**
  Files whose names match `test_bug_predict`, `test_scanner`, or `test_security_scan` are excluded from scoring. If you are scanning a test directory and seeing no results, this is expected behavior.

## Source files

- `workflows/bug_predict.py` — `BugPredictionWorkflow` class and subagent orchestration
- `workflows/bug_predict_report.py` — `format_bug_predict_report()` and `main()` CLI entry point

**Tags:** `bugs`, `prediction`, `scanning`
