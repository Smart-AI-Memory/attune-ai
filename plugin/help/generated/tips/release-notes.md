---
name: release-notes
source: content/features/release-notes.md
tags:
- release
- changelog
- advisory
type: tip
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
