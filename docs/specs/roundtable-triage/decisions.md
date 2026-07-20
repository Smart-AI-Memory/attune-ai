# Roundtable Triage — Decisions

**Status:** active (2026-07-20) — chartered 2026-07-19 (n=1); n=2 validated 2026-07-20; requirements authored + headless appendix implemented (see below)

## 2026-07-19 — Charter (chair, "as synthesized"; thread q-briefing-triage-001)

Born from a live demo in conversation: the moderator pulled the ops
briefing read-only (curator source readers, spec lifecycle buckets,
gate verdict ledger, local spend), distilled four decidable items,
and convened the table. One round; the single divergence resolved on
recorded evidence (the claude seat pre-conditioned its Item 1 pick
on an external clock the session-starter record confirmed — its own
flip applied, making the sequencing effectively 3-0). This thread is
**n=1 of the T4 validation plan**. Promoted board items: positions
#2–#4 + synthesis #5.

**T1 — Approved-not-shipped sequencing (ruled).**
`docs-wiring-audit` advances as the next work unit.
`fable-premium-tier` parks with Resume-Trigger 2026-07-28 (the
DEC-7 07-27 read + fable task 9's ≥07-28 window — the external
clock the claude seat hypothesized and the record confirmed).
`integration-coverage` parks evergreen-dated (no decay cost).
Both park edits applied to the specs' highest-phase files in this
PR, with triggers per R9 below.

**T2 — Status-line hygiene (chartered, next hygiene unit).**
One PR, one ruling: manual status backfill across the ~20
unparseable spec dirs + a `status-line` baseline lint added to the
spec-lifecycle gates ladder. Landed together — a gate without the
sweep fails 20 dirs on arrival. Implementation note discovered
during promotion: the lifecycle detector does not recognize
`parked` as a status token (integration-coverage was already parked
yet bucketed approved-not-shipped) — the lint must define the
recognized status vocabulary, and `parked` must map to an explicit
lifecycle bucket.

**T3 — Briefing-coupled freshness (ruled).** No standing scheduled
LLM sweeps (the quiet-burn class). The triage briefing refreshes
any input source staler than ~7 days WHEN IT RUNS, and otherwise
renders "dark since <date>" honestly. Freshness is a property of
the briefing, not a cron.

**T4 — Routinization: appendix, not a new routine (ruled).**
Briefing→table triage attaches to the existing weekly clean-run as
an appendix digest — one weekly ruling sitting, ≤5 triaged items
per digest, headless only after n=2 manual validation (this thread
is n=1), auto-demoted to chair-invoked after two consecutive
digests producing zero rulings the chair cares about. Guards all
three seats' named risks: decision-budget violation (antigravity),
housekeeping crowding out product work (codex), unvalidated
automation (claude).

**R9 — Resume-Trigger required on parks (accepted; antigravity).**
The T2 status-line lint requires a `Resume-Trigger:` clause on any
`parked` status — a date, a dependency milestone, or an explicit
`evergreen` declaration. Parked specs cannot rot indefinitely.

**Next for this spec:** author requirements (producing run when the
chair queues a pack, or direct) covering the appendix digest format,
the ≤5-item cap mechanics, the freshness thresholds, and the
demotion rule; n=2 manual validation runs alongside.

## 2026-07-20 — n=2 validation run (thread q-briefing-triage-002; chair ruled "go all")

Pre-authorized 2026-07-19 evening; run alongside the first scheduled
clean-run digest (one sitting, per T4). Four items (cap held), none
duplicating the clean-run digest. Seats: claude (session), agy,
codex — independent, one round, halting.

**A1 (3-0, ruled).** docs-wiring-audit CLOSED as shipped — n=1's
"no activity since 07-15" evidence line misread shipped-and-quiet
as silent-rot (v1 + required CI check on main; v1.1 07-15; only
deferred Task 10 open). Status flipped in all four phase files.
Lesson for briefing evidence: "no activity" must be cross-read
against the spec's own status line before it feeds a sequencing
ruling.

**A2 (3-0, ruled).** T2 hygiene unit EXECUTED as the replacement
next work unit, one PR: token-first status backfill (~24 dirs),
`parked`/`living`/`shipped`/`superseded` in the detector vocabulary
(+ `parked` lifecycle bucket), the third status-line bolding
convention in the parser, the `status-line` baseline gate
(CI sweep, D7 pattern), R9 Resume-Trigger enforcement, and the A1
flip folded in (codex amendment). Scope guard honored: the Item-3
tag parser did NOT ride in. usage-signals US-4 named the product
unit next.

**A3 (ruled).** The three 2026-07-20 diagnosis records are
live-fire/dogfood artifacts (85c88fd9 + 63c533fb are the
advanced-debugging spec's named receipts; 0910cf10 falls inside the
overnight Phase C/D dogfood window). No closure/annotation seam
exists yet (store is append-only by design), so the canonical
stream was NOT hand-edited; disposition recorded in
advanced-debugging-plugin/decisions.md with two queued follow-ons
(priors defect; origin-tag + closure seam + automated-suite
exclusion). RR corpus record 85c88fd9 stays (D3 no-backfill; 2-1
tag-don't-delete, recorded evidence over agy's cleanup).

**A4 (effective 3-0, ruled).** Gate verdict ledger is dark locally
BY CONSTRUCTION (D7 CI-only; nothing invokes the lifecycle runner
locally). Briefing contract amended: fetch CI gate verdicts at
briefing render time (timestamped unavailable/expired handling, no
scheduled refresh — T3-compliant). Queued behind this PR with the
A3 follow-ons; not a parallel program (codex risk).

**T4 (ruled: armed).** n=2 validation PASSED — cap held (4/5), zero
digest overlap, and the appendix caught a mis-ruled work unit the
clean-run alone would have missed. Headless appendix is ARMED per
T4; implementation (extend the clean-run routine with the briefing
appendix) queues behind the A3/A4 follow-ons. Auto-demote rule
stands: two consecutive zero-ruling digests demote to
chair-invoked.

Deviation noted: n=2's question was posted as author `moderator`
(chair pre-authorized but did not compose the brief live; n=1 used
`chair`).

## 2026-07-20 — Headless appendix implemented + requirements authored (chair "go 1")

`attune.roundtable.triage_appendix` lands the T4-armed contract:
read-only briefing pull (curator sources + gate ledger + usage
freshness), deterministic ≤5-item distillation with named drops,
same-thread appendix (question → seats → synthesis) under a
4-invocation sub-cap (clean-run + appendix ≤ 8 < R5 ceiling 10),
`ATTUNE_TRIAGE_APPENDIX=off` kill switch, and the T4 demotion loop
(digest records in `~/.attune/ops/triage_appendix.json`;
`record_rulings()` is the ruling session's write; two RECORDED
zero-ruling digests demote; unrecorded never demotes).
`requirements.md` (TA-1..TA-8) codifies the ruled contract — no new
scope. Receipts: 15 contract tests in
`tests/unit/roundtable/test_triage_appendix.py`; first live receipt
= next Monday's 06:00 scheduled run. TA-5's CI-artifact fetch stays
the queued follow-on (A4).
