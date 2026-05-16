---
type: troubleshooting
name: bug-predict-troubleshooting
feature: bug-predict
depth: troubleshooting
generated_at: 2026-05-16T06:19:45.787945+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Troubleshoot bug predict

## Symptom table

| If you observe | Check |
|----------------|-------|
| The scan produces no output or exits silently | Verify the path argument resolves to a readable file or directory; run `/bug-predict src/` and confirm `src/` exists relative to your working directory |
| Risk score is 0 and findings list is empty on a directory you expect to have issues | Check whether the scanned path contains only test files — patterns matching `test_bug_predict`, `test_scanner`, or `test_security_scan` are intentionally suppressed |
| `eval()` or `exec()` calls are not flagged | Confirm the call is not inside a test fixture string or a JavaScript `regex.exec()` context; both are filtered as known-safe patterns |
| Broad exceptions are not flagged | Check whether the exception handler includes an `# INTENTIONAL:` comment or a `# noqa: BLE001` marker — these suppress the finding by design |
| Report output is malformed or truncated | The issue is likely in `format_bug_predict_report()`; see diagnosis steps below |
| The CLI command `bug-predict` fails immediately | Run `python -m attune.workflows.bug_predict_report` directly to separate a PATH/entry-point issue from a workflow failure |
| Findings appear inconsistent across repeated runs | Check for environment-level state: caches, changed files between runs, or environment variables affecting file discovery |

## Diagnose the problem

Work through these steps in order — each one is cheaper than the next.

### 1. Reproduce with a minimal path

Strip the invocation to its simplest form and confirm the failure still occurs:

```
/bug-predict src/
```

If that works, narrow to the specific file or subdirectory that fails:

```
/bug-predict src/hooks/executor.py
```

A failure on a single file rules out directory-traversal and aggregation issues and points the problem at pattern detection or report formatting.

### 2. Check false-positive suppression

Before assuming a bug in the scanner, verify whether the pattern is being intentionally filtered. A finding is suppressed when any of the following is true:

- The file matches a test pattern (`test_bug_predict`, `test_scanner`, `test_security_scan`)
- The exception handler contains one of these keywords in a comment: `fallback`, `ignore`, `optional`, `best effort`, `graceful`, `intentional`
- The line carries a `# noqa: BLE001` marker
- The `eval()` call is inside a test fixture string or is a JavaScript `regex.exec()` call

If your code matches one of these conditions unintentionally, remove the suppressing comment or marker and re-run.

### 3. Run the related tests

```bash
pytest -k "bug_predict or bug_predict_report or scanner" -v
```

A failing test that exercises the broken path gives you a reproducible fixture to work from without modifying production inputs. Pay attention to tests matching `_SCANNER_TEST_PATTERNS` — they cover the false-positive suppression logic specifically.

### 4. Isolate the subagent responsible

The workflow coordinates three subagents in sequence: `pattern-scanner`, `risk-correlator`, and `prevention-advisor`. To determine which stage is failing:

- **No findings at all** — suspect `pattern-scanner`; it runs first and feeds the others.
- **Findings present but risk score is wrong or missing** — suspect `risk-correlator`.
- **Score and findings correct but suggestions are absent or garbled** — suspect `prevention-advisor` or the final synthesis step in `format_bug_predict_report()`.

### 5. Inspect `format_bug_predict_report()` directly

If the report output is malformed, call the formatter in isolation with a known-good result dict:

```python
from attune.workflows.bug_predict_report import format_bug_predict_report

result = {
    "risk_score": 73,
    "findings": [
        {"severity": "HIGH", "file": "src/hooks/executor.py", "line": 89,
         "pattern": "dangerous_eval", "description": "eval() on user input"}
    ],
    "suggestions": ["Replace eval() with ast.literal_eval() where input is data, not code."]
}
input_data = {"path": "src/"}

print(format_bug_predict_report(result, input_data))
```

If this call raises or returns unexpected output, the problem is in report formatting, not in scanning or correlation.

## Common fixes

**Path does not exist or is not readable**

```bash
ls -la src/          # confirm the directory exists
pwd                  # confirm your working directory
```

Pass an absolute path if relative resolution is unreliable in your environment:

```
/bug-predict /home/user/myproject/src/
```

**All findings suppressed by accident**

If a broad exception you expect to be flagged is not appearing, check for an unintentional `# INTENTIONAL:` comment earlier in the same block, or a `# noqa: BLE001` added by a linter auto-fix. Remove the marker and re-run.

**Report synthesis fails after subagents complete**

The orchestrator prompt requires all three subagents to finish before it synthesizes output. If one subagent times out or returns no content, the final report may be empty or partial. Re-run the scan — transient LLM timeouts are the most common cause. If the failure is consistent, reduce scope:

```
/bug-predict src/auth.py
```

Scanning a single file forces all three subagents to complete faster and surfaces whether the issue is scope-related.

**Dependency version mismatch**

If `format_bug_predict_report()` raises an unexpected `TypeError` or `KeyError`, confirm that the installed package matches what the source expects:

```bash
pip show attune
```

A mismatch between an upgraded dependency and the result dict schema (keys `risk_score`, `findings`, `suggestions`) is the most likely cause.

**CLI entry point not found**

If `bug-predict` is not recognized as a command, invoke the module directly to confirm the install is intact:

```bash
python -m attune.workflows.bug_predict_report --help
```

If this fails, reinstall the package:

```bash
pip install --force-reinstall attune
```

## Source files

- `src/attune/workflows/bug_predict.py` — `BugPredictionWorkflow` and subagent orchestration
- `src/attune/workflows/bug_predict_report.py` — `format_bug_predict_report()` and `main()` CLI entry point

**Tags:** `bugs`, `prediction`, `scanning`, `race-condition`
