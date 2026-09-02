# Shared Command Workspaces — Decisions

## D1 — Artifact tier and authority (2026-08-31, chair)

This work is a **spec**: it crosses `attune-ai` and `attune-forms`, changes a
security boundary, spans more than one session, and requires ten follow-on
adapter examples. Requirements are approved. Implementation remains gated per
task; spec creation is not blanket execution authority.

## D2 — Extend the existing renderer (2026-08-31, round table + chair)

The implementation uses the existing `attune_forms.workspace` schemas,
widget renderer, Markdown renderer, and action collector. The new shared
piece is host-side authority and command adapters in `attune-ai`. A parallel
renderer or client-executable callback model is rejected.

## D3 — Phase plus capability, not a universal state machine

View ids describe presentation. The legal action set supplied by the adapter
defines transitions. One workspace revision spans nested Roundtable and Spec
loops, while progress delivery uses a separate sequence. Confirmation binds
to semantic checkpoints, not to the word `preview`.

This resolves the table's main self-identified risk: Fix's linear interaction
shape must not become universal protocol semantics.

## D4 — Coverage is 90% for this initiative (2026-08-31, chair)

The chair modified promotion candidate 19 from the repository's 85% floor to
**90% changed-production-code coverage**. Board message 21 is the promoted
replacement. Boundary receipts remain mandatory; coverage cannot substitute
for them.

## D5 — Rollout order includes both disputed examples

The pilots are `/roundtable` and `/spec`. The next ten-example cohort begins:

1. `/release-prep`
2. `/bug-predict`

Antigravity originally recommended the first for multi-gate operational
rigor; Codex recommended the second for read-only, low-ceremony breadth. The
chair ruled that both ship, in that order, as the first two of the next ten.
Examples 3–10 are selected later from measured semantic gaps.

## D6 — Truncated promotion UI is a failure receipt

The first seven-item native promotion dialog truncated and could not be
scrolled into view. The chair skipped it; that was surface failure, not a
decline. Three compact batches succeeded. Large triage views therefore need
working scrolling, pagination, or compact batching, and the failed shape is a
regression fixture for the Roundtable adapter.

## D7 — Task 1 pinned a three-method adapter seam (2026-08-31, chair)

The production adapter protocol is `create`, `project`, and `apply`, plus a
stable adapter id and schema version. `project` returns the current
`WorkspaceView` and the adapter's normalized contract digest; `apply` returns
opaque successor state, a terminal flag, and result evidence. Legal actions
and confirmation stay in the view, so the host does not need command-domain
methods or fields.

## D8 — Fix migrates behind compatibility wrappers (2026-08-31)

The shared host owns registration, workspace identity, revision/nonce
issuance, server-side canonical storage, adapter-version checks, structural
binding validation, and per-workspace mutation locks. Fix owns intake
normalization, preview rebuilding, its semantic contract hash, exact approved
argv, and its receipt. The generic MCP surface is
`command_workspace_open` + `command_workspace_collect_action`; the existing
Fix tool names delegate to that host and retain their prior response shape.

## D9 — Publisher events are an optional adapter capability (2026-08-31)

Roundtable exposed the first semantic gap in the three-method seam: live seat
progress and moderator-recorded completion are trusted server events, not
chair actions. The shared core therefore adds an optional `publish` capability
without adding any Roundtable field or phase. Authority-changing publications
advance the canonical revision and reissue the nonce; progress-only
publications advance an independent `event_sequence` and are accepted only
when view id, actions, form, and contract hash remain unchanged. Both streams
remain monotonic across later chair actions and intake replacement.

## D10 — Roundtable triage is one candidate per page (2026-08-31)

The seven-entry truncation receipt is resolved with semantic pagination, not a
larger static form: each promotion candidate is rendered as one bounded page
with `promote`, `decline`, and, while the three-round/invocation caps permit,
`another_round`. Every disposition creates a fresh revision and nonce. The
Markdown fallback has the identical page boundary. Native fallback forms use
compact batches of at most three rather than recreating the failed shape.

## D11 — Spec workspace projects, persisted plan state remains authority

