# Feature Lead Governance — Decisions

**Status:** active (2026-07-27) — OPEN-1..4 + approval-evidence +
disposition model chair-ruled; revision pass APPLIED to
requirements/design/tasks/plan the same day. Execution gated by P1.

Chair rulings of 2026-07-27 come from round-table thread
`q-feature-lead-governance-001` (3 rounds, all seats present, one
steelman round; promoted board messages 8, 9, 10, 11, 16). The
deliberation is TTL'd — this file is the durable record.

## D1 — feature lead, not permanent model owner

**RULED (chair, 2026-07-27): approved — resolves OPEN-1.**
Canonical role name is `feature lead` (3/3 seats, both rounds).
"Lead programmer" is permitted as UI copy only — never in schema,
contract, or event text.

## D2 — coherence authority with hard limits

**RULED (chair, 2026-07-27): approved in substance.** The lead
resolves requirement-satisfying implementation choices; repository
rules, required probes, security constraints, and the human chair
remain above the lead. Requirements text needs the revision pass
(authority-boundary wording and R5/D3 transfer consistency) before
execution.

## D3 — immutable review, appended disposition (as amended)

**RULED (chair, 2026-07-27): approved as amended by the table's
disposition model.**

- Findings are atomic and reviewer-owed at record time: one claim,
  exactly one classification (`rule_violation` | `preference_only`),
  `rule_id` required iff `rule_violation`. A mixed comment is a
  schema violation → one re-prompt; on a failed retry the whole
  comment records as ONE blocking `rule_violation` with
  `needs_split: true` — fail toward visibility.
- Dispositions are per atomic finding, never per comment. `accepted`
  alone is not a terminal state: the vocabulary is
  `fixed | rejected_with_reason | deferred | accepted_advisory`,
  with `open → accepted → fixed | disputed` as the rule-violation
  state machine. Completion gates on TERMINAL states of
  `rule_violation` findings only — this closes accept-and-ignore by
  construction (AC-3/AC-4 restated in the revision pass).
- **OPEN-4 resolved:** `preference_only` findings are shown
  COLLAPSED with a count — never hidden (3/3; auditability plus the
  D6 churn metric requires the count).
- Schema ownership per P2 (see D5): cross-review owns the finding
  schema as a versioned board-record revision; governance consumes
  it and never forks it.

## D4 — persistence: split registry (as amended)

**RULED (chair, 2026-07-27): approved as amended — resolves
OPEN-3.** Tracked artifact over board-only state (3/3), SPLIT:

- Authority and lifecycle state live in `docs/assignments/` ON MAIN
  (one file per assignment), mutated only by chair-merged PRs.
- Findings and hash-chained events live branch-side with atomic
  writes; end-of-life on merge (like handoff files).
