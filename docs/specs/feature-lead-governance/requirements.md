# Feature Lead Governance — Requirements

**Status:** DRAFT for Patrick review (2026-07-26)
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

- `lead`: provider/session identity, not merely a model family;
- `scope`: explicit feature slug and repo-contained paths;
- `goal` and failure-sensitive acceptance criteria;
- `started_at`, lifecycle state, and optional expiry;
- `authority` and `constraints` using the fixed policy in R2.

Assignments are opt-in for trivial and single-agent work. They are
recommended when a feature crosses sessions/providers or when two
models may edit the same surface. Overlapping active lead scopes are
rejected unless a human explicitly records hierarchy or disjoint
sub-scopes.

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
- expand scope without a human-approved assignment update;
- merge, release, or declare disputed work complete on human authority;
- reject a finding because another provider authored it.

### R3 — evidence-based review contract

Reviewers remain independent and adversarial, including when they
review the lead's own code. Every actionable objection must name at
least one of:

- a violated requirement or repository rule;
- a failing or missing failure-sensitive probe;
- a concrete regression, security, or maintainability risk;
- an inconsistency with an existing public interface or ratified
  decision.

Style preference without a named consequence is
`preference_only`, not a defect. The original finding is immutable;
the lead appends a disposition of `accepted`, `rejected`,
`deferred`, or `chair_required`, with rationale and evidence.

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

- Activation requires a human-confirmed goal, scope, lead, and
  acceptance criteria.
- Transfer records old/new lead identities, reason, timestamp, current
  decisions, open findings, and verification receipts.
- Completion requires acceptance probes and no unresolved
  `chair_required` findings.
- Revocation is human-only and records a reason.
- Completion or revocation releases scope; no provider gains permanent
  ownership of a module.

### R6 — integration with existing Attune features

- `handoff_create`/`handoff_resume` carry the assignment ID, lead,
  lifecycle state, open findings, and transfer history. Handoff remains
  context, not authority; resume verifies the assignment against the
  current tree.
- `/cross-review` records the assignment and authoring provider,
  selects a different provider where available, and returns immutable
  findings for lead disposition.
- The shared collaboration contract gains the behavioral rule; the
  machine-readable assignment remains in one tracked branch-scoped
  artifact.
- Dynamic-team roles may consume the assignment, but role governance
  must not depend on any single provider being installed.

### R7 — truthful absence and degradation

- If the assigned lead is unavailable, Attune reports
  `lead_unavailable`; it does not silently appoint the reviewer or
  authoring model.
- If no independent reviewer is available, review reports `ABSENT`; it
  never simulates cross-provider review with the lead.
- Read-only inspection continues without assignment writes. Mutating
  operations fail truthfully when workspace write access is denied.

### R8 — auditability without transcript capture

The assignment stores decisions and receipts, not chat transcripts or
hidden reasoning. Every event records actor, provider, role, timestamp,
action, and artifact reference. Telemetry may count lifecycle events
and dispositions but must not contain source code or prompt bodies.

## Acceptance criteria

- **AC-1:** Two active assignments with overlapping paths are rejected
  unless a human-approved hierarchy/disjoint-scope rule exists.
- **AC-2:** A reviewer finding cannot be deleted or rewritten; a lead
  can only append a disposition.
- **AC-3:** A preference-only objection is classified separately and
  cannot block completion without a named consequence or human ruling.
- **AC-4:** A failed required probe or unresolved `chair_required`
  finding prevents `completed`.
- **AC-5:** Transfer preserves decisions, findings, receipts, and scope
  while changing lead identity in one auditable event.
- **AC-6:** A real Claude→Codex or Codex→Claude transfer resumes with
  the same scope and open-finding set, then detects a deliberately
  changed HEAD or file set.
- **AC-7:** Lead or reviewer absence is explicit; the system never
  substitutes self-review.
- **AC-8:** The collaboration projector reports no drift after the
  behavioral rule is added to the master and projected.

## Non-goals

- Permanent provider ownership of directories.
- Automatically choosing the “best” model for a module.
- Replacing CODEOWNERS, human maintainers, branch protection, or CI.
- Making all cross-review findings blocking.
- Autonomous merge, release, or scope expansion.
- Storing chain-of-thought or complete transcripts.

## Open decisions for review

- **OPEN-1:** User-facing name: `feature lead` (recommended) versus
  `lead programmer`.
- **OPEN-2:** First surface: extend the pending handoff/cross-review
  stack (recommended) versus ship a standalone assignment tool first.
- **OPEN-3:** Assignment persistence: branch-scoped tracked YAML/JSON
  artifact (recommended) versus board-only state.
- **OPEN-4:** Whether `preference_only` findings are hidden by default
  or shown in a collapsed section.
