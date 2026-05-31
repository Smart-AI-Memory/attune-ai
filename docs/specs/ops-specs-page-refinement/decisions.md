# Spec: Ops Dashboard Specs Page Refinement — Decisions

**Status:** approved (2026-05-31)

> Pre-committed decisions per the existing lesson "Pre-committed
> decision matrices survive contact with data." Each decision was
> ratified in the 2026-05-31 in-session conversation that produced
> this spec — Patrick stepped through them one-by-one and explicitly
> said "ratify" after each was surfaced with rationale + alternatives.
> Edits to this file after v1 ships require a follow-up PR with
> rationale.

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| **D1 — Lifecycle derivation rules** | See "Lifecycle derivation algorithm" below | Six buckets (Active / Approved-not-shipped / Complete / Paused / Stale / Draft) are the right split per Patrick. First-match evaluation order chosen so explicit author signals (paused, complete) win over inferred states, and Stale wins over Draft/Approved-not-shipped/Active so the "rotting" signal surfaces instead of being hidden behind the spec's nominal state. v1 stays file-only; v2 may add PR-signal refinement for Approved-not-shipped. **Stale bucket added 2026-05-31** during wireframe review — surfaces the "started but rotting" case the original 5 buckets silently hid. |
| **D2 — Filter widget shape** | **Chip row above table, one chip per lifecycle bucket** | Chips show the filter state at-a-glance (no menu open required), one-click toggle, inline counts double as population indicator, matches existing dashboard style (workflows tier-map chips, bulletin actor strip). Alternatives rejected: dropdown hides state behind a click; facet sidebar is overkill for one filter dimension. |
| **D3 — Visual grouping (R1 stretch)** | **Defer to v2** | Chips already cluster; per-row lifecycle indicator already labels each bucket; grouping fights with sort options; collapse/expand adds state to manage (server default? localStorage? URL?). v2 trigger conditions: (a) consistent alphabetical-sort + multi-bucket-active usage, OR (b) spec count past ~80-100 making the flat list unwieldy. Neither currently true. |
| **D4 — Action menu UI** | **Kebab `⋯` in a dedicated last column** | Doesn't fight whole-row-click (R3.1) because the kebab cell has its own explicit hit target. Compact (one icon per row), scales to v2 actions without redesign, standard pattern users recognize, keyboard-friendly. Alternatives rejected: always-visible inline buttons (column bloat, mobile-hostile); row-hover reveal (conflicts with R3.1, invisible on touch); right-click context menu (unexpected in web UIs). |

---

## Lifecycle derivation algorithm

A spec's lifecycle bucket is computed from its 4 phase files
(`decisions.md`, `requirements.md`, `design.md`, `tasks.md`), each
of which has a `status` field in YAML frontmatter. Observed status
values: `draft`, `in-review` / `review`, `approved`, `complete` /
`completed` / `done`, plus custom strings (often containing the word
`paused` with a date).

### Evaluation order (first match wins)

1. **Paused** — ANY phase's status string contains the word `paused`
   (case-insensitive). Custom status text like `paused 2026-05-12 —
   premise invalidated` matches. The explicit pause signal overrides
   everything else; a paused-then-completed spec stays Paused until
   the paused marker is removed.

2. **Complete** — ALL 4 phases have status in
   `(complete, completed, done)`. Explicit author signal that the
   spec is done.

3. **Stale** — `last_modified` is older than **30 days** AND the
   spec didn't match Paused or Complete above. Surfaces the
   "started but rotting" case: a spec that was Active, Draft, or
   Approved-not-shipped but hasn't been touched in over a month.
   The Stale bucket wins over Draft / Approved-not-shipped / Active
   so users see "this is rotting" instead of the spec's nominal
   state. (Threshold ratified 2026-05-31; revisit if 30d proves too
   noisy or too quiet in practice.)

4. **Draft** — `requirements.md` is missing OR its status is NOT in
   `(approved, complete, completed, done)`. The earliest stage, no
   formal commitment yet.

