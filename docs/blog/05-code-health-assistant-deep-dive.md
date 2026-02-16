---
description: One Command to Rule Them All: The Code Health Assistant: **Date:** December 15, 2025 **Author:** Patrick Roebuck **Series:** Memory-Enhanced Development (Part 5
---

# One Command to Rule Them All: The Code Health Assistant

**Date:** December 15, 2025
**Author:** Patrick Roebuck
**Series:** Memory-Enhanced Development (Part 5)

---

## TL;DR

We got tired of running 5 different tools to check our code. So we built one command that runs them all—with auto-fix:

```bash
attune health              # Quick check: lint, format, types
attune health --deep       # Full check: + tests, security, deps
attune health --fix        # Auto-fix safe issues
```

Result: **One health score** (0-100) you can track over time, with trend analysis and hotspot detection.

---

## The Problem

Every Python project needs the same checks:

1. **Linting** — `ruff check .`
2. **Formatting** — `black --check .`
3. **Type checking** — `mypy .` or `pyright`
4. **Tests** — `pytest`
5. **Security** — `bandit -r .`
6. **Dependencies** — `pip-audit`

That's 6 different commands. 6 different output formats. 6 different ways to fail.

And if you want to fix issues? More commands:
- `ruff check . --fix`
- `black .`

Most developers run one or two checks, not all six. Technical debt accumulates silently.

---

## The Solution

```bash
attune health
```

Output:
```
📊 Code Health: Good (87/100)

🟢 Lint: 0 errors, 3 warnings
🟢 Format: All files formatted
🟢 Types: No errors
🟢 Tests: 142 passed, 0 failed
🟡 Security: 2 findings (1 false positive)
🟢 Deps: No vulnerabilities

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] Fix 3 auto-fixable issues  [2] See details  [3] Full report
```

One number. One command. One source of truth.

---

## How Health Scores Work

### Weighted Categories

Not all checks are equal. A security vulnerability is worse than a formatting issue:

| Category | Weight | Why |
|----------|--------|-----|
| Security | 100 | Vulnerabilities can be exploited |
| Types | 90 | Type errors often become runtime errors |
| Tests | 85 | Failed tests = broken functionality |
| Lint | 70 | Code quality affects maintainability |
| Format | 50 | Cosmetic but important for readability |
| Coverage | 40 | Nice to have, not critical |
| Deps | 30 | Usually low-severity, but check regularly |

### Score Calculation

```
health_score = 100 - weighted_penalty

where:
  weighted_penalty = sum(category_weight * category_penalty)
  category_penalty = min(issues / threshold, 1.0)
```

A project with:
- 0 security issues
- 0 type errors
- 3 lint warnings
- All tests passing

Gets a score of ~87/100 (lint warnings have low weight).

---

## The --deep Flag

Quick checks are fast (seconds), but sometimes you need everything:

```bash
attune health --deep
```

This runs:
- All quick checks (lint, format, types)
- Full test suite with coverage
- Security scan (bandit)
- Dependency audit (pip-audit)

Takes longer, but gives you the complete picture.

---

## Auto-Fix: The --fix Flag

```bash
attune health --fix
```

Output:
```
🔧 Auto-fixing safe issues...

Fixed 3 issues:
  ✓ src/api/client.py: Removed unused import
  ✓ src/utils/helpers.py: Fixed line length (2 lines)

Run 'attune health' to verify fixes.
```

### What Gets Fixed Automatically

**Safe fixes (always applied):**
- Unused imports
- Line length issues
- Trailing whitespace
- Import sorting
- Simple formatting

**Prompted fixes (with --interactive):**
- More complex refactors
- Potential behavior changes

```bash
attune health --fix --interactive
```

---

## Trend Tracking

This is where memory shines.

```bash
attune health --trends 30
```

Output:
```
📈 Health Trends (30 days)

Average Score: 85/100
Trend: IMPROVING (+5)
Best: 91/100 (Dec 14)
Worst: 78/100 (Nov 28)

Recent:
  Dec 15: 87/100
  Dec 14: 91/100
  Dec 13: 85/100
  Dec 12: 82/100
  Dec 11: 80/100

🔥 Hotspots (files with recurring issues):
  src/api/client.py: 12 issues over 30 days
  src/utils/helpers.py: 8 issues over 30 days
  tests/test_api.py: 5 issues over 30 days
```

### Why Trends Matter

A single health check tells you where you are. Trends tell you where you're going.

- **Improving trend**: Your refactoring is working
- **Declining trend**: Technical debt is accumulating
- **Stable trend**: You're maintaining quality (good!) or stuck (investigate)

---

## Hotspot Detection

Some files cause repeated issues:

```
🔥 Hotspots (files with recurring issues):
  src/legacy/importer.py: 23 issues over 90 days
  src/api/v1/handlers.py: 15 issues over 90 days
```

These are your high-leverage targets. Fix the hotspots, improve the trend.

---

## Real-World Example

We ran `attune health --deep` on the Attune AI itself:

```
📊 Code Health: Good (89/100)

🟢 Lint: 0 errors, 2 warnings
🟢 Format: All files formatted
🟢 Types: No errors (after v2.2.4 fixes!)
🟢 Tests: 2,236 passed, 3 skipped, 0 failed
🟢 Security: 0 findings
🟢 Deps: No vulnerabilities

Time: 47.3 seconds (with full test suite)
```

The type check took the longest. We fixed ~75 type annotation issues in v2.2.4 to get to "No errors."

---

## Configuration

Customize checks in your project config:

```yaml
# empathy.config.yml
health:
  checks:
    lint:
      enabled: true
      tool: ruff
      weight: 70
    format:
      enabled: true
      tool: black
      weight: 50
    types:
      enabled: true
      tool: pyright  # or mypy
      weight: 90
    tests:
      enabled: true
      tool: pytest
      weight: 85
      coverage_target: 80
    security:
      enabled: true
      tool: bandit
      weight: 100
    deps:
      enabled: true
      tool: pip-audit
      weight: 30

  thresholds:
    good: 85
    warning: 70
    critical: 50

  auto_fix:
    safe_fixes: true
    prompt_fixes: false
    categories: [lint, format]
```

---

## CI/CD Integration

Add to your GitHub Actions:

```yaml
- name: Health Check
  run: |
    pip install attune-ai
    attune health --deep --json > health.json

- name: Upload Health Report
  uses: actions/upload-artifact@v3
  with:
    name: health-report
    path: health.json
```

Fail the build if health drops below threshold:

```yaml
- name: Health Gate
  run: |
    attune health --deep
    if [ $? -ne 0 ]; then
      echo "Health check failed!"
      exit 1
    fi
```

---

## Before/After

| Workflow | Before | After |
|----------|--------|-------|
| Check code | 6 commands, 6 outputs | 1 command, 1 score |
| Fix issues | Manual, per-tool | `attune health --fix` |
| Track trends | Not tracked | Built-in with --trends |
| Find hotspots | Manual analysis | Automatic detection |
| CI/CD | Multiple steps | Single health gate |

---

## Try It Now

```bash
pip install attune-ai

# Quick check
attune health

# Full analysis
attune health --deep

# Auto-fix safe issues
attune health --fix

# See trends
attune health --trends 30
```

---

## What's Next

- **Per-PR health diffs** — "This PR improves health by +3"
- **Team health dashboards** — Compare across repos
- **Custom check plugins** — Add your own tools

---

## Links

- **CLI Guide:** [docs/CLI_GUIDE.md](../CLI_GUIDE.md#code-health-assistant-new-in-v220)
- **GitHub:** [github.com/Smart-AI-Memory/empathy](https://github.com/Smart-AI-Memory/empathy)
- **PyPI:** [pypi.org/project/attune-ai](https://pypi.org/project/attune-ai/)

---

*Built by [Smart AI Memory](https://smartaimemory.com) — One command to check them all.*
