---
name: models
source: content/features/models.md
tags:
- models
- auth
- llm
type: comparison
---

# LLM authentication, provider routing, and tier management

## Comparison

Two layers select a model, and they differ in whether the choice is
static (tier-mapped) or learned (telemetry-driven).

| Capability | Static routing (`get_tier_for_task` + `get_model`) | Adaptive routing (`AdaptiveModelRouter`) |
|---|---|---|
| **Input** | Task type string | Workflow + stage history |
| **Decision basis** | `TASK_TIER_MAP` (fixed) | Observed success rate, latency, cost |
| **Determinism** | Fully deterministic | Depends on telemetry sample size |
| **Cold start** | Works immediately | Needs `MIN_SAMPLE_SIZE` (10) calls first |
| **Cost control** | Tier choice only | `max_cost` / `max_latency_ms` / `min_success_rate` filters |
| **Typical caller** | Any workflow, default path | Long-running workflows that accumulate stats |

**Use static routing** by default — it is predictable and needs no
history. **Use adaptive routing** when a workflow runs often enough to
accumulate telemetry and you want the router to escalate or downgrade
tiers based on real outcomes. Adaptive routing falls back to static
behavior until it has enough samples.

For auth, the analogous fork is `AuthMode`: `SUBSCRIPTION` and `API`
are explicit; `AUTO` defers to `get_recommended_mode`, which resolves
by subscription tier (and, only for `MAX`/`ENTERPRISE`, module size).
Prefer `AUTO` unless you have a reason to pin one mode.
