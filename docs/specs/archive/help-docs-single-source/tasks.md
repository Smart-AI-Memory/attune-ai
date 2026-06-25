# Tasks: Single-Source Help + Docs (pilot)

**Status:** complete (2026-06-24) — pilot executed and the full rollout
landed. Every feature in `.help/features.yaml` is single-sourced
(`status: manual`, projected from `content/features/<F>.md`); the
`remaining` set is empty. The Tier-3 batch finished with help-system
(#1043) and ops-dashboard (#1044). See the closeout note under Exit
criteria.
**Created:** 2026-06-21
**Builds on:** [requirements.md](requirements.md),
[decisions.md](decisions.md), [design.md](design.md)

Execution order is deliberate: the cheapest, highest-signal task
(authoring the master file) comes first so the section schema is
validated against real content **before** any projector code is
written. Cross-repo note: content tasks land in **attune-ai**;
projector tasks land in **attune-author** — the worktree-path guard
blocks Write/Edit across repos, so attune-author work uses Bash writes
or its own session (see `.claude/lessons.md`).

---

## Phase 1 — spec-engine pilot

### T1 — Author the spec-engine master file (attune-ai)

**Objective:** Produce `content/features/spec-engine.md` by
consolidating the existing hand-authored `docs/` pages (how-to,
tutorial, architecture, reference) plus the good parts of the `.help`
corpus into the canonical section schema. This is a **merge of
existing hand-authored content**, not new generation.

**Files:** create `content/features/spec-engine.md`.

**Acceptance:**

- All applicable canonical sections present (Overview, Concepts,
  Quickstart, Tasks, Reference, Comparison, Failure modes, FAQ,
  Notes & tips, Design & extension).
- Frontmatter complete (feature, summary, tags, source_globs, nav).
- No content invented — every claim traceable to an existing doc or
  to source.
- **Decision surfaced:** record whether `tutorial` content fits a
  section or must stay hand-authored (design caveat).

**Risk (medium):** the schema may not cleanly hold all existing
content. If so, adjust the schema in `design.md` in the same change —
the schema is a hypothesis until proven on real content.

### T2 — Build the projector module (attune-author)

**Objective:** A deterministic module that reads a master file and
emits the `.help` kinds + `docs/` feature pages per the projection
map. No LLM in the canonical path (D3).

**Files:** create `src/attune_author/projector/` (reader, projection
map, per-output renderers); reuse `generator._extract_source_info`
(AST) and the `fact_check` package.

**Acceptance:**

- `project(master_path) -> {help_kinds, doc_pages}` returns rendered
  content for each declared output.
- Reference section is enriched from AST extraction (real signatures).
- Missing sections skip their dependent outputs (no error).
- Unit tests: projection map coverage, missing-section handling,
  frontmatter propagation.

**Risk (high):** slicing one section into differently-formatted
outputs (terse `.help/task` vs narrative `how-to#core-api`) may need
per-output templates — prototype within this task.

**Depends on:** T1 (real master file as the fixture).

### T3 — Render spec-engine end-to-end + verify (attune-ai)

**Objective:** Run the projector on `spec-engine.md`, write outputs,
and prove both consumers work.

**Files:** writes `.help/templates/spec-engine/*` and
`docs/{how-to,tutorials,architecture,reference}/spec-engine.md`.

**Acceptance:**

- 11 `.help` kinds + the 4 `docs/` pages produced (or the documented
  subset, if `tutorial` stays hand-authored per T1).
- Help system serves the projected `.help` unchanged (`help_lookup`
  smoke).
- `mkdocs build` clean.
- Diff vs the current files is reviewed — projected output is at least
  as good as today's hand-authored docs/.

**Depends on:** T1, T2.

### T4 — Grounding + fact-check (attune-ai)

**Objective:** Validate the master file before projection.

**Acceptance:**

- `python_refs` / `cli_refs` / `md_links` clean (auto-correct via
  `import_repair`).
- `rag_knowledge_query` grounding report produced for prose claims;
  unsupported claims resolved or noted (warn-mode for the pilot).

**Depends on:** T1.

### T5 — Defuse regen-overwrite for spec-engine (attune-ai/author)

**Objective:** Ensure the weekly LLM regen no longer
generates/overwrites spec-engine (DD5/R8).

**Files:** edit the generator feature manifest
(`.help/features.yaml` and/or attune-author's feature list) to mark
spec-engine `source: projected` or remove it from LLM generation.

**Acceptance:**

- A simulated regen run does not touch spec-engine's projected files.
- Regression guard or test asserting the exclusion.

**Depends on:** T3.

---

## Phase 2 — models pilot

### T6 — Author + render models (attune-ai + projector)

**Objective:** Repeat T1+T3 for `models` — exercises the `cli:` block,
CLI-reference projection, tables, and `cli_refs` fact-check.

**Acceptance:**

- `content/features/models.md` authored.
- Projector emits models outputs incl. the CLI reference page.
- `cli_refs` validates flags against the real CLI.
- Both consumers verified; spec-engine path unchanged.

**Depends on:** T2 (projector proven on spec-engine).

---

## Phase 3 — rollout

### T7 — Write the rollout playbook (attune-ai)

**Objective:** Capture a repeatable migration recipe for the remaining
23 features from what the pilot taught (R7).

**Files:** `docs/specs/help-docs-single-source/rollout.md`.

**Acceptance:**

- Step-by-step per-feature migration recipe.
- Known per-shape gotchas (CLI features, prose-heavy, tutorial).
- Updated `decisions.md` if the pilot changed any decision.

**Depends on:** T3, T6.

---

## Exit criteria (pilot complete)

- spec-engine and models both single-sourced, rendering to both
  consumers, fact-check/grounding green, regen-overwrite defused.
- The chain is repeatable and the rollout playbook is written.
- No regression in the in-tool help system or `mkdocs build`.

---

## Closeout (2026-06-24) — rollout complete

The pilot exit criteria were met and the full rollout ran to completion
using the R7 playbook. Every feature in `.help/features.yaml` is now
single-sourced (`status: manual`, no `files:`); the projector owns the
`.help/templates/<F>/` kinds and the `docs/{how-to,architecture,
reference}/<F>.md` pages; frozen `faq.md` files await the four-channel
FAQ Generator (D6/D7).

- **Tier-3 finishers:** help-system (#1043, the help ENGINE) and
  ops-dashboard (#1044, the runner CORE). Earlier Tier-3: telemetry
  #1034, configuration #1035, resilience #1036, hooks #1037, cli #1038,
  orchestration #1040, plugin #1042.
- **What the adversarial gate kept catching to the end:** behavioral and
  scope fiction the static gates can't see — re-export/import paths,
  async-vs-sync, property-vs-method, deprecated-as-canonical, and
  invented APIs (e.g. ops-dashboard's non-existent `detect_candidates`/
  `Candidate`). Mandatory subagent review stays the load-bearing step.

**Not in scope of this spec (open follow-up):** the rollout edits
repo-root `content/`/`.help/`/`docs/`, which reach ops/website/mkdocs
but NOT `pip install attune-ai`. Delivering to pip users needs a
release-prep-cadence pass that regenerates `plugin/help/generated/`
under the wheel-packaged path. Tracked in the next-session handoff.
