# Host Surface Parity — Requirements

**Status:** approved (2026-09-02) — round 1 of
`q-fable-51-surface-overlap-001` deliberated R1–R8 (3/3 seats);
the chair promoted the round in decisions.md **D5**: R4 adopted as
written, R1/R2/R3/R5/R7/R8 adopted as amended (binding amendment
text lives in D5), R6 adopted with D2's routing-label mechanics,
R9 (capability-descriptor/conformance layer) adopted as the 16.3
foundation. D6 ruled 2026-09-03 (hybrid locus); D7 coverage floor
90%; D8 grants the 16.3 execution gos; D9 (2026-09-03) adopts
tier provenance as R10; D10 (2026-09-04) rules context-routed,
mechanically discovered surface subjects. No proposed decision remains open. Tasks
2, 4, 10, and 12 retain D8's authorization, but D10's dependency order
determines when each may start; each lands against the 90% floor.
Task 0 completed under its earlier characterization go. The original Task 1
go was exhausted by the falsifying pre-implementation probe; neither AF-1 nor
the replacement Task 1B has an implementation go, and neither attune-forms
package publication has a release go.
**Execution correction (2026-09-04):** Task 1's
pre-implementation probe falsified D6's claimed renderer-registry
baseline and found that the host-artifact scope cannot land green
as written. The factual correction and chair ruling are in
decisions.md D10; no Task 1 production change has started. Cross-
package AF-1/AF-2 work is now a portable handoff executed in clean
attune-forms worktrees, never `attune-forms:` pseudo-paths passed to the
local runner.
**Slug:** `host-surface-parity`
**Provenance:** Cowork session with the Claude seat, 2026-09-03,
chair Patrick Roebuck. Companion brief: the artifact "Fable 5.1 and
the Attune Surface" (Claude seat opening position, thread slug
`q-fable-51-surface-overlap-001` proposed, not yet opened on the
board). *(Update: the table was convened 2026-09-02 — all three
seats deliberated; the round was promoted in decisions.md D5.)*

## Position in the existing stack

This spec sits on four shipped seams and adds no new memory store,
orchestration layer, or model-provider registry. Its new renderer
projections and iterable registry stay in `attune-forms`:

- **Surfaces** — `attune-forms` declares
  `ProjectionSurface.RICH / PORTABLE / HEADLESS` and exposes separate
  form and workspace renderers. Its `ProjectionRenderers` type is one
  injectable workspace-renderer bundle, not an enumerable registry.
  The state-bound command workspaces of 16.2.0
  ([shared-command-workspaces](../shared-command-workspaces/requirements.md))
  call the exported workspace renderers through their stateful adapter;
  they do not instantiate `ProjectionRenderers` today.
- **Projection** — the collaboration projector
  ([cross-provider-collaboration-projector](../cross-provider-collaboration-projector/requirements.md))
  owns one master (`content/collaboration/contract.md`) and projects
  it to `AGENTS.md`, `.claude/CLAUDE.md`, and the Antigravity mirror
  `.agents/AGENTS.md`.
- **Memory** — stash → recall → promote, with `resolve_backend()`
  reading `attune.memory_backends`, and cross-provider transport
  shipped in 10.6.x
  ([cross-provider-memory-transport](../cross-provider-memory-transport/requirements.md)).
- **Extensions** — the trust-gated `attune.extensions` system ruled
  in [release-16-manifest](../release-16-manifest/decisions.md)
  D1/D2 (passenger 4), not yet on disk. Chair ruling D1b of this spec
  makes it the seam through which providers, backends and seats
  arrive.

## Problem

The 2026-09-01 host release (Claude Fable 5.1; the Cowork and Claude
Code surfaces around it) ships first-party versions of things Attune
built as portable, verified, multi-provider systems: a structured
question widget (`AskUserQuestion`), desktop-persistent project
memory (`MEMORY.md` + typed topic files), a skill-proposal card, a
multi-agent workflow runner, typed review findings, hosted artifacts
with runtime state, scheduled tasks, and a file monitor.

Two failure modes follow, and they pull in opposite directions:

1. **Ignore the host** and Attune's lowest rendering tier looks worse
   than the native widget sitting next to it; memory reads as a
   duplicate of a feature the host now has by the same name.
2. **Chase the host** and Claude surfaces become privileged: a rich
   Cowork path with a neglected Codex / Antigravity path, which is
   exactly the power-user sacrifice the chair has ruled out.

The requirements below resolve the tension with one rule: **every
host-specific capability ships with its portable twin, receipted,
in the same change** — and the multi-provider roster becomes data
so a vendor change is a config edit, not a PR.

## Hypotheses

- **H1 — tier 0 is a render target, not a rival.** A form admitted by
  the active host-profile record returns the same validated answer as
  widget-HTML and headless tiers. Forms or lifecycle semantics outside
  that profile keep their complete PORTABLE/RICH renderers and are
  never degraded to fit the host.
- **H2 — parity can be mechanical.** "The receipt beats the promise"
  is listed as *aspirational* in the collaboration contract. For
  surfaces it can be an enforcer: a drift guard that fails when a
  host-native or RICH renderer target, or a detected subject capable of
  selecting either, lacks PORTABLE and HEADLESS twins with receipts
  appropriate to its subject kind.
