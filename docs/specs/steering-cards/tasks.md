# Steering cards — tasks

**Status:** draft (2026-09-11) — NON-EXECUTABLE. Entry gate: D1, D2, D3
ruled in [decisions.md](decisions.md). Run `/spec` to approve before
any task starts. Phases start at 1.

## Phase 1 — Master + card 2 (help page + launcher)

- **Task 1.1 — Master file.** `content/steering/steering-card.md` with
  the front-matter schema from design.md, rows 1..N cast from the
  2026-09-11 session (layers table with host column, rules of thumb,
  routing words, generic conventions linking to contract anchors) and
  the `essay` slot left as a marked stub. Schema test: unique `n`,
  known sections, `hosts` ⊆ {claude, codex, antigravity}.
- **Task 1.2 — Help projection.** Curated-input path in the generator
  for the ruled kind (D2); `--check` mode; generator added to
  `tests/unit/help/test_generated_help_drift.py`; corpus rebuild
  (`generate_all.py`, cross links, summaries) so `help_lookup("steering")`
  resolves. Receipts, one per R7 surface: `help_lookup` returns the
  card; `/help steering` routes to it; `/catalog` lists the quickstart;
  the attune-help site build renders the page (URL in the PR body).
- **Task 1.3 — Launcher quickstart.** `quickstarts/steer-claude.md`:
  one goal, one command, one result. Receipt: rendered page + the
  drift test.

## Phase 2 — Card 3 (contract block)

- **Task 2.1 — Projector block.** `scripts/project_collaboration_contract.py`
  emits the `steering` block (host table + pointer, per D3) into every
  provider surface it owns; the contract projection test covers it.
  D11 lane on the PR (governance text). Receipt: preflight
  `collaboration-projection: in sync`; block visible in `AGENTS.md`.
- **Task 2.2 — Verify the unverified cells.** Probe Antigravity's hook,
  rule-text and memory layers; replace "unverified" with a dated fact or
  leave it and say so. Receipt: the probe command and its output in the
  PR body.

## Phase 3 — Card 4 (concept page)

- **Task 3.1 — Essay.** Fill the `essay` slot per D4/D5; render to the
  docs tree; docs projection drift guard. Receipt: page builds; doc
  import audit green.

## Phase 4 — Close

- **Task 4.1 — Status flip + retro row.** Spec status → shipped; the
  card family recorded in the help system's own index. (Card 1 is out
  of scope and outside this repository; linking it to card 2 is the
  chair's own optional edit, not a task here.)