The Spec adapter reuses `spec_intake` for tree-derived areas and collision
awareness, `read_spec` for ordered XML task ids, and `SpecState` for durable
resume. It does not create files, execute tasks, run lifecycle gates, or hide
state writes inside rendering. Those existing seams publish exact receipts;
accepted task decisions return a `save_state` payload that the skill persists
with `attune.spec.save_state`. Thus a server restart resumes from the embedded
plan comment rather than pretending process-local workspace state is durable.

Lifecycle receipt states retain their existing authority: `BLOCKED` and
`REVISE` expose only fix-and-rerun, `CHAIR_REQUIRED` exposes one explicitly
confirmed acknowledgment, and only `PASS` advances directly. Auto-run never
consumes a high-severity task result. No additional shared-core change was
needed after D9.

## D12 — Cohort examples 1 and 2 need no shared-core change (2026-08-31)

`/release-prep` exercises repeated, separately bound gate decisions followed
by a distinct final approval. An absent gatekeeper is synthesized as
`MISSING`; `FAIL`, `ERROR`, and `MISSING` on Security, Testing, or Versioning
remain blockers and cannot be accepted. Documentation warnings require an
explicit warning acceptance. These rules live entirely in the adapter.

`/bug-predict` exercises the opposite authority shape: invocation authorizes
the read-only run, so its initial running view has no action or nonce.
Progress publications cannot alter authority and the only authority-changing
publication is a truthful terminal receipt. A producer failure renders “did
not complete,” never a false zero-findings success. This also fits the D9
publisher seam without changing the shared host.

## D13 — Examples 3–10 are selected by uncovered semantic cells

The ordered remainder is `/bulk`, `/memory-and-context`, `/smart-test`,
`/doc-gen`, `/workflow-orchestration`, `/image-analysis`, `/verify`, and
`/security-audit`. The first four receipts already cover nested governance,
resumable lifecycle, repeated gatekeeping, and immediate read-only work. The
remainder deliberately adds asynchronous reconnect, durable/destructive state,
read-to-write escalation, artifact mutation, mixed fan-out, multimodal input,
per-claim evidence, and remediation handoff.

The exact order, failure-sensitive receipts, and rollback boundaries are in
`cohort.md`. The chair's Task 2 choice to auto-run all remaining tasks is the
approval authority for this ordered selection; it does not waive the separate
Task 7 lifecycle gates or stop-on-failure rule.

## D14 — Bulk status receipts terminate the invocation, not the remote job

The `/bulk` workspace treats provider submission and later status lookup as
separate invocations. A terminal `pending` status means the interactive check
finished while remote work remains pending; it never says the batch completed.
Paid submission requires explicit confirmation, whereas a reconnect is
read-only. No shared-core change was needed.

## D15 — Memory writes prove their effect without rendering their value

`/memory-and-context` makes store and forget explicit confirmations. A store
does not terminate successfully until a retrieve of the same key returns the
same value digest and classification. Forget does not terminate successfully
until the post-delete retrieve misses. The workspace never renders the stored
value, including on SENSITIVE operations. Retrieve and search remain
read-only. No shared-core change was needed.

## D16 — Smart-test separates audit, write authority, and validation

`/smart-test` starts with a read-only audit. The producer must name proposed
test paths before the user can explicitly authorize generation. A successful
generation event is checked against that exact set and hashed from disk; the
workspace then requires an actual test command and exit code. A nonzero exit
retains written-file hashes as rollback evidence and is not success. No
shared-core change was needed.

## D17 — Doc generation is an artifact transaction, not a prose result

`/doc-gen` names proposed artifact paths before an explicitly confirmed write,
checks the producer's changed set against that boundary, hashes each file from
disk, and requires a symbol/import reality probe. A partial write or failed
probe keeps the hashes for rollback and renders failure. No shared-core change
was needed.

## D18 — Orchestration completeness is derived from requested children

`/workflow-orchestration` records progress without changing action authority,
then restores the requested child order at fan-in. Missing children become
explicit `MISSING` receipts. `FAIL`, `ERROR`, or `MISSING` prevents a clean
aggregate; `WARNING` yields a visibly degraded success. No shared-core change
was needed.

## D19 — Image identity comes from bytes, not filename or provider claims

