---
name: testing
description: Test runner, coverage analysis, and test generation
category: hub
aliases: [test, t]
tags: [testing, coverage, generation, pytest]
version: "1.0.0"
question:
  header: "Testing Hub"
  question: "What testing task do you need?"
  multiSelect: false
  options:
    - label: "Run tests"
      description: "Execute pytest test suite"
    - label: "Smart test"
      description: "Run only tests affected by changes"
    - label: "Check coverage"
      description: "Run tests with coverage report"
    - label: "Generate tests"
      description: "Auto-generate behavioral tests for a module"
---

# testing

Test runner, coverage analysis, and test generation hub.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/testing run` | Run full test suite |
| `/testing run <path>` | Run tests at specific path |
| `/testing smart` | Run only tests affected by changes |
| `/testing fix` | Auto-fix failing tests and re-run |
| `/testing coverage` | Run tests with coverage report |
| `/testing generate <module>` | Generate behavioral tests for module |

## Natural Language

Describe what you need:

- "run the tests"
- "check coverage for the config module"
- "generate tests for src/attune/workflows/base.py"
- "what's my test coverage?"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST execute the workflow, not answer ad-hoc.**

### Context Gathering (ALWAYS DO FIRST)

Before executing any action below, gather current project context:

1. Run: `git status --short`
2. Run: `git log --oneline -5`
3. Run: `git branch --show-current`
4. Run: `uv run pytest --co -q 2>/dev/null | tail -5` (test count)

Use this context to inform your actions (e.g., which files changed, how many tests exist).

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/testing run` | `uv run pytest -v` |
| `/testing run <path>` | `uv run pytest <path> -v` |
| `/testing run -k <pattern>` | `uv run pytest -k "<pattern>" -v` |
| `/testing smart` | Invoke `/smart-test` — run only tests for changed files |
| `/testing smart --fix` | Invoke `/smart-test --fix` — smart select + auto-fix failures |
| `/testing fix <path>` | Invoke `/fix-test <path>` — diagnose and fix failing tests |
| `/testing fix --lf` | Invoke `/fix-test --lf` — fix last failed tests |
| `/testing coverage` | `uv run pytest --cov=src --cov-report=term-missing` |
| `/testing coverage <target>` | `uv run pytest --cov=<target> --cov-report=term-missing` |
| `/testing generate <module>` | Run Test-Gen wizard: select target → analyze coverage gaps → decompose test tasks → preview → confirm |
| `/testing generate batch` | Run Test-Gen wizard in batch mode for multiple modules |

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "run tests", "pytest", "test suite" | `uv run pytest -v` |
| "smart test", "changed files", "affected tests" | Invoke `/smart-test` |
| "fix test", "auto fix", "repair test" | Invoke `/fix-test` |
| "coverage", "how much is covered" | `uv run pytest --cov=src --cov-report=term-missing` |
| "generate tests", "write tests for" | Run Test-Gen wizard flow |
| "failing", "broken test", "why does this fail" | Debug the failing test |

**IMPORTANT:** When arguments are provided, DO NOT just display documentation. EXECUTE the command.

### CLI Reference

```bash
# Test execution
uv run pytest
uv run pytest -v
uv run pytest <path> -v
uv run pytest -k "test_name"

# Coverage
uv run pytest --cov=src --cov-report=term-missing
uv run pytest --cov=src --cov-report=html

# Test generation (via wizard)
# Use /wizard run test-gen or /testing generate <module>
```
