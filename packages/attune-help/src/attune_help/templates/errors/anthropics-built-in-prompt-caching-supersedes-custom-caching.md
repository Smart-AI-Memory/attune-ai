---
type: error
name: anthropics-built-in-prompt-caching-supersedes-custom-caching
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Anthropic's built-in prompt caching supersedes custom
  caching

## Signature

Anthropic's built-in prompt caching supersedes custom
  caching

## Root Cause

Since Dec 2024, the Anthropic API provides 90% input token discounts via server-side prompt caching. The Claude Agent SDK uses this automatically. Custom client-side caching with `sentence-transformers` (420MB dep) delivered 0.4% savings vs Anthropic's automatic server-side caching. Removed in favor of the native solution.

## Resolution

1. Removed in favor of the native solution

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Anthropic's built-in prompt caching supersedes custom
  caching
