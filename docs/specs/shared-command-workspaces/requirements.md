# Shared Command Workspaces — Requirements

**Status:** completed (2026-08-31) — implemented and verified; the chair
promoted all seven round-table candidates, raised this initiative's
changed-code coverage requirement to 90%, and selected auto-run for the
remaining separately gated tasks. Tasks 1–7 and all ten cohort adapters are
complete.
**Slug:** `shared-command-workspaces`
**Provenance:** round-table thread
`shared-renderer-command-workspaces-001`; promoted board messages
14–18, 20, and 21. Claude was absent because its workspace API usage cap
was reached; Antigravity and Codex completed three compiler-gated rounds.

## Position in the existing stack

This spec extends the workspace substrate already shipped by
`attune-forms`: `WorkspaceView`, `WorkspaceAction`,
`WorkspaceActionBinding`, `workspace_to_widget_html()`, and
`workspace_to_markdown()`. It does not create another renderer.

It consumes [elicitation-form-surface](../elicitation-form-surface/requirements.md)
for form controls and rendering, and builds on
[workflow-intake-forms](../workflow-intake-forms/requirements.md) for
schema-derived workflow intake. Its new responsibility is the host side:
canonical command state, legal actions, transitions, progress, and receipts
across more than one interaction.

## Problem

The presentation layer is already shared, but only Fix has a complete,
command-owned authority loop in `attune-ai`: canonical state, a revision,
a contract hash, a single-use nonce, server-side contract rebuilding, and
an exact approved command. `/roundtable` and `/spec` still assemble their
forms and gates primarily in skill prose. Other workflows have intake
templates but no reusable intake → preview → progress → receipt workspace.

Copying Fix's host logic into every command would duplicate security code.
Making one universal workflow state machine would be worse: round-table
rounds, spec approvals, read-only analyses, and release gates have different
semantics. The shared layer must standardize authority mechanics while each
adapter keeps command meaning.

## Requirements

**SCW-1 — Architecture and ownership**

- `attune-forms` owns the versioned, non-executable workspace view/action
  schemas plus widget and Markdown renderers. It never selects tools,
  executors, paths, agents, or state transitions.
- `attune-ai` owns canonical state, action authority, confirmation,
  execution dispatch, progress publication, and terminal receipts.
- New behavior extends the existing workspace renderer and MCP surface;
  no parallel renderer, callback-bearing UI model, or client-side business
  logic is introduced.

(source: promoted message 14)

**SCW-2 — Lifecycle, revisions, and security**

- A view id describes the current presentation surface; the adapter-issued
  legal action set determines transitions. Commands may revisit intake or
  preview, repeat checkpoints, or omit inapplicable views.
- One canonical workspace revision spans nested command loops. Every
  accepted state mutation increments it exactly once; rejected actions and
  progress-only delivery do not.
- Mutating actions are bound to workspace id, revision, action id,
  normalized payload/contract digest, adapter version, and a single-use
  nonce or idempotency key. Stale, altered, replayed, unknown, or concurrent
  actions fail closed with no partial mutation.
- Destructive or authority-sensitive actions require explicit server-issued
  confirmation. Read-only actions do not gain ceremony merely to satisfy
  the shared contract.

(source: promoted message 15)

**SCW-3 — Views, progress, and receipts**

- The shared schema supports composable intake, preview, execution,
  checkpoint-evidence, and terminal-receipt views without requiring every
  adapter to expose every view.
- Progress uses a monotonic event sequence independent of the workspace
  revision. Reconnecting clients resume after the last acknowledged event;
  a gap causes a canonical snapshot refresh, never guessed client state.
- Checkpoint evidence remains attached to canonical state but is not a
  terminal receipt. Only the command adapter can declare the interaction
  terminal.
- Terminal receipts describe the actual outcome, including partial or
  cancelled work, and are retrievable idempotently without re-execution.

(source: promoted message 16)

**SCW-4 — Adapter contract and command semantics**

