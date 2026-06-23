---
type: tip
name: release-notes-tip
feature: release-notes
depth: tip
generated_at: 2026-06-23T21:24:13.287162+00:00
source_hash: 3bee45ea7e9bedc48f6fdc7744f2c05ff0fd177419dba9606233f53b10818ab6
status: generated
---

# Draft release notes and an LLM go/no-go readiness advisory with four Agent SDK subagents

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `ReleasePreparationWorkflow` and its async `execute`, and the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_agent_prep`, `_SUBAGENT_NAMES`, `_DEPTH_MAX_TURNS` — are
  internal and may change.
- **Draft, then gate.** Use release-notes to write the changelog and
  read readiness, then run `release-prep` (`release-gate`) to gate the
  actual ship on measured numbers.
- **Use `depth` to trade coverage against cost.** A `quick` pass is
  far cheaper than a `deep` one; `ATTUNE_MAX_BUDGET_USD=0` lifts the
  cap when a pre-release run must finish.
- **Take the changelog from `final_output`.** Release-notes returns
  the drafted notes in the result; review and place them.