- **H3 — the host remembers; Attune recalls.** Projecting the
  promoted-lesson index into each host's native memory surface makes
  a plain host session benefit from the corpus, while recall
  (relevance-ranked, at prompt time) remains the product. Memory
  stays the single source of truth; every projection is
  regenerable and never hand-edited.
- **H4 — local models earn a role before a seat.** Under D1a, a
  local model's first job is the set of low-stakes, high-volume
  roles where cost and privacy dominate — recall re-ranking, lesson
  classification, triage pre-sort, skeptic/countersign at low
  stakes, fact-check probes — not deliberation. Under D1b these
  arrive as extensions under the two ruled capability contracts,
  which makes an Ollama-backed reranker the first real second
  implementer that release-16-manifest D2 named as its falsifier.
- **H5 — roster by role, not vendor.** The three seats are harness
  recipes with role properties (`PLAN_ONLY_SEATS`), not providers.
  Expressing the roster as role slots with a vendor binding keeps
  the fixed three as the default while making "Google changed tiers
  again" or "add a fourth seat" a data change gated by the extension
  system.
- **H6 — select before rendering.** Context routing improves latency
  only when it chooses from already-trusted capability evidence rather
  than probing the host or attempting a renderer on the request path.
  A route decision performs at most one receipt-store lookup (with separate
  local authoritative session/workspace reads) and
  at most one projection-renderer invocation (exactly one when a route is
  selected, zero for `no_supported_surface`). A feedback-capable host may
  present that one projection more than once without re-running the renderer;
  presentation attempts are counted separately. The decision records selection
  latency, renderer-attempt count, and presentation-attempt count. The claim
  remains a hypothesis until the Task
  1B receipt compares the failed-rich-then-fallback baseline with the
  preselected cold and warm routes.

## Requirements

**R1 — Host tier 0 renderer** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: host-profile record, not a hardcoded vendor shape)*
`attune-forms` gains a renderer driven by a declared host-profile
record—not a universal vendor shape. A profile states question count,
option/header limits, multi-select, its exact reserved Other label/token and
free-text behavior, cancellation, question/option text normalization,
response-correlation and raw multi-select encoding, finite validation-attempt cap,
finite server-owned response deadline, and validation-feedback capabilities.
An encoding declares whether each raw atom is an emitted label or a distinct
host response token; the server maps atoms to option IDs through retained
bindings before common validation and never guesses label/token equivalence.
The first shipped profile describes
the current Claude AskUserQuestion contract; Codex or Antigravity may
declare different limits without changing renderer code. Supported
questions preserve order and stable multi-select order. Options use a stable
partition that moves the earliest recommended option first; its emitted label
gets the " (Recommended)" suffix only when the suffixed label remains within
profile bounds and collision-free within that question after profile
normalization, including against the reserved Other label/token. The pure
renderer returns a frozen `HostQuestionBatch` composite whose host payload is
paired with immutable per-question `QuestionAnswerBinding` records. Each binds
stable question ID, emitted ordinal, and exact emitted question text to that
question's ordered `(emitted_label, response_atom, option_id)` triples; repeated labels across different questions
remain unambiguous. The renderer keeps no hidden state. For a policy-owned
host-question interaction, the server retains the composite's bindings/profile
state in the PresentationChallenge and passes only `batch.payload` to
`HostQuestionAdapter.present_and_collect(...)`. The adapter sends that payload
across its host boundary, and its completion returns directly to the server in
the same call while the bindings remain server-side.
No model-mediated follow-up call may claim that presentation. The server never
accepts caller-supplied bindings or reconstructs them from display text.
No path strips suffix text heuristically. Any form
or lifecycle requirement outside the active profile is rejected by a pure
profile-admissibility predicate before any renderer is invoked, so PORTABLE is
selected with the original form intact—never truncated. The public renderer
may defensively return `None` for an unsupported direct call, but the routed
path never uses that return value to discover a fallback. Other, cancellation,
malformed answers, and validation errors re-enter the common
validator/lifecycle path. A rejected post-render answer may rotate the receipt
and re-present the already-selected route when that route supports validation
feedback. The server creates an immutable `ValidationFeedbackEnvelope` from
canonical validator errors, binds its digest into a fresh single-use challenge,
and passes it as a separate adapter argument; it never accepts feedback from the
host or caller. The original `HostQuestionBatch` is reused, so the projection
renderer still runs once. Each `present_and_collect` call increments the separate
presentation-attempt count; the positive cap includes the initial call and the
original deadline never resets. Cap/deadline
exhaustion terminates as `abort` without surface cycling. Adapter exception,
`None`, wrong challenge, or no completion by the deadline is `render_failed`
and creates no new receipt; a trusted user timeout remains `timeout`.
The profile also declares response correlation as `question_id`,
`emitted_text`, or `ordinal`. Admissibility rejects duplicate normalized
question text for a text-keyed host, requires stable IDs in an ID-keyed host
contract, and requires exact ordered cardinality for an ordinal host. The
current AskUserQuestion profile is text-keyed, has a 12-character `header`
limit, and uses the verified scalar codec
`{kind: comma_delimited, delimiter: ", ", atom: emitted_label,
escaping: json_quote_when_delimiter_or_quote, canonical_reencode: required}`.
Atoms containing the delimiter or a quote are JSON-string encoded with JSON
backslash escaping; other atoms are bare. Decoded order is preserved, and an
empty, duplicate, unknown, or non-canonical atom string is rejected. Its
freeform Other answer is a separate global `response`: it is correlated only
when exactly one question lacks a structured `answers` entry; zero or multiple
such questions, or structured and freeform answers for the same question, are
malformed and re-presented rather than guessed. Duplicate emitted questions
fall back before rendering rather than overwrite one another.

