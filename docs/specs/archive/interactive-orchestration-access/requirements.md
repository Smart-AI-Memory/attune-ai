# Requirements: Interactive Orchestration Access

**Status:** ARCHIVED — premise reversed by dogfooding (2026-06-25, #1093); reconciled at 2026-07-14 triage (was: approved)

**Created:** 2026-06-25
**Owner:** Patrick + agent

---

## Problem

attune ships two capability registries that a shipped-plugin user can
now **see but cannot run**:

- **Wizards** (5: `debug`, `refactor`, `release-prep`, `security`,
  `test-gen`) — guided multi-step flows.
- **Agent templates** (14) — reusable agent archetypes for
  multi-agent teams.

Since #1088 both registries are enumerated by `list_capabilities`
(the `catalog` skill), so they are *discoverable*. But there is **no
shipped invocation surface**: no `plugin/skills/` skill names them, no
MCP tool runs them, and there is no `attune wizard` / `attune agent`
CLI subcommand. They are runnable only from the repo's own dev-time
`.claude/skills/{wizard,agent}`, which are **not** part of the
distributed plugin.

### Why they were left out (not an oversight)

Wizards/agents run on an **interactive** engine: `BaseWizard.run()`
loops over declarative `steps` (`StepType` = question / llm / review /
decompose / preview / confirm), pausing to collect human answers
mid-flow. A single-shot MCP tool cannot drive pause → collect →
resume, so the existing "thin MCP tool" surfacing pattern (used for
workflows) does not fit. Surfacing them needs a **Claude-driven
bridge**, which is more design than a mechanical wrapper — hence the
deferral. (The CHANGELOG referenced an "interactive-orchestration-
access spec" that did not yet exist; this is that spec.)

---

## Goals

1. A shipped-plugin user can **run** any registered wizard through the
   natural-language surface, answering its steps conversationally.
2. A shipped-plugin user can **create and run** an agent team from the
   builtin templates through the natural-language surface.
3. The interaction is driven by Claude (the model) using
   `AskUserQuestion`, with the wizard/agent **engine retaining all
   step logic** — no duplication of step execution in the skill.
4. The new surfaces are caught by the registry-coverage guard so they
   cannot silently regress (extend the existing reverse-coverage gate).

## Non-Goals

- Re-architecting the wizard/agent engines beyond the minimal seam
  needed to drive them step-wise.
- Surfacing wizards/agents to **non-Claude** agentskills.io consumers
  (a stateful-server variant is noted as an alternative in design.md
  but is explicitly out of scope here).
- Changing what any individual wizard or agent template *does*.

---

## Scope (phased)

| Phase | Scope |
|-------|-------|
| **1** | Wizards — a `wizard` plugin skill that lists and runs the 5 registered wizards step-by-step. |
| **2** | Agent teams — an `agent` plugin skill that builds and runs a team from the 14 builtin templates. |

Phase 2 is gated on Phase 1 landing and its seam proving out; its
design is sketched, not finalized, here (avoid over-speccing a future
phase against an engine API that may shift).

---

## User stories

- *As a plugin user*, when I say "walk me through the debug wizard",
  the model lists the wizard's steps and asks me each question via
  `AskUserQuestion`, then shows the wizard's output — without me
  touching the CLI.
- *As a plugin user*, when I say "run the security wizard on `src/`",
  the model starts that wizard with my path as initial context and
  drives it to completion.
- *As a plugin user*, when I say "set up a test-coverage agent team",
  the model picks the matching templates and runs the team. *(Phase 2)*

---

## Acceptance criteria

**Phase 1 (wizards):**

- [ ] A `plugin/skills/wizard/SKILL.md` exists, is model-invocable,
      and is synced to `.agents/`.
- [ ] The skill can enumerate wizards (live, via `list_wizards()` /
      `list_capabilities`) and run a chosen one to a `WizardResult`.
- [ ] Each `StepType` is handled: `question` steps render through
      `AskUserQuestion`; `llm`/`review`/`decompose`/`preview`/`confirm`
      steps execute in the engine and surface their content.
- [ ] The engine exposes a step-wise driving API (see design.md) with
      unit tests; the monolithic `run()` still works for the CLI.
- [ ] Registry-coverage guard updated so "wizard registered ⇒ has a
      run surface" is enforced (not just "is listed").
- [ ] `attune-hub` Skills Reference + skill-count guard updated.

**Phase 2 (agents):**

- [ ] An `agent` plugin skill builds + runs a team from builtin
      templates; coverage guard extended to agents' run surface.

---

## Constraints

- The bridge must not weaken the **interactive** UX the wizards were
  designed for (Socratic, step-gated) — see `.claude/CLAUDE.md`
  Socratic Interaction Rule.
- Per `decision-routine.md`, the engine step-API change is real
  implementation work → its tasks use XML-enhanced prompts.
- Markdown/skill-frontmatter rules and the 250-char description cap
  apply to the new skills.