`/image-analysis` derives MIME type, dimensions, byte count, and SHA-256 from
the validated local file before provider execution. Extension and magic bytes
must agree. The provider receipt must match canonical MIME/size, and success
requires non-empty analysis. The initial command authorizes this read-only
call, so there is no synthetic confirmation. No shared-core change was needed.

## D20 — Verify keeps deterministic authority separate from ambient review

`/verify` preserves the real checker-category list and the full
kind/severity/detail/evidence/location chain. Deterministic errors alone decide
the optional hard gate. Ambient semantic findings remain labeled warnings and
cannot override authoritative entity checks. Either layer failing yields an
incomplete receipt, not a clean result. No shared-core change was needed.

## D21 — Security remediation is a separate authority boundary

`/security-audit` is read-only through scan completion. A failed or incomplete
scan cannot render a health score or a clean claim. Successful findings are
paginated one per page; finishing the report and handing all high/critical
findings to Fix are distinct, revision-bound actions. The tenth receipt
required no shared-core change, so the adapter interface is declared stable at
version 1 only now, after the full ordered cohort was verified.

## D22 — Batch rulings require a validated response contract (2026-09-01, chair)

The chair approved the batch-ruling contract approach and the recommended
sequence. The lead corrects its earlier estimate: rendering three candidates
on one page does **not** reduce Roundtable's seven submissions because version
1 `WorkspaceActionResponse` carries one action and no per-candidate values,
while the adapter advances one `triage_index` per accepted response.

The real `+6` to `+2` target therefore requires two separately gated slices:
Task 8 adds generic, action-scoped, structurally validated response fields in
`attune-forms`; Task 9 consumes those values in Roundtable as an atomic
`3 + 3 + 1` ruling path. The shared contract validates fields and binding but
contains no candidate, promotion, or ruling concept. The existing one-item
actions remain the fallback and compatibility witness.

The ordering is binding: Interaction Quality Task 3 remains the measured
one-at-a-time baseline and completes review first; Interaction Quality Task 4
routes the capability gap to this owner; SCW Tasks 8 and 9 then execute behind
their own lifecycle gates; the live-host IQC receipt finally compares both
paths. The `+2` target and constrained native fit remain pending until those
receipts pass. Approval of this approach does not authorize an external file
send, commit, push, or deployment.

The earlier `auto_run: true` state applied only to the completed seven-task
ladder. Adding separately gated Tasks 8 and 9 does not extend that execution
authority. The public spec state writer therefore records `current: null` and
`auto_run: false`; each amended task still requires its own chair gate.

## D23 — Batch-amendment review corrections are binding (2026-09-01, chair)

Claude Fable 5 reviewed all ten authorized amendment files with zero omissions
for $1.9633825 in thread
`review-codex-batch-amendment-review-20260901-1920`. The chair promoted findings
3, 4, 6, and 7 and modified/promoted 1, 2, and 5.

The correction distinguishes approach approval from exact-text ratification,
names SCW task references and the pagination test precisely, repairs the probe
list, and aligns confirmation on the declared `promote` option. Pending local
dependencies use the parser's canonical `<dependencies><dep>` shape. The two
cross-spec edges are execution-boundary state receipts: SCW Task 8 is BLOCKED
unless IQC Task 4 appears in the public state writer's completed set, and IQC
Task 5 is BLOCKED unless SCW Task 9 appears there. Unsupported dependency tags
no longer imply enforcement.

The state comment is regenerated by `attune.spec.save_state`, preserving Tasks
1–7 as completed while leaving the amended queue unarmed. These corrections do
not authorize Task 8, Task 9, external sends, commits, pushes, or deployment.

## D24 — Corrected SCW/IQC amendment ratified (2026-09-01, chair)

The chair ratified the exact corrected requirements, design, and task text from
D23. Tasks 8 and 9 now form an approved amendment ladder, but neither is armed:
the machine-written state remains `current: null` and `auto_run: false`, Task 8
still requires IQC Task 4's accepted owner-routing receipt, and each task keeps
its own execution gate. Ratification authorizes the contract and ordering, not
implementation, external sends, commits, pushes, or deployment.

