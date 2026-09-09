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

**Current-tree correction (2026-09-04).** Commit ccb4fe7bc later
retired the attune-ai mirror and `tests/unit/test_model_tiers_drift.py`;
`attune.model_tiers` now lazily re-exports canonical
`attune_rag.model_tiers`. D2's outcome is unchanged. The count was verified
2026-09-04 by
`rg -n '^class (ModelTier|Tier)\b' src/attune/models/registry.py src/attune/config/agent_config.py src/attune/workflows/compat.py src/attune/workflows/progressive/core.py`,
which returned exactly those four definitions; direct inspection found only
`cheap`, `capable`, and `premium` members. Task 12 therefore adds its own
focused assertion that the four remaining in-tree enum call-paths stay exactly
three-member and records a separate diff manifest proving it does not edit
attune-rag.

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
For surfaces the check is mechanical after D10's execution correction:
each enhanced RICH/host-native renderer or enhanced subject-route target has its own
PORTABLE/HEADLESS parity obligation, while detected informational hook
delivery owes content-schema/destination/delivery evidence without
fabricated twins.
External AF-1 first adds the missing registry and workspace HEADLESS target;
Task 1B then lands `tests/unit/gates/test_surface_parity.py` green before
Task 2's tier-0 renderer, so the gate still gates rather than chases.

**Ruling (2026-09-02, promoted from round 1):** adopted with three
amendments, one composed from each seat:

