---
type: concept
name: bug-predict-concept
feature: bug-predict
depth: concept
generated_at: 2026-05-16T06:19:45.764713+00:00
source_hash: c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde
status: generated
---

# Bug Prediction

Bug prediction scans your codebase for code patterns and complexity signals that historically lead to production failures — before those failures happen.

## How it works

When you run `/bug-predict <path>`, a `BugPredictionWorkflow` orchestrates three specialized subagents in sequence:

- **pattern-scanner** — detects dangerous code patterns such as `eval()` on user input, bare `except:` blocks, and TODO/FIXME markers
- **risk-correlator** — weighs contextual signals like cyclomatic complexity, file churn rate, and code smells to produce a risk score (0–100)
- **prevention-advisor** — synthesizes findings into prioritized, actionable refactoring and testing recommendations

After all three subagents finish, the workflow merges their output into a single structured report with a summary, per-finding severity table, and prevention strategies. The `format_bug_predict_report` function renders this as human-readable markdown with clickable file and line-number links.

## Three-tier severity model

Every finding lands in one of three severity buckets:

| Severity | Pattern | Example |
|----------|---------|---------|
| HIGH | `dangerous_eval` | `eval()` or `exec()` called on user-supplied input |
| MEDIUM | `broad_exception` | Bare `except:` that silently swallows errors |
| LOW | `incomplete_code` | `TODO`, `FIXME`, or `HACK` comments marking unfinished paths |

The scanner suppresses false positives automatically — for example, `eval()` inside test fixture strings, JavaScript's `regex.exec()`, and broad exceptions annotated with `# INTENTIONAL:` or `# noqa: BLE001` are all filtered out before results reach you.

## When it matters

Bug prediction is most valuable at transition points where new risk is most likely to enter the codebase:

- **Before merging a large PR** — surface patterns that escape manual review
- **After inheriting unfamiliar code** — map risk hotspots quickly without reading every file
- **Before a release** — confirm no new HIGH-severity patterns crept into hot files
- **As a recurring health check** — track whether risk scores improve or drift over time

## Relationship to other tools

Bug prediction focuses on *structural* risk — patterns and complexity that predict where bugs will occur. For *existing* security vulnerabilities, use a security audit instead (`"scan for security issues"`). For broader code quality concerns, use the code quality review (`"what is code quality?"`).