**R2 — Surface parity gate** *(chair-ruled — ADOPT as amended, D4/D5; locus ruled in D6 and execution scope corrected in D10: registry for renderers, detection-based subjects in-tree)*
A drift-guard imports the released `attune-forms` renderer registry and its
closed projection-output type vocabulary
and mechanically detects local surface producers (renderer calls,
recognized host-presented content envelopes, commands, and templates),
including statically resolvable repo-local helper call graphs with root
provenance. Event unions schedule one AST scan but results/obligations remain
qualified by producer, event, matcher, signature, sink, and destination; one
event cannot transfer credit to another. Python module-body output uses the
reserved `<module>` anchor. `Optional[T]`/`T | None` candidate typing strips
only `None`; other unions fail closed. Direct allowlist content and attempted
renderer-hiding mutations are gated. Host-exposed
roots own subjects/routes; helpers remain implementation/provenance nodes unless
independently exported or invoked at a host boundary.
Each producer record binds its exact route/target ownership; compatibility-only
renderers cannot be selected by policy or used to bypass the shared resolver.
The only allowed compatibility anchors are the existing fixed-shape
`form_to_ask_payload` adapter and deprecated AskUserQuestion
`elicitation_render_form` MCP handler over the specialized target. Neither is a
policy route; their exact target/shape/provenance is a derived
`compatibility_endpoint` subject with no route list. Context routing uses a new
unified endpoint whose closed response discriminates success payload/completion
from `no_supported_surface`, `render_failed`, `session_ended`,
`challenge_invalidated`, and `challenge_consumed`, with nullable
route/receipt/submission invariants. A success payload that requires deferred
collection carries the server-issued `submission_id` that the collector must
echo; trusted same-call completion and every error arm carry no public
submission ID. Each payload-return render issues a fresh submission ID even
when it reuses an unchanged active receipt. A retry repeats that ID and the
canonical response; reuse with different response content fails
`submission_conflict` without mutation, while a separately rendered concurrent
presentation has a different server-issued ID. The opaque authenticated ID
references a pending record in the receipt-chain store bound to server/store
instance, session/chain, active receipt, selected route, payload digest, and
collection/validator digest. The collector's one store lookup resolves both;
malformed, unauthentic, or unissued IDs fail `invalid_submission`, while an
authentic ID bound to another receipt/session/payload fails
`submission_mismatch`, before validation or side effects. Unused pending IDs
die on supersede, terminal action, expiry, or session close. `challenge_consumed` requires an
already-selected route, null payload/completion/receipt/submission, exposes no
winner receipt, and performs no mutation; it is a challenge disposition, not an
interaction-lifecycle token. Its non-authoritative decision summary has exactly four fields:
`context_reason` (one exact closed reason from the design's 23-row
first-match table), finite non-negative `selection_elapsed_ms`,
`renderer_attempt_count` (integer 0 or 1), and non-negative integer
`presentation_attempt_count`. It is server output only and is never accepted
back as routing or collection authority. Candidate order/dispositions, capability or constraint
IDs/provenance, receipt/store/workspace/schema IDs, and timestamps are forbidden;
the full receipt stays server-side. No old
caller receives an arbitrary route shape. The legacy native ask handler applies
trusted capability/accessibility admissibility before `session.elicit_form`
and preserves its existing unsupported response rather than switching surface.
Every detected interactive subject declares ordered cold/warm surface
preferences. Informational subjects instead declare event-qualified
`delivery_routes` to their exact user/model destination.
The resolver first applies authoritative accessibility constraints,
then trusted host capabilities and the interaction's semantic/lifecycle
requirements; only then does verified cold/warm context choose the
ordered list. Interactive routes end with PORTABLE then HEADLESS as
their safe fallback candidates. That list is pre-render selection metadata:
inadmissible entries are filtered without invoking them and only the first
admissible renderer is called. A selected renderer that raises, returns an
unexpected unsupported result, or cannot deliver records terminal
`render_failed`; it does not trigger a second renderer attempt. There is no
producer-authored opt-out and no
tool/model argument may assert a
capability, accessibility constraint, or warm context.

Projection and transport are separate axes. Cold form discovery prefers the
`mcp-native:native-elicitation` transport when it was negotiated; that
transport serializes through the registered HEADLESS
`form_to_elicitation_schema` projection and asks the host to display native
elicitation. The unified endpoint invokes authenticated `session.elicit_form`
itself for this route and receives the completion on that same trusted
transport; it never returns a caller-presentable native-request object.
Trusted route-active in-process host profiles follow that MCP
transport before PORTABLE and HEADLESS. Warm forms prefer RICH, then current
negotiated MCP-native elicitation, then trusted host-native, PORTABLE, and
HEADLESS. Bare HEADLESS consumes the same data
projection without a host, so this order is not a HEADLESS → PORTABLE →
HEADLESS renderer cycle. Cold
workspaces prefer PORTABLE; warm interactive workspaces prefer a
receipted RICH target; noninteractive execution prefers HEADLESS. Those
defaults are registry data and never trigger trial rendering.

