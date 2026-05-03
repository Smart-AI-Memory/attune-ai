---
name: tool-code-quality
source: plugin/skills/code-quality/SKILL.md
summary: Code Quality is a unified analysis tool that combines code review, bug prediction,
  and deep security analysis across three depth levels (Quick, Standard, and Deep)
  to provide a single quality score and report instead of requiring separate linting,
  bug scanning, and review commands.
tags:
- review
- quality
- linting
type: concept
---

# Code Quality

## What

Code Quality combines code review, bug prediction, and deep review into a single analysis. It operates at three depth levels:

- **Quick** — style and linting
- **Standard** — logic and patterns
- **Deep** — security, architecture, and test gap analysis

## Why

Running separate tools for linting, bug scanning, and code review means three commands and three reports to reconcile. Code Quality merges all three into a single pass and produces a unified score, giving you the full picture in one output.

## When to Use

- Before opening a pull request
- After a large refactor, to verify nothing degraded
- When you need a single quality score for a module
- To compare quality across different parts of a codebase

## What It Covers

| Depth | Tools | Focus |
|-------|-------|-------|
| Quick | Ruff, Black | Style, formatting, imports |
| Standard | + Bug prediction patterns | Logic errors, broad exception handling |
| Deep | + Security, architecture analysis | CWE mapping, coupling, test gap analysis |

## Related Topics

- **Task**: Use the code-quality skill — step-by-step walkthrough
- **Reference**: Skill: code-quality — full reference
