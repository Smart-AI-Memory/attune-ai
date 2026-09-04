# Host Surface Parity — Decisions

## D1 — Three chair rulings at intake (2026-09-03, chair)

Recorded from the Cowork session that produced this spec. The Claude
seat proposed; the chair ruled. The options declined are recorded so
the table does not re-pitch them.

**D1a — Local models' first job is a `LOCAL` tier for low-stakes
roles.** Recall re-ranking, lesson classification, triage pre-sort,
skeptic/countersign at low stakes, fact-check probes. Seats
unchanged for now. *Declined:* a fourth round-table seat now;
"both, LOCAL first" (the chair chose the narrower ruling; a seat
remains a later, separate question).

**D1b — Extensions are the seam.** Providers, memory backends and
seats arrive through the trust-gated `attune.extensions` system
ruled in release-16-manifest D1/D2. This spec sequences behind
passenger 4 for R6 and never edits a roster tuple to add a vendor.
*Declined:* keeping roster and providers as in-tree tuples this
cycle.

**D1c — The deliverable is a spec under `docs/specs/`.** This
directory is the chair's R4 approval for these files and nothing
else; the round-table brief artifact stays the companion page.
*Declined:* a roadmap page only; both.

## D2 — `LOCAL` tier mechanics (RULED 2026-09-02, chair — routing label)

