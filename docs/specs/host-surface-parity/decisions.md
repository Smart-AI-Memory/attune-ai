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

## Open

- None. Every proposed decision in this spec is ruled.

Resolved 2026-09-02/03/04: the table was convened (round 1 complete,
promoted in D5); D2 ruled (routing label); Task 7 ships alone on
Phase A (D5); D6 ruled (hybrid, subject-local); D7 coverage floor
90%; D8 16.3 gos granted; D9 tier provenance adopted as R10; D10
context-routed, mechanically discovered surface subjects adopted; D11 records
the two-provider cross-review contract closure without changing execution gos.
