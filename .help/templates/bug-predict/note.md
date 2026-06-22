---
type: note
name: bug-predict-note
feature: bug-predict
depth: note
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 750014addbbc0825c7da37de3ee7d765c2c29f9e0e9db47dbc9d3df3542340a0
status: generated
---

# Note: bug-predict internals

## How the workflow is structured

`BugPredictionWorkflow` (in `workflows/bug_predict`) is an SDK-native orchestrator that coordinates three specialized subagents: `pattern-scanner`, `risk-correlator`, and `prevention-advisor`. Each subagent focuses on a distinct domain — detection, scoring, and remediation advice — and reports findings as structured markdown. The orchestrator synthesizes those findings into a single report with a **Summary**, **Bugs**, and **Suggestions** section.

The `system_prompt_suffix` parameter on `BugPredictionWorkflow.__init__` lets callers append instructions to the default orchestrator prompt without replacing it.

## Report formatting

`format_bug_predict_report(result, input_data)` in `workflows/bug_predict_report` takes the raw `dict` returned by `BugPredictionWorkflow.execute()` and renders it as a human-readable string. The `main()` function in the same module is the CLI entry point that wires these two together for standalone use.

## False-positive suppression

The scanner skips matches that contain any of the following keywords in surrounding context: `fallback`, `ignore`, `optional`, `best effort`, `graceful`, `intentional`. It also ignores results originating from test files matched by the patterns `test_bug_predict`, `test_scanner`, and `test_security_scan`.

## Source files

- `workflows/bug_predict.py` — `BugPredictionWorkflow` and subagent orchestration
- `workflows/bug_predict_report.py` — `format_bug_predict_report()` and `main()`

**Tags:** `bugs`, `prediction`, `scanning`
