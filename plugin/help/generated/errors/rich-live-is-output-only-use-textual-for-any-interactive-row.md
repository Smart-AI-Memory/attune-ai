---
type: error
name: rich-live-is-output-only-use-textual-for-any-interactive-row
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: `rich.live` is output-only; use `textual` for
  any interactive row navigation

## Signature

`rich.live` is output-only; use `textual` for
  any interactive row navigation

## Root Cause

both libraries share the same author and styling DSL, which makes it easy to reach for `rich.live` when the spec says "drill into a row." But `rich.live` has no concept of focus, selection, or keyboard input — it's for non-interactive auto-refreshing displays (progress bars, status tables). The moment the UX needs arrow-key navigation or screen push/pop, `textual`'s `DataTable` widget, `Screen` subclass, and key bindings are the right primitives. Check the spec before picking: if `$EDITOR path/from/drill-in.output` closes the loop in shell, you may not need a TUI at all — a `--drill-in FEATURE` flag on a CLI script is often strictly better than either option.

## Resolution

1. Check the spec before picking: if `$EDITOR path/from/drill-in.output` closes the loop in shell, you may not need a TUI at all — a `--drill-in FEATURE` flag on a CLI script is often strictly better than either option

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
