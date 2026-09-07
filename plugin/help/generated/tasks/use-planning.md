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
   "What kind of planning? Feature spec, TDD approach, or architecture review?" Skip when the request implies the type.

2. **Define subject**
   Depending on type: - Feature: "What feature? What problem does it solve?" - TDD: "What behavior should the tests verify?" - Architecture: "What system? Any specific concerns?"

3. **Define scope**
   "How deep? Quick outline or detailed plan?" **Order on every host.** The **Subject** phrasing branches on **Type**,
   so never batch all three. On Claude, ask **Type** and **Scope** (both
   select-shaped and independent) in one `AskUserQuestion` call when both are
   open, then ask **Subject** with the type-specific phrasing —
   conversationally unless the conversation supplies honest candidate
   options. On hosts not yet reviewed (Gemini is deferred), settle **Type**
   first, then gather **Subject** and **Scope** as one form via the `elicit`
   skill's compatibility path. If only one dimension is open, ask it as a
   single question — never force a one-field form (the §4 batching rule).

4. **Review planning execution guidance**
   1. Use `EnterPlanMode` to create a structured plan; on Claude, settle
      remaining material choices before leaving plan mode — `AskUserQuestion`
      for select-shaped ones, a typed question otherwise, and never against a
      stated conversation preference
   2. If context from multiple files is needed, call
      `research_synthesis` first to gather insights
   3. Present the plan for user approval before any
      implementation


## Related Topics
- **Reference**: Skill: planning — full reference
