---
type: concept
name: tier-routing
tags: [architecture, cost-optimization]
source: src/attune/model_tiers.py
---

# Concept: Model tier routing

## What

Tier routing automatically selects the right Claude model based on task complexity: CHEAP resolves to Haiku, CAPABLE to Sonnet, and PREMIUM to Claude Fable 5.1 (`claude-fable-5-1`). Simple tasks use cheap models; complex tasks escalate to premium.

## Why

Reduces API costs without sacrificing quality — most workflow stages don't need the most expensive model. Note the premium tier runs `claude-fable-5-1` at 2x the former Opus pricing ($10 input / $50 output per MTok), so premium-tier stages cost twice what they did on Opus.

## How

Each workflow defines a `tier_map` mapping stages to tiers (CHEAP, CAPABLE, PREMIUM). `attune.model_tiers` resolves each tier to a model ID per call, honoring env overrides (`ATTUNE_MODEL_PREMIUM`, `ATTUNE_MODEL_CAPABLE`, `ATTUNE_MODEL_CHEAP`). Tier fallback escalates automatically if a cheaper tier fails. Editing/polish passes are deliberately not a tier: they run a dedicated editing model (`ATTUNE_MODEL_EDITING`, default `claude-opus-5`).

## Example

`tier_map = {"initial_scan": ModelTier.CHEAP, "deep_review": ModelTier.PREMIUM}`

## Related Topics

_No related topics yet._
