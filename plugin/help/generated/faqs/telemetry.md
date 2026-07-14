---
name: telemetry
source: content/features/telemetry.md
tags:
- telemetry
- metrics
type: faq
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
