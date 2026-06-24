---
name: ops-dashboard
source: content/features/ops-dashboard.md
tags:
- ops
- dashboard
- runner
- workflows
- scope-picker
- persistence
- sse
type: tip
---

# The local FastAPI operations dashboard — a workflow runner with per-feature scope, persisted run history, workflow chaining, and live SSE log streaming

## Notes & tips

- **Depend on the documented public surface:** `create_app`,
  `build_config`, `Config` from `attune.ops`. The runner and readers are
  reached from their submodules.
- **`await` the two async surfaces.** `RunnerService.start` and
  `Run.subscribe`; everything else on the runner is sync.
- **Paths are properties.** `runs_dir`, `sessions_dir`,
  `telemetry_path` — no `()`.
- **`--read-only` for a safe demo.** It serves the dashboard with
  execution disabled.
