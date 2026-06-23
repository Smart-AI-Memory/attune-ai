---
type: tip
name: refactor-plan-tip
feature: refactor-plan
depth: tip
generated_at: 2026-06-23T16:06:40.108874+00:00
source_hash: 198d821e7ba1dffdfe00c207be171d13fcf198bedb8c0fd84f251e83f8015fbb
status: generated
---

# Prioritize tech debt — scan for code smells and generate a refactoring roadmap

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `RefactorPlanWorkflow` and its async `execute`, plus the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_agent_plan`, `_SUBAGENT_NAMES` — are internal and may
  change.
- **Plan with refactor-plan, act with simplify-code.** Run the
  planner to get a sequenced roadmap, then apply individual items
  with simplify-code or your own edits.
- **Use `path` and `depth` to keep runs cheap.** A `quick` pass
  over one module is far faster than a `deep` pass over `src/`.
- **Read `metadata` to confirm scope.** It records the `path`,
  `depth`, and `max_turns` the run actually used.
