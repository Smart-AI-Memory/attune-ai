---
type: comparison
name: bug-predict-comparison
feature: bug-predict
depth: comparison
generated_at: 2026-06-02T10:56:02.703254+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Bug Prediction vs. Related Scanning Approaches

Bug prediction finds *where* failures are likely to happen before they do — by analyzing code patterns, complexity, and change frequency. This page helps you decide when to use `BugPredictionWorkflow` directly, when to use the CLI entry point, and when a different tool is the better fit.

## How the approaches compare

| | **`BugPredictionWorkflow` (SDK)** | **`main()` CLI entry point** | **Security audit / code quality scan** |
|---|---|---|---|
| **Primary use** | Embed bug prediction in agent pipelines or automated tooling | Run a one-off scan from the terminal or a script | Vulnerability scanning or broad style enforcement |
| **Output** | `WorkflowResult` — structured, machine-readable | Human-readable report via `format_bug_predict_report()` | Varies by tool |
| **Customization** | `system_prompt_suffix` parameter lets you extend orchestrator behavior | Fixed prompt; no runtime customization | Depends on tool |
| **Subagent coordination** | Yes — orchestrates `pattern-scanner`, `risk-correlator`, and `prevention-advisor` automatically | Yes — same three subagents under the hood | Not applicable |
| **False-positive filtering** | Built in — suppresses known-safe patterns (test fixtures, `regex.exec()`, `# INTENTIONAL:` comments, `# noqa: BLE001`) | Same filtering | Not guaranteed |
| **Severity triage** | HIGH / MEDIUM / LOW with file path and line number | Same, formatted as readable report | Varies |
| **Best for** | CI pipelines, agent workflows, programmatic consumers | Interactive use, quick pre-commit checks | Compliance scanning, style linting |

## What bug prediction detects — and what it doesn't

`BugPredictionWorkflow` targets three specific pattern categories:

| Pattern | Severity | Examples caught |
|---|---|---|
| `dangerous_eval` | HIGH | `eval()` or `exec()` on user input, `compile()` on external data |
| `broad_exception` | MEDIUM | Bare `except:`, unlogged `except Exception:` |
| `incomplete_code` | LOW | TODO, FIXME, HACK, XXX comments in code paths |

It also weighs cyclomatic complexity, change frequency ("hot" files), and code smells (functions over 50 lines, duplicated logic). It does **not** replace a dedicated security audit for vulnerability scanning (e.g., dependency CVEs, injection flaws beyond `eval`) or a linter for style enforcement. Those tools answer different questions.

## Tradeoffs in depth

**`BugPredictionWorkflow` vs. `main()`**

Both use the same three subagents and the same false-positive suppression logic. The difference is in how you consume the output:

- `BugPredictionWorkflow.execute()` returns a `WorkflowResult` you can inspect programmatically. Use `system_prompt_suffix` to steer the orchestrator toward a specific concern (e.g., focusing synthesis on auth-related findings).
- `main()` calls `format_bug_predict_report(result, input_data)` and prints directly to stdout. There is no runtime customization — it is optimized for human readers, not downstream code.

**Bug prediction vs. security audit**

Bug prediction is proactive and pattern-based: it tells you *where* bugs are statistically likely. A security audit is reactive and rules-based: it tells you *what* known vulnerability classes are present. If you need both, run them independently — they don't overlap enough to substitute for each other.

## Use bug prediction when…

- **You're about to merge a large PR** and want to catch `dangerous_eval` or silent exception swallowing before code review.
- **You're onboarding to unfamiliar code** and need a risk map of the hottest files fast.
- **You're building an agent pipeline** that needs structured bug-likelihood data — use `BugPredictionWorkflow` and consume `WorkflowResult` directly.
- **You want a quick pre-release check** — run `main()` to get a formatted report with risk score, file links, and line numbers in seconds.
- **You need to customize orchestration** — pass `system_prompt_suffix` to `BugPredictionWorkflow.__init__()` to extend the orchestrator's default behavior without touching internals.

## Skip bug prediction when…

- Your concern is **known CVEs or dependency vulnerabilities** — use a dedicated security audit instead.
- You need **style or formatting enforcement** — a linter is the right tool.
- You're doing **a single throwaway check** on one function — the three-subagent workflow is heavier than necessary; a direct code review question is faster.
- The files you want to scan match the internal test patterns (`test_bug_predict`, `test_scanner`, `test_security_scan`) — the scanner intentionally skips these to avoid false positives in its own test suite.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_report.py`

**Tags:** `bugs`, `prediction`, `scanning`, `race-condition`
