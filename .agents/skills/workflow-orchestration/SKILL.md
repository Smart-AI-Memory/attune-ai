---
name: workflow-orchestration
description: "Run analysis workflows — security, code review, tests, perf, bugs, docs, release. Triggers on: workflow, run, execute, analyze, security, review, test, perf, release, bugs, docs, audit."
---
# Workflow Orchestration

**IMPORTANT: Start your response by telling the user:**

> **Workflow Orchestration** — Runs multiple analysis workflows in sequence and combines the results.

## Scoping

Before running, ask:

1. **Goal**: "What are you trying to accomplish?"
2. **Scope**: "Which path or files should I analyze?"

Based on the answer, route to the appropriate workflow.

## Workflows

### Analysis

| Workflow | MCP Tool | What It Does |
| -------- | -------- | ------------ |
| Security Audit | `security_audit` | Scans for vulnerabilities, dangerous patterns, secrets |
| Code Review | `code_review` | Quality, correctness, and security analysis |
| Bug Prediction | `bug_predict` | Pattern analysis and likely bug detection |
| Performance Audit | `performance_audit` | Bottleneck detection and optimization |
| Deep Review | `deep_review` | Multi-pass: security, quality, and test gap analysis |

### Testing

| Workflow | MCP Tool | What It Does |
| -------- | -------- | ------------ |
| Test Generation | `test_generation` | Generates unit tests with edge cases |
| Test Audit | `test_audit` | Coverage audit and gap detection |
| Parallel Test Gen | `test_gen_parallel` | Batch test generation for 10-50 modules |

### Documentation

| Workflow | MCP Tool | What It Does |
| -------- | -------- | ------------ |
| Doc Audit | `doc_audit` | Documentation freshness and gap analysis |
| Doc Generation | `doc_gen` | Generate documentation for a module |
| Doc Orchestrator | `doc_orchestrator` | Full documentation maintenance pipeline |

### Release

| Workflow | MCP Tool | What It Does |
| -------- | -------- | ------------ |
| Release Prep | `release_prep` | Health checks, changelog, dependency audits |

## Execution

Route to the matching MCP tool with the scoped path:

```
security_audit(path="<user-specified path>")
code_review(path="<user-specified path>")
test_audit(path="<user-specified path>")
doc_audit(path="<user-specified path>")
```

## Output Format

Present results grouped by severity with clickable
file links using markdown link syntax.

## Help

After presenting results, call:

```
help_lookup(
    topic="workflow-orchestration",
    mode="workflow_help"
)
```

If templates are returned, offer: "I have tips about
this workflow — want to see them?"

## Follow-Up

After presenting results, offer:

- "Want me to fix the critical issues?"
- "Should I run another workflow on the same path?"
- "Want to generate tests for the flagged files?"