**Ruling: option (b), routing label — superseding the seat's own
recorded recommendation of (a).** Promoted from round-1 of
`q-fable-51-surface-overlap-001`, where all three seats ruled (b)
independently on the same grounds: locality is orthogonal to the
quality/cost ladder; an enum member is five coordinated edits (four
copies + the attune-rag mirror) and forces every exhaustive tier
match to handle a value most code paths must never receive; a label
(`placement: local` on the role's routing record) can express
"CHEAP, prefer local, fall back hosted", which an enum member
structurally cannot. D1a's "LOCAL tier" names the user-facing
concept, not the enum mechanics. Same-change consequences applied:
R6's tier-contract sentence and Task 8's enum-edit mechanics amended
to the label. The ops-tile "not a tier" case named as (b)'s cost is
accepted and lands with Task 8.

The superseded proposal text is kept below for provenance.

D1a names a `LOCAL` tier; the mechanics have two honest options.

- **(a) Enum member.** Add `LOCAL = "local"` below `CHEAP` in all
  four tier copies and the `attune-rag` mirror in one release, with
  `tests/unit/test_model_tiers_drift.py` as the receipt. Pricing
  zero; spend gate records tokens for volume. *Cost:* a coordinated
  attune-rag release. *Benefit:* routing, telemetry tiles and cost
  reports all understand the tier without special cases.
- **(b) Routing label.** Leave the enum alone; add a `role → target`
  table where a target is a tier or an enabled extension. *Cost:* a
  second routing vocabulary beside the tier; ops tiles need a case
  for "not a tier". *Benefit:* no cross-package release.

**Seat's recommendation: (a).** The drift guard exists precisely to
make this change safe, and a tier that ops can see is what lets a
power user be demanding about where a role runs. *(Superseded by the
ruling above — the table was unanimous for (b).)*

## D3 — No third capability contract (RULED 2026-09-02, chair — confirmed)

release-16-manifest D1 ruled exactly two capability contracts:
workflows and memory backends. A general "provider" contract — Ollama
as a model provider for every workflow — would be a third. This spec
does not propose it. Local models serve R6's roles as a
memory-backend extension (rerank) and workflow extensions (roles),
which fit the two ruled contracts and make the Ollama reranker the
first real second implementer D2 named as its falsifier.

If the chair later wants a provider-level contract, that is a
release-16-manifest amendment, not a host-surface-parity task.

**Ruling (2026-09-02, promoted from round 1, all three seats
confirming):** the deferral stands, with a recorded tripwire —
D3 reopens when a **second real implementer with code** (not a
hypothetical in a spec) fits neither ruled contract without
contortion, and that implementer sits at the table for the
reopening. Noted for 16.4: Antigravity's conditional challenge
that embedding/scoring may deserve its own `Evaluator`/`Embedding`
seam rather than bloating `memory-backend` — that is round-2 /
tripwire material, not a ruling.

## D4 — Parity gate mechanics (RULED 2026-09-02, chair — adopted as amended)

Collaboration-contract principle 1 ("the receipt beats the promise")
carries the *aspirational* label because no gate can check intent.
For surfaces the check is mechanical: a RICH renderer or host hook
either has its PORTABLE and HEADLESS twins receipted or it does not.
R2 proposes `tests/unit/gates/test_surface_parity.py` as the
enforcer for this case, and Task 1 lands it green before any new
renderer exists so it gates rather than chases.

**Ruling (2026-09-02, promoted from round 1):** adopted with three
amendments, one composed from each seat:

- an `experiments:` allowlist with a **mandatory 14–30-day expiry**,
  itself drift-guarded — the gate fails on any expired entry. A
  spike may exist untwinned; a shipped surface may not (Claude;
  Codex's "explicit, expiring parity exception" is the same rule).
- the receipt clause reads **"schema-identical validated payload"**
  with nonce/revision fields normalized — byte identity is false by
  construction for stateful surfaces (Claude H2 dissent).
- parity assertions include **interaction lifecycle** (abort,
  timeout, validation-feedback semantics), not output identity
  alone (Antigravity).

The enforcement locus (filesystem enumeration vs. declared surface
registry) is NOT ruled here — see D6.

## D5 — Round-1 promotion of `q-fable-51-surface-overlap-001` (RULED 2026-09-02, chair)

The chair ruled the reviewing session's recommended promotion triage
in full ("Proceed with Recommended items using the Recommended
promotion triage"). Basis: the committed round-1 transcript
(`docs/reports/roundtable/q-fable-51-surface-overlap-001.md`,
aac2b1013) and the reviewing session's fidelity check of the
synthesis against the seat messages. Per-item record:

- **R1 — AMEND, adopted.** The tier-0 contract constants (option
  cap, multi-question support, free-text escape, recommendation
  suffix) live in a declared **host-profile record**, with the
  Fable/Claude profile merely the first entry; a form exceeding the
  *current host's* profile falls through to PORTABLE intact.
  Contract tests cover validation errors, multi-select ordering,
  "Other", cancellation, and host capability change (Codex).
  Antigravity's grounding: its native `ask_question` takes
  multi-question forms, so hardcoding the 4-option Fable shape
  would turn one vendor's limit into the universal standard.
- **R2 — AMEND, adopted** per D4's amended ruling; locus open (D6).
- **R3 — AMEND, adopted** (the seat's bare ADOPT was overruled by
  the Codex/Antigravity convergence): generated, sentinel-bracketed
  blocks (`ATTUNE:MEMORY:START/END`) with provenance headers naming
  the regenerate command; **bounded top-K digest** (~25 entries,
  hit-frequency prioritized) — never the unbounded index;
  **per-host independent line budgets**; stale-entry cleanup and
  removal, not only regeneration; hand edits inside the block fail
  closed, edits outside stay legal. No "second master" framing: the
  Attune promoted-lesson index stays the sole authority and host
  files hold projections with provenance.
- **R4 — ADOPT as written, first among the eight.** Receipts record
  both advertised-profile and fallback cases, including stale
  revision, wrong contract hash, and replay rejection.
- **R5 — AMEND, adopted.** One **master automation definition** per
  task; the crontab line and the host task/monitor registration are
  both *generated* from it (twins that share a master cannot
  drift). Operational guards: no autonomous LLM sweeps on raw
  file-system events — deterministic triage probes or an outbox
  stage only; ≥60s debounce; hourly circuit-breaker cap; explicit
  acknowledgment before token-intensive audits; a run's own
  telemetry write must not retrigger its monitor. The fit_source
  budget-clock settlement is separately asserted.
- **R6 — ADOPT** with D2's routing-label mechanics; requirement
  text and Task 8 amended in this change.
- **R7 — AMEND, adopted.** Typed role slots validated for
  invariants (exactly one moderator-with-receipts, one plan-only
  reviewer, one code-native proposer); slots carry execution mode,
  trust boundary, required capabilities, and receipt obligations,
  not just a role name; a **golden behavior test** proves the
  default roster reproduces the current literals byte-for-byte
  (`CANONICAL_SEATS`, `SEAT_RECIPES` argv, `PLAN_ONLY_SEATS`); the
  fourth-slot-requires-enabled-extension rule is enforced **in the
  roster loader**, structurally representable but disabled until a
  chair go.
- **R8 — AMEND, adopted** (union of the Codex and Claude
  amendments): count structured asks per **terminal** outcome so
  abandoned/blocked sessions register; store **raw numerator and
  denominator**, never the ratio (outcome inflation games a ratio);
  keep asks-per-session as a secondary guard; `friction_gate` acts
  only above a minimum-outcomes floor; report zero-outcome rate and
  fallback frequency; never record answer contents; no new store.
- **R9 — ADOPT (new, the round's strongest signal).** The merged
  capability-descriptor/conformance layer all three seats
  independently proposed: a machine-readable **capability
  descriptor** per host adapter and extension; an
  `attune surfaces doctor` probe writing capability receipts; a
  generated, drift-guarded **hosts × capabilities matrix**
  (native / fallback-receipted / absent) in tree; a conformance
  suite proving deliberate degradation, semantic equivalence,
  receipt provenance and replay protection, PORTABLE + HEADLESS
  usable with any adapter removed, and no silent privileged-host
  selection. Must be **assertable in CI with no host present**
  (all-fallback column green). This is the 16.3 foundation item.
- **Noted, not adopted** (round-2 / design-input material):
  Antigravity's SARIF finding-interchange proposal and its
  worktree-lease + turn-attestation proposal (pairs with board
  msg 4); Claude's tier-provenance/Other-rate telemetry (folds into
  R1/R9 task design as the falsifier for H1's "not a rival" claim).
- **Antigravity H4 dissent — noted, not reopened.** D1a's declined
  fourth-seat option stands; seat eligibility remains a later,
  separate question. The advisory-only line holds: fact-check
  probes are advisory-labeled and hosted-model countersigned; a
  local model may raise its hand, never wave things through.
- **Round 2 — deferred.** Both member questions (msg 4: attestation
  schema for host-UI resolutions; msg 6: the single
  no-privileged-host receipt, producible in CI with no host) feed
  R9's design rather than blocking any ruling above; they reopen
  with a fresh chair go when R9 design work makes them concrete.

**Sequencing (moderator read, adopted):** 16.3 — R4 receipt first,
R9 foundation, R1 as amended, D2 label, Task 7 reranker alone.
16.4 — R3, R5, R7, R8, Phase B workflow extensions.

## D6 — R2 enforcement locus (RULED 2026-09-03, chair — hybrid, subject-local)

**Ruling: the lead's recommended hybrid** (chair picked option 1
after the calibration probe below and a UX-impact read: the locus
is CI-side with zero user-facing latency; the differences are in
what each option fails to catch). Renderer parity is asserted
against attune-forms' declared `ProjectionRenderers` registry via a
cross-package drift guard; host-hook/template parity is asserted by
filesystem enumeration in attune-ai where those artifacts live; the
D4 amendments (expiring allowlist, payload-schema receipts,
lifecycle assertions) apply to both. The counter-case's third leg —
a "no renderer escapes the registry" sweep inside attune-forms —
is accepted as part of the ruling and lands in the attune-forms
repo alongside Task 1's gate here.

The one real disagreement inside the round's shared direction:
Codex would replace filesystem enumeration with a **declared
surface registry** ("scanning is too easy to evade accidentally and
too brittle around helpers and templates"); the Claude seat kept
the enumerating gate. The synthesis notes the positions compose
(registry-driven gate + payload-schema receipts + lifecycle
assertions). Not ruled at promotion; the chair rules the locus
before Task 1 lands the gate.

### Calibration probe (2026-09-03, lead — evidence for the ruling, per the probe-before-gate lesson)

Probes run against the real tree and the installed attune-forms
0.12.2; every claim below is verified by the named probe.

1. **A filesystem enumerator in attune-ai is blind by construction,
   not merely evadable.** `grep -r 'Surface\.RICH|Surface\.PORTABLE|
   Surface\.HEADLESS' src/ plugin/` → **zero hits**; `grep -r
   'ui://' src/` → zero. Every renderer lives in the separate
   `attune-forms` distribution; attune-ai only *imports* it (10
   modules, verified). R2's proposed
   `tests/unit/gates/test_surface_parity.py` "enumerating every
   RICH-tier renderer in the tree" would find nothing and pass
   **vacuously green** — the vacuous-gate class, satisfied by the
   very blindness it should catch. This is stronger than Codex's
   stated brittleness argument.
2. **The registry half-exists.** Installed attune-forms already
   exports `ProjectionRenderers` with fields
   `rich / portable / headless / retained` — literally the
   three-twin record per surface — plus `HostCapabilities`,
   `InteractionProfile`, and the `attune_forms.conformance` types
   `ConformanceReceipt`, `ConformanceReport`, `ConformanceStatus`, and
   `ConformanceFinding` matching the R9 convergence vocabulary
   (verified by import + field inspection).
   The registry locus is wiring, not new construction.
3. **Host hooks and templates DO live in this tree** (plugin/
   hooks, `.claude/` hooks, and R5's future task templates), so
   enumeration has a real domain there — and a registry-only gate
   would miss an *unregistered* hook, which is the evasion Codex
   worried about, pointed the other way.

**Lead recommendation: hybrid, subject-local.** (a) Renderer parity
is asserted against attune-forms' declared `ProjectionRenderers`
registry — attune-ai's gate imports it and fails on any registered
surface lacking a twin or receipt (same cross-package drift-guard
pattern as the tier mirror). (b) Host-hook/template parity is
asserted by filesystem enumeration in attune-ai, where those
artifacts actually live. The D4 amendments (expiring allowlist,
payload-schema receipts, lifecycle assertions) apply to both.
**Counter-case (strongest argument against):** a hybrid is two
mechanisms to maintain, and the registry side still trusts
attune-forms to register every renderer — a sweep test *inside
attune-forms* asserting "no renderer module escapes the registry"
is the missing third leg, and it belongs to the attune-forms repo,
which this spec does not control. NOT RULED — chair's call.

## D7 — Coverage floor: 90% (RULED 2026-09-03, chair)

Changed code in this initiative carries a 90% floor, matching
shared-command-workspaces D4 — gate and renderer code is the class
that precedent was set for. The repository-wide 85% floor is
unchanged.

## D8 — 16.3 execution gos (RULED 2026-09-03, chair, via decision form)

The chair granted the go for ALL ungated 16.3 items: the R4
receipt, the R9 capability-descriptor/conformance foundation, R1
as amended (host-profile tier 0), and the D2 placement-label
wiring. Task 7 remains gated on release-16-manifest Phase A
(`attune.extensions` on disk); Phase B items are untouched. R9 and
the D2 label wiring need tasks authored in tasks.md before
execution — authoring them is covered by this go, executing each
still reports against D7's 90% floor. **Zero-spend constraint
(chair, same day): the chair has no API budget — all D8 work runs
in-session on the subscription surface or as plain code+tests;
no API-billed launch of any kind
(`ATTUNE_SESSION_SPEND_CAP_USD=0` enforces this machine-wide).

## D9 — Tier provenance adopted as R10 (RULED 2026-09-03, chair)

Promoted from D5's "noted, not adopted" list by a fresh motivation
receipt: the 2026-09-03 guard-intervention audit ("The Prose Gap",
`~/.attune/reports/guard-intervention-record-2026-09-03.md`) logged
a live instance of the exact failure R9/R10 kill — ledger entry 2:
a widget emitted to a host that does not render MCP-app content,
with the render claimed successful unverified. Every substantive
failure in that audit was a prose-layer claim no mechanical gate
could catch; the chair ruled R9 plus tier provenance **the ONE
mechanical enforcer to adopt from the audit, declining all other
new gates**.

The ruling: tier-provenance/Other-rate telemetry (Claude's round-1
proposal, previously folded into "R1/R9 task design" as a note)
becomes requirement **R10** — every validated answer carries the
surface tier that actually rendered it, derived from the response
envelope and never from the render request, with tier-0
fall-through and Other-rate surfaced through existing telemetry.
It is the falsifier for H1's "tier 0 is not a rival" claim.

Authoring the R9 and R10 task entries (tasks.md Tasks 10 and 11)
is covered by D8's go. Execution: Task 10 (R9) holds D8's 16.3
execution go; Task 11 (R10) executes only behind its own chair go.
Both report against D7's 90% floor and D8's zero-spend constraint.

## Open

- None. Every proposed decision in this spec is ruled.

Resolved 2026-09-02/03: the table was convened (round 1 complete,
promoted in D5); D2 ruled (routing label); Task 7 ships alone on
Phase A (D5); D6 ruled (hybrid, subject-local); D7 coverage floor
90%; D8 16.3 gos granted; D9 tier provenance adopted as R10.
