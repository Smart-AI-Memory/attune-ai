---
type: concept
name: tool-code-quality
tags: [review, quality, linting, skill]
source: plugin/skills/code-quality/SKILL.md
---

# Code Quality Review

A code quality review looks at your code from multiple
angles at once — style, correctness, likely bugs, and
structural health. Instead of running a linter, then a
bug scanner, then a reviewer, and reading three separate
reports, you get one pass with a unified score.

## What it catches

| Category | Examples | Severity | Auto-fixable? |
|----------|---------|----------|---------------|
| **Style** | Unused imports, line length, naming | Low | Often yes |
| **Correctness** | Unreachable code, wrong return types | High | Sometimes |
| **Likely bugs** | Broad exceptions, mutable defaults, race conditions | High | No |
| **Structural** | High coupling, god classes, circular deps | Medium | No |
| **Security overlap** | eval/exec, unvalidated paths (deep only) | Critical | No |

## When you'd use it

Before opening a pull request — catch issues before
reviewers do. After a large refactor — verify nothing
degraded. When inheriting unfamiliar code — get a
quick read on its health. Or any time you want a
single number that summarizes code quality for a file
or directory.

## How thorough it is

| Depth | What it covers | Best for |
|-------|---------------|----------|
| **Quick** | Style and formatting only | Pre-commit check, fast feedback |
| **Standard** | + Logic errors, likely bugs | Pull requests, regular development |
| **Deep** | + Security, architecture, test gaps | Pre-release, critical modules |

The default is standard.

## What to expect

When you ask for a code quality review, you'll be asked
a couple of questions first to scope the work — which
files to review and how deep to go. This keeps the
results focused on what you actually care about instead
of dumping everything at once.

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is security audit?"** for dedicated security analysis
- Say **"tell me about bug prediction"** to predict where failures happen
