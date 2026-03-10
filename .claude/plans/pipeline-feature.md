# Pipeline: Spec-Driven Development Lifecycle

**Created:** 2026-03-05
**Source:** /brainstorm session

## Problem

Attune AI has powerful hubs (/brainstorm, /plan, /dev,
/testing, /release) and real agentic infrastructure
(DynamicTeam, agent templates, quality gates) but they're
disconnected. Users chain commands manually, losing context
between steps. The agent templates sit unused. There's no
first-class SDLC pipeline that brings it all together.

## Goals

- Orchestrate the full development lifecycle as a single
  guided pipeline with four phases
- Activate existing agent teams and templates in the
  Development phase (code_reviewer + security_auditor)
- Support interactive checkpoints (user confirms) and
  automatic gates (simplify, tests — no input needed)
- Let users jump into any phase independently
- Make this beginner-friendly and aligned with Spec-Driven
  Development (SDD)
- Build the feature, then write a LinkedIn article about it

## End State

A user types `/pipeline "add webhook support"`. The system:

1. Walks them through brainstorm (Socratic discovery)
2. Produces an XML-enhanced spec via /plan
3. Executes the spec with agent teams and quality gates
4. Runs the full test suite
5. Asks "Ready to release?" — if yes, bumps version,
   updates changelog, commits, pushes, builds for PyPI

## Phases

### Phase 1: Analysis & Design (Interactive)

- Existing `/brainstorm` + `/plan` flow
- Single agent, Socratic conversation
- Output: XML-enhanced spec with task prompts
- No changes needed — works as-is

### Phase 2: Development (Mixed gates)

For each task in the XML spec:

1. **Build** — Claude Code executes the task
2. **Quality gate** (automatic) — agent team runs in
   parallel: `code_reviewer` + `security_auditor`
3. **Per-task test** (automatic) — test only modified files
4. **Simplify** (automatic) — run simplify on changed code
5. **Next task** — repeat

Agent team uses `two_phase` strategy from DynamicTeam:
build first, then validate.

### Phase 3: Evaluate (Automatic)

- Full test suite as integration gate
- Pass = proceed to release gate
- Fail = pause, show failures, ask user how to proceed

### Phase 4: Release (Interactive gate)

Pipeline pauses and asks: "Ready to release?"

If yes:
1. Version bump (pyproject.toml)
2. Update CHANGELOG.md
3. Update README if needed
4. Commit all changes
5. Push to git repo
6. Clean dist/ and build for PyPI

## Gate Types

| Gate | Type | User input? |
|------|------|-------------|
| Brainstorm discovery | Interactive | Yes |
| Plan confirmation | Interactive | Yes |
| Code review + security | Automatic | No |
| Per-task test | Automatic | No |
| Simplify | Automatic | No |
| Full test suite | Automatic | No (pause on fail) |
| Release decision | Interactive | Yes |

## Entry Points

Users can jump into any phase:

| Command | Phase |
|---------|-------|
| `/pipeline` | Full flow from Phase 1 |
| `/pipeline "topic"` | Full flow with context |
| `/brainstorm` | Phase 1 only |
| `/plan` | Phase 1 (planning only) |
| `/dev` | Phase 2 (with existing spec) |
| `/testing` | Phase 3 only |
| `/release` | Phase 4 only |

## Existing Infrastructure to Leverage

- `DynamicTeam` — multi-strategy agent execution
- `WorkflowComposer` — converts workflows to agent teams
- Agent templates: `code_reviewer`, `security_auditor`,
  `code_simplifier`, `test_generator`
- `AgentStateStore` — persistence between phases
- `MultiAgentStageMixin` — opt-in for workflows
- Progressive tier escalation (CHEAP -> CAPABLE -> PREMIUM)
- Quality gate evaluation

## Open Questions

- Should the pipeline state persist across sessions (resume
  a pipeline started yesterday)?
- What's the CLI command name? `/pipeline`, `/sdlc`,
  `/lifecycle`?
- Should Phase 2 quality gates be configurable (skip
  security audit for docs-only changes)?
