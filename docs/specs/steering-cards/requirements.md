# Steering cards

**Status:** draft (2026-09-11) — scoped from the chair's request the same
evening; nothing built. Card 1 (Patrick's personal Steering Card) exists
as a private artifact and is OUT of scope here. D1–D3 in
[decisions.md](decisions.md) are PROPOSED, not ruled; tasks.md is
non-executable until they are.

## Origin

2026-09-11: after a session on where a correction has to live to change
an assistant (hook → gate → rule text → memory → lesson → chat), the
chair asked for a glanceable memory aid, then for it to be launchable
from the help system for new users, then for a version that applies to
Codex too and one that applies to any AI. Four audiences, one body of
content.

## Scope

Three renderings of ONE generic master:

| Card | Audience | Rendering |
|---|---|---|
| 2 | attune users steering Claude | a help-system page, launched from a genuine quickstart |
| 3 | attune users on any seat (Claude, Codex, Antigravity) | a block projected into the collaboration contract's provider surfaces |
| 4 | anyone steering any AI assistant | a prose concept page on the docs site |

Artifact tier: spec — three surfaces, one of them governance text, with
premise questions (kind fit, projection cost) worth recording.

## Requirements

- **R1 — One master.** All generic steering content lives in one
  tracked file; every card is a projection with a `--check` drift
  guard. No hand-edited twins (contract principle 3).
- **R2 — Host column, verified.** The layers table states per host
  which layer exists. Facts carry their basis: Codex `hooks.json` does
  not execute (verified 2026-07-18, lesson corpus); Antigravity is
  UNVERIFIED until probed. "Unverified" is a legal cell value.
- **R3 — Launcher ≠ container.** The quickstart kind stays "one goal,
  one command, one result": a real quickstart opens the card; the card
  itself lives in a kind that fits its shape (D2).
- **R4 — Budget-aware projection.** The contract block (card 3) must
  not add the whole card to every provider surface's resident context;
  it carries the host table and a pointer (D3).
- **R5 — Rows are stable.** Master rows are numbered; a row keeps its
  number for life; removed rows are struck, not renumbered. Numbering
  is the master's own — card 1's numbers are personal and unrelated.
- **R6 — Chair-ruled scope.** Card 2 carries the steering trio (layers,
  rules of thumb, routing words) PLUS the generic conventions (receipt
  beats promise, claims carry their basis, merge-word gate, …), ruled
  2026-09-11. Where a convention already lives in the contract, the
  row LINKS to it rather than restating it (R1).
- **R7 — Discoverable.** `help_lookup`, `/help`, `/catalog` and the
  attune-help site all find the card after the corpus rebuild
  (`generate_all.py`, cross links, summaries).

## Non-goals

- Card 1 (personal) — stays hand-edited in `~/Documents/claude-memory-aid/`.
- Any change to what the conventions SAY — this spec renders them, it
  does not re-rule them.
- Live telemetry of card usage (the help tracker already exists; not
  extended here).
