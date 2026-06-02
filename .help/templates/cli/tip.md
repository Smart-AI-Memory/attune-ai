---
type: tip
name: cli-tip
feature: cli
depth: tip
generated_at: 2026-06-02T10:56:02.740077+00:00
source_hash: 8c67b256a4817afea8eb428fdc577d8217d9e0d03adf9db67b00bc30a3c490a3
status: generated
---

# Tip: Working effectively with the CLI

Use `cmd_doctor` and `cmd_validate` before debugging routing problems — they surface configuration issues in seconds rather than minutes of log reading.

**Why:** `HybridRouter.route` makes decisions based on learned `RoutingPreference` entries; if the preference data is corrupt or missing, every route silently falls back to defaults. Catching that early saves a long detour.

**Tradeoff:** `cmd_doctor` and `cmd_validate` report on the current state of your environment, not on code changes you haven't committed yet. If you've just modified routing logic, they won't catch regressions — run your tests for that.
