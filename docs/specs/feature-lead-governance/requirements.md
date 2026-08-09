# Feature Lead Governance — Requirements

**Status:** active (2026-08-08 triage refresh) — P1 FULL
ACTIVATION ruled 2026-07-30 at the D8 bar; lead/delegation is the
standing operating mode. Open: D14 review-debt register (unbuilt),
D13c conversation-opener one-pager (unbuilt). Tasks T1–T4 remain
draft in tasks.md — un-gated but unapproved, and no governance
module exists in-tree. History: approved 2026-07-27 with the
revision pass per decisions.md D1–D7 (thread
`q-feature-lead-governance-001`); originally execution-gated by P1.
**Slug:** `feature-lead-governance`
**Artifact tier:** Spec — cross-provider authority is a durable,
multi-session design choice.

## Problem

Claude and Codex bring useful independent skepticism to shared work,
but Attune currently defines no temporary authority for a model leading
a bounded module or feature. Handoff preserves context and cross-review
provides dissent; neither says who keeps the implementation coherent or
how competing model preferences are resolved. The result can be
reciprocal suspicion, preference-only rewrites, and architecture churn.

## Goal

Add a provider-neutral **feature lead** role for non-trivial,
cross-provider implementation. The lead owns coherence within an
explicit scope; reviewers own independent challenge; repository state,
verification receipts, and human rulings remain authoritative.

> The lead owns coherence. Reviewers own challenge. Evidence owns truth.
> The human chair owns unresolved tradeoffs.

## Requirements

### R1 — explicit, bounded assignment

Every governed work item has one active assignment containing:

- `lead`: a PROVIDER-level identity (D7 ruling — session ids are
  recorded as per-event evidence, never as the authority key;
  same-provider session resume is NOT a transfer);
- `scope`: explicit feature slug and repo-contained paths;
- `goal` and failure-sensitive acceptance criteria;
- `started_at`, lifecycle state, and optional expiry;
- `authority` and `constraints` using the fixed policy in R2.

Assignments are opt-in for trivial and single-agent work. They are
recommended when a feature crosses sessions/providers or when two
models may edit the same surface. Overlapping active lead scopes are
rejected against the MAIN-TRACKED registry (D4 ruling — main is the
global comparison set), unless a human explicitly records hierarchy
or disjoint sub-scopes.

### R2 — fixed authority boundary

The lead may:

- synthesize architecture inside the declared scope;
- decompose and sequence work;
- choose between requirement-satisfying implementation alternatives;
- accept, reject, or defer review findings with a written disposition;
- prepare the final handoff and completion recommendation.

The lead may not:

- waive repository rules, security findings, tests, or acceptance
  criteria;
- overwrite unrelated user or agent changes;
- suppress, rewrite, or misattribute reviewer findings;
- expand scope without a chair-evidenced assignment update (R5);
- merge, release, or declare disputed work complete on its own
  authority — those acts require the human chair;
- reject a finding because another provider authored it.

### R3 — evidence-based review contract

Reviewers remain independent and adversarial, including when they
review the lead's own code. Findings are ATOMIC and reviewer-owed at
record time (D3 ruling): one claim, exactly one classification
(`rule_violation` | `preference_only`), `rule_id` required iff
`rule_violation`. A mixed comment is a schema violation → one
re-prompt; on a failed retry the whole comment records as ONE
blocking `rule_violation` with `needs_split: true` — fail toward
visibility. Every `rule_violation` must name at least one of:

- a violated requirement or repository rule;
- a failing or missing failure-sensitive probe;
- a concrete regression, security, or maintainability risk;
- an inconsistency with an existing public interface or ratified
  decision.

Style preference without a named consequence is `preference_only`,
not a defect; it renders COLLAPSED with a count, never hidden (D3).
The original finding is immutable through every governance API; the
lead appends a per-finding disposition from the D3 vocabulary
(`fixed` | `rejected_with_reason` | `deferred` | `accepted_advisory`;
`accepted` alone is in-progress, never terminal), with rationale and
evidence. The finding schema is OWNED by the cross-review spec as a
versioned board record (D5/P2); governance consumes it and never
forks it.

### R4 — deterministic conflict resolution

Disagreements follow this order:

1. Current repository state and executable receipts.
2. Stated acceptance criteria and ratified project decisions.
3. Public interfaces and existing project conventions.
4. The feature lead's coherence decision.
5. Human-chair ruling when evidence is inconclusive, scope changes,
   risk is material, or a reviewer challenges the authority boundary.

`chair_required` pauses only the disputed decision; independent,
non-conflicting work may continue. No model may resolve its own
authority-boundary dispute.

### R5 — lifecycle, transfer, and release

Assignments have these states:

`proposed → active → transferred | completed | revoked`

- The four chair transitions — activation, CROSS-PROVIDER transfer,
  scope expansion, and revocation — are each evidenced by a
  chair-merged PR to the main-tracked registry (D7). No
  caller-supplied flag or MCP-relayed confirmation is evidence.
- Same-provider session succession is recorded as an automatic
  event, not a transfer (D7) — a lead provider resuming in a new
  session does not re-enter the chair queue.
