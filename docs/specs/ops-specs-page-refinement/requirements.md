# Spec: Ops Dashboard Specs Page Refinement

> The Specs tab in attune-ops lets a user with 45+ specs find the
> right one and see what to do next without scrolling/scanning the
> whole table.

**Status:** complete (2026-05-31; A1-A3 shipped in PRs #533, #534, #535, #536, #539)
**Created:** 2026-05-31
**Owner:** Patrick (decisions ratified in-session 2026-05-31)
**Related:** [`decisions.md`](decisions.md) — 4 design decisions ratified in-conversation before requirements were drafted, so they read as constraints here rather than open questions.

---

## Problem statement

The current Specs page (`/specs` route in `attune-ops`) renders a flat
table with `Spec | Updated | Decisions | Requirements | Design | Tasks`
columns — one row per spec, four phase-status pills per row. At
~45 specs (and growing), three concrete pain points surfaced 2026-05-31:

1. **Sheer volume** — no grouping, filtering, search, or sort.
   Scanning ~45 rows to find one spec is exhausting.
2. **Phase information is hard to interpret** — four equally-weighted
   phase pills per row require mental synthesis to answer "what phase
   IS this spec on?" and "what's the next action?"
3. **Row-level actionability is missing** — only the slug is clickable.
   No row click, no per-row action menu, no keyboard nav.

This spec scopes the v1 refinement that addresses all three.

## Outcome (one sentence)

The Specs page surfaces lifecycle state + next action per row, lets
the user filter / search / sort to find the right spec, and exposes
per-row actions through a clean menu — without breaking the existing
drill-in flow or the markdown drill-in page.

## Acceptance criteria

A user with 45+ specs can:

- Filter to "currently active work" with one click and see only specs
  that need attention this week
- Find a specific spec by typing 2-3 characters of its slug
- See for any row: which phase it's on, what's next, what bucket it
  belongs to (Active / Approved-not-shipped / Complete / Paused / Draft)
- Click anywhere on a row to drill into the spec
- Open the action menu and trigger "Open in editor", "Copy slug", or
  "View linked PRs" without leaving the dashboard

---

## Requirement clusters

### R1 — Volume reduction (grouping + filtering)

- **R1.1** Filter by spec **lifecycle state** derived from phase
  statuses + age. Six buckets: Active / Approved-not-shipped /
  Complete / Paused / **Stale** / Draft. User can show any
  combination via a chip row above the table. (See
  [`decisions.md`](decisions.md) § D1 for the derivation rules and
  § D2 for the chip widget shape. The Stale bucket was added
  2026-05-31 during wireframe review — it surfaces specs that
  haven't been touched in 30+ days and aren't already explicitly
  Paused or Complete, addressing the "started but rotting" case the
  original 5 buckets silently hid.)
- **R1.2** Text search on spec slug — substring match, case-insensitive.
  Filters within the already-bucket-filtered set. No fuzzy or semantic
  matching in v1.
- **R1.3** Default view filters OUT specs in `Complete` lifecycle —
  they're noise for day-to-day work. The Complete chip renders greyed
  with a hidden-count marker (`Complete 27 ✗`) so the user can
  one-click reveal.
- **R1.4** Sort options: recently-updated (default), alphabetical,
  oldest-untouched.
- **R1.5** Filter / sort / search state lives in URL query params
  (e.g. `?bucket=active,paused&sort=alpha&q=rag`) so links are
  shareable and browser-back works.

**Out of scope for v1**: visual grouping by lifecycle bucket with
collapsible sections (see [`decisions.md`](decisions.md) § D3 —
deferred to v2 with explicit trigger conditions).

### R2 — Where is this spec, and what's next?

- **R2.1** Each row surfaces a derived **lifecycle indicator** beyond
  the 4 phase pills — a clear bucket label (e.g., a badge or column
  showing `Active` / `Paused` / etc.) so the user sees the spec's
  bucket at a glance.
- **R2.2** Each row surfaces a **next-action label** — a short string
  describing what to do next, derived from the lifecycle state and
  phase statuses (e.g., `Next: design`, `Run impl`, `(paused — see
  decisions.md)`, `Complete`).
- **R2.3** Lifecycle derivation rules are **explicit and testable**.
  The rules are first-match-wins on this evaluation order: Paused →
  Complete → Draft → Approved-not-shipped → Active. Full rule body
  in [`decisions.md`](decisions.md) § D1.

### R3 — Row-level actionability

- **R3.1** Entire row is clickable → `/specs/{slug}`. The slug link
  retains its own click behavior; the kebab menu cell (see R3.2) has
  its own click target separate from the row click.
- **R3.2** Each row gets a **kebab menu** (`⋯`) in a dedicated last
  column. Click opens a small dropdown anchored to the cell with three
  actions: `Open in editor`, `Copy slug`, `View linked PRs`. See
  [`decisions.md`](decisions.md) § D4 for the menu UI choice rationale
  and the keyboard behavior.
- **R3.3** Keyboard navigation: arrow keys move row focus, Enter
  drills in, `M` (or `.`) opens the kebab menu on the focused row.
  Menu interactions: arrow keys + Enter to select, Escape to close.

---

## Non-goals (parking lot)

- **Semantic / fuzzy search** — substring is enough for ~45 specs.
- **Bulk-action toolbar / multi-select** — no current workflow needs
  bulk operations.
- **Owner / assignee field** — specs don't have one; not introducing it.
- **Cross-root collation changes** — existing flat listing across
  configured roots stays as-is.
- **Replacing the markdown drill-in page (`/specs/{slug}`)** — this
  spec scopes the *index* page only.
- **Mark-paused / mark-active row actions** — lifecycle is derived
  from phase pill statuses; adding a separate channel would fight
  the existing pill semantics. Use the pills.
- **Archive concept** — no current need for "irrelevant but not done";
  defer until proven.
- **PR-signal lookup for `Approved-not-shipped`** — v1 is purely
  file-based. v2 could query `gh pr list --search <slug>` to refine
  the bucket.
- **Custom status strings beyond `paused`** — only `paused` is
  detected by keyword. Other custom strings (e.g. "retired",
  "deferred") fall through to file-based rules.

---

## Implementation gates

- **Wireframe required before any code.** A standalone HTML preview
  (per `feedback_standalone_preview_pages.md` memory) covering every
  rendered state — five lifecycle buckets, search active, sort
  variants, kebab menu open, empty state, default-with-Complete-hidden
  — must be built and Patrick-ratified before production code lands.
- **Decisions ratified, design phase to follow.** The four design-level
  decisions in [`decisions.md`](decisions.md) are locked. Phase 2
  (design.md) covers the implementation-level concerns: data shape
  exposed to the template, derivation algorithm, URL param schema,
  JS architecture, test boundaries.

---

## Rollback plan

Single PR for v1 implementation. Rollback = `git revert <merge-commit>`.
The existing `/specs` route + template stays functional; v1 changes
extend the data layer (add lifecycle derivation + filter/sort fields
on the spec record) and replace the template body. A revert restores
the original flat table without schema migration (the new fields are
derived at request time, not persisted).

---

## Carryover

- 2026-05-31 — Spec ratified in conversation following the dashboard
  architecture discussion. Patrick named the three pain points
  (R1/R2/R3); I drafted requirements; we stepped through the four
  design-level decisions together (lifecycle rules, filter widget,
  visual grouping, action menu UI) before writing this file. Result:
  decisions appear here as constraints rather than open questions —
  the design phase ([`decisions.md`](decisions.md)) is mostly
  pre-locked, leaving implementation-level design for design.md.
