---
type: concept
name: tool-workflow-orchestration
tags: [workflows, orchestration, routing]
source: plugin/skills/workflow-orchestration/SKILL.md
---

# Workflow Orchestration

## What

Routes natural language requests to the correct analysis
workflow. Supports security audits, code reviews, test
generation, performance analysis, bug prediction,
documentation generation, and release preparation. Accepts
a workflow name or intent description and dispatches to the
matching workflow with the right parameters.

## Why

Remembering the exact skill name for every task is
friction. Workflow orchestration lets you describe what you
want ("check this module for bugs") and routes to the
right workflow automatically, so you stay in flow.

## When to use

- When you know the analysis type but not the skill name
- To run a workflow by intent rather than exact command
- When chaining multiple analyses on the same target
- To discover which workflows are available

## Available workflows

| Workflow | What it does |
|----------|-------------|
| security-audit | Scans for vulnerabilities and CWEs |
| code-review | Style, logic, and architecture review |
| test-generation | Creates tests for uncovered code |
| bug-predict | Detects likely bug patterns |
| doc-gen | Generates docs from source code |
| release-prep | Multi-agent release readiness check |
| deep-review | Multi-pass security + quality + gaps |

## Related Topics

- **Task**: Use the workflow-orchestration skill -- step-by-step
- **Reference**: Skill: workflow-orchestration -- full reference
