# Cross Review — Design

**Status:** approved (2026-07-22) — D1–D6 ratified by the chair.
OPEN-1..3 values land at the 07-27 usage read; this design names
the knobs, not the values.

## Shape

Roundtable-family: one new module, one skill, zero new subsystems.

```text
src/attune/roundtable/review.py   # one-seat review run
plugin/skills/cross-review/SKILL.md   # + .claude shim + .agents
                                      # mirror (sync_agents_skills)
```

## D1 — module reuses the table's primitives

`review.py` composes what exists: `Board` (thread post/read), the
seat invocation recipes (Codex stdin / agy plan-mode — same
verified commands as the roundtable skill), and the role-budget
pattern (`compiler.ROLE_REPLY_CHARS` gains a `reviewer` entry).
No new board schema: messages are `kind='position'` on threads
named `review-<branch-slug>-<n>`, with a moderator `disposition`
note. Promotion is the existing Step 6 — nothing new to build.

## D2 — diff gathering, read-only

Target resolution: current branch vs `merge-base origin/main`
(default), `--staged`, or explicit paths. Read-only git subprocess,
validated paths (same discipline as the handoff spec's D2). The
budget manifest lists files sent vs omitted, ordered by
diff-size descending, and is included in BOTH the seat brief and
the board post (R3 — a partial review must say so everywhere).

## D3 — mandatory reply format + mechanical lint

The brief demands: `FINDING: <file>:<line> [severity] <claim>`
lines, or the literal line `NO FINDINGS`. A `lint_review()` in the
compiler's style checks the reply mechanically; a noncompliant
reply is posted as-received with `format_noncompliant=True` (R4) —
never repaired into false structure. ABSENT seats post the
roundtable's standard `ABSENT — <reason>` row.

## D4 — advisory rendering

The session renders findings as a plain advisory list (severity,
anchor, claim) plus the truncation manifest. No exit-code coupling:
the run "succeeds" when the review RAN, including a clean
`NO FINDINGS` result and an ABSENT seat (binding posture).

## D5 — dogfood ledger append

Each run appends one row to this spec's `receipts.md` in the
working tree (the moderator session owns file I/O): date, seat,
target, files sent/omitted, findings count, disposition
(`not-triaged` until the human rules on the findings; the skill
offers the disposition edit at render time). Rows are D7-honest:
only real runs, no synthetic entries. The row rides to main with
whatever the session ships (docs-class change).

## D6 — knobs held for OPEN-1..3 (07-27)

| Knob | Location | OPEN item |
|------|----------|-----------|
| default seat | `review.DEFAULT_SEAT` | OPEN-1 (fixed vs rotation) |
| cadence surface | skill text only | OPEN-2 (manual vs suggested) |
| diff budget | `ROLE_REPLY_CHARS['reviewer']` + diff cap const | OPEN-3 |

Provisional values may ship commented as provisional; the Monday
ruling replaces them in one docs+const commit.

## Test plan

- `tests/unit/roundtable/test_review.py` — target resolution,
  budget manifest math, `lint_review()` matrix (compliant /
  noncompliant / NO FINDINGS / ABSENT), ledger-row rendering.
- Board interactions against the same test double the roundtable
  suites use (no live Redis in unit lanes).
- Dogfood receipts are the R5 ledger itself — the first five rows
  double as the live-fire evidence.
