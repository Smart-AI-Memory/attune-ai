---
type: error
name: claude-agent-sdk-is-now-a-core-dependency-of-attune-ai
confidence: Verified
tags: [packaging]
source: .claude/CLAUDE.md
---

# Error: `claude-agent-sdk` is now a core dependency of attune-ai

## Signature

`claude-agent-sdk` is now a core dependency of attune-ai

## Root Cause

As of v4.2.0, the Agent SDK is included in core dependencies. No need for `pip install 'attune-ai[agent-sdk]'` — a plain `pip install attune-ai` includes it. The `[agent-sdk]` extra is kept as an empty placeholder for backward compatibility.

## Resolution

1. As of v4.2.0, the Agent SDK is included in core dependencies

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
