---
type: warning
name: sdk-agent-model-config-uses-stale-model-names
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Warning: SDK agent MODEL_CONFIG uses stale model names

## Condition

The `MODEL_CONFIG` dict in `agents/release/release_models.py` references `claude-3-5-haiku-latest` which returns 404

## Risk

Check model IDs against the Anthropic API when tier escalation fails at CHEAP

## Mitigation

1. Check model IDs against the Anthropic API when tier escalation fails at CHEAP

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: SDK agent MODEL_CONFIG uses stale model names
