---
type: concept
name: tool-spec
tags: [spec, planning, workflow]
source: plugin/skills/spec/SKILL.md
---

# Spec-Driven Development

Spec walks you from a rough idea to working code through
five structured phases. Instead of jumping straight into
implementation, you brainstorm approaches, decompose work
into tasks, review for gaps, get explicit approval, then
execute one task at a time with quality gates after each.

## The five phases

| Phase | What happens | Interaction | Quality gate | Output |
|-------|-------------|-------------|--------------|--------|
| **Brainstorm** | Explore the problem space, surface constraints, generate competing approaches | Socratic Q&A -- you describe the goal, spec asks clarifying questions | At least 2 viable approaches identified | Prose summary with trade-offs |
| **Decompose** | Break chosen approach into ordered tasks with acceptance criteria | Spec proposes tasks, you adjust scope and ordering | Every task has a testable acceptance criterion | XML task blocks saved to `.claude/plans/` |
| **Review** | Walk through the plan task by task, check for gaps and risks | You read each task, flag concerns, suggest edits | No open questions or unaddressed risks | Annotated plan ready for sign-off |
| **Approve** | Final summary with task count, scope, and risk overview | Single yes/no gate -- nothing runs until you say go | Explicit user approval | Locked plan |
| **Execute** | Implement tasks one at a time, run quality gates after each | After each task: approve, redo with new instructions, or auto-run the rest | Quality score per task, severity-gated approval | Working code + state file tracking progress |

## Why spec-first matters

Starting to code without a plan leads to scope creep and
rework. Spec forces clarity upfront -- what are we building,
what are the edge cases, what does "done" look like -- before
a single line is written. The approval gate means you
always see the full plan before any files change. If you
don't like the direction, you adjust the spec, not the
code.

## The Socratic pattern

Each phase is conversational, not automatic. In brainstorm,
spec asks about your constraints, existing code, and goals
before proposing anything. In decompose, it explains each
task and asks if the breakdown matches your mental model.
In review, it highlights risks and asks if you want to
address them. You're always driving -- spec never executes
without your approval.

## When to use it

- For any feature that touches 3+ files
- When requirements are ambiguous or evolving
- To produce an auditable trail of design decisions
- When handing off implementation to another developer
- Before large refactors where the blast radius is unclear
- When you want quality gates on each implementation step

## What it produces

| Output | Where it lives | Purpose |
|--------|---------------|---------|
| Plan file | `.claude/plans/{topic-slug}.md` | Prose summary + XML task blocks |
| State file | `.claude/plans/{topic-slug}.state.json` | Tracks completed/pending tasks |
| Implemented code | Your source tree | Files created or modified per task |
| Quality gate results | Shown inline after each task | Pass/fail with severity and score |

## What to expect

When you ask to build something, you'll have a
conversation first -- not a wall of generated code. Spec
guides you through scoping before anything runs. If you
provide a detailed description upfront, the brainstorm
phase is shorter. If you're vague, expect more questions.

Runs on your Claude subscription -- no API key or
additional cost.

## Want to learn more?

- Say **"how do I use spec?"** for step-by-step
  instructions walking through each phase
- Say **"tell me more about spec"** for the complete
  reference with all phases, gates, and resume behavior
- Say **"plan a feature"** if you want high-level
  planning without the full spec workflow
