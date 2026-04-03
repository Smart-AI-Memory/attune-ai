---
type: task
name: use-workflow-orchestration
tags: [skill, task]
source: plugin/skills/workflow-orchestration/SKILL.md
---

# How to Run Workflow Orchestration

## Quick start

The fastest way: describe the analysis you need in
plain English.

```
run security and code review on src/auth/
```

Or pick specific workflows:

```
/workflow-orchestration security, test-audit, release-prep
```

You'll get a combined report with findings from every
workflow, grouped by severity.

## Choosing which workflows to run

You can name workflows explicitly or describe your goal
and let the skill pick:

| You say | Workflows it runs |
|---------|-------------------|
| "full review of src/" | security, code-review, bug-predict |
| "pre-release check" | security, test-audit, release-prep |
| "security and tests on src/auth/" | security, test-audit |
| "everything on this module" | all available workflows |

If you don't specify, the skill asks:

> "Which workflows do you want to run? For example:
> security + code review, or a full pre-release check?"

You can also specify a path up front or wait to be
asked:

> "Which path or files should I analyze?"

## Choosing execution order

Workflows run in the order you list them. A good
default order for comprehensive analysis:

1. **Security Audit** -- find blockers first
2. **Code Review** -- quality and correctness
3. **Bug Prediction** -- failure hotspots
4. **Test Audit** -- coverage gaps
5. **Release Prep** -- final readiness check

If you don't specify order, the skill uses a sensible
default: security-first, then quality, then testing.

## Reading the combined results

The orchestrator merges findings from all workflows
into one report:

```
Workflow Orchestration Report
Workflows: security-audit, code-review, test-audit
Path: src/auth/
Overall Score: 74/100

Critical (1)
  src/auth/session.py:89  -- eval() on user input
    [security-audit] CWE-95

High (3)
  src/auth/login.py:203   -- Path not validated
    [security-audit] CWE-22
  src/auth/login.py:45    -- Missing error handling
    [code-review]
  src/auth/session.py:*   -- 0% test coverage
    [test-audit]

Medium (2)
  src/auth/oauth.py:112   -- Broad exception
    [code-review]
  src/auth/utils.py:34    -- Dead code path
    [code-review]

Summary by Workflow
  security-audit    82/100  2 findings
  code-review       71/100  3 findings
  test-audit        68/100  1 finding
```

Each finding shows which workflow flagged it, so you
know the source. The overall score is a weighted
average across all workflows.

## What to do next

After reviewing the combined report:

- **Fix critical issues** -- "fix the critical findings"
- **Run another pass** -- "add bug-predict to the results"
- **Generate tests** -- "write tests for the flagged files"
- **Go deeper on one area** -- "deep review src/auth/session.py"
- **Export** -- "export the report as JSON"

## Want to learn more?

- Say **"tell me more"** for the complete reference --
  all workflows, execution order, output format
- Say **"what is workflow orchestration?"** to go back
  to the overview
- Say **"run a security audit"** to run just one
  workflow instead