For a non-MCP host-native candidate, a profile and route-active renderer target
are necessary but insufficient: a live server-registered
`HostQuestionAdapter` whose immutable profile ID matches both must be present.
The adapter exposes one same-call `present_and_collect(payload, *,
presentation_challenge, validation_feedback: ValidationFeedbackEnvelope |
None)` boundary and is never
constructed from a tool/request/model field or doctor cache. Without it the
candidate is inadmissible before rendering and PORTABLE remains next; a
serialized host-question payload plus a later caller response is not trusted
presentation evidence.
Verified deferred RICH/PORTABLE presentation similarly requires an immutable,
server-registered `DeferredPresentationAdapter` and single-use authenticated
callback challenge bound to session, receipt, route, payload digest, adapter,
and correlation. Only that boundary supplies non-serializable transport
context; missing context is validated-but-`unverified_transport`, while a
mismatch/replay fails without rotating the receipt.

Every enhanced renderer target and every enhanced subject-route target
creates its own stable parity obligation. Each obligation must name
PORTABLE and HEADLESS twins and have a machine receipt, so adding a
host-native target to an existing renderer record cannot reuse the
record's older receipt. Machine evidence is bound to the current target's
implementation, fixture, normalization, and canonical owning-record slice
digests. A route-active host-native identity additionally binds the installed
profile-facet and adapter/collector closure. A compatibility-only host-native
identity instead binds its package-shipped fixed compatibility-contract ID and
shape digest; it has no route, installed profile-facet, or live-adapter
precondition, and its consuming compatibility endpoints bind their exact legacy
shapes separately. Status and evidence mode are inseparable:
`route_active` requires `route_roundtrip`, while `compatibility_only` requires
`compatibility_projection`. The latter executes the package canonical form
through the specialized target and its PORTABLE/HEADLESS twins, derives a
canonical raw answer solely from the specialized output's question IDs and
emitted options, and requires the package common collector to return the same
normalized `FormResponse` as both controls. It proves projection/validation
semantics only—never routing, presentation, lifecycle, or rendered tier. The implementation digest closes over statically resolvable
package-local helper functions/classes/constants/defaults/decorators; unresolved
behavior-affecting dynamic dependencies fail unless explicitly artifact-bound.
Replacing behavior under a stable ID therefore requires fresh evidence;
an unrelated registry-record change does not invalidate the target. A full
registry-snapshot hash versions a route decision but is not a parity-evidence
foreign key.
Interactive subjects owe schema-identical
validated payloads and the applicable closed R2 lifecycle tokens `accept`,
`abort`, `timeout`, and `validation_feedback_delivery`; informational
commands/templates owe
content-schema/render/destination/delivery evidence, while recognized
hook deliveries owe content-schema/destination/delivery evidence. They
do not invent accepted payloads or interaction states. Every receipt whose
fixture normalizes payload/state—including lifecycle—binds that normalization
digest; changing validation-content evidence invalidates the existing
validation-feedback-delivery receipt. Unknown
context is cold; only an authentic,
unexpired, server-issued same-session receipt with exact subject,
schema, and state/revision bindings selects warm. Selection uses no
network probe or trial render, performs at most one receipt-store lookup
(separate authoritative session/workspace reads stay local to the same
decision/transaction), and invokes at most one projection renderer—exactly one
for a selected route and zero for `no_supported_surface`. Same-route validation
feedback may re-present that frozen projection without re-entering selection.
It emits reason, selection-time, renderer-attempt, and presentation-attempt
telemetry. The gate is mechanical; it implements
collaboration-contract principle 1 for surfaces and is listed there as
its enforcer.

Every successful render ensures one active receipt: issue/rotate when
authoritative state or collection binding changes, otherwise reuse. Each
submission uses the authenticated pending token contract above. The closed
collector errors add `invalid_submission`, `submission_mismatch`, and
`submission_conflict`; a delivery-loss retry returns its stored transition while
a different issued concurrent submission receives the normal
superseded/terminal disposition. Validation feedback compare-and-swaps the
active receipt and authoritative revision/schema, tombstones the predecessor,
and activates the same-state successor. A terminal action creates only a
terminal tombstone. Presentation failure creates no new receipt and preserves
any predecessor; second/late challenge completions have closed fail-closed
dispositions. A missing current workspace is `record_shape_mismatch`.

Active receipts age from `observed_at`; terminal tombstones retain their exact
reason from `tombstoned_at`. Before 7200 seconds a tombstone returns that reason
and an active record returns `expired` only after earlier binding mismatches;
at 7200 seconds either is logically absent regardless of physical GC. Subject
kind and ID are immutable, form/workspace record shapes are closed, and
workspace-only comparisons run only for valid workspace records.

