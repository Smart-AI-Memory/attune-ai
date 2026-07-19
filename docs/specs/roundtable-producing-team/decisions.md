# Round Table v2 — Producing Team: Decisions

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
and the chair's TR-6 cap number.

## Provenance

- Chair directive and rulings: live session 2026-07-18 (the same
  session that shipped v1 P1–P3, #1451–#1455).
- Board thread `table-v2-001` (TTL 7d from 2026-07-18): question,
  three positions with R7 receipts, synthesis, ruling.
