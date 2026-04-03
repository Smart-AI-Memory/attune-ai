---
type: error
name: bg-var-primary-bg-opacity-10-is-invisible-in-dark-mode
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: `bg-[var(--primary)] bg-opacity-10` is invisible in dark mode

## Signature

`bg-[var(--primary)] bg-opacity-10` is invisible in dark mode

## Root Cause

A 10% opacity tint of dark blue (`#1E40AF`) on a dark background (`#0F172A`) produces near-zero contrast. Use `bg-[var(--background)]` with a colored border instead, or switch to `gradient-accent` (purple) which is brighter. This affected callout boxes and hero sections on the attune-lite page.

## Resolution

1. Use `bg-[var(--background)]` with a colored border instead, or switch to `gradient-accent` (purple) which is brighter

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `bg-[var(--primary)] bg-opacity-10` is invisible in dark mode
