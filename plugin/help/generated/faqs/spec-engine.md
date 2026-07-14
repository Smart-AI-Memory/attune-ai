---
name: spec-engine
source: content/features/spec-engine.md
tags:
- spec
- planning
type: faq
---

# Spec Engine FAQ

## What is the spec engine?

The runtime layer that reads a decomposed plan file, executes
each task in order, runs quality gates after each, and tracks
progress so a run can be paused and resumed.

## When should I use it?

When you have a plan file with XML task blocks under
`.claude/plans/` and want to execute those tasks with quality gates
and approval checkpoints. If you're still brainstorming or
decomposing, you don't need the engine yet.

## What's the main entry point?

Load and parse a plan — `read_spec(plan_path)`. Run the full
pipeline programmatically — `await PipelineOrchestrator(spec_path).run_all()`.
Run with per-task approval — `await execute_with_approval(spec_path,
on_task_complete)`.

## How do quality gates work?

After each task, `run_gates_for_task` evaluates the result and
returns a `TaskResult`. `quality_gate_passed` says whether the task
met its acceptance criteria; `gate_score` gives a numeric score;
`severity` classifies the outcome. If `quality_gate_passed` is
`False`, the pipeline stops unless auto-run is active
(`SpecState.auto_run = True`).

## Can I skip tasks or resume a partial run?

Yes. Pass a set of task IDs to `run_all(skip_task_ids=...)` to
exclude them. To resume, call `get_pending_tasks(tasks, state)` — it
filters out IDs already in `SpecState.completed` — then orchestrate
the remaining tasks.

## How do I check whether the whole pipeline succeeded?

Inspect the `PipelineResult`. `success` is `True` only when
all tasks executed and passed their gates; `summary` is the
human-readable summary; `total_cost` and `duration_ms` are available
for observability.
