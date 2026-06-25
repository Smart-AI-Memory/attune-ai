---
name: agent
description: "Compose and run a multi-agent team from the builtin templates for a goal. Triggers on: run an agent team, set up an agent team, multi-agent, orchestrate agents, agent team for, build a team."
argument-hint: "<the goal for the team>"
---

# Agent Team

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="agent", mode="preamble")` and display the
returned `preamble` text as a blockquote. Then tell the user they can
say "tell me more" for a step-by-step guide, or answer the scoping
question below to proceed.

If the MCP call fails, fall back to:

> **Agent Team** — Composes a multi-agent team from the builtin agent
> templates for your goal, shows you the proposed team and its
> estimated cost, then runs it once you confirm.

## Scoping

1. **Goal** — "What should the team accomplish?" (e.g. "improve test
   coverage to 90%", "audit this module for security").
2. **Context** (optional) — any starting facts (a path, a current
   metric) to inform composition.

## Execution

Two steps: preview the composed team (free, deterministic), then run it
(LLM-heavy) only after the user confirms.

1. **Preview the team** — compose a plan without running it:

   ```bash
   python -c "import json; from attune.orchestration import describe_team_for_task; print(json.dumps(describe_team_for_task('improve test coverage to 90%'), default=str))"
   ```

   Returns `{task, strategy, agents:[{id, role}], estimated_cost,
   estimated_duration, quality_gates}`. Present the proposed agents,
   the composition `strategy`, and the **estimated cost** to the user.

2. **Confirm before running** — use `AskUserQuestion`:
   "Run this team? (est. cost ~$X)" → Yes / No. This is a paid,
   multi-agent run; never skip the confirmation.

3. **Run the team** (only on Yes). This makes real multi-agent LLM
   calls:

   ```bash
   python -c "
   import json, asyncio
   from attune.orchestration import run_team_for_task
   result = asyncio.run(run_team_for_task('improve test coverage to 90%', context={}, input_data={}))
   print(json.dumps(result.to_dict() if hasattr(result, 'to_dict') else result.__dict__, default=str))
   "
   ```

## Output

Present the `DynamicTeamResult` readably: lead with the aggregated
outcome, then per-agent contributions, then run metadata (cost,
duration, which quality gates passed). If it failed, surface the error.

## How this differs from other skills

- **agent** *composes and runs a multi-agent team* (this skill).
- **wizard** runs a single guided step-by-step flow.
- **catalog** *lists* agent templates (and workflows, wizards, tools)
  but does not run them.
- The 6 Claude Code subagents in `plugin/agents/` are a different
  thing — reached via the Agent/Task tool, not this skill.

## Anti-Patterns

- DO NOT run the team without previewing the plan and confirming the
  cost first — it is a paid multi-agent run.
- DO NOT hand-author the team — always compose it live via
  `describe_team_for_task` / `run_team_for_task`.
- DO NOT use this for a single-step task — a plain workflow or the
  `wizard` skill is cheaper.
