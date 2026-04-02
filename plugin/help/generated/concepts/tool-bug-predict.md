---
type: concept
name: tool-bug-predict
tags: [security, bugs, scanning]
source: plugin/skills/bug-predict/SKILL.md
---

# Bug Prediction

## What

Predicts likely bug locations by scanning for three pattern
categories: dangerous_eval (HIGH), broad_exception (MEDIUM),
and incomplete_code (LOW). Applies smart false-positive
filtering to suppress known-safe patterns like test fixtures,
JavaScript regex.exec(), and documented graceful degradation.

## Why

Finding bugs before users do saves hours of debugging. The
scanner focuses on the patterns that historically cause the
most production incidents -- eval injection, swallowed
exceptions, and unfinished TODO code paths.

## When to use

- During code review to catch patterns humans miss
- Before merging large PRs with new business logic
- To audit unfamiliar code you inherited or onboarded
- As a periodic health check on high-churn modules

## What it detects

| Pattern | Severity | What it catches |
|---------|----------|-----------------|
| dangerous_eval | HIGH | `eval()`, `exec()`, `compile()` on input |
| broad_exception | MEDIUM | Bare `except:`, unlogged `except Exception` |
| incomplete_code | LOW | TODO, FIXME, HACK, XXX comments |

## Related Topics

- **Task**: Use the bug-predict skill -- step-by-step
- **Reference**: Skill: bug-predict -- full reference
