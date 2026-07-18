# Decisions — Cross-Provider Collaboration Projector

**All six RATIFIED by Patrick, 2026-07-18 — the recommended option
(a) in every case** ("D1a D2a D3a D4a D5a D6a — ratify all six").

## D1 — Where do completed handoffs live? (RATIFIED: a)

The contract says a handoff lives "in the branch or task's tracked
work" — no canonical path, so two agents can't reliably find the
same artifact. Options: (a) `docs/handoffs/<branch-slug>.md`,
tracked, one per branch, deleted on merge; (b) untracked
`.attune/handoffs/`; (c) leave free-form.
**Recommendation: (a)** — tracked, discoverable by both agents from
the branch name alone, and reviewable in the PR.

## D2 — Generated-source notice inside projected blocks? (RATIFIED: a)

Only the master warns against hand-editing; a reader of AGENTS.md
can't see that. Options: (a) render one comment line inside the
block ("generated from content/collaboration/contract.md — edit the
master"); (b) rely on the markers alone.
**Recommendation: (a)** — one line, costs nothing, prevents the
exact drift class this repo has hit with other projectors.

## D3 — Drift gate surface: CI, pre-commit, or both? (RATIFIED: a)

`--check` exists but is unwired. VERIFIED CONSTRAINT (2026-07-18):
Codex does not execute hooks.json hooks at all in the current build,
so any Codex-side enforcement is off the table; the gate must live
in shared surfaces. Options: (a) pre-commit hook + CI job; (b) CI
only.
**Recommendation: (a)** — this repo's convention (help/skills
projectors) is pre-commit warn + CI enforce; drift caught at commit
time is cheapest.

## D4 — Duplicate or misordered master headings? (RATIFIED: a)

`_parse_sections` is last-wins on a duplicated `## Shared contract`
and order-insensitive. Silent last-wins can project half an edit.
Options: (a) reject duplicates with ProjectionError; (b) document
last-wins.
**Recommendation: (a)** — rejection is 5 lines and converts a silent
content bug into a loud one.

## D5 — Failure guarantee: preflight-only vs. write-phase rollback? (RATIFIED: a)

Implemented: preflight all reads/validation before any write; a
crash mid-write-phase can still leave targets partially updated, but
a rerun converges (idempotent). Options: (a) accept preflight +
idempotent-rerun as the guarantee, documented; (b) add temp-file +
atomic rename per target.
**Recommendation: (a)** — three small local files, self-healing
rerun, and `--check` catches any partial state; (b) adds Windows
rename-semantics risk for little gain.

## D6 — Repo-local infrastructure or reusable Attune feature? (RATIFIED: a)

Options: (a) stay a repo `scripts/` tool until a second repo needs
it; (b) productize now (`attune collaboration sync`).
**Recommendation: (a)** — the "registered ≠ working / dogfood first"
rule; promote only after this repo has lived with it.
