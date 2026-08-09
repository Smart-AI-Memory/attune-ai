---
type: reference
subtype: procedural
name: skill-planning
category: skill
tags: [skill, plugin]
source: plugin/skills/planning/SKILL.md
---

# Reference: Skill: planning

High-level development planning — features, TDD, architecture review. Triggers on: plan, feature, architecture, design, TDD, strategy.

**Usage:** `/planning <what to plan: feature, tdd, architecture>`

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `feature` | Plan a new feature |
| `tdd` | Plan TDD approach |
| `architecture` | Architecture review |

## MCP Tools

| Tool | What It Does |
| ---- | ------------ |
| `research_synthesis` | Synthesize insights from source documents at a path to inform planning |

Use `research_synthesis` when the user needs to gather
context from a directory of files or docs before planning.
Pass the directory (or file) as `path`; optionally set
`depth` to `quick`, `standard`, or `deep`:

```
research_synthesis(path="<dir or file>", depth="standard")
```

## Scoping

Before running, ask:

1. **Type**: "What kind of planning? Feature spec, TDD
   approach, or architecture review?"
2. **Subject**: Depending on type:
   - Feature: "What feature? What problem does it solve?"
   - TDD: "What behavior should the tests verify?"
   - Architecture: "What system? Any specific concerns?"
3. **Scope**: "How deep? Quick outline or detailed plan?"

**Surface.** The **Subject** phrasing branches on **Type**, so don't
batch all three — ask **Type** first (a single `AskUserQuestion`) when
it isn't already given by the `<what to plan>` argument. Once the type
is known, **Subject** (a textarea) and **Scope** (quick / detailed) are
independent and open: gather *those two* as one form via the `elicit`
skill, **preferring the rich widget surface** (`elicitation_render_widget`
→ `show_widget`) with the AskUserQuestion mapping as fallback. If only
one dimension is open, ask it as a single question — never force a
one-field form (the §4 batching rule).

## Execution

1. Use `EnterPlanMode` to create a structured plan
2. If context from multiple files is needed, call
   `research_synthesis` first to gather insights
3. Present the plan for user approval before any
   implementation

## Related Topics
- **Reference**: Tool: Research Synthesis (`research_synthesis`)
