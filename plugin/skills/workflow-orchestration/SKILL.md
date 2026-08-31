---
name: workflow-orchestration
description: "Run several analysis workflows together in one sweep. Triggers on: run all workflows, run multiple workflows, full analysis sweep, workflow orchestration."
argument-hint: "<workflow: security, review, tests, perf, release, bugs, docs>"
---

# Workflow Orchestration

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="workflows", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

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
| Release Notes | `release_notes` | Changelog draft + go/no-go advisory |

## Execution

### Shared command workspace (preferred)

Open adapter `workflow-orchestration` with the goal, validated path, and exact
ordered child list. Present its widget or returned Markdown. The bound
`run_workflows` action requires explicit confirmation because it can invoke
multiple paid workflows. Run only the returned children.

Publish every real child outcome as one `child_result` carrying its name,
status, detail, and exact probe. Then publish `orchestration_complete`. The
adapter restores the requested order and synthesizes `MISSING` for any absent
child; `FAIL`, `ERROR`, or `MISSING` keeps the aggregate failed, while warnings
produce a visibly degraded receipt. Never collapse mixed outcomes into a
clean summary. Preserve the same per-child receipts in compact text when the
shared tools are unavailable.

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
