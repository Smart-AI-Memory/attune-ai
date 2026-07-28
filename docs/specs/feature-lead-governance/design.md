# Feature Lead Governance — Design

**Status:** approved (2026-07-27) — revision pass applied per
decisions.md D1–D7; execution gated by P1.
**Slug:** `feature-lead-governance`

## Design posture

This is a thin governance layer over the SHIPPED handoff-packet and
review-board seams (both T1+T2 on main since 10.6.x), not a third
collaboration subsystem. The canonical noun is **feature lead**
because authority is temporary and scope-bound; “lead programmer” is
acceptable UI copy only. Governance takes no dependency on unshipped
handoff/cross-review T3/T4 and no workflow-engine coupling until the
registry + disposition loop is dogfooded on one real feature (D5).

## D1 — split persistence: main registry + branch-side records

Authority and lifecycle state live in ONE tracked file per
assignment ON MAIN, mutated only by chair-merged PRs:

```text
docs/assignments/<assignment-id>.yaml
```

Findings and hash-chained events live BRANCH-SIDE next to the work,
with atomic writes; the branch artifact is deleted on merge (like
handoff files). Main is thereby the global comparison set for
overlap rejection — a second assignment on any branch is checked
against the registry, not against branch-local files.

Registry schema (v1, intentionally small):

```yaml
schema_version: 1
assignment_id: flg-<stable-id>
feature: feature-lead-governance
state: active
lead:
  provider: codex          # provider-level identity (D7)
scope:
  paths:
    - src/attune/handoff/
goal: Preserve coherent cross-provider ownership for this feature.
acceptance:
  - id: ac-1
    claim: Overlapping active scopes are rejected.
    probe: uv run pytest tests/unit/governance/test_assignment.py -q
authority_profile: feature_lead_v1
```

Branch-side event entries carry the D7 evidence block:

```yaml
event_id: <uuid>
event_type: activate | transfer | scope_change | revoke | succession
assignment_id: flg-<stable-id>
approval:                    # required on the four chair transitions
  pr_number: <int>
  merge_commit_sha: <sha>    # merge commit on main
  merged_by: <github-login>  # must be in the chair allowlist
  registry_blob_sha: <sha>   # blob of the registry file AT merge_commit
lead:
  provider: claude | codex | antigravity
session: <opaque-id>         # evidence only, never the authority key
timestamp: <iso8601>
prev_event_digest: <sha256>  # hash chain
```

Paths are normalized, repo-contained after symlink resolution, and
overlap-checked against the registry. Prose and event sizes are
capped; oversize values are rejected, never silently truncated.
Writers assume SINGLE-WRITER discipline (the invoking lead session is
the only branch-side writer in practice); the core enforces atomic
replace-on-write and rejects a write whose base digest is stale.

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
- `record_finding(...)`
- `dispose_finding(...)`
- `verify_chair_transition(...)` — the D7 probe set
- `check_completion(...)` — terminal-state gate

Chair transitions (activate / cross-provider transfer / scope-expand
/ revoke) have NO mutating core API that asserts approval — they are
edits to the main registry that land via chair-merged PRs; the core
only VERIFIES them (D7). Provider/session invocation stays in
existing adapters. The shared contract works when only one provider
is available.

## D3 — authority is policy, verified against git, not prompt prose

`feature_lead_v1` is a fixed, versioned policy. Validation enforces:

- exactly one active lead per registry file;
- repo-contained, non-ambiguous scope;
- the four chair transitions carry D7 approval evidence that passes
  every forgery probe:
  1. `merge_commit_sha` is an ancestor of `origin/main`
     (kills fabricated SHAs);
  2. the PR resolves host-side, `merged_by` is in the repo-owned
     chair allowlist, and the merge commit's signature verifies
     (kills unsigned/non-chair merges);
  3. the registry blob recomputed at the merge commit equals
     `approval.registry_blob_sha` (kills replay against a real but
     unrelated chair merge);
  4. the event hash chain and the registry transition diff match the
     event type and sequence (kills history tampering);
- immutable findings and append-only events as APPLICATION
  invariants, with out-of-band edits DETECTED by the
  append-only-in-history validator (a detected mismatch leaves the
  prior registry state authoritative);
- completion blocked by failed required probes, unresolved
  `chair_required` findings, or any non-terminal `rule_violation`.

Prompts may explain the policy but cannot broaden it. A
model-proposed chair transition returns `chair_required` plus the
registry-PR instructions; it never claims approval.

## D4 — finding and disposition model

The finding schema is OWNED by the cross-review spec as a versioned
board record (P2); governance consumes it. Shape:

