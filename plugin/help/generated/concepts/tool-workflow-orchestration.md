---
name: tool-workflow-orchestration
source: plugin/skills/workflow-orchestration/SKILL.md
summary: This template covers a workflow orchestration system that routes natural
  language requests to the appropriate analysis workflow (such as security audits,
  code reviews, test generation, bug prediction, documentation generation, and release
  preparation) based on user intent rather than requiring explicit skill names.
tags:
- workflows
- orchestration
- routing
type: concept
---

# Workflow Orchestration

## What

Routes natural language requests to the correct analysis workflow. Supports security audits, code reviews, test generation, performance analysis, bug prediction, documentation generation, and release preparation.

Accepts a workflow name or a plain-language description of intent and dispatches to the matching workflow with the appropriate parameters.

## Why

Remembering the exact skill name for every task creates unnecessary friction. Workflow orchestration lets you describe what you want — for example, "check this module for bugs" — and automatically routes to the right workflow, so you stay focused and in flow.

## When to Use

- You know the type of analysis you need but not the exact skill name
- You want to trigger a workflow by intent rather than by explicit command
- You are chaining multiple analyses against the same target
- You want to discover which workflows are available

## Available Workflows

| Workflow | Description |
|---|---|
| `security-audit` | Scans for vulnerabilities and CWEs |
| `code-review` | Reviews style, logic, and architecture |
| `test-generation` | Creates tests for uncovered code paths |
| `bug-predict` | Detects likely bug patterns |
| `doc-gen` | Generates documentation from source code |
| `release-prep` | Multi-agent release readiness check |
| `deep-review` | Multi-pass security, quality, and gap analysis |

## Related Topics

- **Task** — Use the workflow-orchestration skill: step-by-step walkthrough
- **Reference** — Skill: workflow-orchestration: full parameter and option reference