- Main is thereby the global comparison set for overlap rejection
  (AC-1's cross-branch enforceability defect resolves here).

## D5 — first surface: thin module + P1 + P2

**RULED (chair, 2026-07-27, post-steelman): resolves OPEN-2 and
REPLACES the drafted D5.** Governance ships as its own thin module
consuming the SHIPPED handoff-packet and board seams (transfers ride
the existing packet frontmatter + digest verify; no parallel
assignment/approval/disposition stores; new fields are proposed as
handoff/cross-review T3 amendments, never a parallel format), with
two elements harvested from the steelman round:

- **P1 — gate inheritance:** governance activation sits behind the
  SAME chair usage-signal read that gates cross-review T3/T4. No
  second activation criterion is invented; one chair read ungates or
  kills both.
- **P2 — single schema owner:** the finding/disaggregation schema is
  owned by the cross-review spec as a versioned board record;
  governance consumes it. Hash-chain and probe machinery stays
  single-homed.

Cross-review's ratified posture is untouched: board-only advisory,
never a merge gate until dogfooded finding-quality earns it — and
governance state must never be readable by any required check
(drift-guard test owed in the revision pass).

**Steelman record:** the split held 2/3 (thin module — Codex,
Claude) vs 1/3 (cross-review T3 — Antigravity, whose decoupled
AdvisoryReviewRecord/LeadGovernanceRecord design is preserved on
board message 14 as the dissent). All three seats produced real
designs; the ruling harvests the T3 vehicle's demonstrated
advantages without housing authority state in an advisory-posture
spec.

## D6 — advisory rollout

**RULED (chair, 2026-07-27): approved unchanged.** Opt-in dogfood;
measure accepted/rejected/preference-only findings, chair
escalations, transfers, and repeated rewrites; not mandatory until
the data shows less churn without slower delivery. P1 supplies the
concrete activation gate.

## D7 — approval evidence: chair-merged PR to the main registry

**RULED (chair, 2026-07-27): new decision — resolves the forgeable
human-approval defect (all seats, both rounds).** Evidence standard
(ii), unanimous in round 2: every chair transition (activate /
cross-provider transfer / scope-expand / revoke) is evidenced by a
chair-merged PR to the main-tracked registry. No caller-supplied
flag, MCP confirmation relay, PR URL, or copied merge metadata is
ever evidence — the MCP surface shrinks to propose/status/dispose
and never claims human approval.

Event schema (union of seats): `event_id`, `event_type`,
`assignment_id`, `sequence`,
`approval{pr_number, merge_commit_sha, merged_by, registry_blob_sha,
registry_digest}`, `lead{provider}` (provider-level identity —
session ids are per-event evidence; same-provider session resume is
NOT a transfer), `timestamp`, `prev_event_digest` (hash chain),
plus `parent_state_digest` on scope changes.

Failure-sensitive probe set, each step killing a distinct forgery
class: (1) `merge-base --is-ancestor origin/main` — fabricated SHA;
(2) host-side PR resolution with `merged_by` in a repo-owned chair
allowlist + commit signature verification — unsigned/non-chair;
(3) registry blob-sha recomputed at the merge commit — a REAL but
unrelated chair merge (replay/misbinding); (4) event hash-chain and
registry-transition diff match — history tampering. Append-only is
an application invariant plus DETECTION (AC-2 rewording owed in the
revision pass); a detected mismatch leaves the prior registry state
authoritative.

Bound-in mitigations for the shared 3/3 risk (chair-merge ceremony →
bypass): gate ONLY the four named transitions; scope changes may
batch; urgent revocation may set an advisory `revoke_pending`
branch-side flag that carries no authority until merged; a
drift-probe AC flags branches with cross-review activity but no
active assignment.

## Not promoted

The round-1 defect register (12 classified items) was declined for
promotion by the chair; it informs the revision pass via the
moderator's session review and expires with the board thread.

## 2026-07-28 — P1 gate DISCHARGED by inheritance

Chair ruling. D5's P1 says governance activation "sits behind the SAME
chair usage-signal read that gates cross-review T3/T4. No second
activation criterion is invented; one chair read ungates or kills
both."

That read was **killed as a gate** on 2026-07-28 — it could not answer
its own question (the `usage-signals` corpus measures PyPI/GitHub
adoption, not feature invocation; its newest snapshot captured zero
rows), and it was circular (the data it wanted comes from the dogfood
runs it was blocking). Full reasoning and receipts:
`docs/specs/cross-review/decisions.md`, 2026-07-28 entry.

**By the inheritance clause, that ruling discharges P1 here.** No
second activation criterion is invented — the clause is honored
exactly: one chair decision resolved both, which is what it was written
to guarantee.

Also settles the artifact conflict the round table's appendix raised
(item 4): the bucket read `approved-not-shipped` while the internal
status token read `draft (2026-07-27)`. The appendix's antigravity seat
concluded chair approval was missing; the other two seats read it as an
un-run gate, not absent sign-off, and the recorded design agrees —
P1 *inherits* cross-review's gate. It was a **label mismatch, not a
re-approval trigger**, and this entry is the one line that fixes it.
Re-running approval would have re-litigated approved design and
multiplied chair work for nothing.

## 2026-07-29 — P1 re-based onto the dogfood ledger (chair, in-session form)

The chair usage-signal read P1 pointed at was killed 2026-07-28
(circular; measures adoption, not invocation) and cross-review
T3/T4 shipped, so P1's original wording gated this spec on a
mechanism that no longer exists. Re-ruled with the north-star leg-3
re-ratification (leg 3 = cross-review dogfood evidence):

**P1 (re-based): governance stays GATED on the cross-review R5
dogfood ledger, ungating at 10 total ledger runs (5 exist at
ruling time) OR the first measurable accepted-vs-rejected finding
pattern, whichever comes first — then the chair rules
ungate-or-kill.** This honors the ledger's own calibration ("no
gate-upgrade claim from five runs"). No second activation
criterion is invented; the single-read principle carries over with
the ledger as the read's new substrate.

## 2026-07-29 — Pilot ruled; integrating-lead shape ratified (chair, in-session form)

Two rulings from the evening team-model session (same day as the
P1 re-basing above — the two are designed to compose, not
conflict):

**D8 — Pilot on ONE module; pilot runs feed the ledger.** The
cross-LLM lead/delegation model activates as a PILOT on exactly
one feature/module. The pilot's delegated runs are recorded in the
cross-review R5 dogfood ledger, so the pilot GENERATES the
evidence P1 waits on rather than bypassing it; full activation is
ruled at the bar (10 runs / first accepted-rejected pattern).
Lead's pilot-module recommendation (chair picks at launch):
`orchestration/_strategies/base.py` QA pass — bounded, tests-only
(Class 1 lane), crisp suite receipts, flagged 2026-07-29 in the
omit-audit as needing a coverage pass. Low blast radius is the
point: the pilot tests the TEAM MECHANISM, not the module.

**D9 — Integrating lead.** Global lead programmer: Claude, unless
a per-feature lead is set via this spec's mechanism. The lead owns
integration, synthesis, central receipt re-runs, and the final
recommendation BELOW the chair. Seats stay advisory; R8 untouched
— only the chair promotes. Scope-widening initiative per the
2026-07-29 global ruling (same-defect neighbors fixed without a
separate ask, widening named for cheap reversal).

**Substrate + discipline (lead-recommended, chair-accepted in the
same exchange):** (a) the lead rule is encoded in the projected
collaboration contract (scripts/project_collaboration_contract.py
master → all provider adapters) — seats are stateless, so the
contract carries the role, not per-prompt reminders; (b) the
receipt-declared delegation rule is BINDING for cross-LLM lanes:
every delegated lane names its receipt type at launch and the lead
re-runs receipts centrally — a seat's self-report is never the
receipt. Both land as the pilot's first tasks.

## 2026-07-29 — Pilot FIRED; first delegated lane complete (lead record)

Chair fired the D8 pilot the same evening. Receipts:

- **Task A (substrate):** lead-programmer + receipt-declared
  delegation clauses landed in the contract master and projected to
  all three provider surfaces (AGENTS.md, .agents/AGENTS.md,
  .claude/CLAUDE.md).
- **Task B (pilot module):** `orchestration/_strategies/base.py`
  46% → 100% (net-new `test_execution_strategy_base.py`, 13 tests,
  serial pass); omit entry converted per its convert-after-QA note.
- **Task C (delegated lane):** codex seat reviewed the REAL pilot
  diff (6 files sent, 0 omitted; board thread
  `review-pilot-feature-lead-base-strategies-20260729-1420`).
  ONE high finding — the lead clause contradicted the contract's
  single-provider requirement. **Lead disposition: ACCEPTED, fixed
  in-branch** (single-provider fallback: lead duties devolve to the
  chair; contract stays one-provider-executable). Ledger row
  appended to the R5 dogfood ledger (feeds P1) with disposition
  `real`.

Pilot observation for the P1 evidence stream: the delegated seat's
first finding was a real defect in the lead's OWN work — the
different-model review caught what the author could not. That is
the accepted-vs-rejected signal the gate measures, seeded run 1.
