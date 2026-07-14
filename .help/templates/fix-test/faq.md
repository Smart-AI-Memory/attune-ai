---
type: faq
name: fix-test-faq
feature: fix-test
depth: faq
generated_at: 2026-07-14T15:58:52.133407+00:00
source_hash: 2a68f682c715ddba2510a8395022ba9b502452e2fce1c7a1d13419ce2a2f0f1b
status: generated
---

# Fix Test FAQ

## Does fix-test write tests for me?

No. It decides *what* test work a change implies and *whether*
it is safe to run automatically. Generating test code is the
smart-test feature's job.

## Is there an `attune fix-test` command?

No dedicated CLI subcommand — fix-test is reached as the
`/fix-test` skill, and the planning/measurement logic is the Python
API on this page (`TestMaintenanceWorkflow` and the `test_runner`
functions).

## What's the entry point?

`await TestMaintenanceWorkflow(project_root).run({"mode":
"analyze"})` for a whole-project plan, or the `on_file_*` handlers
for a single file event.

## Which calls are async?

`run` and the three `on_file_*` handlers. The summary methods
and all `test_runner` functions are synchronous.

## How do I run only the safe items?

`await workflow.run({"mode": "auto"})` — it executes the
`auto_executable` subset and leaves `REVIEW` / `MANUAL` items for a
human. Add `"dry_run": True` to preview the count first.
