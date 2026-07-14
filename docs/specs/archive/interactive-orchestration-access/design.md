# Design: Interactive Orchestration Access

**Status:** ARCHIVED — feature removed after dogfooding showed both
engines were dead. See [decisions.md](decisions.md) D-FINAL. The design
below is preserved for historical context only; the shipped surfaces
(`wizard`/`agent` skills, drivers) were removed, not maintained.
**Requirements:** [requirements.md](requirements.md) ·
**Decisions:** [decisions.md](decisions.md)

---

## The seam

The wizard engine is already **declarative**:

- `BaseWizard.steps: list[WizardStep]` — an ordered list of step
  definitions (`src/attune/wizards/base.py`).
- `StepType` ∈ {`question`, `llm`, `review`, `decompose`, `preview`,
  `confirm`} — each handled by a private `_run_*_step` coroutine.
- `async run(initial_context)` — loops the steps, pausing inside
  `question`/`review`/`confirm` steps to collect input.

The interaction (asking the human) and the work (LLM calls,
decomposition, building results) are *tangled* inside `run()`. The
design **splits** them:

- **Engine keeps the work** — every `_run_*_step` stays in the engine.
- **Skill provides the human I/O** — the model drives the loop,
  rendering `question` steps via `AskUserQuestion` and feeding answers
  back to the engine.

This avoids re-implementing step logic in the skill (Goal 3).

---

## Chosen approach: Claude-driven skill + a step-wise engine API

Add a minimal **resumable driver API** to `BaseWizard`, leaving
`run()` intact for the CLI:

```text
list_steps() -> list[StepView]
    # Declarative view of each step: id, type, prompt/options for
    # `question` steps; for non-question steps, a flag that the engine
    # will execute it (no human input needed).

submit_step(step_id, answers, context) -> StepOutcome
    # Engine executes ONE step with the supplied answers (for question
    # steps) or no answers (for llm/review/etc.), mutates/returns the
    # running context, and returns either:
    #   - content to display (llm/review/preview output), or
    #   - the next step id, or
    #   - a terminal WizardResult.
```

`StepView` / `StepOutcome` are small dataclasses; `context` is the
same dict `run()` threads today, so the two code paths share state
semantics.

### Flow (the `wizard` skill drives this)

```text
1. user: "run the debug wizard [on X]"
2. skill: resolve wizard via list_wizards(); seed initial_context
3. loop over list_steps():
     - question step  -> AskUserQuestion(step.prompt, step.options)
                         -> submit_step(id, answers, context)
     - other step     -> submit_step(id, {}, context); display content
   (the SKILL holds `context` across conversation turns — it is the
    pause/resume mechanism; no server-side session store needed)
4. render the terminal WizardResult
```

The model is the natural driver: it already pauses for
`AskUserQuestion` and resumes on the user's reply, turn to turn. The
skill file is the script that tells it how.

### Why not stateful MCP tools

A `start/answer/status/resume` MCP-tool quartet holding session state
server-side also works and would serve non-Claude consumers — but it
is heavier (server-side session lifecycle, expiry, concurrency) and
the model would still have to poll it. Since the model is *already* an
interactive agent, letting it hold `context` and drive
`AskUserQuestion` is lighter and matches the existing skill model.
Recorded as the rejected alternative in decisions.md (D2); revisit
only if a non-Claude surface is required.

---

## Phase 2 (agents) — IMPLEMENTED

Agent-team access reuses the same "model drives, engine works"
principle, with a deterministic preview + a gated run:

- `attune.orchestration.team_driver.describe_team_for_task(task)` —
  deterministic, **no LLM**. Wraps
  `MetaOrchestrator().analyze_and_compose(task)` and serializes the
  resulting `ExecutionPlan` (agents from the templates, composition
  strategy, estimated cost/duration, quality gates) for a preview.
- `team_driver.run_team_for_task(task, ...)` — composes AND executes:
  `MetaOrchestrator().compose_team(task)` → `DynamicTeam.execute()`.
  This is the LLM-heavy step.
- The `agent` skill: goal → `describe_team_for_task` preview → confirm
  the cost via `AskUserQuestion` → `run_team_for_task` → present the
  `DynamicTeamResult`.

Guard `TestAgentRunSurface` enforces the run surface. Tests cover the
deterministic compose/preview offline; the LLM-heavy run is left to
manual/integration use (cost + keyed-CI hazard), mirroring Phase 1.

---

## Guard change (reverse coverage, run-surface)

Today's registry-coverage guard checks "wizard is *listed* in the
catalog" (catalog-completeness) — not "wizard is *runnable*". Add a
check that every `list_wizards()` entry is named by a run-surface skill
(the `wizard` skill), mirroring the existing tool→skill check. Same for
agents in Phase 2. This is what stops the gap from silently returning.

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Engine `run()` and `submit_step()` drift (two code paths) | medium | `submit_step` is the unit `run()` calls per step; refactor `run()` to loop over `submit_step` so there is ONE execution path. |
| A wizard step type needs mid-step human input the StepView can't express | medium | Phase-1 audit of all 5 wizards' step definitions before finalizing `StepView`; cover every `StepType` in tests. |
| Model mis-drives the loop (skips/reorders steps) | low | The skill script is explicit and step-gated; `submit_step` returns the authoritative next step id rather than trusting the model to sequence. |
| Phase-2 team API shifts under the sketch | low | Phase 2 design deferred until Phase 1 lands. |
