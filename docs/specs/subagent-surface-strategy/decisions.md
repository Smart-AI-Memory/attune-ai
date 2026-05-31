# Per-decision log — Subagent surface strategy

Append-only log. Single decision recorded 2026-05-31 that
closes the recurring carryover-briefing item.

---

## D1 — Close the carryover; the 1:15 ratio is the right shape (2026-05-31)

**Decision:** **Close the "subagent surface vs skills" carryover
item.** The 1-agent / 15-skill ratio reflects current
architecture correctly. The two angles a future briefing might
re-surface (conversion for context isolation, parallel
orchestrator) are both retired with measurement. The one
residual angle (remediation pattern) earns its own spec only
if concrete appetite surfaces — not a sub-phase of this one.

**What the carryover briefing surfaces and why:**

The morning briefing's un-actioned-items table has repeatedly
listed:

> Subagent surface vs skills — still 1 agent (`setup-guide`)
> vs 15 skills; gap noted in prior briefings, no movement.

The phrasing implies the ratio itself is evidence of a gap.
The grounding rule added by
[`spec-status-self-truthing`](../spec-status-self-truthing/)
requires checking whether the work has already been thought
through before recommending it as fresh. It has — twice.

**What's already been decided:**

| Angle | Spec | Outcome | Why |
|---|---|---|---|
| Convert analytical skills to subagents for context isolation | [`agent-surface-rebalance`](../agent-surface-rebalance/) | Retired 2026-05-12 | MCP already isolates intermediate `AssistantMessage` bytes inside the workflow's SDK session. Only `WorkflowResult.final_output` crosses (3,710 B for security-audit, 486 B for refactor-plan). Conversion saves zero bytes. |
| Parallel orchestrator subagent for multi-workflow sessions | [`agent-surface-parallelism-evaluation`](../agent-surface-parallelism-evaluation/) | Retired 2026-05-29 | Probe found the proposed orchestrator already ships in `deep_review.py`, which fans out parallel subagents internally. |
| Document the architectural reasoning to close the carryover | (this spec) | Approved 2026-05-31 | One-pass spec; analysis IS the deliverable. |
| Remediation pattern as a subagent (fix-test-shaped agents that take action, iterate, re-check) | (none yet) | Deferred | Different shape entirely; earns its own spec only when concrete appetite surfaces (per `agent-surface-rebalance/decisions.md` D4 already-recorded recommendation). |

**Rationale:**

- **The ratio reflects scope, not gap.** Detect-and-adapt
  patterns (the `setup-guide` shape) are rare in attune's
  current surface — there's basically only one of them today.
  Remediation patterns aren't built (zero today). Both of these
  are subagent-shaped, but neither has been needed at scale.
- **Skills cover the dominant use case.** Every workflow
  dispatch, every conversational/Socratic flow, every
  user-facing entry point fits the skill shape better than a
  subagent shape. Adding a subagent for any of these would add
  indirection without value (the
  [`agent-surface-rebalance` D4 skills survey](../agent-surface-rebalance/skills-survey.md)
  closed this loop file-by-file).
- **The briefing's grounding pass should now skip this item.**
  With this spec on `main`, the briefing's grounding rule
  (per [`spec-status-self-truthing/decisions.md`](../spec-status-self-truthing/decisions.md))
  will find a documented resolution and elide the carryover
  rather than re-surfacing it as fresh work.

**Alternatives considered:**

- **Re-litigate the conversion angle.** Rejected — two
  measurement passes already invalidated the premise. A third
  pass with the same premise would burn cost for the same
  answer.
- **Author the remediation-pattern spec preemptively.**
  Rejected — no concrete trigger exists. Preemptive spec
  authoring without appetite tends to produce abstract
  artifacts that nobody picks up. Wait for a concrete pain
  point (e.g. a fix-test failure pattern the current workflow
  consistently misses) before drafting.
- **Add subagents for individual skills that "feel"
  underused.** Rejected — skill underuse is a discoverability
  / UX problem, not a shape problem. A different spec class
  (skill-discoverability or similar) would address that.

**Implementation note:**

The "implementation" of this decision is the documentation
itself. No code changes. After this PR merges:

1. The carryover-briefing item should stop appearing once
   `spec-status-self-truthing` is fully implemented (its
   Phase 4 will make the briefing's grounding rule
   automatically find this spec's `approved` status).
2. Until then, the briefing skill author (or whoever runs
   the briefing) can manually skip this item by referencing
   this spec.

**Trigger for re-opening:**

If a concrete remediation-pattern need surfaces — e.g. a
fix-test failure mode the current workflow consistently misses,
or a user complaint about over-broad edits — that's the
signal to draft a NEW spec (`remediation-agent-pattern` or
similar), not to re-open this one. This spec stays closed
even if related work lands.
