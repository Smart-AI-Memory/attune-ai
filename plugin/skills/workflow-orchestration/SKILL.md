---
name: workflow-orchestration
description: "Run automated analysis workflows — security, reviews, tests, performance, and release prep"
---

## Scoping

Before running, ask:

1. **Goal**: "What are you trying to accomplish?"
2. **Scope**: "Which path or files should I analyze?"

Based on the answer, route to the appropriate workflow.

## Workflows

| Workflow | MCP Tool | What It Does |
|----------|----------|--------------|
| Security Audit | security_audit | Scans for vulnerabilities, dangerous patterns, secrets |
| Code Review | code_review | Quality, correctness, and security analysis |
| Bug Prediction | bug_predict | Pattern analysis and likely bug detection |
| Test Generation | test_generation | Generates unit tests with edge cases |
| Performance Audit | performance_audit | Bottleneck detection and optimization |
| Release Prep | release_prep | Health checks, changelog, dependency audits |

## Execution

Route to the matching MCP tool with the scoped path:

```
security_audit(path="<user-specified path>")
code_review(path="<user-specified path>")
```

## Output Format

Present results grouped by severity with clickable
file links using markdown link syntax.

## Follow-Up

After presenting results, offer:

- "Want me to fix the critical issues?"
- "Should I run another workflow on the same path?"
- "Want to generate tests for the flagged files?"
