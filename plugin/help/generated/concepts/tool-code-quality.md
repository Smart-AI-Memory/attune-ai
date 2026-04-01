---
type: concept
name: tool-code-quality
tags: [review, quality, linting]
source: plugin/skills/code-quality/SKILL.md
---

# Code Quality

## What

Combines code review, bug prediction, and deep review into
a single quality analysis. Operates at three depth levels:
quick (style and linting), standard (logic and patterns),
and deep (security, architecture, and test gap analysis).

## Why

Running separate tools for linting, bug scanning, and
review means three commands and three reports. Code quality
merges them into one pass with a unified score, so you see
the full picture in a single output.

## When to use

- Before opening a pull request for review
- After a large refactor to verify nothing degraded
- When you want a single quality score for a module
- To compare quality across different parts of the codebase

## What it covers

| Depth | What runs | Focus |
|-------|-----------|-------|
| Quick | Ruff + Black checks | Style, formatting, imports |
| Standard | + Bug predict patterns | Logic errors, broad exceptions |
| Deep | + Security + architecture | CWE mapping, coupling, gaps |

## Related Topics

- **Task**: Use the code-quality skill -- step-by-step
- **Reference**: Skill: code-quality -- full reference
