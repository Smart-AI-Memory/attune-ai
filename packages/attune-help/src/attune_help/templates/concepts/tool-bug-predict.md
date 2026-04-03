---
type: concept
name: tool-bug-predict
tags: [security, bugs, scanning]
source: plugin/skills/bug-predict/SKILL.md
---

# Bug Prediction

Bug prediction scans your codebase for the patterns that
historically cause production incidents. Instead of waiting
for bugs to surface, it analyzes code structure, complexity,
and known anti-patterns to tell you where failures are most
likely to happen next.

## What it predicts

The scanner looks for three categories of risk, each with
different confidence levels and severity:

| Pattern | Severity | Confidence | What to look for |
|---------|----------|------------|------------------|
| **dangerous_eval** | HIGH | High | `eval()`, `exec()`, `compile()` on any input — code injection vectors |
| **broad_exception** | MEDIUM | Medium | Bare `except:`, unlogged `except Exception:` — errors silently swallowed |
| **incomplete_code** | LOW | Low | TODO, FIXME, HACK, XXX comments — unfinished code paths that break under edge cases |

## Risk factors beyond patterns

The scanner also weighs contextual signals that increase
bug likelihood:

- **Cyclomatic complexity** — deeply nested conditionals
  and long function bodies correlate with higher defect
  rates
- **Change frequency** — files modified often ("hot" files)
  are more likely to contain regressions
- **Code smells** — functions over 50 lines, classes with
  too many methods, duplicated logic across modules

## Smart false-positive filtering

Not every match is a real bug. The scanner automatically
suppresses known-safe patterns:

- `eval()` inside test fixture strings (test data, not
  executable code)
- JavaScript `regex.exec()` method calls (safe, not
  Python's `exec()`)
- Broad exceptions with `# INTENTIONAL:` comments and
  `# noqa: BLE001` markers
- Version detection fallbacks, cleanup/teardown code, and
  optional feature guards

## When you'd use it

- Before merging a large PR — catch patterns humans miss
- During code review — focus human attention on real risks
- After onboarding unfamiliar code — map risk hotspots fast
- As a periodic health check on high-churn modules
- Before a release — verify no new high-severity patterns
  crept in

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is security audit?"** for vulnerability scanning
- Say **"what is code quality?"** for a broader code review
