---
type: warning
name: bg-var-primary-bg-opacity-10-is-invisible-in-dark-mode
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: `bg-[var(--primary)] bg-opacity-10` is invisible in dark mode

## Condition

A 10% opacity tint of dark blue (`#1E40AF`) on a dark background (`#0F172A`) produces near-zero contrast

## Risk

Ignoring this guidance may cause: `bg-[var(--primary)] bg-opacity-10` is invisible in dark mode

## Mitigation

1. Use `bg-[var(--background)]` with a colored border instead, or switch to `gradient-accent` (purple) which is brighter

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `bg-[var(--primary)] bg-opacity-10` is invisible in dark mode
