# Shared Command Workspaces — Design

**Status:** completed (2026-08-31) — implemented and verified through Tasks
1–7.
**Last updated:** 2026-08-31

## Verified baseline

The current code already contains both halves needed for a thin extraction:

- `attune_forms.workspace` provides validated `WorkspaceView`,
  `WorkspaceAction`, `WorkspaceSection`, `WorkspaceBlock`,
  `WorkspaceActionBinding`, widget rendering, Markdown rendering, and
  structural action collection.
- The standalone `attune-forms` MCP exposes
  `elicitation_render_workspace` and
  `elicitation_collect_workspace_action`.
- `src/attune/elicitation/fix_workspace.py` owns the authoritative Fix
  state. It canonicalizes answers, rebuilds the executable preview, binds
  revision + nonce + contract hash, consumes authority before returning an
  approved argv, and never executes the command itself.
- `src/attune/mcp/server.py` currently stores Fix workspaces and exposes
  Fix-specific preview/action handlers.

The gap is not rendering. It is a reusable host authority seam and typed
command adapters.

## Layer boundary

```text
skill / CLI / MCP entry
          |
          v
CommandWorkspaceHost (attune-ai, canonical authority)
          |
          +-- adapter: Fix / Roundtable / Spec / ...
          |      owns normalized state + legal transitions
          |
          v
WorkspaceView + WorkspaceActionBinding (attune-forms, data only)
          |
          +-- widget renderer
          +-- Markdown/text fallback
          +-- structural response validator
```

`attune-forms` validates that a response belongs to the exact rendered view
and optional binding. `attune-ai` then compares it with canonical state,
rebuilds the command-owned contract, consumes authority, and returns a typed
host action. Neither layer accepts an executable callback from the client.

## Host contract

The first implementation should be a protocol plus plain data, not a deep
class hierarchy:

```python
class CommandWorkspaceAdapter(Protocol):
    adapter_id: str
    schema_version: int

    def create(
        self,
        intake: Mapping[str, object],
        *,
        prior_state: object | None = None,
    ) -> object: ...
    def project(self, state: object) -> CommandWorkspaceProjection: ...
    def apply(
        self,
        state: object,
        action: WorkspaceActionResponse,
    ) -> CommandWorkspaceTransition: ...

class CommandWorkspacePublisher(Protocol):
    def publish(
        self,
        state: object,
        event: Mapping[str, object],
    ) -> CommandWorkspaceTransition: ...
```

`CommandWorkspaceProjection` contains the exact `WorkspaceView` plus its
normalized authority digest. `CommandWorkspaceTransition` contains the
adapter-owned successor state, terminal flag, portable result mapping, and
an `authority_changed` flag used only for trusted progress publication. It
never contains an executable callback or client-supplied command. The host
owns a versioned envelope:

```text
workspace_id          stable interaction identity
adapter_id/version    command-specific decoder and compatibility key
revision              one counter for canonical mutable state
state                 adapter-owned canonical serialized state
view                   current presentation projection
contract_hash         digest of normalized state + legal action contract
action_nonce          single-use authority for the rendered revision
terminal              adapter-declared terminal state
event_sequence        progress delivery cursor, separate from revision
```

Every accepted mutation yields a new revision and binding. Progress delivery
increments only `event_sequence` unless it changes canonical state or legal
actions. A client cannot combine a view from one revision with authority from
another. The host validates workspace id, adapter identity/version, current
projection equality, contract hash, revision, nonce, action membership, and
confirmation before the adapter receives a `WorkspaceActionResponse`; those
authority fields are intentionally absent from `adapter.apply()`.

Trusted moderator/executor progress enters through
`CommandWorkspacePublisher.publish()`. A progress-only transition must retain
the view id, legal actions, form, and contract hash or the host rejects it;
otherwise publication advances both revision and `event_sequence`.

## Non-linear views and checkpoints

The existing `WorkspaceViewId` values—intake, preview, execution, receipt—are
presentation categories, not an enforced transition graph. The adapter
returns the legal actions for each revision. A round-table execution may
therefore pause for another-round approval, return to execution, pause for
promotion triage, and only then emit a receipt. A spec may alternate task
execution and approval checkpoints.

Consequential actions bind confirmation to:

```text
(workspace_id, revision, adapter_id/version, action_id,
 normalized_payload_digest, contract_hash, nonce)
```

The adapter's stage/checkpoint identity and legal action set are inputs to the
contract hash, so no separate client-controlled `checkpoint_id` exists. Any
intervening mutation invalidates the binding. Read-only navigation can omit
explicit confirmation, but it still requires membership in the exact
server-issued view and passes through the same serialized host collection;
action-bearing non-form views also carry the current revision, contract hash,
and single-use nonce.

## Pilot adapters

### Roundtable

- Intake: question, expected round budget, and any allowed invocation caps;
  the fixed roster remains command-owned policy.
- Preview: roster, spend gate, recording destination, and absent-seat rules.
- Execution: per-seat status, compiler-gate results, follow-up questions,
  synthesis, and bounded next-round checkpoints.
- Promotion checkpoint: compact/paginated per-item chair rulings.
- Receipt: thread id, seat receipts, halt reason, promoted message ids,
  tracked destination, and absent/degraded seats.

### Spec

- Intake: reuse `spec_intake` and its tree-derived candidates.
- Preview: outcome, done-when, owning area, planned artifacts, and lifecycle
  gate expectations.
- Execution: task progress, gate results, redo/approve checkpoints, and
  resumable state.
- Receipt: created/updated artifact paths, approved task ids, exact probes,
  results, and remaining gated work.

## Fix migration rule

Fix migrates only after characterization tests name its security properties.
The generic host may own workspace storage, revision comparison, binding
validation, and nonce consumption. Fix continues to own answer vocabulary,
preview rebuilding, contract hashing input, legal actions, and approved argv.
The migration is rejected if any existing replay or mutation test weakens.

## Fallback and viewport behavior

Widget and Markdown renderings are projections of the same `WorkspaceView`.
Missing rich capabilities cannot broaden the legal action set. Large triage
surfaces use bounded batches or pagination. The page cursor is adapter-owned
canonical state, and each page-changing action is collected by the host,
advances the revision, and reissues authority; viewport parameters never
bypass canonical state through `project()`. If the host dialog cannot scroll,
the portable fallback must remain operable. The seven-item truncated dialog
observed while approving this spec is a regression fixture, not an anecdote.

## Cohort selection

`/release-prep` and `/bug-predict` are fixed examples 1 and 2. After their
receipts, examples 3–10 are chosen to fill missing cells in this matrix:

| Axis | Contrasting shapes |
| --- | --- |
| Authority | read-only / mutating |
| Duration | one-shot / resumable |
| Orchestration | single executor / multi-agent |
| Gating | confirm-free / repeated chair gates |
| Outcome | success-only / partial and failed receipts |
| Input | small fixed schema / derived candidates and large triage |

No candidate is selected merely because it is easy to adapt.

## Verification strategy

The receipt ladder is ordered from cheapest to most boundary-sensitive:

1. schema and contract tests for every registered adapter;
2. shared state-machine and adversarial action tests;
3. golden widget + Markdown equivalence tests;
4. concurrency and reconnect tests;
5. live Fix compatibility receipt;
6. live Roundtable and Spec lifecycle receipts;
7. one receipt per cohort adapter, including its fallback path.

Changed production code must reach 90% coverage. A green unit suite cannot
replace the live renderer/action, persistence, subprocess, or multi-provider
receipts.