An active 14–30-day experiment waiver and a current machine parity receipt for
the same obligation are mutually exclusive. Starting the waiver removes the
machine receipt but preserves append-only human history; expiry immediately
restores the obligation and requires fresh execution rather than reactivating
stale evidence.
The 30-day-in-180 cap remains keyed to stable obligation identity. Separate
machine history retains prior intervals. A chair-approved over-cap exception
binds one experiment, that same key, the current implementation digest,
decision reference, and bounded dates; it relaxes only the rolling cap and is
not itself a waiver. Target renaming or implementation churn cannot reset
waiver history.

Every interactive-form route token has its own lifecycle transport binding.
The binding-key set equals the union of that subject's declared cold and warm
route tokens: MCP-native tokens resolve to their named interaction-transport
subject, host-native tokens resolve to the matching host-profile record, and
direct RICH/PORTABLE/HEADLESS tokens resolve to an interaction-transport
subject. One form-level reference cannot silently stand in for several
different transports.

*Execution status (2026-09-04): paused before implementation.* The
renderer registry named by D6 does not exist in `attune-forms`
0.12.2, and the current tree has registered host hook entrypoints
with no declared twins or receipts. D10 records the required
cross-package prerequisite, clean-worktree handoff, and ruled context-
routing mechanism;
R2's approved outcome is unchanged.

**R3 — Memory index projection** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: bounded top-K sentinel-bracketed digest, per-host budgets)*
The collaboration projector gains a generated projection source from
the existing promoted-lesson index, which remains the sole authority,
and projects it to every configured host memory
surface: the configured Cowork project-memory `MEMORY.md` path (one line
per lesson, pointing at the Attune store), the memory block of
`.claude/CLAUDE.md`, `AGENTS.md`, and `.agents/AGENTS.md`. Promotion
triggers a hit-frequency-prioritized top-K regeneration inside literal
`<!-- ATTUNE:MEMORY:START -->` and `<!-- ATTUNE:MEMORY:END -->`
sentinel comments. Links are target-relative projections of one canonical,
path-validated promotion record; semantic parity compares lesson ID/order/hook,
not target-relative link bytes. Independent per-host line and byte budgets (also bounded by
the collaboration contract's 20,000-byte eager-load ceiling) and stale-entry
removal are drift-guarded. One common `K` is the minimum of 25 and every
target's current capacity and must be positive. When active promotions await a
first successful projection, the newest occupies slot 1 and the remaining
`K - 1` use hit frequency with a deterministic tie-break; otherwise all `K`
use normal ranking. After all target writes, one atomic metadata transaction
timestamps every previously-null emitted promotion. Any target/metadata failure
leaves them null, records store-level stale status, and raises for idempotent
retry. Source/render digests detect edits; ordinary projection refuses an
edited block, while explicit repair replaces only the sentinel-owned block.
Edits outside remain legal.
No bare repository `MEMORY.md` path is assumed. Recall is unchanged.

**R4 — MCP Apps round-trip receipt** *(chair-ruled 2026-09-02 — ADOPT as written, first among the eight, D5)*
A recorded receipt covers the Fix preview workspace rendered by the
Cowork host through the standard `ui://` profile. The live transcript
intentionally begins with a cold PORTABLE render, echoes
its server receipt, and reopens the unchanged workspace warm before a RICH
widget may be claimed. `fix_workspace_collect_action` returns revision, nonce and
contract hash intact; replay, stale revision, and wrong contract hash
all fail closed. The advertised-profile and absent-profile Markdown
fallback paths each receive independent evidence even when only one is
the live host's current state. The unobserved path is exercised by a
controlled, keyless conformance fixture with an immutable capability snapshot;
that fixture is labeled simulated and never presented as live-host evidence.
The two host-capture records live in a dedicated machine R4 receipt file and
are not misclassified as replayable parity-registry fixtures.
No production change unless a receipt fails.

**R5 — Scheduled and monitored delivery, twinned** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: one master definition, generated bindings, sweep guards)*
Exactly four master automation definitions—`discovery-sweep`,
`bug-predict`, `release-prep`, and `context-fit-monitor`—each generate both the host
scheduled/monitor binding and its portable `cron` + `attune` CLI twin;
generated bindings are drift-guarded. File events run deterministic
triage or enqueue an outbox item only—never an autonomous LLM sweep.
The host binding supplies native file events; the portable cron twin
polls from a durable cursor and feeds the same normalized event path.
Projected masters reject `automation_kind: interactive`, which is reserved for
manual runtime receipts. Twin equality applies to normalized semantic receipt
fields; adapter cursor/event config may differ. Monitors enforce at least 60
seconds of debounce, a positive per-definition `max_runs_per_hour` in a
half-open UTC hour, explicit acknowledgment before token-intensive audits,
and self-origin suppression. Every path remains under the spend gate.
Acknowledgment is a separate authenticated action available through host UI or
`attune automation acknowledge <event-receipt-id>` over owner-only local IPC
with peer UID/SID verification plus an OS-authenticated operator-confirmation
provider; a TTY alone is not authority. The server's `AckChallenge` binds
server instance, event, and operator to a digest-only 256-bit CSPRNG nonce, issued/expires timestamps
under a half-open at-most-five-minute TTL, and durable consumed state. The raw
nonce never enters argv, cron payloads, logs, or durable storage. Verification
atomically consumes challenge and pending event through an owner-only SQLite
transaction and conditional update; a two-process race commits one launch.
The authenticated host path uses a server-registered adapter/session identity
and consumes the same challenge—request/model fields cannot assert it. Expiry,
restart of the acknowledgment server with an
uncompleted challenge, replay across restart, mismatch, unavailable/refused OS
authentication, PTY-only automation, cron, and headless use fail closed. A
client/CLI restart does not invalidate the server challenge. The first event
beyond the hourly cap emits `hourly_cap_exceeded`, launches/consumes nothing,
and stays pending. A
cron/headless poll never auto-acknowledges and leaves the event pending. Run receipts record
`automation_kind: scheduled | monitor | interactive` separately from
`delivery_adapter: host | cron | interactive`.
Task completion requires a keyless, non-mocked production-boundary receipt on
at least one implementation-declared supported platform: the real portable
command traverses the real owner-only socket/pipe, the server observes and
matches the peer UID/SID, and the real platform confirmation provider approves
one event before a replay is refused. Every implementation-declared
unsupported platform must instead receipt the production provider's explicit
fail-closed `operator_confirmation_unavailable` result; a skipped fake seam is
not evidence. A machine receipt file carries the declared support matrix and
all per-platform record IDs referenced from the Markdown ledger.
The first monitored path is `~/.attune/telemetry/context_fit.jsonl`,
which also settles the fit_source budget clock in `TASKS.md`.

