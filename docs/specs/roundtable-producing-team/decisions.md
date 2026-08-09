# Round Table v2 — Producing Team: Decisions

**Status:** shipped (2026-07-29; flipped at 2026-08-08 triage) —
design phase waived 2026-07-20 (entry below); P1–P4 landed and the
re-run queue is closed.

## Thread table-v2-001 — promoted (2026-07-18, chair: Patrick)

Promoted from `attune:roundtable:thread:table-v2-001` per D2 (this
spec is the owning destination). One round of three used — the
moderator halted early because the three positions were one
architecture described at three zoom levels: pipeline stages
(codex), output formats (antigravity), round semantics (claude).

**Question:** the chair's v2 directive — a producing team that
authors powerful specs and generates AI solutions, under the v1
constraints (chair-only promotion, text-only members,
moderator-owns-I/O, 3-round ceiling, four artifact tiers).

**Positions (independent, round 1):**

- **claude** (subagent, 53s): typed round contracts; moderator-
  built grounding pack (anti spec-drift); artifact compiler;
  materialize-and-validate with cross-seat review; dissent
  register; provenance + budget ledger. Risk: the TRUST MACHINE —
  green receipts + tidy queues train the chair to rubber-stamp;
  cap candidates/session, dissent register non-empty or attested.
- **antigravity** (agy plan-mode, 8s): tier auto-classification +
  template schema enforcement; adversarial critique probes;
  apply-ready unified-diff outputs; pre-promotion receipts in the
  moderator sandbox. Risk: moderator context saturation /
  diff-integration bottleneck on multi-file work.
- **codex** (codex exec, 53s): role-specialized rotation;
  traceable proposal ledger (per-item IDs end-to-end); dissent as
  an output; executable spec quality gates; budget-aware
  decomposition + checkpoint recovery. Risk: GOVERNANCE THEATER —
  excellent ledgers, less software; shared blind spots made
  authoritative; measure by shipped artifacts only.

**Structural convergence (all three, independently):** moderator
as sole materializer into scratch worktrees; receipts before
chair; dissent preserved first-class; per-item promotion extended
to per-REQ spec drafts; per-round roles.

## Chair rulings (2026-07-18)

Ruled "1" on the moderator's pushback form — recommendations
adopted as initial settings WITH two accepted amendments:

1. **Phase-1-minimal (pushback accepted).** V2-P1 is spec
   authoring ONLY, with exactly three settings live: grounding
   pack, typed round outputs, per-REQ promotion. The artifact
   compiler, full ID-ledger, and all code generation are deferred
   until one real spec ships through the loop. Rationale: codex's
   own governance-theater risk; the #1093 precedent (surfaces
   built before engines proven get reversed); v1's own P0→P3
   incremental success; bounds antigravity's moderator-saturation
   risk.
2. **Fixed roles first, rotation later (pushback accepted).**
   First one-two specs: claude drafts (grounding pack plays to
   repo-context strength), codex + antigravity critique.
   Rotation — which two seats independently demanded, and which
   remains the end-state (V2-P4) — switches on after the loop is
   baselined.
3. **Adopted as-is:** moderator-as-sole-materializer,
   receipts-before-chair, dissent-preserved, per-item promotion,
   candidate-per-session cap, dissent-register attestation.

**Open (chair):** the candidate-per-session cap NUMBER (TR-6).

## TAC-1 receipt — V2-P1 first spec-authoring loop SHIPPED (2026-07-19)

Thread `mem-signal-001` → `docs/specs/memory-feedback-signal/`
(requirements APPROVED per-REQ by the chair; provenance names the
thread). All three ratified P1 settings exercised for real:

- **Grounding pack** killed the first subject before any member
  spend (workflow-failure-exit-propagation: already shipped +
  archived; the stale memory that recommended it was fixed) and
  grounded the actual loop in PR #1366 / session_stash / ops/data
  code facts.
