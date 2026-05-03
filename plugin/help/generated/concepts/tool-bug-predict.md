---
name: tool-bug-predict
source: plugin/skills/bug-predict/SKILL.md
summary: Bug Prediction identifies and ranks three categories of risky code patterns—dangerous
  eval usage, broad exception handling, and incomplete code markers—while filtering
  out false positives to help developers catch bugs before production.
tags:
- security
- bugs
- scanning
type: concept
---

# Bug Prediction

## What

Bug Prediction scans your code for three categories of risky patterns and ranks them by severity:

| Category | Severity | What it catches |
|---|---|---|
| `dangerous_eval` | HIGH | `eval()`, `exec()`, `compile()` called on external input |
| `broad_exception` | MEDIUM | Bare `except:` clauses, unlogged `except Exception` blocks |
| `incomplete_code` | LOW | `TODO`, `FIXME`, `HACK`, `XXX` comments marking unfinished logic |

Smart false-positive filtering suppresses known-safe patterns — such as test fixtures, JavaScript `regex.exec()` calls, and documented graceful-degradation handlers — so results stay focused on genuine risks.

## Why

Catching bugs before users encounter them saves hours of debugging and prevents production incidents. These three pattern categories account for a disproportionate share of real-world issues: eval injection opens security vulnerabilities, swallowed exceptions hide failures silently, and unfinished code paths surface unexpectedly under edge-case conditions.

## When to Use

- **Code review** — catch risky patterns that are easy to overlook during manual inspection
- **Pre-merge checks** — audit large PRs introducing new business logic before they land
- **Onboarding unfamiliar code** — quickly assess inherited or recently acquired codebases
- **Periodic health checks** — monitor high-churn modules on a regular cadence

## Related Topics

- **Task:** Use the bug-predict skill — step-by-step walkthrough
- **Reference:** Skill: bug-predict — full option and output reference
