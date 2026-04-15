---
type: task
feature: bug-predict
depth: task
generated_at: 2026-04-14T14:47:32.530164+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Work with bug predict

Use bug predict when you need to identify potential bug hotspots in your codebase before they cause production issues.

## Prerequisites

- Access to the project source code
- Python environment with the attune SDK installed

## Run bug prediction analysis

1. **Execute the bug prediction workflow from the command line.**
   ```bash
   python -m attune.workflows.bug_predict_report /path/to/your/codebase
   ```

2. **Review the generated report.**
   The workflow produces a structured analysis with:
   - Overall risk score (0-100)
   - Predicted bugs organized by severity (HIGH, MEDIUM, LOW)
   - File paths and line numbers for each identified pattern
   - Actionable prevention strategies

3. **Verify the analysis completed successfully.**
   Check that the report includes all three sections (Summary, Bugs, Suggestions) and contains specific file references with line numbers.

## Customize bug prediction programmatically

1. **Import the BugPredictionWorkflow class.**
   ```python
   from attune.workflows.bug_predict import BugPredictionWorkflow
   ```

2. **Initialize the workflow with your parameters.**
   ```python
   workflow = BugPredictionWorkflow(**your_config)
   ```

3. **Execute the analysis.**
   ```python
   result = workflow.execute(path="/path/to/codebase")
   ```

4. **Format the output for human consumption.**
   ```python
   from attune.workflows.bug_predict_report import format_bug_predict_report
   formatted_report = format_bug_predict_report(result, input_data)
   ```

5. **Confirm the workflow returned valid results.**
   Verify that `result` contains findings from all three subagents: pattern-scanner, risk-correlator, and prevention-advisor.

## Test your changes

Run the bug prediction test suite to verify your modifications:
```bash
pytest -k "test_bug_predict or test_scanner"
```

Your tests pass when all bug prediction patterns are correctly identified and the report format matches expected structure.

## Key files

- `src/attune/workflows/bug_predict.py` — Core workflow implementation
- `src/attune/workflows/bug_predict_report.py` — Report formatting and CLI entry point
- Related pattern detection helpers in the same directory
