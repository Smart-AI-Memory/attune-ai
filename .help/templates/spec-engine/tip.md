---
type: tip
name: spec-engine-tip
feature: spec-engine
depth: tip
generated_at: 2026-07-14T15:59:02.694082+00:00
source_hash: 657458c4d06bb198d067760775b69a5c87288113feaddb9cdaf3df631c188617
status: generated
---

# Spec-driven development with approval loops

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