- A small server-side adapter contract supplies the current view, legal
  actions, action validation, transition application, confirmation policy,
  execution delegation, progress projection, and receipt construction.
- Existing command/workflow business logic remains callable without a UI;
  adapters delegate to it rather than reimplementing it.
- Shared code contains no domain concepts such as round, seat, dissent,
  requirement, task approval, or release gate. Those remain typed,
  command-owned state.
- Duplicate adapter identifiers and unsupported semantic needs fail
  explicitly rather than falling through to a generic bag of data.

(source: promoted message 17)

**SCW-5 — Fix compatibility, migration, and client fallback**

- Fix is migrated onto the shared host contract as the compatibility and
  security witness. Its path validation, canonical rebuilding, contract
  hash, nonce consumption, at-most-once approval, and exact approved argv
  behavior remain unchanged.
- `/roundtable` and `/spec` are the first new adapters. Their skills become
  thin invocation/guidance surfaces after behavioral parity is proven;
  legacy entry paths remain until then.
- Widget, Markdown, text-only, polling, and headless JSON paths preserve the
  same legal actions and authority checks. An unsupported required control
  disables mutation and provides a safe fallback.
- Large decision and triage views must remain usable in the available
  viewport through compact batches, pagination, or working scrolling. The
  2026-08-31 seven-item promotion form that truncated without navigable
  scrolling is the baseline failure receipt.

(source: promoted message 18; observed surface receipt added to the
approved fallback scope)

**SCW-6 — Verification and live receipts**

- Contract, golden-render, malformed-input, property/fuzz, stale/replay,
  concurrency, reconnect, fallback, and nested-checkpoint tests run against
  the shared host contract and every registered adapter.
- Existing Fix security tests remain green and gain shared-invariant cases,
  including two concurrent confirmations producing at most one execution.
- `/roundtable` and `/spec` each require a non-mocked round trip through the
  real render → action → canonical-state boundary and a terminal receipt.
- Changed production code for this initiative carries at least **90%**
  coverage, stronger than the repository-wide 85% floor.
- Unit tests alone cannot certify rendering, persistence, subprocess,
  multi-provider, or reconnect boundaries; each requires its named live or
  behavioral receipt.

(source: message 21, replacing message 19 per chair modification)

**SCW-7 — Ten-example extensibility cohort**

- After Fix compatibility and the `/roundtable` + `/spec` pilots, the next
  ten adapters form an explicit extensibility cohort.
- The chair-fixed first two are **1. `/release-prep`** and
  **2. `/bug-predict`**. Both ship; neither is merely an alternative.
- Examples 3–10 are selected after the first two receipts to maximize
  semantic diversity across read-only/mutating, short/resumable,
  single/multi-agent, confirm-free/multi-gate, and success/partial/failure
  receipt shapes.
- Every example uses the shared renderer and host contract. A required core
  change must be classified as reusable lifecycle infrastructure or rejected
  as leaked command semantics.
- Cohort evidence records adapter code size, new shared-core changes,
  fallback parity, failures, and live receipts so stability is measured
  rather than declared.

(source: promoted message 20 plus chair ruling in message 11)

## Non-goals

- No new form-control system or renderer.
- No universal workflow state machine or low-code command builder.
- No client-side execution authority or callback serialization.
- No rewrite of the underlying workflow, round-table, spec, or release
  engines.
- No removal of legacy skill flows before parity, fallback, rollback, and
  live-boundary receipts exist.
- No claim that one view sequence fits every adapter.
- No automatic implementation authority from approval of this requirements
  artifact; every task retains its own chair gate.

## Counter-case

The strongest argument against this spec is that Fix plus two form-heavy
commands will overfit the abstraction. The mitigation is structural: extract
only mechanics already proven by Fix, make lifecycle transitions
adapter-issued rather than phase-implied, and require a ten-example cohort
whose first two deliberately stress opposite ends—multi-gate release work and
read-only diagnostics. If later adapters require domain concepts in the core,
the adapter boundary has failed and must be simplified before rollout.
