---
name: spec-engine
source: content/features/spec-engine.md
tags:
- spec
- planning
type: comparison
---

# Spec Ladders — goal-driven spec development with approval loops

## Comparison

The engine exposes two layers for running spec-driven workflows: a
high-level interactive layer (`spec.runner.execute_with_approval`) and
a low-level pipeline layer (`PipelineOrchestrator`). Both execute the
same tasks with the same quality gates, but differ in who controls the
approval loop and how much state they manage for you.

| Capability | `spec` layer (`execute_with_approval`) | `pipeline` layer (`PipelineOrchestrator`) |
|---|---|---|
| **Import path** | `from attune.spec.runner import execute_with_approval` | `from attune.pipeline import PipelineOrchestrator` |
| **Approval loop** | Per-task, interactive — pauses after each task | Batch — runs all tasks unless you pass `skip_task_ids` |
| **Resume support** | Yes — `load_state` / `save_state` / `find_resumable_plans` persist `SpecState` | No built-in persistence; caller owns resumability |
| **Progress feedback** | Presenter functions render live output | Callback only — wire `on_task_complete` yourself |
| **Skip flags** | `skip_gates`, `skip_tests`, `skip_simplify` | Same flags on `__init__` |
| **Task filtering** | `get_pending_tasks` against persisted state | Pass `skip_task_ids: set[str]` to `run_all` |
| **Result model** | `PipelineResult` (shared) | `PipelineResult` (shared) |
| **Concurrency** | Async coroutine — `await` it | Async coroutine — `await run_all` (or `asyncio.run`) |
| **Typical caller** | Conversational / interactive session | Automated scripts, CI pipelines |

**Use the `spec` layer** when a human approves each task, you want
automatic resume support, and you want formatted output without
writing presenter logic. **Use the `pipeline` layer** when running in
CI with no interactive step, when you need to skip tasks by ID at call
time, or when you want to inspect gate results programmatically with
no display logic in the way.

When in doubt, start with the `spec` layer. The `pipeline` layer is
the better fit only when you are certain you do not need state
persistence or interactive approval — and are prepared to manage both
yourself.