```text
Finding
  id, parent_comment_id?, reviewer, provider, artifact, anchor,
  classification (rule_violation | preference_only), rule_id?,
  severity, claim, evidence, needs_split?, created_at

Disposition
  finding_id, lead, outcome
  (fixed | rejected_with_reason | deferred | accepted_advisory),
  rationale, evidence, resolved_by_event_id?, created_at
```

- Findings are atomic and reviewer-owed at record time; the recorder
  validates one claim + one classification and re-prompts once on a
  mixed comment; the failed-retry fallback records the whole comment
  as one blocking `rule_violation` with `needs_split: true`.
- A disposition never mutates the finding; dispositions are per
  atomic finding, never per comment.
- `accepted` is in-progress (`open → accepted → fixed | disputed`);
  the completion gate counts TERMINAL states of `rule_violation`
  findings only. `preference_only` renders collapsed with a count.
- The lead may reject a substantiated finding
  (`rejected_with_reason`); the rationale remains visible; material
  rejection may be escalated by the reviewer or human.

## D5 — thin module on shipped seams (ruled, replaces the draft D5)

Per the chair ruling (post-steelman, thread
`q-feature-lead-governance-001`):

- Governance ships as its own thin module consuming the SHIPPED
  handoff-packet and board seams. A cross-provider transfer IS a
  handoff packet whose frontmatter carries `assignment_id` +
  `approval.merge_commit_sha`, checked by the already-shipped digest
  verify — which is also the resume-tamper probe.
- **P1 — gate inheritance:** governance activation sits behind the
  SAME chair usage-signal read that gates cross-review T3/T4; no
  second activation criterion exists.
- **P2 — single schema owner:** cross-review owns the finding
  schema; governance consumes the versioned record; hash-chain and
  probe machinery stays single-homed.
- No parallel assignment/approval/disposition stores; any field
  governance needs on the packet or board is proposed as a T3
  amendment to the owning spec, never a parallel format.
- Cross-review's ratified posture is untouched: board-only advisory,
  never a merge gate — a drift-guard test asserts no governance
  state is readable by any required check.

## D6 — contract projection and UX

The master collaboration contract gains a short “Feature leadership”
section containing the R2/R3 behavioral rules and directing agents to
the active registry. The existing projector updates `AGENTS.md` and
`.claude/CLAUDE.md`.

Tool-first UX, shrunk to lead-authority actions (D7):

- `assignment_propose`
- `assignment_status`
- `assignment_dispose_finding`

Transfer/complete/revoke REQUESTS are proposals: the tools return
`chair_required` with the registry-PR instructions and never claim
human approval. A later `/feature-lead` skill may make this more
conversational after dogfood proves the state model.

## D7 — observability and privacy

Structured events:

- assignment proposed/activated/transferred/completed/revoked;
- same-provider session succession;
- finding recorded/disposed/escalated;
- lead/reviewer unavailable;
- assignment drift detected on resume;
- forgery-probe rejection (which probe failed);
- registry-vs-practice drift (review activity without assignment).

Fields are IDs, providers, lifecycle states, disposition category,
duration, and counts. Source text, code, prompts, and model reasoning
are excluded.

## Failure-sensitive test plan

- Unit: schema/path validation, registry overlap matrix (including
  the cross-branch case via the main registry), transition table,
  authority matrix, immutable findings, terminal-state completion
  blockers, mixed-comment split + fallback.
- Security: traversal, symlink escape, malformed YAML, oversized
  content, and one test per D3 forgery probe (fabricated SHA,
  non-chair merger, registry-blob replay, broken hash chain).
- History: the append-only-in-history validator fails when a prior
  finding/event line changes relative to the git parent.
- Integration: real MCP dispatch and registry/branch-record round
  trip; handoff packet carrying assignment reference + digest.
- Projection: edit master, project, then `--check` exits zero.
- Live (conditional on seat availability AND distribution — the
  Codex/Antigravity seats consume the PUBLISHED attune-ai, so the
  matrix waits for a release carrying the governance tools): one
  feature led by Claude and reviewed by Codex; one led by Codex and
  reviewed by Claude; one transfer between them with a deliberately
  introduced SCOPED drift (and an irrelevant HEAD move that must NOT
  flag).

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
- **Branch-scoped authority files (the draft's D1):** structurally
  cannot enforce AC-1 across branches and cannot evidence chair
  approval; replaced by the main registry (D4/D7 rulings).
- **MCP-asserted human approval:** the confirmation relay transits
  the agent and is forgeable; replaced by chair-merged registry PRs
  verified out-of-band (D7).
- **Governance as cross-review T3 (steelman minority):** a real
  design (board message 14) — kept out to avoid housing authority
  state in a spec whose ratified advisory posture is untouchable;
  its two demonstrated advantages ship anyway as P1 and P2.
