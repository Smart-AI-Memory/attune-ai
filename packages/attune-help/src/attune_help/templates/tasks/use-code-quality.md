---
type: task
name: use-code-quality
tags: [review, quality, skill, task]
source: plugin/skills/code-quality/SKILL.md
---

# How to Run a Code Quality Review

## Quick start

Say what you want reviewed:

```
review src/auth/
```

Or use the skill directly:

```
/code-quality src/auth/
```

You'll get a health score and a list of issues grouped
by category.

## The guided flow

When you ask for a review, you'll be guided through two
quick questions before anything runs:

| Step | What you're asked | Why |
|------|-------------------|-----|
| 1. Scope | "Which files or directory should I review?" | Keeps results focused — a full project scan takes longer and produces noise |
| 2. Depth | "Quick scan, standard, or deep review?" | Matches thoroughness to what you actually need right now |

If you provide both upfront ("deep review of src/auth/")
the questions are skipped and it runs immediately.

## Choosing what to review

| Command | What it reviews | When to use |
|---------|----------------|-------------|
| `/code-quality src/config.py` | One file | Quick check on a specific change |
| `/code-quality src/auth/` | A directory tree | Review a module before PR |
| `/code-quality .` | The whole project | Baseline health assessment |
| "compare quality of src/auth/ vs src/api/" | Side-by-side | Find which area needs more attention |

## Choosing depth

| Depth | What runs | Time | Best for |
|-------|-----------|------|----------|
| **Quick** | Style and formatting only | Seconds | Pre-commit, fast feedback |
| **Standard** | + Logic errors, likely bugs | ~1 min | Pull requests (default) |
| **Deep** | + Security, architecture, test gaps | ~3 min | Pre-release, critical modules |

Natural language works:

- "quick review of src/" — style only
- "deep review of src/auth/" — everything including security
- "review src/" — standard (default)

## Reading the results

Results come back as a scored report:

```
Code Quality Report
Health: 78/100 | Files: 23 | Issues: 12

Style (4 issues)
  src/config.py:45     — Unused import 'os'
  src/auth/login.py:12 — Line exceeds 100 chars

Correctness (3 issues)
  src/api/handler.py:89  — Unreachable code after return
  src/auth/session.py:34 — Mutable default argument

Likely Bugs (3 issues)
  src/hooks/executor.py:67 — Broad except masks errors
  src/api/webhook.py:23    — Race condition on shared state
  src/cache.py:91          — Off-by-one in range boundary

Structural (2 issues)
  src/auth/             — High coupling (8 cross-imports)
  src/api/handler.py    — 340 lines, consider splitting
```

Each finding includes the file, line number, and
description. File links are clickable — click to jump
directly to the issue.

## What the score means

| Range | Rating | What it tells you | Typical action |
|-------|--------|-------------------|----------------|
| 90-100 | Excellent | Clean, minor style nits at most | Ship it |
| 75-89 | Good | Some issues but nothing blocking | Fix before merge |
| 50-74 | Needs work | Significant issues present | Prioritize fixes |
| 0-49 | Poor | Major problems | Stop and address |

## What to do next

After the results, you'll be offered follow-up options:

| Goal | What to say |
|------|-------------|
| Fix auto-fixable issues | "fix the quality issues" |
| Focus on one category | "just show me the likely bugs" |
| Go deeper | say "tell me more" for the full reference |
| Run a security audit | "scan for vulnerabilities" |
| Generate tests | "write tests for the risky files" |

## Want to learn more?

- Say **"tell me more"** for the complete reference — every check, scoring details, configuration
- Say **"what is code quality?"** to go back to the overview
- Say **"scan for vulnerabilities"** to run a security audit instead
