---
type: tip
name: spec-engine-tip
feature: spec-engine
depth: tip
generated_at: 2026-06-02T10:56:02.721300+00:00
source_hash: f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337
status: generated
---

# Tip: Use `skip_task_ids` to re-run a single task without restarting the pipeline

Pass a `set[str]` of already-completed task IDs to `run_all(skip_task_ids=...)` instead of clearing state and running the whole plan from scratch.

**Why it sticks:** `clear_state` is irreversible mid-run — skipping completed tasks preserves your `SpecState.completed` list and keeps `total_cost` and `duration_ms` accurate in the final `PipelineResult`.

**Tradeoff:** You are responsible for knowing which task IDs to skip. If a completed task produced an artifact that a later task depends on, skipping it without re-validating that artifact may cause the downstream task to fail its quality gate silently — check `TaskResult.quality_gate_passed` and `TaskResult.gate_score` on the returned result before assuming success.

## Source files

- `src/attune/pipeline/**`
- `src/attune/spec/**`

**Tags:** `spec`, `planning`
