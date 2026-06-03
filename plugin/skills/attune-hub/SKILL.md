---
name: attune-hub
description: "Developer workflow hub — routes to the right skill based on what you need. Triggers on: attune, help me, what can you do, workflows, setup, configure, capabilities."
argument-hint: "<what you need help with>"
---

# Attune Hub

**IMPORTANT: Start your response by telling the user:**

> **Attune Hub** — Your starting point — discovers what you need and routes you to the right skill.

## Scoping

If no argument is provided, use `AskUserQuestion`:

```yaml
question: "What are you trying to accomplish?"
header: "attune-ai"
options:
  - label: "Run a workflow"
    description: "Security audit, code review, test gen, perf, release prep"
  - label: "Manage memory"
    description: "Store, retrieve, search, or forget patterns"
  - label: "Configure settings"
    description: "Check setup, update attune-ai, view telemetry"
  - label: "Learn what attune-ai does"
    description: "Overview of capabilities and skills"
```

## Execution

Based on the user's answer or arguments, describe the
intent so Claude matches the right skill:

| Input | Describe to Claude |
| ----- | ------------------ |
| "Run a workflow" or `security` | "Run a security audit on the code" |
| "Run a workflow" or `review` | "Review the code for quality issues" |
| "Run a workflow" or `tests` | "Generate tests for uncovered code" |
| "Run a workflow" or `perf` | "Analyze code for performance issues" |
| "Run a workflow" or `release` | "Prepare for a release" |
| "Run a workflow" or `bugs` | "Predict likely bug locations" |
| "Manage memory" or `memory` | "Store or retrieve from memory" |
| "Configure settings" or `setup` | Run `attune doctor` and `attune auth` |
| "Configure settings" or `update` | Run `pip install --upgrade attune-ai` |

## Natural Language Routing

| Pattern | Route to |
| ------- | -------- |
| "security", "vulnerability", "audit" | security-audit skill |
| "review", "quality", "code review" | code-quality skill |
| "test", "generate tests", "coverage" | smart-test skill |
| "performance", "bottleneck", "optimize" | workflow-orchestration skill |
| "release", "publish", "ship" | release-prep skill |
| "bug", "predict", "risk" | bug-predict skill |
| "memory", "store", "remember" | memory-and-context skill |
| "docs", "documentation" | doc-gen skill |
| "plan", "feature", "architecture" | planning skill |
| "refactor", "tech debt", "simplify" | refactor-plan skill |
| "spec", "brainstorm", "plan and execute" | spec skill |

## Skills Reference

| Skill | Triggers |
| ----- | -------- |
| security-audit | security, vulnerability, audit, scan |
| code-quality | review, quality, bugs, code smell |
| bug-predict | predict bugs, risky code, what might break |
| doc-gen | generate docs, documentation, README |
| smart-test | generate tests, test gaps, coverage |
| fix-test | fix test, broken test, debug test |
| planning | plan, feature, architecture, TDD |
| refactor-plan | refactor, tech debt, simplify |
| release-prep | release, publish, deploy |
| memory-and-context | memory, store, retrieve, empathy |
| workflow-orchestration | workflow, run, analyze |
| spec | spec-driven dev, brainstorm and execute |
| rag-code-gen | grounded code, cite sources, verify against attune (needs `[rag]` extra) |
| coach | coach, learn, explain, tell me more, deeper |
| recall | recall, remember, what did I learn, prior session, past findings |

## MCP Server Not Running

If the MCP server is not responding, run:

```bash
pip install attune-ai
attune doctor
```
