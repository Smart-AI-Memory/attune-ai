---
name: spec
description: "Spec-driven development — brainstorm, plan, review, and execute with quality gates and approval."
argument-hint: "<what to build, path to import, or 'resume'>"
---

Spec-driven development for `$ARGUMENTS`.

If no arguments, use AskUserQuestion to ask what the
user wants to do:

- Start a new spec (brainstorm, decompose, save)
- Resume an in-progress spec (check for resumable plans)
- Import a spec file (load from another project/path)
- Execute a spec (review then task-by-task with approval)

## Import

If the user provides a file path or chooses "Import":

1. Validate path with `_validate_file_path()`
2. Copy to `.claude/plans/` if not already there
3. Load tasks with `read_spec(path)`
4. If tasks found, proceed to Review
5. If no tasks, offer to create a spec instead

## Create

Run brainstorm flow (Context, Problem, Goals, End State).
Auto-decompose approach into XML `<task>` blocks. Save to
`.claude/plans/`.

## Review

Load tasks with `read_spec(plan_path)`. Show each task:
name, objective, files, risks. Use AskUserQuestion for
approve/edit/reject.

## Execute

For each pending task:

1. Show progress bar
2. Show task detail
3. Implement the task (create/modify files)
4. Run quality gates via PipelineOrchestrator
5. Severity-gated approval:
   - HIGH severity (score < 50): only "Fix and retry"
     or "Acknowledge risk" (no auto-run)
   - MEDIUM/LOW: "Approve" / "Redo" / "Auto-run remaining"
6. Save state after each decision

## Resume

Check `find_resumable_plans()` on startup. Offer to
resume incomplete specs.

Use `from attune.spec import` for all helpers:
`present_tasks`, `present_task_detail`, `format_progress_bar`,
`load_state`, `save_state`, `find_resumable_plans`,
`get_pending_tasks`, `SpecState`.
