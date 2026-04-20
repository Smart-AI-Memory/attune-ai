# Help-System Maintainer TUI Dashboard

**Created:** 2026-04-19
**Source:** /brainstorm session
**Audience:** Solo maintainer of the attune-help corpus

## Problem

Maintaining the help system today requires juggling three CLI tools to
answer a single question: "what needs work?" Completeness lives in a
directory listing (template kind counts per feature). Staleness lives
behind `attune_author.check_staleness`. Benchmark scores live in
attune-rag's golden fixtures. There's no unified view, so drift is
caught too late — the recurring pattern behind documented failures like
sidecar-schema mismatches, 3-kind orphan dirs, and mutual-competition
regressions between polished features.

## Goals

**Must-have:**

- Keyboard-fast TUI, one row per feature, three columns: completeness
  (X/11 kinds), staleness (current/stale), benchmark P@1
- Drill-down into any feature → per-template status list
- Jump-to-editor from the per-template view (`$EDITOR` env var)
- Cached benchmark results — TUI never blocks on live LLM calls or
  fixture runs

**Nice-to-have (defer):**

- Tag-overlap visualization across features
- In-TUI action triggers (regenerate, re-run benchmarks) — keep these
  in CLI where proper knobs exist
- File-watch auto-refresh

## End State

Open the TUI in under 3 seconds. See ecosystem status at a glance —
red rows for stale/incomplete/low-score features jump out. Drill into
any red row to find the exact templates needing work. Jump to editor,
fix the template, regenerate via existing CLI workflow. TUI stays a
read-only triage tool; editing and regeneration live where the proper
budget/confirmation UX already exists.

## Approach

1. **Data contract first** — spec the `.help/benchmarks/latest.json`
   schema (path-keyed, P@1/P@3, timestamp, fixture count). Add a
   cache writer to the existing golden-fixture runner so scores are
   persisted after each run.
2. **Data aggregator (no UI)** — one Python API that merges
   completeness (directory scan), staleness
   (`attune_author.check_staleness`), and benchmarks (cached JSON) into
   a list of `FeatureRow` dataclasses. Prototype and test before any
   TUI work.
3. **Dashboard screen** — sortable table, color-coded severity,
   keyboard nav. Keep it minimal in v1.
4. **Drill-down screen** — per-template status for one feature, with
   editor-jump keybinding.
5. **Package as `attune-author dashboard` subcommand** — natural
   discovery, reuses the package closest to the data.

## Next Steps

- [ ] Decide TUI library: `textual` (CSS-styled, richer) vs `rich.live`
  (table-first, simpler, already a transitive dep)
- [ ] Spec `.help/benchmarks/latest.json` schema
- [ ] Add benchmark cache writer to the golden-fixture runner (locate
  canonical home: attune-rag's eval module vs attune-ai's
  `tests/golden/`)
- [ ] Prototype the data aggregator — no UI, just a CLI that prints
  the unified `FeatureRow` list
- [ ] Build v1 dashboard screen against the aggregator
- [ ] Build drill-down screen with editor jump
- [ ] Wire up as `attune-author dashboard` subcommand

## Open Questions

- Which package owns the TUI? Leaning `attune-author` (closest to the
  data model), but a new `attune-tui` or `attune-dashboard` is an
  option if TUI deps feel out of place in author.
- Does benchmark caching live in attune-rag (who runs fixtures) or
  attune-help (who ships the corpus)? Likely attune-rag — the runner
  is the natural writer.
- Is `textual` worth the new dep for v1, or does `rich.live` cover the
  must-haves? Lean `rich.live` for v1, upgrade to `textual` only if
  drill-down UX demands it.
- How to distinguish "no benchmark data yet" from "benchmarks ran but
  feature not in fixture set"? Schema needs a `features_covered` field,
  not just path-keyed scores.
