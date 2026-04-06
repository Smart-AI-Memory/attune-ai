---
name: planning
description: "High-level development planning — features, TDD, architecture review. Triggers on: plan, feature, architecture, design, TDD, strategy."
---
# Planning

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="spec-engine", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Planning** — Helps you plan features, architecture, and TDD strategy before writing code.

High-level development planning and architecture design.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `feature` | Plan a new feature |
| `tdd` | Plan TDD approach |
| `architecture` | Architecture review |

## MCP Tools

| Tool | What It Does |
| ---- | ------------ |
| `research_synthesis` | Synthesize insights from multiple documents to inform planning |

Use `research_synthesis` when the user needs to gather
context from multiple files or docs before planning.

## Scoping

Before running, ask:

1. **Type**: "What kind of planning? Feature spec, TDD
   approach, or architecture review?"
2. **Subject**: Depending on type:
   - Feature: "What feature? What problem does it solve?"
   - TDD: "What behavior should the tests verify?"
   - Architecture: "What system? Any specific concerns?"
3. **Scope**: "How deep? Quick outline or detailed plan?"

## Execution

1. Use `EnterPlanMode` to create a structured plan
2. If context from multiple files is needed, call
   `research_synthesis` first to gather insights
3. Present the plan for user approval before any
   implementation