- Transfer records old/new lead identities, reason, timestamp,
  current decisions, open findings, and verification receipts.
- Completion requires passing acceptance probes, no unresolved
  `chair_required` findings, and every `rule_violation` finding in a
  TERMINAL state (D3 — `accepted` is not terminal; accept-and-ignore
  cannot complete).
- Revocation is chair-only. An urgent revocation may set an advisory
  `revoke_pending` flag branch-side for immediacy; it carries no
  authority until the registry PR merges (D7).
- Scope changes may batch into one chair PR (D7 ceremony
  mitigation).
- Completion or revocation releases scope; no provider gains
  permanent ownership of a module.

### R6 — integration with existing Attune features

- `handoff_create`/`handoff_resume` carry REFERENCES only: the
  assignment ID, registry path, lifecycle state, and a content
  digest (D5 — handoffs never duplicate or establish authority
  state). Handoff remains context, not authority; resume verifies
  the digest and reports assignment drift.
- `/cross-review` records the assignment and authoring provider,
  selects a different provider where available, and returns
  immutable findings which the invoking session appends for
  separate lead disposition. Its ratified posture is untouched:
  board-only advisory, never a merge gate until dogfooded
  finding-quality earns it — and governance state must never be
  readable by any required check.
- The shared collaboration contract gains the behavioral rule; the
  machine-readable authority state lives in the main-tracked
  registry (D4), findings/events branch-side.
- Dynamic-team roles may consume the assignment, but role governance
  must not depend on any single provider being installed.

### R7 — truthful absence and degradation

- If the assigned lead is unavailable, Attune reports
  `lead_unavailable`; it does not silently appoint the reviewer or
  authoring model.
- If no independent reviewer is available, review reports `ABSENT`;
  it never simulates cross-provider review with the lead. `ABSENT`
  (seat missing/unauthenticated/timed out) is distinguished from
  probe FAILURE — live cross-provider receipts are conditional on
  seat availability and distribution lag, and degradation must be
  deterministic and stated.
- Read-only inspection continues without assignment writes. Mutating
  operations fail truthfully when workspace write access is denied.

### R8 — auditability without transcript capture

The assignment stores decisions and receipts, not chat transcripts or
hidden reasoning. Every event records actor, provider, role, timestamp,
action, and artifact reference, hash-chained to its predecessor (D7).
Telemetry may count lifecycle events and dispositions but must not
contain source code or prompt bodies.

## Acceptance criteria

- **AC-1:** Two active assignments with overlapping paths are rejected
  against the main-tracked registry — including when the second
  assignment originates on a different branch — unless a
  chair-recorded hierarchy/disjoint-scope rule exists.
- **AC-2:** No governance API can delete or rewrite a reviewer
  finding; a lead can only append a disposition. Out-of-band edits
  are DETECTED: an append-only-in-history validator fails when any
  existing finding/event line changed relative to the git parent,
  and a detected mismatch leaves the prior registry state
  authoritative.
- **AC-3:** A preference-only objection is classified separately,
  renders collapsed with a count, and cannot block completion
  without a named consequence or human ruling. For a split mixed
  comment, resolving the preference child never resolves the
  rule-violation child.
- **AC-4:** A failed required probe, an unresolved `chair_required`
  finding, or any `rule_violation` finding in a non-terminal state
  prevents `completed`.
- **AC-5:** Transfer preserves decisions, findings, receipts, and scope
  while changing lead identity in one auditable, chair-evidenced
  event.
- **AC-6:** A real Claude→Codex or Codex→Claude transfer resumes with
  the same scope and open-finding set against a recorded baseline
  (commit, scoped-file manifest, digest), then distinguishes
  irrelevant HEAD movement from SCOPED drift and flags only the
  latter.
- **AC-7:** Lead or reviewer absence is explicit; the system never
  substitutes self-review.
- **AC-8:** The collaboration projector reports no drift after the
  behavioral rule is added to the master and projected.
- **AC-9:** A chair-transition event whose approval evidence fails any
  forgery probe (non-ancestor merge SHA, non-chair or unsigned
  merger, registry-blob mismatch at the merge commit, broken event
  hash chain) is rejected and reported.
- **AC-10:** A branch with cross-review activity but no active
  assignment is flagged on the board (registry-vs-practice drift
  probe — the D7 bypass mitigation).

## Non-goals

- Permanent provider ownership of directories.
- Automatically choosing the “best” model for a module.
- Replacing CODEOWNERS, human maintainers, branch protection, or CI.
- Making all cross-review findings blocking.
- Autonomous merge, release, or scope expansion.
- Storing chain-of-thought or complete transcripts.

## Resolved decisions

OPEN-1..4 were ruled by the chair on 2026-07-27 (round-table thread
`q-feature-lead-governance-001`) and are recorded in
[decisions.md](decisions.md): D1 (`feature lead`), D5 (thin module +
P1 gate inheritance + P2 schema ownership), D4 (split registry), D3
(`preference_only` collapsed with count). D7 (approval evidence) is
the new ruling this revision folds in throughout.
