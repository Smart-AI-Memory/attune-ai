---
type: warning
name: bug-predict-warning
feature: bug-predict
depth: warning
generated_at: 2026-05-16T06:19:45.785661+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Bug Prediction: What to Watch For

## False negatives from the false-positive filter

The scanner automatically suppresses patterns it recognizes as safe — `eval()` in test fixture strings, `regex.exec()` calls, and broad exceptions marked with `# INTENTIONAL:` or `# noqa: BLE001`. This suppression is keyword-driven: if your intentional exception handler uses a phrase from `_INTENTIONAL_KEYWORDS` (such as `fallback`, `graceful`, or `best effort`) in a comment, the scanner silently drops the finding.

The risk: a genuinely risky `eval()` or swallowed exception next to one of those keywords gets suppressed alongside the safe one. Before treating a clean report as a green light, verify that no high-severity findings were filtered by checking the surrounding comments in flagged files yourself.

## Test files excluded from scanning by name pattern

The workflow skips files matching `_SCANNER_TEST_PATTERNS` — specifically filenames containing `test_bug_predict`, `test_scanner`, or `test_security_scan`. If your test suite exercises security-sensitive helpers (for example, plugin loader logic that uses `exec()`), those files will not appear in the report even if they contain real `dangerous_eval` findings.

Avoid naming security-relevant test helpers after those patterns, or run a separate, targeted scan on your test directory if you need coverage there.

## `format_bug_predict_report()` returns an empty report on missing keys

`format_bug_predict_report(result, input_data)` formats the structured output from the three subagents into the final markdown report. If `result` is missing the expected top-level keys (`summary`, `bugs`, or `suggestions`), the function produces a report that is syntactically valid but empty in the affected sections — no error is raised.

This can happen when a subagent (`pattern-scanner`, `risk-correlator`, or `prevention-advisor`) times out or returns a partial response. Treat a report with a zero finding count as a signal to check whether all three subagents completed successfully, not as confirmation that the codebase is clean.

## Subagent synthesis can mask conflicting findings

`BugPredictionWorkflow` runs three subagents and then synthesizes their output into a single report. The orchestrator's system prompt instructs it to be "thorough but concise," which means it may consolidate or drop lower-confidence findings during synthesis to keep the report readable.

If you need the raw per-subagent output — for example, to audit why a known risky pattern did not appear in the final report — you currently have no way to access intermediate results through the public API. Rely only on the synthesized report for decision-making, and re-run a scoped scan (`/bug-predict src/specific_module/`) to zoom in when the top-level results seem incomplete.

## Private constants can change without notice

`_INTENTIONAL_KEYWORDS`, `_SCANNER_TEST_PATTERNS`, and `_SUBAGENT_NAMES` are underscore-prefixed module constants. If your tooling or scripts reference them directly to replicate suppression logic or subagent routing, a refactor can break that integration silently. Use only the public entry points — `/bug-predict <path>` or `main()` — to invoke the workflow.

## How to reduce risk

1. **Audit suppressed findings manually.** After each scan, spot-check a sample of files the scanner did not flag to confirm that intentional-keyword suppression did not hide a real issue.

2. **Scope scans to catch test-file gaps.** If security-sensitive logic lives in test helpers, run a second, focused scan: `/bug-predict tests/` and verify the results separately from your main report.

3. **Treat empty sections as incomplete, not clean.** A `## Bugs` section with zero entries is only meaningful when you can confirm all three subagents returned complete results. A partial subagent response produces the same output as a clean codebase.

4. **Pin to the public API.** Call the workflow through `/bug-predict` or `main()` rather than importing private helpers directly. This insulates your workflow from internal refactors to `_INTENTIONAL_KEYWORDS` and `_SCANNER_TEST_PATTERNS`.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_report.py`

**Tags:** `bugs`, `prediction`, `scanning`, `race-condition`
