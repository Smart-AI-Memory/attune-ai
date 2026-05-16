---
type: note
name: bug-predict-note
feature: bug-predict
depth: note
generated_at: 2026-05-16T06:19:45.797241+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Note: Bug Prediction internals

## How the workflow is structured

Bug prediction runs as an orchestrated workflow — `BugPredictionWorkflow` coordinates three subagents in sequence: `pattern-scanner`, `risk-correlator`, and `prevention-advisor`. Each subagent focuses on its own domain and returns structured markdown, which the orchestrator synthesizes into a single report with a Summary, Bugs, and Suggestions section.

The public surface has two distinct roles:

- **`BugPredictionWorkflow`** (`src/attune/workflows/bug_predict.py`) — manages the Agent SDK lifecycle, accepts an optional `system_prompt_suffix` to extend the default orchestrator prompt, and returns a `WorkflowResult`.
- **`format_bug_predict_report()`** and **`main()`** (`src/attune/workflows/bug_predict_report.py`) — handle presentation. `format_bug_predict_report()` converts the raw result dict into a human-readable report; `main()` is the CLI entry point that wires everything together.

## False-positive suppression

The scanner skips findings that match known-safe signals defined in `_INTENTIONAL_KEYWORDS` (`fallback`, `ignore`, `optional`, `best effort`, `graceful`, `intentional`) and test files matched by `_SCANNER_TEST_PATTERNS`. This means results reflect production code, not test fixtures or graceful-degradation paths.

## Source files

- `src/attune/workflows/bug_predict.py` — workflow orchestration
- `src/attune/workflows/bug_predict_report.py` — report formatting and CLI entry point

**Tags:** `bugs`, `prediction`, `scanning`