## D25 — Chair authorizes the gated latency sequence (2026-09-01, chair)

After IQC Task 4 acceptance, the chair accepted the lead's recommended sequence
as one decision: preserve the accepted external source, execute SCW Task 8,
execute SCW Task 9, then execute IQC Task 5. Signed local commit
`ec5ff8927fcbb6be2d69ddfc7bf53bb856019c5d` satisfies the first step with no
push or PR.

This decision supplies implementation authority for Tasks 8 and 9 in that
order, but does not bypass either execution gate, task-scoped verification,
different-model review where required, or chair acceptance. It does not
authorize an external send, push, PR, or deployment by implication.

## D26 — Task 8 reuses both existing renderers (2026-09-01, implementation)

The Task 8 implementation extends the originally named five-file boundary with
`src/attune_forms/widget.py` and `src/attune_forms/markdown_surface.py`. This is
the smallest contract-complete path: action-scoped fields remain ordinary
`FormQuestion` values and use the existing widget and portable Markdown
controls, while the selected action's schema is validated through the public
`collect_form_response` boundary. Creating action-specific controls or a second
validator would violate the approved shared-renderer design.

The new generic renderer arguments default to the version 1 envelope. A direct
base-versus-task probe hashed the action-only preview widget and Markdown plus
the existing intake-form widget and Markdown; all four SHA-256 values are
byte-identical. The implementation adds no Roundtable candidate, promotion, or
ruling concept. `workspace_action_contract` exposes action association, field
order, item definitions, and option order for the host digest; canonical-state
rebuild, nonce consumption, replay rejection, and atomic mutation remain in
`attune-ai`.

Central local receipts initially passed on the complete `attune-forms` suite:
945 tests on Python 3.10 and 945 on Python 3.11, including a real MCP stdio
subprocess. D28 records the corrected final receipts. No commit, push, PR, or
deployment has occurred.

## D27 — Task 8 Fable 5.1 attempt is inconclusive (2026-09-01, evidence)

The chair authorized one exact 13-file Task 8 implementation/evidence review
with tools and session persistence disabled and a $3 hard cap. The installed
Claude CLI could not address `claude-fable-5-1`, so the same packet was sent
once through the stateless Anthropic Messages API with no tools and no fallback.
The manifest contained 13/13 files with zero omissions.

Message `msg_011CedSr3EGAoBpVrHm6ehmX` counted 127,628 input tokens, consumed
the bounded 16,000 output tokens, stopped at `max_tokens`, and returned no
review text. Exact cost was $2.07628. The remaining $0.92372 could not fund the
same packet's standard-price $1.27628 input cost, so no second standard-price
request was attempted. D28 records the half-price low-effort batch recovery
that remained under the same cumulative $3 cap.
This receipt is INCONCLUSIVE, not `NO_FINDINGS`; it promotes no finding and does
not by itself satisfy Task 8's different-model-review gate.

## D28 — Task 8 Fable 5.1 ruling and corrections (2026-09-01, chair)

Low-effort batch `msgbatch_01Hat3poCmNwz6knDYyHRgY9` reviewed the exact 13
current Task 8 implementation/evidence paths with zero omissions, no tools, and
no session. It returned six findings at `end_turn`, using 128,863 input and
6,021 output tokens for $0.79484. Combined with D27, the complete review cost
was $2.87112 under the original $3 hard cap.

The chair modified/promoted F1, F2, F4, F5, and F6 and rejected F3. The
corrections defensively snapshot and deeply freeze each action response schema;
pin the four signed-base renderer hashes in a tracked regression; validate
nonce/hash syntax before `compare_digest`; prove field-order digest sensitivity,
the widget's baked envelope, and response-field rendering over real MCP stdio;
and preserve the previously hashable action/response values. A correction-time
probe also caught a frozen nested list escaping through `responses_payload`;
the detached payload now recursively returns ordinary mutable containers while
the stored response remains unchanged.

F3 is rejected with executable evidence: `FormSchema` accepts `form_id`,
`collect_form_response` accepts `template_id`, and the two failure-sensitive
immutable-response/real-stdio tests pass. Final central receipts are 81 focused
tests, 950/950 complete tests on Python 3.10 and Python 3.11, 190/190 executable
changed production lines covered, identical tracked version-1 hashes, and
passing repository-pinned Black, Ruff, and diff hygiene. Task 8 is ready for
chair acceptance; Task 9 remains unarmed until that acceptance.

