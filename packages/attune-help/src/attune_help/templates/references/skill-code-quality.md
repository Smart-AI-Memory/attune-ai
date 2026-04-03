---
type: reference
subtype: procedural
name: skill-code-quality
category: skill
tags: [review, quality, skill, plugin, reference]
source: plugin/skills/code-quality/SKILL.md
---

# Code Quality Review Reference

Complete reference for the code quality skill — every
check it runs, how scoring works, and how to act on
results. Runs on your Claude subscription — no API key
or additional cost.

## Invocation

```
/code-quality <path>
```

Or natural language:

```
review my code
check src/ for quality issues
analyze the auth module
how's the code health?
```

## The guided flow

The skill uses a Socratic discovery pattern — it asks
questions to scope the work before running. Here's what
to expect:

| Step | What you're asked | Default if skipped |
|------|-------------------|-------------------|
| 1. Scope | "Which files or directory?" | Current working directory |
| 2. Depth | "Quick, standard, or deep?" | Standard |

Provide both inline to skip the questions entirely:

```
deep review of src/auth/
```

## Depth levels

| Depth | Checks run | Estimated time | Use case |
|-------|-----------|----------------|----------|
| **Quick** | Style, formatting, imports | Seconds | Pre-commit, single file |
| **Standard** | + Logic, exceptions, likely bugs | ~1 min | Pull requests, daily work |
| **Deep** | + Security, architecture, test gaps | ~3 min | Pre-release, critical code |

## All checks by category

### Style

| Check | What it catches | Severity | Auto-fixable? |
|-------|----------------|----------|---------------|
| Unused imports | `import os` never referenced | Low | Yes |
| Line length | Lines exceeding 100 characters | Low | Yes |
| Inconsistent naming | mixedCase vs snake_case | Low | Sometimes |
| Missing type hints | Public functions without annotations | Low | No |
| Formatting | Spacing, quotes, trailing whitespace | Low | Yes (Black/Ruff) |

### Correctness

| Check | What it catches | Severity | Auto-fixable? |
|-------|----------------|----------|---------------|
| Unreachable code | Statements after return/raise/break | High | No |
| Wrong return type | Return value doesn't match type hint | High | No |
| Mutable defaults | `def f(items=[])` — shared across calls | High | No |
| Shadowed names | Variable in inner scope hides outer | Medium | No |
| None comparison | `x == None` instead of `x is None` | Medium | Yes |

### Likely bugs

| Check | What it catches | Severity | Auto-fixable? |
|-------|----------------|----------|---------------|
| Broad except | `except Exception:` masks real errors | Medium | No |
| Race conditions | Shared mutable state without locks | High | No |
| Off-by-one | Wrong boundary in range/slice | High | No |
| Unclosed handles | File opened without `with` statement | Medium | No |
| Format mismatch | Wrong arg count in string formatting | High | No |

### Structural

| Check | What it catches | Severity | Auto-fixable? |
|-------|----------------|----------|---------------|
| High coupling | Too many cross-imports between modules | Medium | No |
| God classes | Single class with too many responsibilities | Medium | No |
| Long functions | Methods exceeding 50 lines | Low | No |
| Circular deps | Package A imports B imports A | High | No |
| Dead code | Functions defined but never called | Low | No |

### Security overlap (deep only)

| Check | What it catches | Severity | Auto-fixable? |
|-------|----------------|----------|---------------|
| eval/exec | Code injection risk (CWE-95) | Critical | No |
| Path traversal | Unvalidated file operations (CWE-22) | Critical | No |
| Hardcoded secrets | API keys or tokens in source | Critical | No |

For thorough security analysis, use the dedicated
[security audit](con-tool-security-audit) skill.

## Output format

Results are presented as a scored report grouped by
category:

```markdown
## Code Quality Report

**Health:** 78/100 | **Files:** 23 | **Issues:** 12

### Style (4 issues)

| File | Line | Issue | Auto-fix? |
|------|------|-------|-----------|
| [config.py:45](src/config.py#L45) | 45 | Unused import 'os' | Yes |
| [login.py:12](src/auth/login.py#L12) | 12 | Line exceeds 100 | Yes |

### Correctness (3 issues)

| File | Line | Issue | Auto-fix? |
|------|------|-------|-----------|
| [handler.py:89](src/api/handler.py#L89) | 89 | Unreachable code | No |

### Likely Bugs (3 issues)

| File | Line | Issue | Auto-fix? |
|------|------|-------|-----------|
| [executor.py:67](src/hooks/executor.py#L67) | 67 | Broad except | No |

### Structural (2 issues)

| File | Issue | Suggestion |
|------|-------|------------|
| src/auth/ | 8 cross-imports | Extract shared types to a common module |
| handler.py | 340 lines | Split into handler + helpers |
```

File links are clickable — click to jump directly to
the issue.

## Scoring

| Range | Rating | Meaning | Typical action |
|-------|--------|---------|----------------|
| 90-100 | Excellent | Clean, minor nits | Ship it |
| 75-89 | Good | Issues but no blockers | Fix before merge |
| 50-74 | Needs work | Significant issues | Prioritize fixes |
| 0-49 | Poor | Major problems | Stop and address |

The score weights by severity: critical and high issues
reduce the score more than style issues. A project can
have 20 style nits and still score 85, but one
unvalidated eval drops it below 50.

## After the review

You'll be offered follow-up options based on what was
found:

| Goal | What to say | When it's offered |
|------|-------------|-------------------|
| Fix auto-fixable issues | "fix the quality issues" | When auto-fixable issues found |
| Focus on one category | "just show me the likely bugs" | Always |
| Compare before/after | "review again and compare" | After making fixes |
| Generate tests | "write tests for the risky files" | When likely bugs found |
| Security audit | "scan for vulnerabilities" | When security overlap found |
| Export results | "export quality report as markdown" | Always |

## Want to learn more?

- Say **"what is code quality?"** to go back to the overview
- Say **"how do I run a code quality review?"** for the step-by-step guide
- Say **"what is security audit?"** for dedicated security analysis
- Say **"tell me about bug prediction"** to predict where failures happen
