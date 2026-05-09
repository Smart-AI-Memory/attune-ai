---
type: concept
name: tier-routing
tags: [architecture, cost-optimization]
source: src/attune/workflows/base.py
---

# Concept: Model tier routing

## What

Tier routing automatically selects the right Claude model (Haiku, Sonnet, or Opus) based on task complexity. Simple tasks use cheap models; complex tasks escalate to premium.

## Why

Reduces API costs by 80-96% without sacrificing quality. Most workflow stages don't need the most expensive model.

## How

Each workflow defines a `tier_map` mapping stages to tiers (CHEAP, CAPABLE, PREMIUM). The authentication strategy resolves each tier to a specific model ID. Tier fallback escalates automatically if a cheaper tier fails.

## Example

`tier_map = {"initial_scan": ModelTier.CHEAP, "deep_review": ModelTier.PREMIUM}`

## Related Topics

_No related topics yet._
