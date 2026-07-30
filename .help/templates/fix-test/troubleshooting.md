---
type: troubleshooting
name: fix-test-troubleshooting
feature: fix-test
depth: troubleshooting
generated_at: 2026-07-30T21:39:00.970482+00:00
source_hash: 56383ae48a3d6c0dcdadb645912bf30697dbdd296c66e69e3c40100a6c12ab69
status: generated
---

# Auto-diagnose test gaps from file changes and track test outcomes

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeError: coroutine ... was never awaited` | `run` / `on_file_*` called without `await` | These are coroutines — `await` them or use `asyncio.run` | high |
| `FileNotFoundError: Coverage file not found` | `track_coverage` given a missing path | Generate `coverage.xml` first (e.g. `pytest --cov --cov-report=xml`) | high |
| `ValueError: Invalid coverage.xml format` | `track_coverage` given a malformed/empty XML | Regenerate the report; confirm the run finished | medium |
| Plan comes back with zero items | No tracked changes / index reports nothing needing work | Pass `changed_files`, or confirm the `ProjectIndex` is populated | medium |
| `"auto"` mode executes nothing | No plan item has `auto_executable=True` | Inspect `get_auto_executable_items()`; `REVIEW`/`MANUAL` items never auto-run | medium |
| Calling the wrong `get_files_needing_tests` | Two functions share the name (module fn vs workflow method) | Import the module function or call the method explicitly; their signatures differ | medium |
| `get_file_test_status` returns `None` | No `FileTestRecord` was ever recorded for that file | Run `track_file_tests` or `run_tests_with_tracking` first | low |

### Risk areas

- **The async/sync split is easy to get wrong.** Only `run` and the
  three `on_file_*` handlers are coroutines; the summary methods and
  every `test_runner` function are plain calls. Awaiting a sync
  function (or forgetting to await a coroutine) is the most common
  fix-test bug.
- **`auto_executable` defaults to `True`.** A `TestPlanItem` is
  auto-runnable unless something sets the flag to `False`. Before
  trusting `"auto"` mode in CI, inspect the plan and confirm the
  auto-executable subset is what you expect.
- **Planning is only as current as the index.** The workflow refreshes
  its `ProjectIndex` when you pass `changed_files`, but a stale index
  yields stale priorities. Pass the files that changed, or refresh
  before planning.

### Diagnosis order

1. Reproduce with a minimal `await workflow.run({"mode": "analyze"})`
   — inspect `result["status"]` and `result["plan"]["items"]`.
2. If a handler misbehaves, call it directly
   (`await workflow.on_file_modified(path)`) and read the returned
   `status`.
3. For measurement issues, call the `test_runner` function in
   isolation and inspect the returned record (or the raised
   `FileNotFoundError` / `ValueError`).
4. Confirm the index: `workflow.get_test_health_summary()` should
   report sane counts.
5. Run the related tests: `pytest -k "test_maintenance or test_runner" -v`.
