---
type: tip
name: fix-test-tip
feature: fix-test
depth: tip
generated_at: 2026-07-30T21:39:00.970482+00:00
source_hash: 56383ae48a3d6c0dcdadb645912bf30697dbdd296c66e69e3c40100a6c12ab69
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
