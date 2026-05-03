---
name: tool-attune-hub
source: plugin/skills/attune-hub/SKILL.md
summary: Attune Hub is a natural-language router that serves as a single entry point
  for all Attune skills, using Socratic discovery to understand your intent and dispatch
  you to the appropriate workflow for tasks like security audits, code reviews, test
  generation, planning, and refactoring.
tags:
- hub
- routing
- discovery
type: concept
---

# Attune Hub

## Overview

Attune Hub is the central natural-language router for all Attune skills. Describe what you want to accomplish in plain English, and the hub identifies the right skill and dispatches to it — handling security audits, code reviews, test generation, planning, refactoring, and every other registered workflow. When your intent is ambiguous, the hub uses Socratic discovery to ask targeted clarifying questions before routing.

## Why Use the Hub

With 13+ skills available, remembering which one to invoke for each task adds unnecessary cognitive overhead. The hub eliminates that friction by serving as a single entry point: describe your goal, and the hub handles the rest.

## When to Use

- As your default starting point for any Attune workflow
- When you are unsure which skill fits your task
- To discover skills you did not know existed
- When you want guided, Socratic scoping before execution begins

## Routing Reference

The table below shows how common intents map to specific skills.

| Intent | Routed Skill |
|---|---|
| "find security issues" | `security-audit` |
| "review this code" | `code-quality` |
| "generate tests" | `smart-test` |
| "plan a feature" | `planning` |
| "prepare a release" | `release-prep` |
| "fix failing tests" | `fix-test` |
| "refactor this module" | `refactor-plan` |
| "write docs" | `doc-gen` |
| "predict bugs" | `bug-predict` |
| "run a workflow" | `workflow-orchestration` |

## Related Topics

- **Task** — [Use the Attune Hub skill: step-by-step](#)
- **Reference** — [Skill: attune-hub: full reference](#)
