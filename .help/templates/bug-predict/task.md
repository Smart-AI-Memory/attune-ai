---
type: task
name: bug-predict-task
feature: bug-predict
depth: task
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 750014addbbc0825c7da37de3ee7d765c2c29f9e0e9db47dbc9d3df3542340a0
status: generated
---

# Run Bug Prediction

Use `/bug-predict` when you want to find likely bug locations in a codebase before they surface in production, using pattern detection and complexity analysis.

## Prerequisites

- Access to the project source code
- The target path you want to scan (a single file, a directory, or `.` for the whole project)

## Run a scan

1. **Choose your entry point.**
   - To scan interactively from the command line, call `main()` in `workflows.bug_predict_report`. This is the CLI entry point for the bug prediction workflow.
   - To run a scan programmatically, instantiate `BugPredictionWorkflow` from `workflows.bug_predict` and call `execute()`:

     ```python
     from workflows.bug_predict import BugPredictionWorkflow

     workflow = BugPredictionWorkflow()
     result = workflow.execute(path="src/")
     ```

2. **Scope the scan to the path you care about.**
   Pass the target as the `path` argument to `execute()`. You can target a single file, a directory tree, or the whole project:

   | Target | Example |
   |--------|---------|
   | One file | `path="src/auth.py"` |
   | A directory | `path="src/"` |
   | Whole project | `path="."` |

3. **Format the output.**
   Pass the `WorkflowResult` returned by `execute()` to `format_bug_predict_report()`:

   ```python
   from workflows.bug_predict_report import format_bug_predict_report

   report = format_bug_predict_report(result=result.data, input_data={"path": "src/"})
   print(report)
   ```

   The report organizes findings by severity (HIGH, MEDIUM, LOW) with file paths, line numbers, pattern types, and plain-English descriptions.

4. **Customize the orchestrator prompt if needed.**
   `BugPredictionWorkflow.__init__` accepts a `system_prompt_suffix` keyword argument. Pass a string to append additional instructions to the default orchestrator prompt — for example, to restrict the scan to specific pattern types or adjust the output format.

   ```python
   workflow = BugPredictionWorkflow(system_prompt_suffix="Focus only on dangerous_eval findings.")
   ```

5. **Run the tests to verify your changes.**
   After any modification to `workflows/bug_predict.py` or `workflows/bug_predict_report.py`, run:

   ```
   pytest -k "bug-predict"
   ```

## Confirm success

The scan succeeded when `format_bug_predict_report()` returns a non-empty report string that includes a **Summary** section with an overall risk score (0–100), a **Bugs** section with at least one severity group, and a **Suggestions** section with prioritized prevention strategies.

## Key files

| File | Purpose |
|------|---------|
| `src/attune/workflows/bug_predict.py` | `BugPredictionWorkflow` class and three subagents (`pattern-scanner`, `risk-correlator`, `prevention-advisor`) |
| `src/attune/workflows/bug_predict_report.py` | `format_bug_predict_report()` and the `main()` CLI entry point |
