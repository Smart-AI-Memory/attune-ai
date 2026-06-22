---
type: tip
name: fix-test-tip
feature: fix-test
depth: tip
generated_at: 2026-06-22T11:30:53.046085+00:00
source_hash: 2a68f682c715ddba2510a8395022ba9b502452e2fce1c7a1d13419ce2a2f0f1b
status: generated
---

# Auto-diagnose test gaps from file changes and track test outcomes

## Notes & tips

- **Depend on the documented public surface.**
  `test_maintenance` gives you `TestMaintenanceWorkflow`,
  `TestMaintenancePlan`, `TestPlanItem`, `TestAction`, and
  `TestPriority`. `test_runner` gives you `run_tests_with_tracking`,
  `track_coverage`, `track_file_tests`, `get_file_test_status`, and
  `get_files_needing_tests`. Names with a leading underscore are
  internal and may change.
- **Preview with `dry_run` before executing.** Both `"execute"` and
  `"auto"` modes accept `dry_run=True`, which reports what *would* run
  without touching anything — the cheapest way to sanity-check a plan.
- **Pass `changed_files` for event-driven runs.** Supplying the files
  that changed refreshes the index and focuses the plan, instead of
  re-evaluating the whole project.
