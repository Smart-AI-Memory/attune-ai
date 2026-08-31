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