**R6 — Local-model roles via extensions** *(chair-ruled D1a, D1b; D2 mechanics ruled 2026-09-02 — routing label)*
Local models (Ollama first) enter as extensions under the two ruled
capability contracts: a **memory-backend** extension advertising an
optional `rerank` capability (Phase A of release-16-manifest D3), and
**workflow** extensions for classification, triage pre-sort,
skeptic/countersign at low stakes, and fact-check probes (Phase B).
Local routing uses a `placement: local` **routing label** on the
role's routing record — the tier enum stays `CHEAP / CAPABLE /
PREMIUM` in every in-tree call-path and the canonical attune-rag model-
resolution source does not change (D2, ruled: the label lets a role say
"CHEAP, prefer local, fall back hosted"). No change to
`ModelProvider`; no third capability contract (D3, ruled with the
second-implementer tripwire).
The reranker accepts only a complete permutation of known candidate IDs.
Timeout, HTTP/protocol/malformed/partial/duplicate/unknown-ID failures emit
closed health reasons and atomically return the original store order. The
frozen eval requires a healthy invocation and reranked P@3 no lower than the
store baseline, with raw counts so fallback cannot create a vacuous tie.
Only a role declaring `placement: local` enters local stakes routing. Stakes
are evaluated before availability: above the chair threshold routes directly
to the existing hosted `PREMIUM` enum member; otherwise an unavailable local
extension falls back to the role's originally declared hosted tier. No tier
enum changes. The cost ledger
records actual placement and `local_no_api_charge` with zero API-billed cost
for a local run rather than pricing it from the role's hosted quality tier.
Ledger rows keep `placement_preference`, `actual_placement`, and
`placement_reason` distinct; before Phase A, local preference records actual
hosted placement with `local_unavailable`.

**R7 — Roster as data** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: typed slots, golden-roster receipt, loader-enforced fourth-slot gate)*
`CANONICAL_SEATS`, `SEAT_RECIPES` and `PLAN_ONLY_SEATS` become derived views of
one immutable `ActiveRosterSnapshot` loaded at the composition root from a
roster document of role slots — one plan-only reviewer, one
code-native proposer, one moderator with receipts — each bound to a
harness recipe. Every typed slot carries a unique, stable `slot_id` matching
`^[a-z][a-z0-9_-]{0,63}$`, unique active seat ID, execution mode, trust boundary, required
capabilities, and receipt obligations, plus a typed
`brief_transport: argv_placeholder | stdin` recipe-delivery field. The loader
requires exactly one reserved `moderator`, `plan_reviewer`, and
`code_proposer` role and rejects duplicate slot/seat IDs. `PLAN_ONLY_SEATS`
derives from execution mode; an extension may be plan-only without becoming
the reserved reviewer. `argv_placeholder` requires exactly one whole-token
placeholder and no stdin brief; `stdin` requires zero placeholders and exactly
one piped brief. The default roster is the
current three, byte-for-byte in
behavior and loads without an activation receipt. The only override is a fixed
operator-owned, non-symlink, owner-only (`0600` or platform-equivalent) path
outside the worktree, rooted in the OS-account profile for effective UID/SID
rather than environment home variables. Any
non-default roster requires a fresh `RosterOverrideReceipt` bound to the full
roster digest, trusted path, local operator identity, and chair-decision
reference. It carries those identities plus `issued_at`/`expires_at` under a
half-open `(0, 30 days]` interval; approval binds kernel-derived operator ID and
a Task-6-owned OS-authenticated confirmation (TTY is presentation only), stamps
server UTC, and rejects future/caller time. A worktree-local `.attune` file cannot self-activate. The snapshot
loads once before seat invocation, all legacy constants derive from it, and
external changes require a new process. Its `valid_until` is the earliest
authorization expiry (`None` for the embedded default) and is checked before each new seat launch without
rereading files. A valid receipt may be verified on
every load until expiry; only duplicate approval issuance for an already-active
digest/decision is rejected. Workspace gates check roster
size from that snapshot, not the literal three. A fourth slot is structurally
representable but its role must be `extension:<role>` and it loads only with
the named enabled extension, the roster-wide override receipt, and a fresh
typed `RosterActivationReceipt`. That receipt
contains `slot_id`, `roster_digest`, `extension_id`, `operator_id`, `decisions_ref`,
`issued_at`, and `expires_at`; the loader rejects a mismatched slot, roster,
extension, unresolved chair-decision reference, future issue, interval outside
`(0, 30 days]`, or expired half-open interval. It comes only from
`~/.attune/roundtable/activations/<slot-id>.json` under the same trusted
ownership/no-symlink rules. `slot_id` equals the explicit ID on that roster
slot—never the colon-bearing `extension:<role>` value—and resolve-under-root
containment is mandatory before any read.
`attune roster activate <slot-id>` is the sole issuance path and applies the
same operator confirmation/time rules; an already-active identical issuance is
refused.

**R8 — Asks-per-outcome** *(chair-ruled 2026-09-02 — ADOPT as amended, D5: terminal outcomes, raw counts, floor)*
The session ledger stores raw structured-ask and terminal **work-unit** events,
each with `session_id` and `work_unit_id`. A work unit is the session/workflow objective (for example one Fix run,
workflow run, or promotion attempt), not an individual question; it emits at
most one outcome per identity pair, partitioned as accepted, cancelled, aborted (including abandonment),
timed_out, or blocked. Several structured asks may precede that one outcome,
so asks per outcome remains a real friction signal;
it never stores a ratio or answer contents. Asks per session remains a
secondary guard. Above a declared minimum-outcomes floor,
`friction_gate` may compute asks per terminal outcome over the existing ledger's
trailing 30-day aggregate per project/workflow key and also reports
zero-outcome rate plus fallback frequency. Below the floor it reports
insufficient evidence, not zero friction. The ratio includes asks attributed to
terminal work units in the same half-open window; open/zero-outcome asks remain
separate diagnostics. A session increments zero-terminal only on close and
only if none of its work units terminated. No new telemetry store.
These session outcomes map to R2 without expanding its lifecycle vocabulary:
accepted → `accept`; cancelled or aborted → `abort`; timed_out → `timeout`;
blocked is terminal for that work unit before an interaction lifecycle began.

**R9 — Host capability descriptor and conformance layer** *(chair-adopted 2026-09-02 at promotion, D5 — the 16.3 foundation item)*
Every host adapter and extension publishes a machine-readable
**capability descriptor** (structured-question shape, memory
surfaces, `ui://` profiles, scheduling/monitoring support, action
round-trip guarantees, receipt schema versions). An
authoritative discovery pass unions production capability-provider
registrations with shipped/enabled `attune.*` extension entry points;
its ID set must equal the descriptor ID set, so a new unregistered
adapter cannot escape the matrix. An
`attune surfaces doctor` probe records which contracts the current
host actually advertises and writes a capability receipt; from
accumulated receipts a generated, drift-guarded **hosts ×
capabilities matrix** (each cell native / fallback-receipted /
absent) lives in tree, so "no privileged surface" is a visible red
cell rather than a vibe. A shared conformance suite runs canonical
transcripts against each adapter and proves: unsupported
capabilities degrade deliberately; semantic outputs stay
equivalent; receipts keep provenance and replay protection;
removing any host adapter leaves PORTABLE and HEADLESS execution
usable; no workflow silently selects a privileged host. The matrix
must be assertable in CI with **no host present** (all-fallback
column green), or HEADLESS parity is a promise again. The surface policy
consumes the capability-provider snapshot and passes only the selected route's
immutable profile to one renderer; renderers do not query the provider. The doctor
refreshes that snapshot outside the render path, so selection performs
no network probe or per-render host sniff. Fresh request-negotiated
observations come only from the server adapter's authenticated MCP
initialize/session capability object; non-MCP observations come only from an
immutable trusted in-process adapter profile. Tool arguments, request payload
fields, and model output are untrusted and cannot populate either channel.
Those observations override cached cells. Every cell is typed
`session_negotiated` or `host_static` and distinguishes unknown from an
observed negative. Doctor cache may fill only unknown `host_static` cells
during its explicit half-open, at-most-one-hour validity interval;
MCP-native/MCP-Apps selection always requires current authenticated negotiation
and never revives from cache when that source is absent.
*(Provenance: all
three seats proposed this layer independently in round 1 — Codex
R9, Claude R9, Antigravity's R1 capability descriptor.)*

**R10 — Tier provenance on validated answers** *(chair-ruled 2026-09-03, D9 — promoted from D5's "noted" list by the guard-intervention audit)*
Every validated answer has one exhaustive provenance disposition. A
server-observed completion or authenticated adapter callback carries
`provenance_status: verified` and the surface tier it establishes (tier 0
host-native / RICH / PORTABLE / HEADLESS). A policy-selected surface whose
answer returns through a model-mediated or otherwise unauthenticated path
carries `provenance_status: unverified_transport` and no invented
`rendered_tier`; the deprecated `elicitation_render_form` → legacy
form-plus-answers path similarly carries `unverified_compatibility`. The render
request and selected-route receipt alone never establish presentation. All
unverified rows are counted separately and excluded from tier/Other-rate
denominators, so a surface claimed but never displayed cannot masquerade as
evidence. Telemetry
surfaces the tier-0 fall-through rate (forms
exceeding the current host profile that fell to PORTABLE) and the
Other-rate (host free-text escape usage) from existing stores — no
new store. This is the falsifier for H1: if tier-0 answers
diverge, fall through excessively, or drown in "Other", the host
widget is degrading forms and the "render target, not a rival"
claim fails visibly.
`rendered_tier` is the presentation class, not the transport token:
negotiated MCP-native elicitation stamps `host_native`, while bare
programmatic consumption of the same HEADLESS schema stamps `headless`.
`selected_route` and transport provenance remain separately receipted. The
tier stamp comes only from a server-observed MCP completion, an authenticated
deferred callback bound to the active receipt, or a same-call
HostQuestionAdapter completion bound to the server-owned PresentationChallenge
whose compare-and-consume atomically creates the receipt—never from caller
input, the requested route, or a render receipt by itself.
Task completion additionally requires live, keyless, non-mocked evidence: a
negotiated production `session.elicit_form` completion stamps `host_native`,
and the identical schema's bare control stamps `headless`. Any RICH,
PORTABLE, or non-MCP host-native row may stamp its tier only when its own
authenticated adapter callback is captured; otherwise the row remains
`unverified_transport`. If no negotiated native host is available, Task 11
remains blocked rather than substituting a simulated host-display claim.

## Non-goals

- No fourth round-table seat in this spec. A seat arrives through
  R7 plus an enabled extension, in a later cycle, behind its own
  chair go.
- No general Ollama provider for all workflows. `ModelProvider` stays
  Claude-native; local models serve the roles in R6 only. A
  provider-level capability contract would be a third contract and
  is deferred to the chair (decisions.md D3).
- No change to recall ranking, the promote gate, or lesson content/authority.
  R3 adds only nullable projection metadata `first_projected_at` to the curated
  record schema; a missing legacy field reads as null and is written lazily
  after the first all-target projection. R3 projects; it does not move truth.
- No parallel per-host renderer framework in `attune-ai`. The new
  workspace HEADLESS and tier-0 projections live in `attune-forms` and
  enter through its one renderer registry; R4 remains a receipt.
- No auto-promotion, no auto-advance. R4 in
  [spec-lifecycle-gates](../spec-lifecycle-gates/requirements.md)
  applies unchanged.

## Public compatibility constraints

- `attune fix` CLI behavior and exit contract are unchanged
  ([outcome-first-fix](../outcome-first-fix/requirements.md)).
- The `attune.memory_backends` entry-point group keeps working
  through the compatibility adapter ruled in release-16-manifest D1.
- Three legacy `ModelTier` enums plus progressive workflow `Tier` remain
  in four in-tree call-paths
  (`src/attune/models/registry.py`, `src/attune/config/agent_config.py`,
  `src/attune/workflows/compat.py`, `src/attune/workflows/progressive/core.py`)
  and each remains three-member. The former local
  `attune.model_tiers` mirror and `test_model_tiers_drift.py` were
  retired by ccb4fe7bc; model resolution now lazily re-exports the
  canonical `attune_rag.model_tiers`. Under D2, `placement: local` is a
  field on the existing role-routing record. Task 12's focused unit test
  asserts that no in-tree enum gains `LOCAL` and that the lazy re-export still
  resolves to the canonical attune-rag source. A separate changed-file-manifest
  receipt—not the unit test—proves the Task 12 diff contains no sibling
  `attune-rag` path.
- R7 must not change the brief preamble's observable behavior for
  the default roster; the "three-model round table" wording becomes
  templated from the roster.
- The brand-drift gate (G5) applies to every file in this spec.

## Dissent register

- The Claude seat's own earlier candidate (bridge to Cowork
  `MEMORY.md` only) is withdrawn in favor of R3, which projects to
  every host memory surface. Reason: a Claude-only bridge would make
  memory the one place Attune quietly picks a vendor.
- Anticipated pushback to weigh at the table: whether R3 dilutes
  "Attune recalls" positioning by making the host notebook good
  enough. The seat's answer: a corpus with no recall is the demo;
  recall is the product.
- Historical pushback, resolved by D2: whether `LOCAL` belongs in the
  tier enum at all versus a role-routing label. The chair ruled the
  placement label; both original options remain in decisions.md only as
  provenance.

## Open questions for the chair

1. ~~Convene before ruling R1–R8?~~ Resolved: convened 2026-09-02,
   round 1 promoted (D5).
2. ~~Coverage floor~~ Ruled 2026-09-03: 90% (D7).
3. ~~D2 mechanics~~ Ruled: routing label (D2).
4. ~~Task 7 phasing~~ Ruled: the reranker ships alone on Phase A
   (D5).
5. ~~D6 — R2 enforcement locus~~ Ruled 2026-09-03: hybrid,
   subject-local (D6).
