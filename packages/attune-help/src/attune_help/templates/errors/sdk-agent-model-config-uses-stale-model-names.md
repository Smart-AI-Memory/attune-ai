---
type: error
name: sdk-agent-model-config-uses-stale-model-names
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: SDK agent MODEL_CONFIG uses stale model names

## Signature

SDK agent MODEL_CONFIG uses stale model names

## Root Cause

The `MODEL_CONFIG` dict in `agents/release/release_models.py` references `claude-3-5-haiku-latest` which returns 404. The current Haiku model ID is `claude-haiku-4-5-20251001`. Check model IDs against the Anthropic API when tier escalation fails at CHEAP.

## Resolution

1. Check model IDs against the Anthropic API when tier escalation fails at CHEAP

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
