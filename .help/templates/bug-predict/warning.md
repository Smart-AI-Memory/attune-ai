---
type: warning
name: bug-predict-warning
feature: bug-predict
depth: warning
generated_at: 2026-06-02T10:56:02.684528+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Bug Predict Cautions

## What to watch for

Bug prediction coordinates three subagents (`pattern-scanner`, `risk-correlator`, `prevention-advisor`) and merges their output into a single report. Most surprises come from how that synthesis behaves at the edges — not from the pattern matching itself.

## Risk areas

### False-negative suppression removes real findings

The scanner automatically filters out patterns it considers safe — including `eval()` inside test fixture strings, `regex.exec()` calls, and broad exceptions annotated with `# INTENTIONAL:` or `# noqa: BLE001`. It also skips any file whose name matches `_SCANNER_TEST_PATTERNS` (e.g. `test_bug_predict`, `test_scanner`, `test_security_scan`).

If a high-severity pattern like `dangerous_eval` disappears from your report after renaming or restructuring a file, check whether the new filename matches one of those test-file patterns. Production code in a file named `test_*` will be silently skipped.

### `format_bug_predict_report()` expects a specific result shape

`format_bug_predict_report(result: dict, input_data: dict)` formats the final output from `BugPredictionWorkflow.execute()`. It does not validate that `result` conforms to the expected structure — missing keys (such as `Summary`, `Bugs`, or `Suggestions` sections) produce incomplete or blank output rather than an error. If you pass a partial result, the report will appear to succeed but will omit findings silently.

Always pass the unmodified `WorkflowResult` from `execute()` rather than a hand-constructed dict unless you can confirm your dict includes every expected section.

### `system_prompt_suffix` appended without a separator

`BugPredictionWorkflow.__init__` accepts a `system_prompt_suffix` keyword argument that is appended directly to `_SYSTEM_PROMPT`. There is no newline or separator injected between the base prompt and your suffix. A suffix that begins mid-sentence or contains conflicting instructions can degrade the orchestrator's output quality in ways that are difficult to trace in the report.

Start `system_prompt_suffix` with a newline and a clear directive so it reads as a distinct instruction rather than a run-on continuation.

### Private subagent names can change without notice

The subagent identifiers in `_SUBAGENT_NAMES` (`pattern-scanner`, `risk-correlator`, `prevention-advisor`) are module-level private constants. If your code references them directly — for example, to filter or re-route subagent output — a refactor can break that logic silently. Depend only on the public interface: `BugPredictionWorkflow` and `format_bug_predict_report`.

## How to avoid problems

1. **Verify suppression rules don't apply to your target.** Before concluding a file is clean, confirm it isn't being excluded by a test-file pattern match or an `# INTENTIONAL:` annotation that was added without review.

2. **Pass `execute()` output directly to `format_bug_predict_report()`.** Avoid reshaping the `WorkflowResult` before formatting. If you need to filter findings, do so after formatting, not before.

3. **Prefix `system_prompt_suffix` with a newline.** This keeps your additions structurally separate from the base orchestrator prompt and reduces the chance of malformed instruction sequences.

4. **Use only the public API.** `BugPredictionWorkflow` and `format_bug_predict_report` are the stable surface. Private helpers and constants — anything prefixed with `_` — can change between releases without a deprecation notice.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_report.py`

**Tags:** `bugs`, `prediction`, `scanning`, `race-condition`
