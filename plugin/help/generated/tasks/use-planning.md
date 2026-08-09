---
type: task
name: use-planning
tags: [skill, task]
source: plugin/skills/planning/SKILL.md
---

# Task: Use the planning skill

High-level development planning — features, TDD, architecture review. Triggers on: plan, feature, architecture, design, TDD, strategy.

Invoke with: `/planning <what to plan: feature, tdd, architecture>`

## Steps

1. **Define type**
   "What kind of planning? Feature spec, TDD approach, or architecture review?"

2. **Define subject**
   Depending on type: - Feature: "What feature? What problem does it solve?" - TDD: "What behavior should the tests verify?" - Architecture: "What system? Any specific concerns?"

3. **Define scope**
   "How deep? Quick outline or detailed plan?" **Surface.** The **Subject** phrasing branches on **Type**, so don't
batch all three — ask **Type** first (a single `AskUserQuestion`) when
it isn't already given by the `<what to plan>` argument. Once the type
is known, **Subject** (a textarea) and **Scope** (quick / detailed) are
independent and open: gather *those two* as one form via the `elicit`
skill, **preferring the rich widget surface** (`elicitation_render_widget`
→ `show_widget`) with the AskUserQuestion mapping as fallback. If only
one dimension is open, ask it as a single question — never force a
one-field form (the §4 batching rule).

4. **Execute the planning workflow**
   1. Use `EnterPlanMode` to create a structured plan
2. If context from multiple files is needed, call
   `research_synthesis` first to gather insights
3. Present the plan for user approval before any
   implementation


## Related Topics
- **Reference**: Skill: planning — full reference
