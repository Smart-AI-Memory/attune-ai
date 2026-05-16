---
type: task
name: bug-predict-task
feature: bug-predict
depth: task
generated_at: 2026-05-16T06:19:45.770969+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Run Bug Prediction

Use bug prediction when you want to find likely bug locations in your codebase before they reach production — catching dangerous eval usage, swallowed exceptions, and incomplete code paths by analyzing patterns and complexity.

## Prerequisites

- Access to the project source code
- The `src/attune/workflows/bug_predict.py` module available in your working environment

## Steps

1. **Choose the path to scan.**
   Decide the scope of your scan: a single file, a directory, or the whole project. The broader the scope, the more findings you may need to filter.

   | Target | Command |
   |--------|---------|
   | Single file | `/bug-predict src/auth.py` |
   | Directory | `/bug-predict src/` |
   | Whole project | `/bug-predict .` |

2. **Run the scan.**
   Invoke the skill with your chosen path:

   ```
   /bug-predict src/
   ```

   If you omit a path, the skill prompts you to choose a scope and severity filter before running.

3. **Read the risk report.**
   The workflow coordinates three subagents — `pattern-scanner`, `risk-correlator`, and `prevention-advisor` — and synthesizes their output into a single structured report:

   ```
   Bug Prediction Report
   Risk Score: 73/100 | Files: 34 | Findings: 8

   HIGH (2 findings)
     src/hooks/executor.py:89   dangerous_eval  eval() on user input
     src/plugins/loader.py:142  dangerous_eval  exec() in plugin loader

   MEDIUM (3 findings)
     src/api/webhook.py:67      broad_exception bare except: masks errors
     ...

   LOW (3 findings)
     src/auth/session.py:45     incomplete_code TODO: add token rotation
     ...
   ```

   Each finding includes a file path, line number, pattern type, and a plain-English description. File links are clickable — select one to jump directly to the flagged line.

4. **Act on HIGH-severity findings first.**
   Ask for a guided fix on any critical finding:

   ```
   fix the dangerous_eval in executor.py
   ```

   Then work through MEDIUM and LOW findings in priority order.

5. **Verify the report output programmatically (optional).**
   If you are calling the workflow directly in code, use `format_bug_predict_report()` to render results:

   ```python
   from attune.workflows.bug_predict_report import format_bug_predict_report

   report_text = format_bug_predict_report(result, input_data)
   print(report_text)
   ```

6. **Run the tests.**
   After any changes to the workflow or report formatter, confirm nothing regressed:

   ```
   pytest -k "bug-predict"
   ```

## Key files

- `src/attune/workflows/bug_predict.py` — `BugPredictionWorkflow` and the three-subagent orchestration logic
- `src/attune/workflows/bug_predict_report.py` — `format_bug_predict_report()` and the `main()` CLI entry point

## Verify success

The task is complete when:

- The scan finishes and returns a report with an overall risk score (0–100), findings grouped by severity (HIGH, MEDIUM, LOW), and a Suggestions section with prioritized prevention strategies.
- All tests pass: `pytest -k "bug-predict"` exits with no failures.
