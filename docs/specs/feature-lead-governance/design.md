# Feature Lead Governance — Design

**Status:** DRAFT for review (2026-07-26)
**Slug:** `feature-lead-governance`

## Design posture

This is a governance layer over the pending cross-provider handoff and
cross-review features, not a third collaboration subsystem. The
canonical noun is **feature lead** because authority is temporary and
scope-bound; “lead programmer” remains acceptable UI copy.

## D1 — branch-scoped assignment artifact

One tracked file per governed branch:

```text
docs/assignments/<branch-slug>.yaml
```

The file is the portable, inspectable state shared by providers. The
first schema version is intentionally small:

```yaml
schema_version: 1
assignment_id: flg-<stable-id>
feature: feature-lead-governance
branch: codex/example
state: active
lead:
  provider: codex
  session: <opaque-session-id>
scope:
  paths:
    - src/attune/handoff/
goal: Preserve coherent cross-provider ownership for this feature.
acceptance:
  - id: ac-1
    claim: Overlapping active scopes are rejected.
    probe: uv run pytest tests/unit/governance/test_assignment.py -q
authority_profile: feature_lead_v1
open_findings: []
events: []
```

Paths are normalized, repo-contained after symlink resolution, and
overlap-checked. Prose and event sizes are capped; oversize values are
rejected, never silently truncated.

## D2 — pure governance core

Add a provider-agnostic core:

```text
src/attune/governance/
├── __init__.py
├── assignment.py   # schema, validation, lifecycle transitions
├── findings.py     # immutable finding + appended disposition
└── policy.py       # authority matrix and conflict-resolution result
```

Public operations return structured results and never invoke a model:

- `propose_assignment(...)`
- `activate_assignment(...)`
- `transfer_assignment(...)`
- `record_finding(...)`
- `dispose_finding(...)`
- `complete_assignment(...)`
- `revoke_assignment(...)`

Provider/session invocation stays in existing adapters. This keeps the
shared contract functional when only one provider is available.

## D3 — authority is policy, not prompt prose

`feature_lead_v1` is a fixed, versioned policy. Validation enforces:

- exactly one active lead;
- repo-contained, non-ambiguous scope;
- human activation, transfer, scope expansion, and revocation;
- immutable findings and append-only events;
- completion blocked by failed required probes or unresolved
  `chair_required` findings.

Prompts may explain the policy but cannot broaden it. A model-proposed
transition returns `chair_required` when human authority is needed.

## D4 — finding and disposition model

```text
Finding
  id, reviewer, provider, artifact, anchor, category, severity,
  claim, evidence, created_at

Disposition
  finding_id, lead, outcome, rationale, evidence, created_at
```

Findings are append-only. A disposition never mutates the finding.
Mechanical validation flags missing anchors/evidence and distinguishes
`preference_only`. The lead may reject a substantiated finding, but the
rationale remains visible; material rejection may be escalated by the
reviewer or human.

## D5 — integrate handoff and cross-review by reference

The assignment file owns governance state. Handoff frontmatter carries
only `assignment_id`, assignment path, state, and a content digest.
`handoff_resume` verifies the digest and reports assignment drift.

`/cross-review` accepts an optional assignment path:

- reviewer must differ from the authoring provider when possible;
- the review brief includes scope, acceptance IDs, and policy summary;
- raw findings are appended to the assignment by the moderator;
- lead dispositions happen separately, preserving reviewer text.

No governance data is duplicated into the board beyond IDs, summaries,
and artifact pointers.

## D6 — contract projection and UX

The master collaboration contract gains a short “Feature leadership”
section containing the R2/R3 behavioral rules and directing agents to
the active assignment artifact. The existing projector updates
`AGENTS.md` and `.claude/CLAUDE.md`.

Initial UX should be tool-first:

- `assignment_create`
- `assignment_status`
- `assignment_transfer`
- `assignment_dispose_finding`
- `assignment_complete`

The tools report recommendations and required human decisions; they do
not claim human approval. A later `/feature-lead` skill may make this
more conversational after dogfood proves the state model.

## D7 — observability and privacy

Structured events:

- assignment proposed/activated/transferred/completed/revoked;
- finding recorded/disposed/escalated;
- lead/reviewer unavailable;
- assignment drift detected on resume.

Fields are IDs, providers, lifecycle states, disposition category,
duration, and counts. Source text, code, prompts, and model reasoning
are excluded.

## Failure-sensitive test plan

- Unit: schema/path validation, overlap matrix, transition table,
  authority matrix, immutable findings, completion blockers.
- Security: traversal, symlink escape, malformed YAML, oversized
  content, forged human-approval flag.
- Integration: real MCP dispatch and assignment file round trip.
- Projection: edit master, project, then `--check` exits zero.
- Live: one feature led by Claude and reviewed by Codex; one led by
  Codex and reviewed by Claude; one transfer between them with a
  deliberately introduced drift warning.

## Alternatives rejected

- **Permanent model ownership:** creates silos and fossilizes current
  model strengths.
- **Lead decides everything:** weakens tests, security, and human
  control.
- **Reviewer vetoes everything:** recreates reciprocal suspicion as a
  blocking mechanism.
- **Prompt-only role:** unauditable and lost at provider/session
  boundaries.
- **Board-only state:** unavailable or ephemeral at exactly the handoff
  boundary this feature must survive.