## D29 — Task 8 accepted and Task 9 armed (2026-09-01, chair)

The chair accepted Task 8 after the D28 corrections and central receipts. The
public state writer advanced `docs/specs/shared-command-workspaces/tasks.md`
from completed Tasks 1–7/current Task 8 to completed Tasks 1–8/current Task 9;
`auto_run` remains false.

The Task 9 execution-boundary gate ran against its five declared paths and
passed symbol reality (`6b5521a13c13`) and falsifiability (`aa6999add899`). Task
9 is therefore armed under D25's approved sequence, but its implementation has
not started. No commit, push, PR, or deployment is authorized by this ruling.

## D30 — Task 9 local implementation is ready for review (2026-09-01, implementation)

Roundtable now projects at most three current candidates as ordered,
action-scoped `promote`/`decline` fields on one explicitly confirmed
`apply_rulings` action. The adapter independently checks the exact canonical
message-id sequence, validates every disposition, constructs the entire ruling
set before mutation, and advances the host revision once. Seven candidates
complete through exactly three accepted submissions (`3 + 3 + 1`), while the
existing current-candidate `promote` and `decline` actions remain available and
produce the same terminal rulings and receipt.

The implementation consumes Task 8's complete `workspace_action_contract` in
the Roundtable digest. Focused tests reject unconfirmed, stale, partial,
foreign, invalid, non-canonical, repeated, and duplicate-candidate batches
without mutation. The deterministic constrained profile proves three fields
and the terminal batch action are structurally reachable on each page when
`another_round` is unavailable. A separate failure-sensitive sentinel proves
that the four-action view which still offers `another_round` exceeds the
constrained profile's non-scrolling capacity of three; resolving that broader
navigation shape stays with IQC Task 5. Neither receipt is a live-native paint,
transport, dwell, abandonment, or latency receipt.

Task 9 integration exposed one Task 8 conformance-harness edge: mixed
action-scoped forms plus field-free fallback actions rendered valid portable
Markdown, but the parser searched only for the old field-free reply heading.
The parser now recognizes the first validated JSON response contract after the
bounded Actions section, with a mixed-action regression. Final local receipts
are 87 focused tests, 419 command-cohort tests, 951 complete `attune-forms`
tests, 100% Task 9 changed executable production coverage, pinned Black, Ruff,
diff hygiene, and verification-boundary symbol reality `577872cc90ac` plus
falsifiability `c72da2329d12`. Task 9 remains current—not completed—until its
required different-model review, chair ruling, corrections if any, and chair
acceptance.
The current published `attune-forms` 0.11.1 does not yet contain Task 8's new
API, so release integration must publish/version Task 8 and update the
`attune-ai` dependency floor before Task 9 can ship without the verified local
source overlay. No external send, commit, push, PR, or deployment has occurred.

## D31 — Task 9 Fable 5.1 review awaits chair ruling (2026-09-01, advisory)

Tool-free, stateless Message Batch `msgbatch_018AgZrMsdX8Smfv928EKfoq`
reviewed the exact ten authorized Task 9 implementation/evidence files with
zero omissions. Message `msg_011CedXZR52FRfA2yYdTC5dw` ended normally after
112,987 input and 4,363 output tokens for $0.67401, below the $3 hard cap.

The advisory review found no blocker and returned three gaps. F1 observes that
the constrained-profile pass covers the cap-exhausted three-action view, while
a view that still offers `another_round` has four actions and fails the
three-action viewport. F2 asks the portable parser to bound action scanning at
the first response contract and to pin adversarial bullets/fences plus the
mixed constrained profile. F3 asks for one interleaved legacy/batch ruling
equivalence regression. The integrating recommendation is to modify/promote
F1 as an evidence qualifier and explicit failure sentinel, modify/promote F2
with the minimal parser bound and three regressions, and promote F3. These are
recommendations only: no finding is promoted, no correction is applied, and
Task 9 remains current until the chair rules.

