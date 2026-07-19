# Roundtable Triage — Decisions

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
