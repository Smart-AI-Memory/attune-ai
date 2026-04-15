---
type: comparison
feature: fix-test
depth: comparison
generated_at: 2026-04-14T14:58:21.402719+00:00
source_hash: add950818a88e621df7bd12cd03ded18fe60e40bac9a1bae6eb24fe1ff69abc8
status: generated
---

# TestLifecycleManager vs TestMaintenanceWorkflow vs manual test tracking

The test automation system provides three approaches for managing test lifecycle and maintenance. Each targets different automation levels and integration patterns.

## Feature comparison

| Feature | TestLifecycleManager | TestMaintenanceWorkflow | Manual tracking functions |
|---------|---------------------|------------------------|---------------------------|
| **Automation level** | Full event-driven automation | Workflow orchestration | Manual execution |
| **File change detection** | Automatic via file events | Manual trigger | No detection |
| **Queue management** | Built-in task queue with priorities | Plan-based execution | No queuing |
| **Execution model** | Real-time or batch processing | On-demand workflow runs | Immediate execution |
| **Git integration** | Pre/post-commit hooks | No git integration | No git integration |
| **Scheduling** | Configurable maintenance intervals | Manual scheduling | No scheduling |
| **Configuration complexity** | Medium (auto_execute, queue settings) | Low (project root only) | Minimal (optional params) |

## Detailed tradeoffs

**TestLifecycleManager** provides the most comprehensive automation but requires setup overhead. It monitors file changes in real-time and can automatically execute test actions, making it ~10x faster for continuous integration scenarios. However, the event-driven nature means debugging issues requires understanding the queue state and callback system.

**TestMaintenanceWorkflow** offers a middle ground with explicit control flow. You trigger workflows manually but get structured planning via TestMaintenancePlan objects. This approach is ~3x slower than lifecycle automation for frequent changes but provides better visibility into what actions will be taken before execution.

**Manual tracking functions** give you precise control over individual operations with zero setup cost. Each function (`run_tests_with_tracking`, `track_coverage`, etc.) executes immediately and returns specific results. This is fastest for one-off debugging but becomes inefficient when managing more than a handful of test files.

## Use TestLifecycleManager when...

- You need continuous test maintenance during active development
- Your project has frequent file changes that affect test validity
- You want automated responses to git operations (pre-commit, post-commit)
- You can tolerate some debugging complexity for maximum automation

## Use TestMaintenanceWorkflow when...

- You prefer explicit control over when test maintenance runs
- You want to review planned actions before execution
- Your test maintenance happens in scheduled batches rather than continuously
- You need structured reporting via TestMaintenancePlan objects

## Use manual tracking functions when...

- You're debugging specific test failures interactively
- You need to integrate test tracking into existing scripts or tools
- You want immediate results without queue delays
- You're working with a small number of files that don't change frequently

**Winner:** TestLifecycleManager for active development environments where test maintenance overhead is a bottleneck. The automation benefits outweigh the complexity cost once you have more than 10-15 test files to manage.

## Source files

- `src/attune/workflows/test_runner.py`
- `src/attune/workflows/test_maintenance.py`
- `src/attune/workflows/test_lifecycle.py`

**Tags:** `tests`, `debugging`, `fixes`
