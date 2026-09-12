# Steering cards — decisions

**Status:** draft (2026-09-11) — D1–D3 PROPOSED by the lead with their
counter-cases; nothing ruled. The chair rules; then tasks.md becomes
executable.

## D1 — One master, three projections (PROPOSED)

**Proposal:** all generic steering content lives in one master file;
cards 2, 3 and 4 are projector outputs with drift guards. Card 1 stays
hand-edited.

**Why:** the cards share ~80% of their rows. Four hand-maintained copies
drift — the socratic help note was found 14 lines behind its CLAUDE.md
source the same day this spec was written (#2509), because notes had
no guard. Contract principle 3.

**Counter-case (strongest):** a projector is more machinery than three
Markdown files, and card 4 wants prose, not rows — the `essay` slot is
where "one master" starts costing more than it saves. If card 4 turns
out to be mostly prose, it may deserve to be an authored article that
merely LINKS to the master.

## D2 — The quickstart is the launcher, not the container (PROPOSED)

**Proposal:** a genuine quickstart ("Steer Claude in five minutes" → one
command) opens the card; the card lives in a kind that fits ~30
numbered rows — `concept` as-is, unless the chair wants a new `guide`
kind.

**Why:** the quickstart kind is defined as one goal, one command, one
result (`scripts/generate_quickstart_templates.py`, its template); a
30-row card under that kind misnames itself to `help_lookup` and the
site.

**Counter-case:** a new kind touches the generators, the site, and the
cross-link builder; `concept` costs nothing and is close enough. The
chair chose "quickstart page" on 2026-09-11 before this distinction
was drawn — this decision asks whether the choice survives it.

## D3 — The contract block carries the host table and a pointer, not the card (PROPOSED)

**Proposal:** card 3's projection into provider surfaces is the host
column table (~600 bytes) plus one line pointing at the full card.

**Why:** provider surfaces (`CLAUDE.md`, `AGENTS.md`, …) are resident
context for every session; the rules corpus already runs a byte budget
(`tests/unit/rules/test_rules_residency_budget.py`, 20,000 bytes eager).
The host table is the only steering fact a seat needs at hand: what
"block it" means on THIS host.

**Counter-case:** a pointer is one more hop for a Codex user who has no
`/help` hub; the full routing-words list (~9 lines) might earn its
place in the block.

## D4 — Does card 4 name attune? (OPEN)

Essay-only body, attune in a footer link — or attune as the worked
example throughout. Affects whether card 4 is marketing or method.

## D5 — Is the "give a correction that sticks" recipe generic? (OPEN)

The recipe (name the layer, write the trigger as the situation, date
the enforcer against its ruling) reads as generic; the routing words
(`remember` / `ratify` / `block` / `guard`) are attune-Claude vocabulary
today. Decide whether the recipe ships in the master with the words
marked `hosts: [claude]`.
