---
type: faq
name: telemetry-faq
feature: telemetry
depth: faq
generated_at: 2026-07-14T15:59:03.107497+00:00
source_hash: 70af5f419937014536c9522dee18a1346bb18f723c2ed51057c807380c66ee6b
status: generated
---

# Telemetry FAQ

## What does attune telemetry record?

Every LLM call's cost/tokens/cache/duration (`UsageTracker`),
a quality score per workflow stage and tier (`FeedbackLoop`), and
agent coordination signals (`EventStreamer`, `HeartbeatCoordinator`).

## Where is the data stored?

Locally under `~/.attune/telemetry`. Nothing leaves your
machine unless you enable an opt-in phone-home.

## How do I see my usage/metrics?

`UsageTracker.get_instance().get_stats(days=30)` from Python,
the `telemetry_stats` MCP tool from a conversation, or the ops
dashboard.

## Why won't the feedback loop change my tier?

It needs at least `MIN_SAMPLES` (10) feedback rows for a stage
before `recommend_tier` will move off the current tier.
