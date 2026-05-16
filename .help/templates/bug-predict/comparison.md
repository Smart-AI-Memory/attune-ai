---
type: comparison
name: bug-predict-comparison
feature: bug-predict
depth: comparison
generated_at: 2026-05-16T06:19:45.799901+00:00
source_hash: c4c1270dc9f702985426a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Comparison: Bug Prediction vs Security Audit vs Code Quality Review

## What each tool does

Bug prediction, security auditing, and code quality review all inspect your source code, but they answer different questions and operate at different scopes.

| Capability | Bug Prediction | Security Audit | Code Quality Review |
|---|---|---|---|
| **Primary question** | Where will production failures happen next? | What vulnerabilities exist? | How maintainable is this code? |
| **Output** | Risk score (0–100) + prioritized finding list | Vulnerability report | Style, complexity, and coverage report |
| **Severity tiers** | HIGH / MEDIUM / LOW | Typically CVE-severity | Usually no severity — all findings are peers |
| **False-positive filtering** | Built-in (suppresses test fixtures, `regex.exec()`, `# INTENTIONAL:` comments, `# noqa: BLE001`) | Varies by tool | Rarely built-in |
| **Actionable next step** | Named file + line number + plain-English description | Patch or configuration change | Refactor suggestion |
| **Subagent architecture** | Three specialized subagents: `pattern-scanner`, `risk-correlator`, `prevention-advisor` | Single-pass scanner | Single-pass linter |
| **Guided flow** | Yes — prompts for path and severity filter if you omit them | No | No |

## What bug prediction detects

The three subagents coordinate to cover distinct risk surfaces:

- **`pattern-scanner`** — flags `dangerous_eval` (HIGH), `broad_exception` (MEDIUM), and `incomplete_code` (LOW) patterns
- **`risk-correlator`** — weighs cyclomatic complexity, change frequency, and code smells (functions over 50 lines, excessive methods, duplicated logic)
- **`prevention-advisor`** — produces prioritized refactoring advice and testing recommendations specific to the findings

A security audit covers a wider vulnerability surface (dependency CVEs, authentication logic, data exposure) but does not correlate those findings with change frequency or complexity. Code quality review catches maintainability problems but assigns no severity and does not predict which issues are most likely to cause a runtime failure.

## Tradeoffs

**Bug prediction wins when:**
- You need a ranked, severity-ordered list of where failures are *most likely*, not an exhaustive catalog of every issue
- You want automatic suppression of known-safe patterns so you aren't triaging noise
- You're working against a deadline (pre-merge, pre-release) and need to know what to fix *first*

**Bug prediction loses when:**
- You need CVE references or dependency vulnerability data — use a security audit
- You need compliance-oriented metrics (test coverage, documentation coverage, line-length rules) — use a code quality review
- You're doing exploratory work on a throwaway script where the overhead of a three-subagent workflow isn't justified

## Feature entry points

| Entry point | Source file | Use it when |
|---|---|---|
| `/bug-predict <path>` | `bug_predict.py` | Running interactively in Claude Code |
| `format_bug_predict_report(result, input_data)` | `bug_predict_report.py` | Embedding a formatted report in another workflow |
| `main()` | `bug_predict_report.py` | Running from the CLI outside Claude Code |

## Use bug prediction when…

- **Pre-merge review:** You're merging a large PR and want to focus human attention on the highest-risk changes, not every style warning.
- **Unfamiliar code:** You've onboarded a new module and need a risk map before touching anything.
- **Pre-release check:** You want confirmation that no new HIGH-severity patterns (`eval()` on user input, bare `except:`) crept in during the sprint.
- **Recurring health check:** You run it weekly on high-churn modules to track whether risk scores are improving or drifting.

**Use a security audit instead** when your concern is vulnerability classes that bug prediction doesn't model — CVEs in dependencies, insecure cryptography, or authentication bypass paths.

**Use a code quality review instead** when your goal is maintainability metrics, compliance reporting, or enforcing team style conventions across the whole codebase.

## Source files

- `src/attune/workflows/bug_predict.py`
- `src/attune/workflows/bug_predict_report.py`

**Tags:** `bugs`, `prediction`, `scanning`, `race-condition`
