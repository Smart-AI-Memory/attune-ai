---
type: reference
subtype: procedural
name: skill-workflow-orchestration
category: skill
tags: [skill, plugin]
source: plugin/skills/workflow-orchestration/SKILL.md
---

# Workflow Orchestration Reference

Complete reference for the workflow orchestration skill
-- every available workflow, execution order, combined
output format, and configuration.

## Invocation

```
/workflow-orchestration <workflows> [path]
```

Or natural language:

```
run security and code review on src/
pre-release check on the whole project
full analysis of src/auth/
```

## Socratic flow

The skill asks before executing:

1. **Goal** -- "What are you trying to accomplish?"
   (pre-release, comprehensive review, quick check)
2. **Workflows** -- "Which workflows should I run?"
   (or picks based on your goal)
3. **Scope** -- "Which path or files should I analyze?"
4. **Order** -- confirms execution sequence if you
   listed specific workflows

## Available workflows

The skill runs on your Claude subscription -- no API
key or additional cost. All workflows below are
available.

### Analysis

| Workflow | What it does | Typical time | Best for |
|----------|-------------|-------------|----------|
| **security-audit** | Scans for vulnerabilities, eval/exec, path traversal, secrets, SSRF | ~2 min | Pre-release gates, new code review |
| **code-review** | Quality, correctness, style, architecture analysis | ~3 min | PR review, onboarding to a module |
| **bug-predict** | Pattern analysis, complexity hotspots, failure prediction | ~1 min | Identifying fragile code before it breaks |
| **deep-review** | Multi-pass: security + quality + test gap analysis in one | ~5 min | Thorough review when time permits |
| **performance-audit** | Bottleneck detection, memory patterns, optimization tips | ~2 min | Before scaling or after perf regressions |

### Testing

| Workflow | What it does | Typical time | Best for |
|----------|-------------|-------------|----------|
| **test-generation** | Generates unit tests with edge cases | ~3 min | Filling coverage gaps |
| **test-audit** | Coverage audit and gap detection | ~2 min | Finding untested public APIs |
| **test-gen-parallel** | Batch test generation for 10-50 modules | ~8 min | Large-scale coverage campaigns |

### Documentation

| Workflow | What it does | Typical time | Best for |
|----------|-------------|-------------|----------|
| **doc-audit** | Documentation freshness and gap analysis | ~1 min | Pre-release doc check |
| **doc-gen** | Generates docs from source code | ~2 min | New module documentation |
| **doc-orchestrator** | Full documentation maintenance pipeline | ~4 min | Comprehensive doc refresh |

### Release

| Workflow | What it does | Typical time | Best for |
|----------|-------------|-------------|----------|
| **release-prep** | Health checks, changelog, dependency audits | ~3 min | Final check before publishing |

## Execution order

When you specify multiple workflows, they run in the
order you list them. If you describe a goal instead,
the skill uses this default order:

| Phase | Workflows | Why this order |
|-------|-----------|----------------|
| 1. Security | security-audit | Find blockers first |
| 2. Quality | code-review, bug-predict | Assess code health |
| 3. Deep | deep-review | Comprehensive pass if requested |
| 4. Testing | test-audit, test-generation | Coverage and gaps |
| 5. Docs | doc-audit, doc-gen | Documentation state |
| 6. Release | release-prep | Final readiness |

Security runs first so critical findings surface
immediately. You can stop the sequence at any point.

## Common workflow combinations

| Goal | Workflows to run | Total time |
|------|-----------------|------------|
| Pre-release gate | security-audit, test-audit, release-prep | ~7 min |
| Full code review | code-review, bug-predict, deep-review | ~9 min |
| Coverage campaign | test-audit, test-generation | ~5 min |
| New module review | security-audit, code-review, doc-audit | ~6 min |
| Everything | all workflows | ~20 min |

## Combined output format

The orchestrator merges findings from all workflows
into a single report:

```markdown
## Workflow Orchestration Report

**Workflows:** security-audit, code-review, test-audit
**Path:** src/auth/
**Overall Score:** 74/100

### Critical

| File | Issue | Source |
|------|-------|--------|
| [session.py:89](src/auth/session.py#L89) | eval() on user input (CWE-95) | security-audit |

### High

| File | Issue | Source |
|------|-------|--------|
| [login.py:203](src/auth/login.py#L203) | Path not validated (CWE-22) | security-audit |
| [login.py:45](src/auth/login.py#L45) | Missing error handling | code-review |
| [session.py](src/auth/session.py) | 0% test coverage | test-audit |

### Summary by Workflow

| Workflow | Score | Findings | Time |
|----------|-------|----------|------|
| security-audit | 82/100 | 2 | 1m 48s |
| code-review | 71/100 | 3 | 2m 32s |
| test-audit | 68/100 | 1 | 1m 15s |
| **Overall** | **74/100** | **6** | **5m 35s** |
```

Findings are deduplicated -- if security-audit and
deep-review flag the same line, it appears once with
both sources noted.

## Scoring

The overall score is a weighted average:

| Range | Rating | Meaning |
|-------|--------|---------|
| 90-100 | Excellent | No critical or high findings |
| 75-89 | Good | Minor issues, no blockers |
| 50-74 | Needs work | High-severity findings present |
| 0-49 | Critical | Critical findings, do not release |

## After the report

| Goal | What to say |
|------|-------------|
| Fix critical issues | "fix the critical findings" |
| Add another workflow | "also run bug-predict on the same path" |
| Generate tests | "write tests for the flagged files" |
| Deep dive one file | "deep review src/auth/session.py" |
| Export for CI | "export the report as JSON" |
| Compare over time | "compare with last orchestration run" |

## Want to learn more?

- Say **"what is workflow orchestration?"** to go back
  to the overview
- Say **"how do I run workflow orchestration?"** for the
  step-by-step guide
- Say **"what is security audit?"** to learn about a
  specific workflow
- Say **"run a pre-release check"** to start one now
