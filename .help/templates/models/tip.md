---
type: tip
name: models-tip
feature: models
depth: tip
generated_at: 2026-05-16T06:19:45.854797+00:00
source_hash: 5adb390f8bab40245661da7d744647a071fca96494807648005429a8766e4254
status: generated
---

# Tip: working effectively with models

Use `AdaptiveModelRouter.get_best_model()` to select a model rather than hardcoding model IDs — it ranks candidates by `quality_score` (derived from `success_rate`, `avg_latency_ms`, and `avg_cost`) against your actual telemetry, so routing improves automatically as your workflows accumulate history.

**Why:** Hardcoded model IDs bypass the circuit breaker and fallback chain, meaning a single provider outage can halt a workflow that `AdaptiveModelRouter` would have recovered from silently.

**Tradeoff:** `get_best_model()` requires a `min_success_rate` threshold (default `0.8`) and a populated telemetry store. If your `sample_size` is too low, the router falls back to registry defaults anyway — so the benefit only compounds after enough runs to produce reliable `ModelPerformance` data.

**Tags:** `models`, `auth`, `llm`
