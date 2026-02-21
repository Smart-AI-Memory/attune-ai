---
name: plan
description: Planning, TDD scaffolding, architecture, and refactoring strategies
category: hub
aliases: [planning, p]
tags: [planning, tdd, architecture, strategy, refactoring, brainstorm]
version: "1.0.0"
question:
  header: "Planning Hub"
  question: "What do you need to plan?"
  multiSelect: false
  options:
    - label: "Plan a feature"
      description: "Break down a feature into implementation steps"
    - label: "Brainstorm"
      description: "Think through a problem with guided discovery"
    - label: "Refactoring strategy"
      description: "Plan safe incremental refactoring steps"
    - label: "Architecture review"
      description: "Evaluate and plan architectural changes"
---

# plan

Planning hub — feature breakdowns, TDD scaffolding, refactoring strategies, and architecture reviews.

**This hub is advisory.** It helps you think through plans before executing. Use it to break down complex work into safe, ordered steps.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/plan feature <description>` | Break feature into implementation tasks |
| `/plan brainstorm` | Guided brainstorming with structured discovery |
| `/plan tdd <module>` | Design test cases first, then plan implementation |
| `/plan refactor <path>` | Plan incremental refactoring steps |
| `/plan architecture` | Evaluate current architecture, propose improvements |
| `/plan review <path>` | Review code and plan improvements |

## Natural Language

Describe what you need to plan:

- "plan adding user authentication"
- "break down this feature into steps"
- "help me think through this problem"
- "how should I refactor the config module?"
- "design tests for the workflow engine"
- "review the architecture of the agent system"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST execute the planning workflow, not answer ad-hoc.**

### Context Gathering (ALWAYS DO FIRST)

Before executing any action below, gather current project context:

1. Run: `git status --short`
2. Run: `git log --oneline -5`
3. Run: `git branch --show-current`

Use this context to inform your planning (e.g., current branch, recent changes, uncommitted work).

### Reasoning Approach

For planning tasks, use structured reasoning to produce thorough plans:

<analysis-steps>
1. **Architecture analysis** — Read the target code and its imports to understand the current structure, patterns, and conventions in use
2. **Dependency mapping** — Identify which files depend on the target and which the target depends on; flag breaking change risks
3. **Step decomposition** — Break the work into ordered steps where each step is independently testable and deployable
4. **Risk assessment** — For each step, classify risk as LOW (isolated change), MEDIUM (touches shared code), or HIGH (changes public API or data schema)
5. **Test strategy** — Define what tests validate each step: unit tests for logic, integration tests for boundaries, manual verification for UX
6. **Rollback plan** — For MEDIUM/HIGH risk steps, identify how to revert if something goes wrong
</analysis-steps>

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/plan feature <desc>` | Break feature into numbered tasks with files, dependencies, and risks |
| `/plan brainstorm` | Invoke `/brainstorm` — guided discovery through Context → Problem → Goals → End State → Plan |
| `/plan tdd <module>` | Design test cases first, then create implementation plan |
| `/plan refactor <path>` | Run Refactor wizard: describe goal → analyze structure → decompose steps → preview → confirm |
| `/plan architecture` | Analyze project structure, evaluate architecture, propose improvements |
| `/plan review <path>` | `uv run attune workflow run code-review --path <path>` |

### Planning Output Format

When generating plans, use this structure:

```text
## Plan: <title>

### Overview
<1-2 sentence summary>

### Steps
1. **<Step name>** — <description>
   - Files: <files to modify>
   - Risk: LOW/MEDIUM/HIGH
   - Dependencies: <what must be done first>

2. **<Step name>** — <description>
   ...

### Risk Assessment
- <key risks and mitigations>

### Testing Strategy
- <how to verify the changes>
```

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "plan", "break down", "steps" | Break into implementation tasks |
| "brainstorm", "think through", "figure out" | Invoke `/brainstorm` guided discovery |
| "tdd", "test first", "design tests" | TDD scaffolding |
| "refactor", "restructure", "reorganize" | Run Refactor wizard flow |
| "architecture", "design", "structure" | Architecture review |
| "review", "evaluate" | Code review with planning |

**IMPORTANT:** When arguments are provided, DO NOT just display documentation. EXECUTE the planning workflow.
