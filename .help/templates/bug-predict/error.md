---
type: error
feature: bug-predict
depth: error
generated_at: 2026-04-14T14:47:50.267438+00:00
source_hash: bdce26567d10cd4bcfc419ff9a7191f2baac8f5a8e219c06d9ae6c6e38f95653
status: generated
---

# Bug Predict errors

Bug prediction workflow failures typically stem from subagent coordination issues, malformed analysis results, or report formatting problems in the three-phase orchestration process.

## Common error signatures

- `KeyError` when expected subagent results are missing from the workflow output
- `ValueError` during report formatting when risk scores are outside the 0-100 range
- `AttributeError` when `WorkflowResult` objects lack required fields for synthesis
- `FileNotFoundError` when the target codebase path doesn't exist or isn't accessible
- Template rendering errors when markdown structure is malformed in subagent outputs

## Where errors originate

Bug prediction failures commonly trace back to these coordination points:

- `BugPredictionWorkflow.execute()` — Orchestrates the three subagents (pattern-scanner, risk-correlator, prevention-advisor) and synthesizes their findings
- `format_bug_predict_report()` — Transforms workflow results into structured markdown with Summary, Bugs, and Suggestions sections
- `main()` — CLI entry point that handles path validation and workflow initialization

## How to diagnose

1. **Check subagent completion status.** The workflow requires all three subagents to complete successfully. Missing results from pattern-scanner, risk-correlator, or prevention-advisor will cause synthesis failures.

2. **Validate the target codebase path.** Ensure the analyzed directory exists and contains readable source files. The workflow cannot predict bugs in inaccessible code.

3. **Examine risk score ranges.** Bug prediction reports expect risk scores between 0-100. Values outside this range indicate corrupted analysis results from the risk-correlator subagent.

4. **Verify markdown structure in subagent outputs.** Each subagent must return properly formatted markdown. Malformed structure prevents the final report synthesis step.

5. **Test with a minimal codebase.** If the workflow fails on complex projects, try running it on a single-file test case to isolate whether the issue is in orchestration logic or analysis complexity.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_*.py`

**Tags:** `bugs`, `prediction`, `scanning`
