---
type: tip
name: ops-dashboard-tip
feature: ops-dashboard
depth: tip
generated_at: 2026-06-24T12:00:17.825226+00:00
source_hash: 1cad6797952953474159da11cd78e2e6f3b36b4845377e700eb2570427d138e7
status: generated
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
