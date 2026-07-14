---
name: fix-test
source: content/features/fix-test.md
tags:
- tests
- debugging
- fixes
type: faq
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