- **Typed rounds**: draft (6 REQs) → two adversarial critiques
  (6 + 14 cited items; codex's injection catch became MI-7) →
  revision (7 REQs, six agreed, one 2-1, dissent register,
  nothing rejected). Four of five open questions settled by
  deliberation; ONE reached the chair.
- **Per-REQ promotion**: chair approved all seven; the 2-1
  resolved by ruling with both critics' positions surviving
  (antigravity's formula = headline; codex's reversibility =
  reader shape).

Field note carried to V2-P2: seat-reply caps must be ROLE-AWARE
(the 8000-char cap truncated the drafter's revision; positions and
documents need different budgets — fold into the typed round
contracts).

## V2-P2 — artifact compiler + proposal ledger SHIPPED (2026-07-19)

Built AFTER V2-P1's real loop, exactly as the phase gate required —
every design choice traces to something the live loop did by hand:

- `src/attune/roundtable/compiler.py`: typed round-contract LINTS
  (`lint_draft` / `lint_critique` / `lint_final` — TR-4's
  mechanical gate applied to spec loops: uncited critique items,
  untagged final items, and unattested-empty dissent registers are
  rejected before posting); `parse_draft` (drafter documents →
  per-item structures with convergence tags); `link_critiques`
  (the proposal ledger's objection column: critique items attached
  to the requirement they target); `compile_requirements`
  (deterministic assembly honoring per-item chair rulings —
  approved items only, declined/unruled ids recorded honestly in
  the header, thread id in provenance per R10).
- **Role-aware output budgets** (`ROLE_REPLY_CHARS`): the V2-P1
  field-note fix — drafter 40k / critic 16k / position 8k chars.
- Skill gains the spec-loop section (lint before post; budgets;
  compile after rulings).

Receipts: 14 golden tests validating the compiler against the REAL
`mem-signal-001` artifacts (tracked as fixtures): round-1 draft
parses 6 items, round-3 final parses 7 with MI-5's 2-1 tag and the
dissent register, both real critiques lint clean with their
verdicts extracted, codex's four MI-1 objections link to MI-1,
compile is byte-deterministic and honors approved/declined/unruled
per item. Deferred to V2-P3 (per the phase plan): diff
materialization, scratch-worktree validation, cross-seat review.

## V2-P3 — solution materializer SHIPPED (2026-07-19)

`src/attune/roundtable/solutions.py`: member proposals stay TEXT
(R1) — full-file blocks or unified diffs; `materialize` creates a
detached scratch git worktree (never a tracked branch), validates
every path (absolute / traversal / git-internal rejected — the
critical-rules file-op gate, with a six-probe security battery),
and applies the proposal; `validate` runs named checks SERIALLY
with exact-tail `CheckReceipt`s; `diff_against_base` renders the
chair's review surface; `discard` removes worktree + registration
idempotently. TAC-4 semantics enforced structurally: a failing
candidate carries its receipts, and `Candidate.green` is False
with zero receipts — an unvalidated candidate can never read as
green. The repair round (one, counts against D3) and cross-seat
review are loop orchestration in the skill's V2-P3 section.

Receipts: 18 tests against REAL git repos/worktrees (no mocked
git) — security battery, both proposal formats, non-applying diff
fails clean with scratch cleanup, failed-with-receipts, missing
check binary = failed receipt, idempotent discard. Board client
hardening shipped alongside (#1463): bounded connect/socket
timeouts so a stale REDIS_URL fails fast in bounded time (live
chair-terminal receipt drove it).

Remaining: **V2-P4** (rotation + producing-team routines) — gated
on one more spec-authoring loop run ON the P2 compiler machinery;
and the chair's TR-6 cap number. *(Both closed 2026-07-19 — next
section.)*

## Loop #2 + P4 requirements — thread table-p4-001 (2026-07-19, chair: Patrick)

The phase gate ("one more spec-authoring loop ON the P2 compiler
machinery") was satisfied by running the loop WITH V2-P4 itself as
the subject — chair-chosen over waiving the gate. Second full loop
through the P1–P3 machinery, fixed roles (claude drafts, codex +
antigravity critique):

- **TR-6 ruled: 7** candidates per session (matches the first live
  loop's 7 REQs; requirements.md updated).
- **Loop receipts**: draft 7 REQs, `lint_draft` clean first pass;
  critiques codex 15 items (103s) + antigravity 9 items (51s),
  both `lint_critique` clean, both `needs-revision` — headline
  catches: the RR-2/RR-3 rotation-pointer self-contradiction
  (both critics independently), quorum-abort vs binding R6
  (codex), headless compile has no chair rulings so it must
  assemble an UNRULED candidate compilation (codex), lint repairs
  must not consume the D3 ceiling (antigravity), missing
  schedulable input contract (both), board TTL vs durable rotation
  ledger (codex). Final revision `lint_final` clean: 5 agreed,
  RR-3 contested, RR-5 2-1, dissent register 4 entries. Objection
  ledger linked (19 objections across 7 items). Compiled
  deterministically to
  [p4-requirements.md](p4-requirements.md) via
  `compile_requirements`.
- **Chair rulings (elicit-form, 2026-07-19)**: all seven items
  APPROVED. RR-3 quorum: **proceed + UNCRITIQUED flag** (binding
  R6 preserved; the drafter's abort alternative declined — the
  dissent survives in the register). RR-5 R5 cap:
  **max_invocations = 10 RATIFIED** (4 role invocations + 4
  repairs + 2 discovery margin; codex's pre-ratification dissent
  recorded 2-1). Producing-run cadence: **per-spec arming** (the
  chair queues a grounding pack per subject; no standing spec
  cadence).
- Board thread `table-p4-001` (TTL 7d from 2026-07-19): question +
  grounding pack, draft, both critiques, final, synthesis, chair
  ruling; promoted (item 5) to p4-requirements.md.

Baseline ledger per RR-4 (structured lines; `rotation_status`
input):

P4-BASELINE: thread=mem-signal-001 promoted=MI-1..MI-7 downstream=PR#1459
P4-BASELINE: thread=table-p4-001 promoted=RR-1..RR-7 downstream=PR#1466

Eligibility per RR-4 was met 2026-07-19 (both baselines
non-pending once #1466 merged); the chair ARMED rotation the same
day after reviewing the live dogfood receipts below:

P4-ROTATION: armed 2026-07-19

From the next producing run onward, assignment basis is
`rotation`: the drafter is `next_owed` over the durable ledger,
critics derived. Fixed roles end here.

## V2-P4 dogfood — first LIVE headless producing runs (2026-07-19)

Chair-authorized dogfood, same day #1466 merged. Subject:
pipeline-learner v1 requirements refresh (commit-or-kill input).
Two runs, both paths of the machinery exercised for real:

- **Run 1 (`producing-pipeline-learner-v1-20260719`) — honest
  failure.** The claude seat 401'd (revoked stored OAuth; no API
  key in the launching env — fix: source `~/.attune/anthropic.env`
  into the runner's env). RR-3 fallback fired live: antigravity
  substituted as drafter, `fallback` event posted, ledger recorded
  `owed=claude / actual=antigravity / served=1` (owed turn
  preserved). Antigravity's round-3 final failed `lint_final`
  (all items untagged) after its one repair → typed `LINT_DIRTY`
  terminal, zero candidates, dissent-and-failure-first digest.
  TAC-4 spirit held end-to-end: nothing laundered.
- **Run 2 (`producing-pipeline-learner-v1-20260719-2`) —
  success.** 5 of 10 invocations: claude drafted, both critics
  returned cited needs-revision critiques, final passed all lint
  gates. 8 items → 7 staged + RR-8 `deferred_over_cap` (TR-6
  respected, full text preserved); real dissent reached the
  register (RR-4 2-1 bulletin-deferral; RR-7 contested→resolved,
  registry mutation killed by both critics). R8 held: zero
  promotions by the routine.
- **Chair ruling**: all eight approved; RR-8 restaged
  chair-initiated (the RR-6 recourse path, exercised live); RR-4
  2-1 upheld. Compiled to
  `docs/specs/pipeline-learner/requirements.md`, replacing the
  falsified 2026-05-17 draft.

P4-BASELINE: thread=producing-pipeline-learner-v1-20260719-2 promoted=RR-1..RR-8 downstream=pending

## Provenance

- Chair directive and rulings: live session 2026-07-18 (the same
  session that shipped v1 P1–P3, #1451–#1455).
- Board thread `table-v2-001` (TTL 7d from 2026-07-18): question,
  three positions with R7 receipts, synthesis, ruling.

## 2026-07-20 — Design phase WAIVED (round-table thread q-producing-team-design-need-001; chair: Patrick)

The table deliberated whether this spec needs a design.md (1 round,
all seats, unanimous on the core; status split ruled with the 2-seat
majority). Board messages 2/3/4/7 promoted; ruling posted as
message 8-adjacent (see thread). Precedent: the agent-round-table
completion ruling earlier today — waiver + as-built pointer beats
retroactive design archaeology; rotation arming is operational
state, not missing architecture.

**As-built map (the design lives here):**
`src/attune/roundtable/producing.py` (headless draft→critique→final
loop; the 12-code failure taxonomy is `producing.FAILURE_CODES` —
point at the enum, never restate it), `compiler.py` (round lint
gates: draft/critique/final), `rotation.py` (ledger semantics;
FIXED roles until an explicit `P4-ROTATION: armed` chair line in
THIS file — the arming transition commits here, answering the
table's follow-up), the R5 cap `max_invocations=10`
(chair-ratified), and `tests/unit/roundtable/`
(test_producing/test_compiler/test_rotation).

**Embodied invariants (load-bearing per all three seats):**
compiler-gated rounds — lint-dirty output returns to its seat,
never the board; failure honesty — the closed taxonomy receipts
every degradation, failures and dissent BEFORE candidates, nothing
laundered green; R8 absolute — a producing run never promotes;
TR-6 — at most 7 promotable candidates, overflow held as
`deferred_over_cap` with full text preserved.

**Verification receipts:** Run 1 (`producing-<slug>-…`, LINT_DIRTY
terminal, zero candidates — the honest-failure invariant observed
live) and Run 2 (`producing-pipeline-learner-v1-20260719-2`, 7
staged + 1 deferred, real dissent in the register, chair-ruled and
compiled into pipeline-learner) — both recorded above in this file.

**Open-design register (NOT settled; resolution lands as chair
rulings in this file):** rotation arming semantics beyond the
fixed-roles default; evolving P4 items in p4-requirements.md.

**Divergence rule:** if the implementation departs structurally
from the invariants above, design REOPENS via a new dated entry
(and a real design pass if warranted) — never by silently editing
this waiver.

**Status ruling (bounded active):** requirements.md STAYS `active`.
Flip to terminal when BOTH: (a) the chair commits the
`P4-ROTATION: armed` line here, and (b) the first rotated-roles
producing run lands its receipts. Reviewed at each Monday sitting
so "active while arming" cannot become permanently open.

PHASE-WAIVED: design (2026-07-20 — waiver entry above; thread q-producing-team-design-need-001)

## 2026-07-29 — 07-19 re-run queue ruled (chair, in-session form)

The three re-runs queued by the 2026-07-22 archive ruling
(docs/reports/roundtable/producing-runs-20260719-failure-archive.md,
tracked as issue #1621) are dispositioned post-#1559-lift:

- **spec-lifecycle-gates re-run: KILLED (moot).** The spec shipped
  2026-07-21; its gates are built and live-consumed by the P2
  gate-triage inbox (#1734). Nothing left for a drafting run to
  draft.
- **pipeline-learner-v1 re-run: KILLED (superseded).** Requirements
  approved 2026-07-19 and the fixture core shipped; the salvaged
  8-item draft is superseded by ruled requirements. RR-5 (next
  unit) is gated on RR-1 corpus viability — live-checked at ruling
  time: NOT viable (334 eligible records, 21 workflows, 3 distinct
  active days). Viability comes from accumulation, not
  deliberation.
- **usage-signals-refresh re-run: DEFERRED** until the chair
  re-ratifies the north star's third leg (the usage-signal read
  was killed 2026-07-28 as circular). Any future arm needs a
  re-scoped grounding pack at a stable tracked path and fresh
  per-spec chair confirmation. Issue #1621 re-scoped to carry only
  this subject, blocked on the re-ratification.

The salvage value in the failure archive (seat drafts) remains
minable; the archive itself is unchanged.

## 2026-07-29 — usage-signals-refresh re-run KILLED (chair; follows leg-3 re-ratification)

The subject deferred earlier today is now ruled: with the
north-star leg 3 re-ratified onto cross-review dogfood evidence,
the question the usage-signals-refresh producing run would
deliberate died with its mechanism. Run KILLED; issue #1621
closed. The 07-19 re-run queue is fully dispositioned (2 killed
this morning, 1 killed here).
