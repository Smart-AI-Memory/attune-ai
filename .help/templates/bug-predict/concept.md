---
type: concept
name: bug-predict-concept
feature: bug-predict
depth: concept
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 750014addbbc0825c7da37de3ee7d765c2c29f9e0e9db47dbc9d3df3542340a0
status: generated
---

# Bug Prediction

Bug prediction scans your codebase for code patterns and complexity signals that correlate with production failures, so you can act before bugs surface at runtime.

## How it works

`BugPredictionWorkflow` orchestrates three specialized subagents — `pattern-scanner`, `risk-correlator`, and `prevention-advisor` — that each focus on a distinct domain and report structured findings. After all three finish, the workflow synthesizes their output into a single report with three sections:

- **Summary** — an overall risk score (0–100) and a brief executive summary of predicted hotspots
- **Bugs** — findings organized by severity (HIGH, MEDIUM, LOW), each with a file path, line number, pattern type, and plain-English description
- **Suggestions** — prioritized prevention strategies, including specific refactoring advice and testing recommendations

The orchestrator prompt instructs the workflow to cite file paths and line numbers wherever possible, so findings are immediately actionable rather than vague.

## The three-subagent pipeline

Each subagent handles one slice of the analysis:

| Subagent | Role |
|---|---|
| `pattern-scanner` | Detects dangerous code patterns such as `eval()` on user input, bare `except:` clauses, and TODO/FIXME markers |
| `risk-correlator` | Weighs contextual signals — cyclomatic complexity, change frequency, and code smells — to rank which findings matter most |
| `prevention-advisor` | Translates ranked findings into concrete refactoring and testing recommendations |

This division keeps each subagent focused, which improves both precision and the quality of the final synthesized report.

## Report formatting

`format_bug_predict_report(result, input_data)` converts the raw workflow output into the human-readable report you see in your conversation. The same formatting logic powers `main()`, the CLI entry point, so the report looks identical whether you invoke bug prediction through Claude Code or directly from the command line.

## False-positive suppression

Not every pattern match represents a real bug. The scanner automatically ignores known-safe cases — for example, code marked with intentional keywords such as `fallback`, `graceful`, or `intentional`, and test files matched by patterns like `test_bug_predict` and `test_scanner`. This filtering happens before findings reach the risk-correlator, so your report reflects genuine risk rather than noise.

## When bug prediction matters

- **Before merging a large PR** — surface patterns that slip through manual review
- **After onboarding unfamiliar code** — quickly map risk hotspots in a new module
- **Before a release** — confirm no new HIGH-severity patterns crept into high-churn files
- **As a periodic health check** — track whether risk scores improve or drift over time
