---
name: spec-engine
source: content/features/spec-engine.md
tags:
- spec
- planning
type: tip
---

# Spec Ladders — goal-driven spec development with approval loops

## Notes & tips

- **Depend only on the public API.** `pipeline` exports
  `PipelineOrchestrator`, `PipelineResult`, `TaskResult`, and
  `read_spec`. `spec` exports `SpecState`, `clear_state`,
  `find_resumable_plans`, `format_progress_bar`, `get_pending_tasks`,
  `load_state`, `present_task_detail`, `present_task_result`,
  `present_tasks`, and `save_state`. `execute_with_approval` lives in
  `attune.spec.runner`. Private helpers can change without notice.
- **Presenter functions are pure.** `present_tasks`,
  `present_task_detail`, `present_task_result`, and
  `format_progress_bar` accept `pipeline` data types, hold no state,
  and have no coupling to the pipeline layer — safe to call anywhere.
- **Prefer `skip_task_ids` over `clear_state` for re-runs.** Clearing
  state is irreversible mid-run; skipping completed tasks preserves
  your `completed` list and keeps `total_cost` / `duration_ms`
  accurate.
