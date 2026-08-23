# Cross Review — Decisions

Dated chair rulings. Newest last.

## 2026-07-22 — Feature ratified (roundtable amendment)

Roundtable `q-multi-llm-obvious-win-001`: `cross_review` proposed by
the claude seat as its lead pick. Initial chair ruling recorded it
as a second-pick candidate gated on the 07-27 usage read; same-day
chair amendment RATIFIED it as the second committed multi-LLM
feature — the usage read now informs sequencing/design only.
Binding posture from the amendment: board-only advisory, never a
merge gate until dogfooded finding-quality earns it. Report:
`docs/reports/roundtable/q-multi-llm-obvious-win-001.md` (#1600).
Tracking issue: #1602.

## 2026-07-22 — Scheduling amendment (chair)

Spec AUTHORING pre-07-27; IMPLEMENTATION post-lift, SECOND after
cross-provider-session-handoff. Note: the second position is a
chair sequencing ruling, not a code dependency — the mechanism
reuses the shipped roundtable core only.

## 2026-07-22 — Requirements APPROVED (chair)

R1–R6 + non-goals as drafted; binding posture is a requirement
(blocking-path wiring violates the spec). OPEN-1 (default seat),
OPEN-2 (cadence surface), OPEN-3 (diff budget) explicitly held for
the 07-27 usage-signal read.

## 2026-07-22 — Design RATIFIED + tasks APPROVED (chair, one ruling)

D1 roundtable-primitive composition (`attune.roundtable.review`);
D2 read-only diff gathering with everywhere-visible truncation
manifest; D3 mandatory reply format + `lint_review()`,
noncompliance flagged never repaired; D4 advisory rendering, no
exit-code coupling; D5 per-run ledger append to receipts.md
(D7-honest); D6 knobs named, values land with OPEN-1..3.
Tasks T1 (module) → T2 (skill + mirrors) → T3 (five-run dogfood
ledger across ≥2 seats; low quality is a valid, posture-fixing
result) → T4 (docs + OPEN closure citing usage-read data). Spec is
now fully authored 2026-07-22; implementation staged post-07-27.

## 2026-07-22 — T1+T2 BUILT (held draft #1607, chair pulled forward)

Chair asked for the build same-evening; sequencing intent (handoff
first) is preserved at the LIFT (handoff #1605 merges before #1607).
`attune.roundtable.review` + `/cross-review` skill (plugin + shim +
.agents mirror), attune-hub row, skill count 25→26,
`ROLE_REPLY_CHARS['reviewer']=16k`. `DEFAULT_SEAT="codex"` and
`DIFF_CAP_CHARS=60_000` ship PROVISIONAL per D6 — OPEN-1/OPEN-3
rulings replace them in the 07-27 OPEN-closure commit; OPEN-2 has
no code surface yet (skill text only). Receipts on the PR: 19 new
tests, roundtable 175 serial-green, plugins 148 serial-green,
mutating-git grep clean. T3 dogfooding remains gated on the
OPEN-1..3 rulings.

## 2026-07-28 — OPEN-1..3 RULED; the usage-read gate is KILLED

Chair ruling. The gate held OPEN-1..3 for "the 07-27 usage read."
That read is retired as a gate — not deferred — on three findings, each
verified rather than argued.

**1. The corpus cannot answer the question.** OPEN-3 needs "frequency
and typical diff size" of cross-review runs. `usage-signals` snapshots
measure PyPI/GitHub adoption:

```json
{"attempts": [{"captured": 0, "outcome": "rate-limited"}],
 "github": {}, "pypi_recent": {}, "manifest": {"complete": false}}
```

Zero occurrences of `cross-review`, `roundtable`, or `invocation` in
the snapshot corpus. The newest snapshot (2026-07-26) captured nothing
at all — rate-limited, zero rows.

**2. The gate is circular.** OPEN-3 wants usage data → usage data comes
from T3's five dogfood runs → T3 `<depends>` names "OPEN-1..3 ruled."
Waiting cannot satisfy this gate; it can only expire.

**3. The gate protects nothing.** `DEFAULT_SEAT = "codex"` and
`DIFF_CAP_CHARS = 60_000` are live in shipped 10.6.1
(`src/attune/roundtable/review.py:35-36`) — provisional values are in
users' hands today. Withholding the ruling withheld the label, not the
behavior.

### Rulings

- **OPEN-1 — default reviewer seat: FIXED default, `codex`** (the
  shipped value) for v1. Rotation is not ruled out; it needs T3
  evidence. Carry into that evidence the finding recorded in
  `docs/reports/roundtable/routine-clean-run-20260728-1020.md`: in that
  appendix the antigravity seat diverged on all four triage items by
  reasoning from lifecycle labels and declared status rather than
  PR/receipt state. That is a seat-behavior signal relevant to who
  should review by default.
- **OPEN-2 — invocation ergonomics: MANUAL-ONLY for v1.** No suggested
  cadence, no reminder. Auto-trigger was already a v1 non-goal; this
  makes the whole surface manual until dogfooding shows demand.
- **OPEN-3 — diff budget: RATIFY the shipped `60_000` chars as the v1
  cap**, explicitly provisional. T3's five runs produce the real
  frequency and diff-size distribution; OPEN-3 is **re-ruled from that
  evidence**, which is the data the original gate wanted and could
  never have obtained by waiting.

**T3 is UNBLOCKED.** Its `<depends>` is satisfied by this entry.

Binding posture is unchanged and not reopened: board-only advisory,
never a merge gate until dogfooded finding-quality earns it. A
low-finding-quality outcome remains a VALID result that rules the
advisory posture permanent (dogfood-or-remove).

## 2026-07-28 — T3 EXECUTED; dispositions ruled (chair)

Five real runs across two seats, 2026-07-28 ET evening session
(2026-07-29 UTC stamps). Ledger + carried findings + T4 evidence
notes: this spec's `receipts.md`. Chair ruled all dispositions
as recommended: run 1's five skeptic findings carry-to-#1559;
run 3's single lessons finding dismissed (dated context by
design); run 5's three findings ride the stale docs branch only
if revived. Live-fire checks pass: 5 board threads posted, one+
run per seat, rows == runs (D7). Seat evidence for OPEN-1 and
diff-size evidence for OPEN-3's re-rule are recorded in
receipts.md; T4 (docs + OPEN closure) is now the remaining task.

## 2026-07-28 — T4: OPEN-1..3 CLOSED on T3 evidence (chair)

The 2026-07-28 rulings above set the values and named T3's ledger
as the evidence that would re-rule them. T3 executed the same
session (five runs, `receipts.md`); each item now closes citing
its datum:

- **OPEN-1 — default seat: CLOSED, fixed `codex`.** Datum: codex
  produced findings on 3/3 targets (5, 1, 3 — including three
  substantive contract gaps in the #1559 draft); antigravity
  returned NO FINDINGS on 2/2 targets including the same 821-line
  diff. Rotation stays an extension point, not a default.
- **OPEN-2 — cadence: CLOSED, manual-only.** Datum: all five T3
  runs were manual with zero invocation friction; no demand signal
  for a suggested cadence surfaced. No code surface changes.
- **OPEN-3 — diff budget: CLOSED, `60_000` chars ratified
  (provisional label removed).** Datum: both code targets fit
  whole (max 821 insertions / 3 files, 0 omitted); the one
  truncation (30-file docs target, 23 sent / 7 omitted) degraded
  visibly with every omitted file named, and review quality held.
  No run needed a larger cap for code content.

Same commit (D6's docs+const commit): the PROVISIONAL comment on
`review.DEFAULT_SEAT` / `DIFF_CAP_CHARS` is replaced with the
ruled citation, and the feature page ships
(`content/features/cross-review.md` → 15 projected outputs).
Binding posture unchanged: board-only advisory. With T4 done, all
spec tasks are complete; the ledger stays open for future runs.

## 2026-07-29 — this spec's dogfood ledger is the north star's third leg (chair)

Re-ratified in-session: cross-review dogfood evidence replaces the
killed usage-signal read as the evidence source that picks what's
next. The R5 ledger in receipts.md is the surface; its first
closed loop (run-1 findings → #1559 lift → 4 fixes shipped, 1
dismissed-with-probe) is the ruling's receipt. Coupled:
feature-lead-governance P1 re-based onto this ledger (bar: 10
total runs OR first accepted/rejected pattern — see that spec's
decisions.md). Posture unchanged: board-only advisory; this grants
the ledger a ranking role, not a gate role.

## 2026-08-23 — the ledger's yield is tallied by a script, not by reading (chair-ratified retro item)

"Yield stays measured in the R5 ledger" (feature-lead-governance,
2026-07-30) had no mechanism: the measurement was a human reading
~90 prose rows. `scripts/ledger_precision.py` now tallies per-seat
precision from the disposition cells (clean / real / N real /
dismissed|noise|rejected — the vocabulary D11a fixed), plus any tool
precision a row records inline (bug-predict). First run on the 89
rows at ratification: **codex 88% (126 real / 143 sent, 77 lanes,
9 clean), antigravity 83% (5/6), bug-predict 100% (3/3, one note)**.
Within a classified row, "rejected" is the conservative remainder —
every finding the lead did NOT accept as real (a `4 real` of 5 counts
one). Rows the script cannot classify (parked `stale-branch`, chair-
ruled, partial-manifest) contribute to NO column; they are listed.

Three rows the script cannot read are named, not dropped, and
pinned in `tests/unit/scripts/test_ledger_precision.py` as a
shrink-only set: a NEW row outside the vocabulary fails the test,
so the tally cannot silently stop being "measured". Posture
unchanged — a report, never a gate; exit code is always 0.