5. **Approved-not-shipped** — `requirements.md` approved AND no phase
   marked `complete` / `completed` / `done` AND `tasks.md` exists.
   Means design + tasks artifacts are ratified but work-shipping
   hasn't happened. v1 is file-only; v2 may refine with PR-signal
   (`gh pr list --search <slug>`).

6. **Active** — default. `requirements.md` approved AND doesn't match
   any rule above. The "work in progress" state.

### Trade-offs ratified

- **No PR signal in v1**: "Approved-not-shipped" is purely file-based.
  A spec with all artifacts approved but zero merged PRs looks
  identical to one with all artifacts approved and five merged PRs.
- **Custom status strings loosely honored**: only `paused` is detected
  by keyword. Other custom strings (e.g., `retired`, `deferred`) fall
  through to the file-based rules.
- **No "Complete" override**: no mechanism in v1 to mark a spec
  complete without flipping all 4 phase pills. Use the pills.
- **Stale threshold is fixed at 30 days** for v1 — no per-spec
  override, no user-configurable knob. If 30d turns out to flag too
  many specs that are still active in your head but lightly touched,
  lengthen it in a follow-up; if too few, shorten it. The visual
  treatment is amber (distinct shade from Paused) signaling "needs
  decision."
- **Default Stale chip is ACTIVE (visible)**: stale specs need
  attention, not concealment. The only default-hidden bucket is
  Complete (per R1.3).

---

## Filter widget behavioral details (D2)

- **Default chip state**: all chips ACTIVE except Complete (per R1.3).
  Visual: active chips colored, Complete chip greyed with hidden-count
  marker (e.g., `Complete 27 ✗`).
- **All-off state**: if all chips are toggled off, show empty state
  "All buckets filtered out — re-enable at least one chip."
- **Search**: filters the *already-bucket-filtered* set. 0-result
  state: "No specs in active buckets match '<query>'."
- **Persistence**: chip selections + sort + search live in URL query
  params (`?bucket=active,paused&sort=alpha&q=rag`).

## Kebab menu behavioral details (D4)

- **Menu items (v1)**: `Open in editor`, `Copy slug`, `View linked PRs`.
- **Close behavior**: click outside, Escape, or selecting an item
  closes the menu. One menu open at a time per page.
- **`View linked PRs` target**: opens
  `https://github.com/Smart-AI-Memory/attune-ai/pulls?q=<slug>` in a
  new tab. `↗` glyph signals external nav.
- **`Open in editor`**: emits `vscode://file/<abs-path-to-spec-dir>`.
  Works for VS Code, Cursor, Codium forks. v1 hardcodes the URL
  scheme; v2 could read a `~/.attune/editor.json` setting.
- **`Copy slug`**: writes bare slug to clipboard with a toast (mirrors
  the chat-tools copy pattern from the dashboard-tools-inventory work).
- **Disabled state**: in read-only mode, the menu still works (all 3
  actions are non-mutating). No `allow_run` gating needed for v1.
- **Keyboard**: arrow keys focus row (R3.3), Enter drills in, `M`
  (or `.`) opens menu on focused row, arrows in menu, Enter to fire.

---

## Out of scope (parking lot)

- **PR-signal lookup**: querying merged PRs to distinguish
  `Approved-not-shipped` from `Complete`. v2 if the file-only rule
  proves insufficient.
- **Visual grouping** (D3 trigger conditions above).
- **Editor preference setting**: `~/.attune/editor.json` for non-VSCode
  users. v2 if requested.
- **Bulk multi-select / archive / mark-paused row action** — explicitly
  out per the requirements.md non-goals list.

---

## Carryover

- 2026-05-31 — All four decisions ratified in conversation. The
  pre-locked-design-before-requirements shape (decisions ratified
  before requirements.md was written) was Patrick's explicit choice
  — he pulled the design questions forward so they'd be constraints
  rather than open questions. Result: design.md (Phase 2 artifact)
  scope shrinks to implementation-level concerns (data shape exposed
  to template, derivation algorithm code, URL param schema, JS
  architecture, test boundaries) rather than the conceptual decisions
  captured here.