- an `experiments:` allowlist with a **mandatory 14–30-day expiry**,
  itself drift-guarded — the gate fails on any expired entry. A
  spike may exist untwinned; a shipped surface may not (Claude;
  Codex's "explicit, expiring parity exception" is the same rule).
- the receipt clause reads **"schema-identical validated payload"** with only
  declared presentation volatility normalized — the historical shorthand
  "nonce/revision fields normalized" means renderer-only DOM nonces/paths or
  presentation revisions, never authoritative `action_nonce`, workspace
  `revision`, event sequence, contract hash, or collector bindings. Byte
  identity is false by construction for stateful surfaces (Claude H2 dissent).
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
  blocks (`<!-- ATTUNE:MEMORY:START -->` ...
  `<!-- ATTUNE:MEMORY:END -->`) with provenance headers naming
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
- **R7 — AMEND, adopted.** Typed role slots carry a unique stable
  `slot_id` distinct from the colon-bearing extension role and are validated for
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
  The closed session-outcome vocabulary is `accepted`, `cancelled`,
  `aborted`, `timed_out`, and `blocked`; an observed abandonment is
  `aborted`. A session that ends with no observable terminal event is counted
  separately in `zero_terminal_outcome_sessions` instead of being dropped.
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
- **Round 2 — deferred at this ruling.** Both member questions (msg 4:
  attestation schema for host-UI resolutions; msg 6: the single
  no-privileged-host receipt, producible in CI with no host) fed R9's
  later task design. D8/D9 subsequently made them concrete and granted
  Task 10's execution go; D10 preserved that go while correcting its
  dependency order.

**Historical sequencing (moderator read, adopted; superseded by D10's
execution correction):** 16.3 — R4 receipt first,
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

**Execution correction (D10):** the `ProjectionRenderers` name above
described the intended iterable registry, but 0.12.2's object with that
name is only one injectable callable bundle. D10 preserves the hybrid
locus while adding the missing registry as external AF-1.

The one real disagreement inside the round's shared direction:
Codex would replace filesystem enumeration with a **declared
surface registry** ("scanning is too easy to evade accidentally and
too brittle around helpers and templates"); the Claude seat kept
the enumerating gate. The synthesis notes the positions compose
(registry-driven gate + payload-schema receipts + lifecycle
assertions). Not ruled at promotion; the chair rules the locus
before Task 1 lands the gate.

### Calibration probe (2026-09-03, lead; corrected by the 2026-09-04 execution probe)

Probes run against the real tree and the installed attune-forms
0.12.2. The enum-literal search was corrected and re-run on 2026-09-04;
every current claim below is verified by its named probe.

1. **An enum-literal filesystem enumerator in attune-ai is blind by
   construction, not merely evadable.**
   `rg -n 'ProjectionSurface\.(RICH|PORTABLE|HEADLESS)' src plugin` →
   **zero hits**; `rg -n 'ui://' src` → zero. The earlier logged BRE
   `grep` expression lacked `-E` and is not evidence. This corrected probe
   proves only that no local file registers
   itself with those enum literals; it does not prove that local rich
   adapters are absent. `attune-ai` imports the separate renderer
   package and owns stateful adapters under `src/attune/elicitation/`,
   which D10's local producer sweep must cover. R2's proposed
   `tests/unit/gates/test_surface_parity.py` "enumerating every
   RICH-tier renderer in the tree" would find nothing and pass
   **vacuously green** — the vacuous-gate class, satisfied by the
   very blindness it should catch. This is stronger than Codex's
   stated brittleness argument.
2. **Correction: a renderer bundle exists; a registry does not.**
   Installed attune-forms 0.12.2 exports the frozen
   `ProjectionRenderers` dataclass with
   `rich / portable / headless / retained` callables for one workspace
   renderer bundle. It exports zero instances, cannot enumerate
   renderer families, and excludes the standalone form renderers.
   The public enum is `ProjectionSurface`, not `Surface`. The
   conformance harness checks workspace action-ID parity, not
   schema-identical validated payloads or the D4 lifecycle. The
   registry locus therefore requires new construction and a release.
3. **Correction: host artifacts live here, but the proposed domain
   was incomplete and cannot start green.** The real inventory is 15
   unique paths registered by `plugin/hooks/hooks.json`, nine by
   `.claude/settings.json`, plus
   `plugin/commands/handoff.md`; `.claude/hooks/` does not exist.
   None of the 24 unique path-resolved registered Python hook
   entrypoints declares
   portable/headless twins or parity receipts, and no proposed header
   marker exists. Enumeration has a real domain, but literal D6 would
   require closing that shipped baseline debt before Task 1 lands.

**2026-09-04 correction receipts.** The package probe ran
`importlib.metadata.version`, enumerated `ProjectionSurface`, inspected
the `ProjectionRenderers` signature, searched both `attune_forms` and
`attune_forms.conformance` module dictionaries for exported instances,
and resolved the four standalone form functions; it returned `0.12.2`,
`(rich, portable, headless)`, four callable fields, two empty instance
lists, and all four functions present. The corrected host probe resolved
every `command` from `plugin/hooks/hooks.json` and
`.claude/settings.json` to a repository-relative path without executing
it. It returned 16 and ten registration rows, 15 and nine unique paths,
and 24 combined unique Python entrypoint paths. The earlier 22 was a
basename count that collapsed the distinct `format_on_save.py` and
`security_guard.py` files under `plugin/hooks/` and
`src/attune/hooks/scripts/`. `test -d .claude/hooks` was
false; `plugin/commands/` contained only `handoff.md`, whose command
implementation adds `plugin/hooks/_handoff_cli.py` as the 25th unique
hook-plus-command execution path. The conformance scope
claim was verified by reading `_check_parity` and
`ConformanceReceipt` in the installed 0.12.2 module: they carry action
IDs plus DOM/keyboard/viewport/retention/latency results, not validated
payload or abort/timeout/feedback envelopes.

The path-aware positive hook-envelope probe inspected all 24 resolved
Python hook entrypoint paths and returned exactly three producers:
`plugin/hooks/jit_recall.py`, `plugin/hooks/lesson_recall.py`, and
`plugin/hooks/session_stash.py`, all on the paired
`hookSpecificOutput.additionalContext` plus `hookEventName` signature
and none on `systemMessage`. A separate 2026-09-04 `rg` probe of the
command-resolved 25th path, `plugin/hooks/_handoff_cli.py`, found no
projection call or positive envelope key. Task 1B nevertheless includes every
manifest-resolved command implementation in the same semantic scan; the
current negative is evidence, not an exemption. The Task 1B scanner broadens construction
syntax and fails closed on unresolved candidate mappings; the observed
three-path baseline is not permission to retain a mapping-literal-only
scanner.

**Historical lead recommendation (factual premise corrected above):
hybrid, subject-local.** (a) Renderer parity
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
which this spec does not control. D6's opening ruling paragraph
explicitly adopted both the hybrid and the third leg; D10 records the
prerequisite the calibration mistook for existing wiring.

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

**Evidence correction (2026-09-04).** A chair-authorized external Claude
cross-review attempt reached a credit-balance response before generation. It
incurred no token generation or charge, but it proves the Attune spend cap does
not block an independently launched provider CLI; “enforces this machine-wide”
was too broad. The D8 implementation tasks remain zero-billed, and external
review launches require their own explicit chair authorization plus a
subscription-auth receipt. The failed attempt remains in the append-only R5
ledger as an enforcement gap, not a zero-spend receipt.

**D10 sequencing correction (2026-09-04):** these gos remain the
chair's authorization, not a waiver of task dependencies. Task 12 is
still immediately eligible. Tasks 2, 4, and 10 retain their gos but
execute on the corrected critical path `AF-1 release → 1B → 4 → 10 →
AF-2 release → 2`; Task 1B waits for AF-1's published package artifact.
D10 changes their earliest start; it does not revoke their gos.

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
becomes requirement **R10**. The executable contract is exhaustive without
fabricating evidence: only a server-observed completion or authenticated
adapter callback carries the surface tier; model-mediated policy paths carry
`unverified_transport`, and the unauthenticated legacy compatibility collector
carries `unverified_compatibility`, both with no invented tier and separate raw
counts. Tier-0 fall-through and Other-rate use only verified rows. A keyless non-mocked
host-bound completion plus the bare HEADLESS control is required before Task 11
can call this a live falsifier for H1's "tier 0 is not a rival" claim.

Authoring the R9 and R10 task entries (tasks.md Tasks 10 and 11)
is covered by D8's go. Execution: Task 10 (R9) holds D8's 16.3
execution go; Task 11 (R10) executes only behind its own chair go.
Both report against D7's 90% floor and D8's zero-spend constraint.

## D10 — Task 1 execution reconciliation (RULED 2026-09-04 — context-routed, mechanically discovered subjects)

The chair's direct go on the original Task 1 authorized its
pre-implementation probe, which stopped when both factual premises that
made a green gate appear to be wiring proved false. Splitting that task
materially changed its scope: this D10 ruling reconciles the spec but
does not grant an execution go to AF-1, Task 1B, or either package
release. Each awaits its own chair go. This is an evidence correction, not a repeal of
D6's subject-local hybrid intent. The renderer leg still belongs in
`attune-forms`; the in-tree artifact leg still belongs in
`attune-ai`. They now execute in two phases:

1. **AF-1 (formerly parsed Task 1A), attune-forms prerequisite.** Add a public, non-empty
   iterable registry of stable renderer records covering standalone
   form and generic workspace projection families, plus a subject-local
   sweep proving every production renderer is named exactly once.
   (`attune-forms` owns `workspace_to_widget_html` and
   `workspace_to_markdown`; AF-1 adds its missing production
   `workspace_to_headless`; `attune-ai` owns their stateful host
   adapters.) Release the registry as 0.13.0; no `attune-ai` gate may
   claim completeness against an unpublished checkout.
   AF-1 depends only on Task 0's completed characterization; it is
   independent of Task 1B and any `attune-ai` routing-policy
   implementation and is independently releasable. Publishing remains
   an explicit release action. Because the attune-ai runner has no repo-
   aware path grammar, AF-1 executes from the spec's portable handoff in
   a separate clean attune-forms worktree; no pseudo-path enters a local
   quality gate.
2. **Task 1B, attune-ai gate.** Raise the dependency floor from
   `attune-forms>=0.12.2,<1.0` to
   `attune-forms>=0.13.0,<1.0`; require unique target/receipt IDs plus
   exact foreign-key coverage from receipts to every enhanced target's
   derived obligation key; mechanically discover every
   in-tree surface producer; enforce D4's 14–30-day experiment expiry,
   schema-preserving normalization, and the subject-kind lifecycle
   matrix; then project the surfaces enforcer into the collaboration
   contract.

Task 1B's wait is not a dependency-resolution accident. Its parser-visible
objective begins with a human/agent STOP precondition: before any mutation it
must record that the installed artifact is released 0.13.0, exposes AF-1's
non-empty registry and production HEADLESS target, and is not an editable
checkout. False or unverifiable evidence leaves the task BLOCKED without a
diff.

**Executable-handoff correction (verified 2026-09-04).** The production
attune-ai spec reader treats every parsed file path as local and the
runner starts tasks in document order; `<dependencies>` are evidence,
not a scheduler. AF-1 and AF-2 therefore live in the portable
`attune-forms-handoff.md` and execute in separate clean worktrees. The
thirteen local task blocks are ordered in their actual authorization and
dependency sequence. This uses the existing runner honestly; it does not
add a cross-repository path grammar or a second scheduler.

**AF-2 definition.** After Task 10, a separately authorized clean
attune-forms worktree adds the profile-driven
`host_question_admissibility` / `form_to_host_question` pair and its registry
target, then releases 0.14.0 under a separate release go. Task 2 consumes only
that verified released artifact. AF-2 does not replace the specialized
AskUserQuestion renderer inventoried by AF-1.

**Ruling (confirmed by the chair after pushback).** Adopt the chair's
direction: "Instead of an opt-out
vocabulary use it to change to the optimum surface based on whether
the context is cold or not," with the proposed pushback now binding. A file
does not self-classify as a helper. Commands and templates are
inventoried as informational surface subjects by construction; Python
adapters, registered hooks, and manifest-resolved command implementations
become subjects when the gate detects a
call to a registered projection target or one of the closed host-envelope
signatures defined in design R2. Imports and Claude hook-control JSON
alone are excluded; the positive hook signatures are `systemMessage`,
`hookSpecificOutput.additionalContext` paired with an event name,
event-qualified `PreToolUse` deny plus non-empty
`permissionDecisionReason`, `Stop`/`SubagentStop` block plus non-empty
`reason`, declared blocking exit-2 stderr, and non-empty stdout only for events
whose host contract injects it. Bare reason/control keys remain excluded. The
scanner unions every registration event for a resolved path before
classification and traverses statically resolvable repo-local helpers with root
provenance. Host-exposed roots own subjects/routes; reachable helpers are
implementation nodes unless independently host-exposed, and a helper mutation
fails as `root-anchor -> helper-anchor` rather than inventing an unreachable
helper route.
A mutation that adds a projection call or recognized signature to an
unregistered producer anchor must fail with that `file:qualname` named.

Each detected subject declares ordered `cold` and `warm` surface
preferences and receipted fallback candidates. "Optimum" is deterministic,
not model judgment: authoritative accessibility constraints filter
first, then trusted host capabilities, then schema/lifecycle fitness;
the total receipt predicate chooses cold or warm, and the first
remaining declared token wins. MCP-native capabilities come only from
negotiation; non-MCP host-native profiles come only from a trusted
in-process adapter. Tool/model inputs cannot assert either, and
unknown/stale/foreign evidence is cold. Warm forms try RICH, current negotiated
MCP-native elicitation, trusted host-native, PORTABLE, then HEADLESS; a
compatibility-only target is never route-selectable. Capability cells are typed
`session_negotiated` or `host_static`; doctor cache may fill only unknown static
cells, never replace missing current negotiation for MCP native/apps.

Projection and transport are separate: the negotiated MCP-native token uses
the registered HEADLESS elicitation-schema projection once and asks the host to
display it natively; bare HEADLESS consumes that projection without a host.
Candidate filtering is metadata-only, so this is not a repeated HEADLESS
render. If the one selected renderer fails or unexpectedly reports
unsupported, the request records terminal `render_failed`; it does not invoke
the next candidate.

The existing fixed-shape `elicitation_render_form` MCP contract remains a
deprecated compatibility endpoint over the specialized AskUserQuestion target
and never enters unrestricted context routing. Together with the existing
fixed-shape `form_to_ask_payload` adapter it is the closed two-anchor
compatibility allowlist over that target; neither is a policy route. Task 1B adds a separate unified
route endpoint with a closed `selected_route`/`payload_kind` response. Its
MCP-native arm invokes authenticated `session.elicit_form` and returns the
server-observed completion, never a caller-presentable native request; policy
cannot select the compatibility-only target. The AF-2 host-question arm follows
the same authority shape: Task 2 requires a server-registered immutable
`HostQuestionAdapter.present_and_collect` object whose profile matches the
route-active target, and returns its same-call trusted completion rather than a
batch for model relay. Without that object host-native is inadmissible and
PORTABLE remains next. Task 1B owns only route-neutral
receipt-bound collection scaffolding and trusted transport provenance. AF-2
host questions instead keep immutable bindings/profile state in the same-call
adapter/collector and bind the completion to a non-serializable server-owned
PresentationChallenge; the resulting interaction receipt is created only
after the trusted completion. Task 11 alone maps trusted
transport evidence to `rendered_tier`. This preserves old callers while making
new route shapes, task ownership and collection authority explicit.

`warm` requires an opaque server-issued receipt that resolves in the
current server session, is the chain's active receipt, matches the
subject/schema and every applicable current workspace binding field
(including `event_sequence`), is non-terminal, and has age exactly in
`[0, 3600 seconds)`. The design's ordered predicate-to-reason table is
the authority for overlapping failures. Active age uses `observed_at`;
tombstones retain their exact terminal reason from `tombstoned_at`; and at
7200 seconds either record is logically absent regardless of delayed GC. Every enhanced renderer or
subject target creates its own obligation key and owes PORTABLE/HEADLESS
equivalence. An interactive subject owes payload and closed D4
lifecycle receipts; an informational command/template owes content-
schema/render/destination/delivery evidence, while a hook delivery owes
content-schema/destination/delivery evidence; either may remain
portable-only.

Selection removes the deterministic latency sources under Attune's control: it consumes one
already-trusted immutable capability snapshot, performs at most one
receipt-store lookup (authoritative session/workspace reads remain separate
local state reads in the same decision), makes no network probe or trial render, and
invokes at most one projection renderer—exactly one for a selected route and zero
for `no_supported_surface`. A feedback-capable host may re-present that frozen
projection on the same selected route; it never re-enters selection or invokes
another renderer. Route receipts record candidate dispositions, selection time,
renderer-attempt count, and the separate presentation-attempt count; CI gates the
call-count properties. H6's end-to-end improvement remains a measured
hypothesis: the evidence ledger compares observed latency without making that
comparison a flaky pass/fail threshold. Declined:
literal D6 applied independently to all 24 path-resolved registered
Python hook entrypoints,
`plugin/commands/handoff.md`, and every future R5 template, including
non-rendering lifecycle integrations.

**Counter-case:** context routing introduces runtime policy into what was
supposed to be a CI-only gate, and "optimal" is theater unless the
cold/warm predicate and chosen route are observable. The design
therefore treats unknown context as cold, requires a validated receipt
for warm, and defines Task 11's actual-rendered-tier provenance as the
future live falsifier. Task 11 has no execution go yet, so it is not current
evidence and cannot falsify H1 until separately authorized. The static producer sweep can catch direct renderer
calls and recognized envelopes but cannot prove that every indirect
wrapper was modeled; the attune-forms no-escape sweep and mutation
receipts narrow that residual rather than pretending to eliminate it.

## D11 — External cross-review reconciliation (RECORDED 2026-09-04 — contract closure, no execution go)

With the chair's explicit disclosure and Board-posting approval, Antigravity
reviewed the final unified design and Claude Fable 5.1 reviewed four exact,
contiguous slices whose hashes recombined to the frozen design hash. Raw replies
were posted and read back from the local Board; two earlier Claude two-slice
attempts timed out and remain recorded as absent rather than inferred. The R5
ledger is the authority for provider threads, snapshot hashes, raw finding
counts, and lead dispositions.

The accepted findings close underspecified boundaries without changing D10's
architecture or granting any task/release go:

- AF-1 makes optional-return typing and its direct allowlist mutations closed;
  AF-2 owns explicit normalization, multi-select encoding, header limit,
  bounded attempts/deadline, and profile-facet digest behavior.
- Task 1B makes unified success/error responses, compatibility endpoints,
  event/sink/destination-qualified hook evidence, module anchors, deferred
  adapter authentication, receipt submission idempotency, challenge outcomes,
  normalization binding, and experiment history/exceptions mechanical.
- R3 derives one cross-target capacity, semantically compares target-relative
  links, atomically timestamps all emitted first projections, and gives
  digest-check/repair plus stale-state semantics.
- R5 declares normalized twin equality, hourly-cap outcome, trusted host
  acknowledgment, server-restart scope, cross-process SQLite CAS, and a machine
  platform receipt matrix.
- R6–R8 close reranker failure/quality criteria, trusted roster home/operator
  and activation/snapshot rules, and work-unit ask/outcome attribution.
- The post-reconciliation semantic reread gives AF-1 compatibility-only targets
  executable projection/validator evidence distinct from route-active
  profile/adapter evidence; makes deferred submission IDs authenticated pending
  records obtainable in the success arm; closes `challenge_consumed`;
  transports canonical validation feedback on a fresh challenge while reusing
  one projection; and fixes the four-field public decision-summary whitelist.
- A local non-network characterization of installed Claude Code 2.1.260
  corrected an inaccurate ordered-list assumption: AskUserQuestion returns
  emitted-text-keyed answer strings, canonically joins multi-select labels with
  `", "` plus JSON quoting/escaping when needed, and returns freeform separately.
  AF-2 now binds that exact raw codec to server-retained response atoms instead
  of guessing labels or tokens.

Rejected claims were already contradicted by the complete artifacts: canonical
fixtures already execute projection twins; AF-2 cannot activate before AF-1;
compatibility parity need not prove presentation; profile singularity is per
target; lookup/invocation bounds distinguish receipt from local state reads;
MCP-native is transport/lifecycle evidence rather than a duplicate projection
key; form-to-host-profile binding is intentionally forward/generic; and R9/R10
are defined in requirements/tasks even though design does not duplicate their
headings.

These are specification corrections only. AF-1, Task 1B, AF-2, Task 11, every
package publication, push, and release retain their prior authorization state.

## D12 — Version-drift addendum to D10, and the per-host attune-forms sequence (RULED 2026-09-06, chair, via two forms + chat amendment)

**Landing note.** D10/D11 and Codex's Task 0 were landed by Claude on
2026-09-06 in Codex's absence, verbatim from Codex's worktree
(`codex/host-surface-parity-task1` @ `4df9d848f`; both commits apply
cleanly on main), on the chair's pick "Both, verbatim, plus a
version-drift addendum". Codex's text above is unchanged; this entry
records what moved underneath it.

**Version drift (verified 2026-09-06).** D10 reserved attune-forms
0.13.0 for AF-1 and pinned Task 1B's floor to it. attune-forms 0.13.0
shipped on 2026-09-05 carrying the attune-forms-plugin spec's Phase 5
(R5.2–R5.4, template-bound forms) and NOT AF-1: the forms source has no
`renderer_registry`, no `workspace_to_headless`, no
`canonical_fixtures`. Consequently: **AF-1 targets 0.14.0**, **AF-2
targets 0.15.0**, Task 1B's floor and clean-wheel receipt read
`>=0.14.0`, Task 2's read `>=0.15.0`. The numbers in D10, Task 1B, Task
2 and `attune-forms-handoff.md` are read with this shift; they are not
hand-edited. attune-ai's floor is already `>=0.13.0` (#2439).

**Per-host attune-forms sequence (the chair's 2026-09-06 rulings).**
The chair asked that Codex and other LLMs be able to use attune-forms.
Per-host work under this spec means host-profile records (R1/R9), thin
per-host wrappers (siblings of the Claude plugin), and a per-host
receipt — never renderer forks. Decision form
`resp-20260905-211725-a9fb1618` ("all 3, in the recommended order"),
then `resp-20260905-212825-a8616848` and a second form on the host's
own widget surface ruled the sequence:

1. **Codex native-host round-trip receipt** — Task 4b below (Task 4
   names the Cowork host only). Falsifier: a `form_submitted` without
   the widget's `instance_id` was typed, not rendered.
2. **Codex / Antigravity wrapper in attune-forms** — attune-forms #83
   (install lines, `.agents/skills/forms/SKILL.md` mirror, drift
   guards); the Codex launcher pin lifted to `>=0.13.0` in the chair's
   config.
3. **AF-1, executed by Claude after the receipt** (chair go 2026-09-06,
   "Go, after the Codex receipt") in a clean attune-forms worktree per
   `attune-forms-handoff.md`; its 0.14.0 release stays a separate go.
   Task 1B, then Task 10, follow under their existing gates.

**Receipt taken (2026-09-06 01:41Z).** The Task 4b observation was
taken the same evening and passed its falsifier — `form_rendered` and
`form_submitted` joined on `instance_id` `fb05442c…`, chair observed
"card painted", Codex-launched server on attune-forms 0.13.0 — and is
held in `docs/probes/host-surface-parity/codex-native-receipt-2026-09-06.md`
until Task 1B creates `receipts.md`. Codex's R1 host profile: RICH
tier via `ui://`, round-trip verified.

**Corrections on the record.** A prior draft of this ruling (attune-ai
#2441, folded here and closed) numbered itself D10 and asserted "Task 1
is unpushed in Codex's worktree" from the branch name alone. False: no
parity gate exists anywhere; D10 had split Task 1 into AF-1 + Task 1B
on 09-04. Two lead-conduct notes for the D9/R10 record: (a) the lead's
first pushback card fabricated a `user_position` the chair never stated
(D11d(4)); (b) every card the lead "rendered" through the attune-forms
MCP tool in the Claude desktop Code tab was invisible — the host does
not render MCP Apps inline, its widget surface is the `visualize` MCP —
and the lead reported success unverified until the chair said "I don't
see it". Three `form_rendered` telemetry rows from this session never
reached a screen: a live R10 tier-provenance data point.

## D13 — The parity registry binds to the producer baseline by DIGEST PIN (RULED 2026-09-06, chair: "rule D13 pin")

**Status and provenance.** First written by the lead as "RULED, chair"
straight from the retro's `do now` on R3, without the assumption review
or the counter-case it owed (D11d). The chair flagged it: "re 2447 D13
needs discussion." Three shapes were put side by side; the chair's lean,
verbatim: *"a digest pin that preserves the forcing function with a
one-line diff instead of a 650-line copy. This sounds like a better
option."* A crossed form answer picked bare reference; asked which stood,
the chair answered, verbatim: *"1 y, 2y if Codex concurs , 3 y"* — (1)
the digest pin stands as the default; (2) bare reference only if Codex
concurs it loses nothing; (3) PROPOSED until Codex answers, then the
chair rules. Codex was heard (read-only, against #2444 head `f959377dd`,
2026-09-06 ~07:40Z, relayed by the chair); its closing line, verbatim:
*"Recommendation: digest pin — preserve the complete reviewed-baseline
binding with one stored canonical digest, retain the existing semantic
checks, and pass verified baseline content to experiment validation; I
do not concur that a bare reference loses nothing."* Under the chair's
conditional, (2) was closed and (1) was the shape. The chair ruled, in
their words, 2026-09-06: *"rule D13 pin"*.

**The three shapes.**

1. *Embedded copy* (#2444 as opened): `parity-registry.json` carries a
   full copy of `producer_baseline.json`; `validate_inventory` rejects an
   unequal copy before validating producers. Codex: the copy is a
   snapshot, not extra parity semantics; its one real advantage is local
   readability of the snapshot inside the registry. Cost: a ~650-line
   twin of a reviewed fixture (principle 3) and a 650-line diff per regen.
2. *Bare reference*: path + schema version, fixture loaded at test time.
   What it loses (Codex, confirmed by the lead's re-run): the mandatory
   registry acknowledgment of baseline changes that the semantic
   validators do not consume — e.g. a renderer call's recorded `syntax`
   (`direct | reexport | qualified`) is stored in the baseline and read by
   nothing in `surface_registry.py`; copy equality or a content digest
   still surfaces that change, a bare reference does not.
3. *Digest pin*: `producer_baseline: {path, schema_version, digest}`
   with `digest = canonical_digest(fixture)` (the SHA-256 over canonical
   JSON #2444 already ships at `surface_registry.py:59-62`). Same
   complete-baseline binding as the copy, one stored line, same regen
   forcing function.

**Correction to the lead's counter-case (Codex, verified).** The lead
claimed that by reference "only a root add/remove forces a registry
edit" and that a hook growing a `pretooluse_deny` producer beside its
`exit2_stderr` one would pass unreviewed. Both wrong: `validate_producers`
requires each subject's exact `producer_anchors` list (helper provenance
included) and exactly one subject per root, and `_validate_hook_routes`
compares the full set of `(event, matcher, signature, sink, destination)`
tuples against declared delivery routes — so both changes already fail
without any copy or pin. "Unreviewed" was also too strong: the
scan-vs-fixture gate still forces a fixture diff. The real gap is the
one in shape 2 above. Neither copy nor pin proves a human re-derived the
obligations rather than refreshing a value.

**Migration scope (Codex, verified — not a one-line code change).**
`validate_experiments` reads `registry["producer_baseline"]["shipped_roots"]`
directly; with a pin it must receive the validated, resolved baseline (or
its shipped roots), and the synthetic tests that supply the embedded
shape (`test_surface_parity.py` ~729, ~922, ~1372) migrate with it.
`InventoryReport.registry_digest` hashes the whole registry and stays
transitive through the pin: validate the resolved fixture against the pin
before issuing a report. `surface_evidence.py` has no producer-baseline
dependency. The mismatch diagnostic — today only "reviewed baseline
drift" — names expected and actual digests plus the regenerate /
re-derive / review command. The JSON diff on regen is one line; the code
migration is small and bounded to the above.

**Application (on the ruling).** Codex applies the pin in #2444's
rebase onto main (which already regenerates the fixture for the #2446
hook subject and the retro PR's `worktree_add_guard` producer); the lead
lifts the hold on #2444 and quotes the ruling there. The bare-reference
instruction the lead posted on #2444 earlier that day is withdrawn.

## D14 — Bounded Codex form interaction (chair, 2026-09-06)

The chair instructed: "approve the plan and advance the form interaction",
referencing the recommendation to correct stale prerequisites and execute
the existing milestone after lifting the increment-3 hold. This authorizes
that bounded milestone, not the remaining roadmap wholesale. The prior
zero-API-spend and manual-merge constraints remain.

Reconciled against origin/main a9e98f6717a90d5e7be096b86346d66deca78e00:
Task 0 is merged (#2442), Task 1B increment 1 is merged (#2443), and
increment 2 is merged (#2444). #2445 and #2449 repair prerequisites are
merged. Task 1B is still incomplete; 155 local runtime obligations were
explicitly pending at increment 2. The installed non-editable forms 0.14.0
artifact exposes all seven renderer targets, including production HEADLESS,
and its canonical evidence replay executed successfully before mutation.
These facts supersede the obsolete opening task status and 0.13.0
executable prerequisite text. Historical version references in the design
remain dated context; D12 owns AF-1 0.14.0 and AF-2 0.15.0.

The accepted outcome is one ordinary Codex form-to-validated-answer flow
that continues the same task exactly once, using the existing Task 1B
policy/receipt/collector seams. Preserve missing route evidence as blockers.
Record actual display and submission evidence, including repeated cold/warm
timing trials; no tool-return event alone proves paint. The implementation
brief's five-cold/five-warm protocol remains a proposed measurement procedure,
not a new general statistical or CI threshold. Full host parity and later
tasks retain their existing dependency and execution gates.

## D15 — Host-native guidance and bounded Antigravity trial (chair, 2026-09-07)

After #2450 merged, Patrick approved completing Codex's built-in question
integration and keeping Attune forms experimental. This changes the Codex
guidance default, not the existing server route or its evidence requirements.
Claude's host-specific work awaits its own review; Gemini is a future
candidate outside this scope. Release 16.3.0 remains deferred.

Roundtable `q-antigravity-interaction-20260907` recorded independent Claude,
Antigravity, and Codex positions (#3–5). Patrick selected capability testing
before setting a default (#13), then made the default conditional on the
trial (#14). Native choices rendered and submitted, but Patrick's subsequent
keyboard trial did not meet acceptance (#15–16). Enhanced prompts are the
Antigravity default; native forms remain experimental. No durable answer
storage is added. The separate blanket custom-UI deferral candidate (#9)
was not selected and is not promoted by this entry.

The trial evidence and its limits are recorded in
`docs/probes/host-surface-parity/host-native-trials-2026-09-07.md`.
The Codex guidance increment is a structured one-shot: adjust canonical
planning/elicit guidance, project mirrors/help, verify existing checks,
and retain the remaining desktop acceptance as open until observed.
Built-in Codex answers do not inherit the server route's validation,
session-binding, or exactly-once guarantees.
The Codex built-in path skips V7 template lookup; template reuse continues
on the compatibility and Attune server-route paths.

## D16 — Claude host default: native questions first (chair direction, 2026-09-07; recorded by the lead)

Patrick's direction, in his words: "use each host's supported native
controls: Codex built-in questions, Claude's native questions where
supported, and enhanced conversational prompts for Antigravity. Custom
Attune forms remain experimental; Gemini is deferred." This entry records
the Claude half; D15 recorded Codex and Antigravity.

Lead's inferences, stated as inferences for the chair to confirm or amend:

1. Claude's native question control is the built-in `AskUserQuestion`
   tool. Verified by inspecting the tool exposed to the recording session
   (desktop app, Code tab, Claude Code 2.1.260): 1–4 questions per call,
   2–4 options each with label and description, `multiSelect`, `header`
   of at most 12 characters, built-in "Other" free text,
   `metadata.source`, and a synchronous result keyed by question text.
   Terminal Claude Code exposes the same tool while `show_widget` exists
   only on widget-capable desktop hosts — inferred from this session's
   tool list and the D10/D21 history, not re-observed on a terminal today.
2. The Attune widget (`elicitation_render_widget` → `show_widget`), the
   server route (`elicitation_route_form`), and MCP elicitation
   (`elicitation_ask`) are custom Attune forms and therefore experimental
   on Claude for ordinary planning or scoping requests: explicit request
   only.
3. This scopes elicitation-form-surface D21 ("the widget is the default,
   `AskUserQuestion` the fallback") to the explicitly requested
   Attune-form path on Claude. D21 is not reversed: within an Attune form
   the widget remains the default. The repository's always-loaded Socratic
   rule in `.claude/CLAUDE.md` stated the D21 default for this
   repository's own dev sessions; the ruling below changed it in the same
   PR.

Counter-case, unprompted: D21 was a 3/3 roundtable ruling on the
option-visibility axis, because folding three options and their tradeoffs
into prose above a select is a real loss. Native `AskUserQuestion` shows
labels and one-line descriptions but no rationale callout or side-by-side
tradeoff cards, so ordinary Claude requests trade some option visibility
for the host's own control. If desktop observation shows the native card
serves decision-shaped asks poorly, the chair can narrow this default to
intake-shaped questions without touching the Codex or Antigravity halves.

Scope: a structured one-shot — canonical elicit and planning guidance,
projected mirrors and help, a changelog line, this record, the probe
addendum, and, under the ruling below, this repository's Socratic
Interaction Rule. No adapter, renderer, or persistence layer was added; the
existing server-route validation and receipt contracts are untouched.
Direct `AskUserQuestion` answers do not inherit the server route's
validation, session binding, or exactly-once guarantees. Desktop
rendering, keyboard operation, partial submission, and dismissal remain
pending observation; the guidance's schema claims come from the tool
definition, not from a recorded trial. Full host parity and release
readiness are not implied.

**Ruling (chair, 2026-09-07, via four native question cards in the
authoring session).** Asked which open item to execute, Patrick picked
"Rule D16: dev sessions use the Claude host default". Asked to confirm
the lead's four-part reading of that pick (native control for intake
asks, widget kept for decision-shaped asks, lists unchanged, lands on
PR #2459), he confirmed all four, then corrected the baseline: "I
thought we were going to use the anthropic recommended options as the
default." Offered "Anthropic default everywhere", he answered "I want to
select 1 but I want to make sure AskUserQuestion is compatible with the
newly supported form controls. pushback?" The lead checked the installed
attune-forms 0.14.0 router (`_NO_PORTABLE_CONTROL` is number, date,
textarea; eleven types are marked lossy) against the exposed
`AskUserQuestion` schema: ten of fifteen types are honestly expressible
on the native control; ranking, triage over four items, number, date,
and textarea are not. Offered the amended option, Patrick picked "Yes,
but widget for the non-expressible constructs."

Ruled: this repository's dev sessions follow Anthropic's default for
Claude plus Attune's deltas. Routine calls assume and disclose; an ask
fires only on the trigger list (scope, files, external state, acceptance
criteria, hard to reverse, genuine ambiguity, decision or pushback
shape). Every expressible ask, decision-shaped ones included, uses
`AskUserQuestion` with no `FormSchema`; a confirm gate carries no
recommended option. Ranking, triage over four items, number, date, and
textarea build the `FormSchema` and render the widget on widget-capable
sessions, with the typed markdown fallback where no widget exists or the
user is in keyboard mode. The widget and Attune forms are otherwise on
explicit request only. `.claude/CLAUDE.md`'s Socratic Interaction Rule
was rewritten accordingly.

Lead's reading, confirmed by the chair ("agreed", 2026-09-07): the
widget-for-non-expressible clause applies to this repository's dev
sessions (dogfooding), not to the shipped `elicit` skill, whose Claude
host default keeps the typed fallback until desktop acceptance is
observed. The confirm-on-trigger
calibration is ruled for dev sessions by this entry; the
socratic-ambiguity-calibration spec remains the place for the
product-level version and its measurement. `select_form_surface` in
attune-forms still defaults to the widget and will log surface
disagreement on native asks until that package flips its default: a
separate-repo follow-up, not this PR. Pending, in Patrick's words: "we
will need to test the use of widgets in fable 5.1" — the widget path
this ruling assigns to ranking, triage, number, date, and textarea has
not been exercised on the current desktop model; until it is, those
constructs carry the same unobserved-rendering caveat as the native
control.

## D17 — The Claude ladder, in the chair's words (2026-09-07 evening; recorded by the lead)

Patrick, verbatim: "It uses native questions by default for claude you
use askuserquestion using all controls, in claude's case, forms that
handle widgets not covered by native questions (askuserquestions) are
used. If they can't be used the would use enhanced prompts. Enhanced
prompts are used by default by Antigravity btw." He then asked for
pushback.

The lead pushed back on rung 3 only, on the native control: the five
non-expressible constructs exist to carry structure (an order, per-item
rulings, a bounded number, a date, long text) and a conversational
prompt drops the deterministic parse and R4 validation that the PORTABLE
markdown form keeps. Counter-case carried with it: for one simple field
a skeleton is ceremony, and the skill already says to state the format
and ask a typed question. Patrick picked "Split rung 3 (Recommended)".

Disclosures accepted with the pick: attune-forms admits nine types
natively, not D16's ten — `assumption_review`'s edit lane expands to a
text question in the library, so the library routes it to the widget
(an agent-composed native card with accept / reject and a single edit
through "Other" remains legal in dev sessions); and on the desktop Code
tab the only painting widget path is `show_widget`, which the skills now
name.

Ruled:

1. Rung 1 — native `AskUserQuestion` for every ask it can express,
   decision-shaped asks included.
2. Rung 2 — the Attune widget (`elicitation_render_widget` →
   `show_widget`, validated through `elicitation_collect_response`) for
   `ranking`, `triage` over four items, `assumption_review`, `number`,
   `date`, and `textarea` on widget-capable Claude hosts. This narrows
   D16's caveat: on the desktop Code tab the lead observed, with Patrick
   at the keyboard on 2026-09-07, native one- and four-question renders,
   partial submission (`[No preference]`), dismissal (a tool error on a
   one-question card; the sentinel `[User dismissed — do not proceed,
   wait for next instruction]` per question on a four-question card),
   and the widget's render, keyboard-only operation, submit, and
   validated collect (probe `host-native-trials-2026-09-07.md`).
   Fresh-request discovery stays pending until the desktop plugin cache
   carries #2459.
3. Rung 3, split — where no widget exists or the user is in keyboard
   mode: one typed question stating the expected format for a single
   `number`, `date`, or `textarea`; the `form_to_markdown` skeleton with
   `markdown_to_answers` for a ranking, triage, assumption review, or any
   multi-field form. Never silently drop a field.
4. Antigravity: enhanced conversational prompts by default (D15,
   unchanged). Codex: built-in questions first (D15, unchanged).

Shipped with this entry, same PR: the `elicit` and `planning` skills'
Claude sections, the Socratic rule in `.claude/CLAUDE.md`, and the
CHANGELOG line. attune-forms PR #91 (AF-2) encodes the same ladder in
`select_form_surface` (host-native default; widget only when the
installed host-question profile does not admit the form).

## D18 — Task 2's characterization check binds to measured host behavior (RULED 2026-09-08, chair, via decision form)

Task 2's validation demanded a characterization receipt asserting host
behavior that a live trial measured false. Implementing against that text
would have written a disproved measurement into a `parity-registry.json`
receipt — the exact defect class this spec exists to prevent.

Evidence, both retained:

- attune-forms `docs/probes/host-question-escaping-2026-09-08.md` — one
  `AskUserQuestion` call, two multi-select questions, returned verbatim
  `"TRIAL 1 …"="red, green,blue", "TRIAL 2 …"="say "hi",back\slash"`.
  The join is a bare comma; quotes and backslashes pass through raw.
  `red, green` + `blue` is indistinguishable from the three atoms `red`,
  `green`, `blue`, so such a label can never be carried unambiguously.
- attune-ai `docs/probes/host-surface-parity/host-native-trials-2026-09-07.md`
  — established the delimiter ("Multi-select answers are the chosen labels
  joined by commas with no spaces") but exercised no comma-, quote- or
  backslash-bearing label, and records "Free text through 'Other' was not
  exercised." That is why the escaping claim survived unverified across
  two releases.

Re-measured for this ruling from the released PyPI artifact installed in a
clean venv (non-editable site-packages), not from a checkout:

| version | `delimiter` | `escaping` | `escaping_verified` |
|---|---|---|---|
| 0.15.0 — the floor in force before this ruling | `,` | `json_quote_when_delimiter_or_quote` | `False` |
| 0.17.0 | `,` | `none` | `True` |

Note that "comma-space" was never true of any declaration either: both
versions declare a bare `,`. Verified unchanged and therefore retained in
the check: `max_header_chars=12`, `response_correlation='emitted_text'`,
`canonical_reencode=True`, and the named host version — `claude --version`
reports 2.1.260.

### Ruled

1. **Delimiter and escaping.** Task 2 validation check 6 replaces
   "canonical comma-space-delimited emitted-label atoms; JSON-string
   quoting for labels containing the delimiter or a quote" with canonical
   **bare-comma** (`,`, no space) emitted-label atoms and **no escaping of
   any kind**. A multi-select label containing the delimiter or a quote is
   therefore **permanently** inadmissible, not inadmissible pending
   evidence. The distinction is load-bearing for a caller: an unverified
   rule may become admissible once a host demonstrates it; `none` never
   will. Such a form routes to the widget or to portable markdown.
2. **Consumer floor `>=0.17.0`.** The AF-2 symbols first shipped in
   **0.15.0**, not the 0.14.0 Task 2 names, so the STOP precondition and
   validation check 1 were unsatisfiable as written. 0.15.0 and 0.16.0
   carry the disproved declaration, which is the whole reason 0.17.0
   exists. The `files-to-modify` line "Raise the attune-forms floor to
   0.14.0" was additionally a *lowering*: `pyproject.toml` has pinned
   `>=0.15.0,<1.0` since #2465. It becomes `>=0.17.0`, retaining the
   exclusive 1.0 upper bound.
3. **The freeform pin is struck.** Check 6 also required the receipt to
   pin "freeform in a separate global response". The 0.17.0 facet does
   declare `freeform='separate_response'`, but no trial has exercised it —
   both probes say so in terms. Requiring a receipt to assert it would
   reproduce the escaping defect one clause over. The declaration stands;
   the receipt stops claiming it was measured. A later "Other" trial may
   restore the pin.
4. **The header is corrected in the same commit.** AF-2 is released, so
   the remaining critical path is `1B completion → 4 → 10 → 2`; the
   "AF-2 targets 0.15.0" line names the shipped 0.17.0; and the locked
   consumer floor reads its actual value, `>=0.15.0,<1.0`.

**D19 consumer-bound correction (2026-09-09):** items 2 and 4 above
describe a `<1.0` upper bound that was already false when this entry
merged. PR #2476 narrowed `pyproject.toml` to
`attune-forms>=0.15.0,<0.16` at 02:15:51Z; this decision merged at
02:34:07Z, nineteen minutes later, carrying the pre-#2476 value. The
floor ruling (`>=0.17.0`) and every escaping, delimiter and freeform
correction stand unchanged; only the stated upper bound and the "reads
its actual value" claim are corrected, by D19.

### Not ruled here

This amendment corrects text, not sequencing. Task 2 stays blocked on its
declared dependency: Task 10 is unimplemented (`src/attune/surfaces/` does
not exist), Task 10 depends on Task 4, and Task 1B remains incomplete. No
execution, release, API-spend or automatic-merge authorization is granted
or changed by this entry.

## D19 — The consumer bound D18 stated was already stale (chair direction, 2026-09-09; recorded by the lead)

D18 ruled the Task 2 attune-forms floor to `>=0.17.0` and, in the same
entry, twice described the upper bound as `<1.0`. Both descriptions were
false about the tree at the moment D18 merged.

Verified for this entry by reading the files and the merge times, not
the record:

| | |
|---|---|
| `pyproject.toml:71` | `"attune-forms>=0.15.0,<0.16"` |
| PR #2476 merged (installed that ceiling) | 2026-09-09T02:15:51Z |
| PR #2475 merged (carried D18) | 2026-09-09T02:34:07Z |

#2476 narrowed the ceiling because attune-forms 0.16.0+ ships AF-2
registry changes this repo has not consumed, and the Task 1B
surface-parity gates fail against them
(`SurfaceRegistryError: lifecycle:subject:surface-native-elicitation:abort:
stale/missing implementation_digest`). D18's text was authored before
#2476 existed and was not re-read against the tree it landed on — the
same defect class D18 was written to correct, a claim about the world
stated in the grammar of a verified fact.

### Ruled

1. **D18's floor ruling stands.** The Task 2 consumer floor is
   `>=0.17.0`. No delimiter, escaping or freeform correction is
   reopened.
2. **Two present-tense claims in D18 are corrected.** Item 2's
   "retaining the exclusive 1.0 upper bound" and item 4's "the locked
   consumer floor reads its actual value, `>=0.15.0,<1.0`" are both
   false about the tree, which reads `attune-forms>=0.15.0,<0.16`.
   Note the precise error: the FLOOR is correct — 0.15.0 matches —
   and only the ceiling is wrong. Item 2's earlier clause,
   "`pyproject.toml` has pinned `>=0.15.0,<1.0` since #2465", was true
   for the window #2465 to #2476 and is false only in its
   present-perfect framing. The correction is an inline dated note
   inside D18; no ruled text is deleted.
3. **Task 2's `files-to-modify` no longer instructs "retain the
   existing exclusive 1.0 upper bound".** There is no `<1.0` bound in
   the tree to retain, and read literally against what is there the
   instruction yields `>=0.17.0,<0.16` — an empty specifier.
4. **The replacement ceiling is NOT decided here.** #2476 set `<0.16`
   on measured evidence. Restoring `<1.0` would recreate the
   fresh-resolve exposure that turned main red on 2026-09-08 —
   conditional on some future unconsumed minor, since Task 2 is itself
   what makes 0.17.0 pass. Whether the lifted pin should be `<0.18`,
   `<1.0`, or something else is for Task 2 to establish with its
   receipt or for a later ruling; this entry only removes the false
   instruction and records the hazard.
5. **Task 1B's increment-3 record is corrected.** The header lists
   increments 1 and 2 as merged and names increment 3 only as
   AUTHORIZED (D14, lines 11-12), never as landed; line 168 calls
   #2450 "in draft" though it merged 2026-09-07 as `6934b177e`, an
   ancestor of `origin/main`. Only the PR's status is stale — that
   line's substance is corroborated by the merge diffstat. "Full Task
   1B remains incomplete" stays true and is preserved: increment 4,
   the cross-repo-compat advisory jobs, has not started.

### Not ruled here

Sequencing is untouched. Task 2's `<dep>10</dep>`, the critical path,
and D18's own "Not ruled here" all stand exactly as written. A
dependency audit run on 2026-09-09 found no code coupling between
Task 2 and Task 10 and one narrow technical need in the capability
snapshot's static channel. That finding is deliberately NOT recorded
here: its wording did not survive verification (two clauses were
literally false, and whether the unwritten static channel is a defect
or an intended not-yet-implemented state was not established). It
changes no order without its own ruling, on language that has been
checked.

## D20 — Task 2 executes next; Task 10 is not its prerequisite (RULED 2026-09-09, chair)

Chair, verbatim: "rule task 2: do task 2 next, skip 10".

D18 and D19 both state in present tense that Task 2 is blocked on its
declared dependency. This ruling supersedes that sequencing. It does
not reopen any other part of either entry.

### Basis, re-verified against the tree for this entry

A 12-agent dependency audit on 2026-09-09 found the Task 2 to Task 10
dependency is spec sequencing, not code coupling; all six adversarial
refuters agreed. Each load-bearing fact was re-measured before being
written here:

| Claim | Probe | Result |
|---|---|---|
| No Task 10 artifact exists | `ls src/attune/surfaces` | absent |
| Nothing references its API | `grep -rn CapabilityProvider src/ tests/ scripts/` | 0 hits |
| Task 2's four modified source files name no Task 10 artifact | grep for `attune.surfaces`, `CapabilityProvider`, `capability_matrix` | 0 hits |
| The only Task-10-flavoured string in them | `surface_policy.py:508` | the word "doctor", in a docstring |
| What Task 2 actually needs already exists | `surface_policy.py:141` | `class PresentationChallenge` |
| Task 4 produces no code | its own objective | "No production change unless either receipt fails" |

### Ruled

1. **Task 2 is next.** Its `dependencies` block no longer names Task
   10, and `tasks.md`'s critical path drops Task 10 from Task 2's
   prerequisites.
2. **Task 4 and Task 1B increment 4 are not prerequisites either.**
   Task 4 emits prose plus `r4-receipts.json`, which `grep -rn
   "r4-receipts" src tests scripts .github` shows is consumed by
   nothing. They proceed on their own schedules.
3. **Task 2's receipt must NOT claim the host-native route is live.**
   `CapabilitySnapshot.supports()` consults `host_static` then
   `cached_static` for routes outside the negotiated channel
   (`surface_policy.py:522`), and **nothing writes either**: the field
   is declared at `:513` and read at `:522`, and those are its only two
   references in `src/`. The runtime builds the snapshot with the
   negotiated tuple alone (`surface_runtime.py:116-120`). So a
   host-native route is selectable only once some provider writes that
   cell. Task 2 may land the consumer; it may not report the route as
   firing. Registry state at this ruling: two renderer targets carry
   `surface: host-native` and one receipt exists for the
   compatibility target.

4. **Task 10 is DEFERRED, not cancelled** (chair, same session:
   "defer 10"). It leaves Task 2's critical path and keeps its D8
   execution go; it is not descoped, and R9 stands. This matters
   precisely because of ruling 3: Task 10's doctor remains the only
   thing designed to write the static capability cell, so deferral —
   unlike cancellation — leaves a named owner for closing that gap.
   Until it lands, or a narrower substitute writes `host_static`, the
   host-native route stays admissible-but-latent and no receipt may
   report it firing.

### Not ruled here

**When Task 10 executes.** Deferral fixes that it still happens; it
does not schedule it.

No release, API-spend or automatic-merge authorization is granted or
changed.

## D21 — Increment 3 is built behind an unregistered profile; both open PRs take one combined review lane (RULED 2026-09-09, chair, via round table)

Promoted from round-table thread `q-2496-2497-next-step-001` (board
messages 2, 3, 6; full transcript machine-local at
`~/.attune/reports/roundtable/q-2496-2497-next-step-001.md`, per D2). One
round, fixed roster, 3/3 seats answered, no absent seat. The chair
promoted items 3, 6 and 7; items 1, 2, 4 and 5 were presented and NOT
ruled, and nothing was written for them.

### Ruled

1. **One combined review lane over both open PRs, before chair-read.**
   #2496 (the host-question adapter boundary) and #2497 (this spec's
   text reconciliation) are reviewed in a single different-model pass
   rather than two. Two seats reached this independently; the reason
   recorded here is the one only the Claude seat stated, because it is
   the reason the combined shape beats two separate lanes: **the
   highest-value finding available is cross-PR.** #2497 corrects the
   task text to say the admissibility gate belongs in
   `surface_runtime.py`, while #2496 declares the boundary that gate
   will admit or refuse. A reviewer holding one diff cannot check that
   the corrected text and the shipped adapter agree about where
   enforcement lives — which is the entire point of reconciling text
   against tree, and is invisible to a single-PR lane.

2. **Increment 3 is built behind an UNREGISTERED profile.** The seam is
   implemented and fully tested without adding the profile to
   `host_profiles`; registration plus the parity-registry rows, the
   receipts, the demo render and a green parity gate then land together
   as one small final PR. This reuses the shape #2496 already
   proved — a complete, fully tested component with **no production
   caller** — and it splits a large diff **without splitting the atomic
   obligation**, which is the constraint that makes the naive split
   illegal.

   Corrected 2026-09-09, same day, by the review lane this ruling
   authorized: the first wording credited that isolation to the adapter
   being "not exported from the package `__init__`", which is not what
   makes it inert. The module is directly importable — #2496's own tests
   import it — so omitting a re-export hides nothing. What makes it inert
   is that **nothing calls it**. The distinction is load-bearing for
   increment 3: the property to maintain is "no caller", which an author
   must hold deliberately, not "no re-export", which packaging could
   satisfy while a caller quietly existed.

   The reason it is illegal to split the other way: **registration is a
   one-way door.** Registering the profile is the act that CREATES the
   parity obligation (`surface_registry.py:420`, pinned by
   `tests/unit/gates/test_surface_parity.py:1253`), so the gate demands
   satisfaction in the same PR that registers. There is no state in
   which the profile is registered and the receipt is still owed.

3. **The receipt shape for increment 3 is an OPEN question, recorded not
   answered.** Raised by the Antigravity seat (board message 6): the
   parity gate will demand a receipt for the newly-obligated host-native
   target, while D20 ruling 3 forbids any Task 2 receipt from reporting
   the host-native route as firing, because nothing writes the static
   capability cell. Both constraints are settled and neither yields.
   Increment 3 may not begin until this has an answer; producing one is
   in scope for its planning, not for this entry.

### Recorded, not ruled

The table was **unanimous** that the D11 lane is owed on BOTH PRs, and
that splitting the spec text into #2497 relocated the trigger rather
than discharging it. The chair did not rule that question here; ruling 1
authorizes the lane as an action without settling the doctrine, and the
two precedent questions the table raised — whether a shrink-only
ratchet's baseline entry is itself a D11 trigger (seats split 2/1), and
whether a risk class that is DECLARED but not yet CROSSED fires the lane
at the declaring or the wiring diff — remain open for a future ruling.

One correction the table produced about this project's own reporting,
kept because it outlives the thread: **100% statement and branch
coverage on `host_question_adapter.py` was measured and is true, but it
does not speak to the boundary contract, because the adapter under test
is a fake.** Coverage over a cooperative fake proves the module's own
control flow. This is the same shape as the MGET-migration lesson, where
ten emptiness-asserting tests passed precisely because the logic never
ran. The figure should not be cited as evidence about the trust
boundary.

## Open decisions

Three, all opened by D21 (2026-09-09). Recorded because an inventory
reading "None" while a ruling in the same file leaves questions open is a
claim the file itself disproves.

- **Increment 3's receipt shape.** The parity gate will demand a receipt
  for the newly-obligated host-native target the moment the profile is
  registered, while D20 ruling 3 forbids any Task 2 receipt from reporting
  the route as firing. Both constraints are settled and neither yields.
  D21 ruling 3 makes answering this a precondition of starting increment 3.
- **Does a shrink-only ratchet's baseline entry trigger a D11 lane?** The
  round table split 2/1: two seats held that permitting one more broad
  catch changes what the gate allows even with gate logic untouched; one
  held the trigger weak, because the baseline GREW with an annotation
  rather than shrinking, and treating every entry as a trigger makes the
  ratchet's own escape hatch expensive to use honestly. Unruled.
- **Declared versus crossed.** When a risk class is DECLARED but not yet
  CROSSED — an unexported trust boundary with no caller — does the lane
  fire at the declaring diff or at the wiring diff? Unruled.

Resolved 2026-09-02/03/04: the table was convened (round 1 complete,
promoted in D5); D2 ruled (routing label); Task 7 ships alone on
Phase A (D5); D6 ruled (hybrid, subject-local); D7 coverage floor
90%; D8 16.3 gos granted; D9 tier provenance adopted as R10; D10
context-routed, mechanically discovered surface subjects adopted; D11 records
the two-provider cross-review contract closure without changing execution gos.