## D32 — Task 9 findings corrected under chair ruling (2026-09-01, chair)

The chair accepted the integrating recommendation exactly:
`modify/promote F1,F2; promote F3`. F1 now qualifies the constrained-profile
receipt to cap-exhausted views without `another_round`, and a failure-sensitive
sentinel proves that the four-action view fails the non-scrolling capacity of
three; navigation remediation remains explicitly owned by IQC Task 5. F2
bounds portable action discovery before the first JSON response contract,
retains fail-closed validation of that first contract, rejects an injected
pre-contract action or decoy JSON fence, ignores post-contract decoys, and runs
the mixed action-form/fallback fixture through both portable and constrained
profiles. F3 interleaves legacy and batch rulings over seven candidates and
proves the same terminal rulings, promoted ids, view, and Markdown receipt as
the pure-batch path while pinning their respective four- and three-transition
revision counts.

Corrected central receipts pass: 89 focused command tests; 1,134 broader
command tests with 35 environment skips; 953/953 complete `attune-forms` tests
on Python 3.10 and Python 3.11; 29/29 Task 9 executable changed lines and 2/2
parser-correction executable changed lines covered; repository-pinned Black
and Ruff; diff hygiene; and verification-boundary symbol reality
`6fb2ce5699e9` plus falsifiability `158066ae650c`. The cross-review ledger
guards pass separately. Task 9 is ready for chair acceptance but remains
current and unaccepted. No commit, push, PR, or deployment is authorized.

## D33 — Task 9 accepted; SCW ladder complete (2026-09-01, chair)

The chair accepted Task 9 after the exact Fable 5.1 review, the D32 ruling and
corrections, and the complete central receipt set. The public state writer now
records Tasks 1–9 completed, no current task, and `auto_run: false`. The shared
command workspace ladder is complete through the approved atomic Roundtable
batch amendment.

Acceptance promotes only the deterministic claims proved by D32: seven
candidates complete in `3 + 3 + 1`, the accepted batch path requires three
submissions instead of seven, and the added navigation count falls from `+6`
to `+2` while producing the same terminal receipt. The four-action
`another_round` viewport and live-host latency, paint, dwell, abandonment, and
retry measurements remain explicit IQC Task 5 work. IQC Task 5's named
cross-spec state probe now passes, so it is unblocked but not armed or started
by this acceptance. No commit, push, PR, or deployment is authorized.

## D34 — Public renderer dependency advances to 0.12.2 (2026-09-02, implementation)

The interim `attune-forms` release train exposed a real host-boundary defect:
the action-scoped explicit-confirmation path used a native browser dialog,
which could leave a user-visible submit button appearing inert when the host
did not surface the dialog. `attune-forms 0.12.2` replaces that boundary with
visible inline two-click confirmation, preserves the action consequence, and
disarms confirmation after every response-field mutation.

The 0.12.2 GitHub release and PyPI publication target exact merge commit
`5e69e1567d1e9047c97f3645e268a61dd22abd45`. Public PyPI lists both the wheel
(`216877fda1a1ba96ae2028ae4ff864c98e0b8b248a7f549410e52cf1155f367e`) and
sdist (`2542cef995af0816772eef48b97f6344190b6fd36485d2aa3003c09e3c860f25`). A
clean environment installed the public wheel into `site-packages` and proved
the renderer contains the inline armed state, visible consequence, and
second-click instruction with no native `window.confirm` call. Therefore the
`attune-ai` dependency floor advances to `attune-forms>=0.12.2,<1.0`; 0.12.0
or 0.12.1 is insufficient for the release's complete interaction contract.

## Round-table provenance

- Thread: `shared-renderer-command-workspaces-001`
- Full machine-local transcript:
  `~/.attune/reports/roundtable/shared-renderer-command-workspaces-001.md`
- Question: message 1
- Claude: absent, message 2 (workspace API usage cap; no inferred vote)
- Round 1: messages 3–6
- Round 2 critiques: messages 7–8
- Round 3 finals: messages 9–10
- Chair cohort ruling: message 11
- Final synthesis: message 13
- Promoted candidates: 14–18, 20, and replacement 21
- Final promotion ruling: message 22
