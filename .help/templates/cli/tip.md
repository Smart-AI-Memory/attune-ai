---
type: tip
feature: cli
depth: tip
generated_at: 2026-04-14T15:12:31.654048+00:00
source_hash: 8dc008ad217367e499b9e8a37c6cdbb6a23f53f03d344c9793da916a7fb8ab3c
status: generated
---

# Use the HybridRouter for mixed command types

## Context

The Attune CLI handles both structured commands (like `attune costs today`) and natural language input through a hybrid routing system.

## Recommendation

Route user input through `route_user_input()` instead of parsing commands directly. This function automatically determines whether input is a slash command or natural language and delegates appropriately.

The HybridRouter learns from usage patterns and builds routing preferences over time, making the CLI smarter with each interaction.

## Why this matters

Direct command parsing misses natural language input entirely, forcing users into rigid command syntax when they could express intent more naturally.

## Source files

- `src/attune/cli_router.py`
- `src/attune/cli_minimal.py`

**Tags:** `cli`, `commands`
