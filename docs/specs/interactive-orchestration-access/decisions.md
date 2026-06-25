# Decisions: Interactive Orchestration Access

**Status:** approved
**Requirements:** [requirements.md](requirements.md) ·
**Design:** [design.md](design.md)

---

## Decision log

### D1 — Scope: both wizards and agents, phased (decided 2026-06-25)

Cover both registries in one spec but sequence delivery: **Phase 1
wizards**, **Phase 2 agent teams**. Wizards are the simpler, more
uniform problem (5 of them, a clean guided-Q&A pattern); agent-team
orchestration is harder and its build/run API is less settled.

**Why:** one spec keeps the "interactive pair" together (they share
the same root cause and the same "model drives, engine works"
solution), while phasing avoids blocking the easy win on the hard one.

### D2 — Bridge: Claude-driven skill, not stateful MCP tools
(decided 2026-06-25)

The model drives the interactive loop via `AskUserQuestion`, holding
the wizard `context` across conversation turns; the engine exposes a
thin step-wise API (`list_steps` / `submit_step`) and keeps all step
logic.

**Why:** the model is already an interactive agent that pauses and
resumes turn to turn — that IS the pause/collect/resume mechanism, so
no server-side session store is needed. It is lighter than a
`start/answer/status/resume` MCP-tool quartet and matches how the
existing skills work.

**Rejected alternative:** stateful MCP tools holding session state
server-side. More robust for **non-Claude** agentskills.io consumers,
but heavier (session lifecycle, expiry, concurrency) and unnecessary
while the only consumer is Claude. Revisit only if a non-Claude run
surface becomes a requirement (a Non-Goal here).

---

## Open decisions (resolve during Phase 1)

- **OD1 — `run()` re-use vs parallel path.** Strong preference: refactor
  `BaseWizard.run()` to loop over the new `submit_step()` so there is a
  single execution path (kills the drift risk in design.md). Confirm
  this is feasible for all six `StepType`s before committing.
- **OD2 — `StepView` shape.** Audit all 5 wizards' declarative `steps`
  first; `StepView` must express every `question`-step's prompt/options
  faithfully enough for `AskUserQuestion`, and flag non-question steps
  as engine-executed. Decide after the audit.
- **OD3 — skill naming collision.** A `wizard` skill name will exist in
  both `plugin/skills/` (new, shipped) and `.claude/skills/` (old, dev).
  Decide whether the dev one is retired or left as-is (per the
  three-skill-dir lesson, `.claude/skills/` is a separate non-shipped
  set; likely leave it, but confirm no loader picks both).
- **OD4 — guard for "runnable".** Extend `test_registry_coverage.py`
  with a wizard→run-surface check (every `list_wizards()` id named by
  the `wizard` skill). Mirror for agents in Phase 2.

---

## Cross-references

- Surfaced-but-not-runnable finding + sweep: this session's
  hidden-functionality audit (catalog completeness shipped in #1088).
- `.claude/rules/attune/xml-enhanced-prompts.md` — the engine step-API
  change is implementation work; its tasks use XML-enhanced prompts.
- `.claude/rules/attune/decision-routine.md` — spec origination path.
- Engine: `src/attune/wizards/base.py` (`BaseWizard`, `WizardStep`,
  `StepType`); registry: `src/attune/wizards/registry.py`
  (`list_wizards`). Agents: `src/attune/orchestration/agent_templates/`
  (`get_all_templates`), `team_builder.py`, `meta_orchestrator.py`.
