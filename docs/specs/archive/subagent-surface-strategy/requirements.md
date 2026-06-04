# Spec: Subagent Surface Strategy

> Closes the recurring carryover-briefing item "1 agent
> (`setup-guide`) vs 15 skills — no movement." The imbalance has
> been twice analyzed and twice retired. This spec documents
> *why* the ratio is the right shape given current architecture
> and names the one residual angle worth a separate spec if
> appetite ever surfaces.

**Status:** approved (2026-05-31) — see [decisions.md](./decisions.md)
**Created:** 2026-05-31
**Owner:** —
**Related:**
- [`agent-surface-rebalance`](../agent-surface-rebalance/) (retired 2026-05-12 — context-bleed premise was false because MCP isolates)
- [`agent-surface-parallelism-evaluation`](../agent-surface-parallelism-evaluation/) (retired 2026-05-29 — proposed orchestrator already ships in `deep_review.py`)
- [`docs-release-prep`](../docs-release-prep/) (carryover-drain context for 2026-05-31)
- The morning briefing's recurring un-actioned-items table

---

## Phase 1: Requirements

**Status:** approved (2026-05-31; recommendation in
[decisions.md](./decisions.md) — close the carryover, no
follow-up needed unless appetite for the remediation pattern
surfaces)

### Problem statement

The daily briefing's un-actioned-items table has repeatedly
surfaced the asymmetry:

> Subagent surface vs skills — still 1 agent (`setup-guide`)
> vs 15 skills; gap noted in prior briefings, no movement.

The carryover phrasing implies the ratio is itself evidence of
a gap. But the briefing's grounding rule (per
[`spec-status-self-truthing/decisions.md`](../spec-status-self-truthing/decisions.md))
requires checking whether the work has already been thought
through before recommending it as "fresh."

Two prior specs already addressed angles of this question:

1. **`agent-surface-rebalance`** (2026-05-12) — proposed
   converting analytical skills (security-audit, refactor-plan)
   to subagents to reduce main-agent context bloat. **Retired
   after Phase 0 measurement** showed MCP-invoked SDK workflows
   already isolate intermediate `AssistantMessage` bytes inside
   the workflow's SDK session; only `WorkflowResult.final_output`
   crosses to the main agent (3,710 B for security-audit, 486 B
   for refactor-plan). The premise was false.

2. **`agent-surface-parallelism-evaluation`** (2026-05-29) —
   proposed an orchestrator subagent that fans out multiple
   analytical workflows in parallel. **Retired after probe**
   found the proposed orchestrator already ships in
   `deep_review.py` (which spawns parallel subagents
   internally).

So conversion-for-isolation = not needed; parallelism-via-
orchestrator = already shipped. What's actually left to ask?

### Scope

**In scope (this spec, one-pass):**

- Document the architectural reasoning: WHY 1 agent / 15 skills
  is the right shape today, not a gap.
- Name the one residual angle (remediation pattern) so the
  briefing's grounding rule has a record to point at.
- Close the carryover-briefing item with a documented
  resolution, so future briefings don't keep surfacing it.

**Out of scope:**

- Conversion of any existing skill to a subagent. Retired by
  `agent-surface-rebalance`.
- Parallel orchestrator subagent. Retired by
  `agent-surface-parallelism-evaluation`.
- The remediation pattern itself (fix-test-like agents that
  take action, iterate, re-check). If pursued, it earns its
  own spec from scratch — not a sub-phase of this one.
- Changing the existing `setup-guide` agent. It's the
  reference implementation of the detect-and-adapt pattern and
  works correctly.

### Architectural reasoning

**Skills are right for:**

- Workflow dispatch — a skill points the main agent at an
  MCP tool, which runs the actual work in an isolated SDK
  session. The skill is essentially a routing instruction +
  context document.
- Conversational / Socratic flows — `coach`, `planning`,
  `spec` need the main agent's context to participate in a
  multi-turn discussion with the user. A subagent would lose
  that conversational thread.
- User-facing entry points — `/security`, `/coach`,
  `/release` need to look like skills to users (skills are
  Claude Code's primary surface). A subagent here would add
  indirection without value.

**Subagents are right for:**

- **Environment detection + adaptive guidance** — `setup-guide`
  is the canonical example. It needs its own tool palette
  (`Bash`, `Read`) bounded for safety, runs a finite
  detection sequence, and produces a structured report. A
  skill would mix this detection logic into the main agent's
  context.
- **Remediation loops** *(none today)* — an agent that takes
  action, observes the result, decides next action,
  iterates. `fix-test` is the closest existing capability
  but it's currently a skill that delegates to a workflow
  rather than a true remediation agent. The retired
  `agent-surface-rebalance` D4 noted this as a "different
  shape entirely; earns its own spec."

The 1:15 ratio isn't a gap — it reflects that detect-and-adapt
patterns are rare in attune's current scope (just `setup-guide`)
and remediation patterns are unbuilt (zero today).

### The residual question

**Remediation pattern as a subagent.** `fix-test` today is a
skill that runs a workflow which itself attempts fixes. The
loop is encoded in the workflow, not in a subagent. A
hypothetical alternative:

```text
User: "this test is failing"
  ↓
Skill: "I'll spawn a fix-test agent"
  ↓
Subagent (with Edit/Bash tools, bounded turns):
  1. Run the test, observe failure
  2. Read related source, hypothesize fix
  3. Apply fix, re-run
  4. If still failing and turns remain: iterate
  5. If turns exhausted: report what was tried
  ↓
Skill: surfaces the subagent's report to the user
```

Whether this is better than the current workflow-internal loop
depends on:

- Whether the agent's per-turn replanning is meaningfully
  different from the workflow's templated retry logic.
- Whether bounded-tool isolation (subagent can't accidentally
  modify unrelated files) is a real win.
- Whether the wall-clock cost (each turn is a full LLM call)
  is acceptable.

This is **not analyzed in this spec**. It earns its own spec
if and when there's a concrete trigger — e.g. a fix-test
failure pattern that the current workflow consistently misses,
or a user complaint about over-broad file edits.

### Acceptance criteria

This spec is "done" when:

- [x] `requirements.md` documents the architectural reasoning
  for 1:15.
- [x] `decisions.md` records the close-the-carryover decision
  with rationale.
- [ ] The carryover-briefing item "Subagent surface vs skills"
  is removed from the next un-actioned-items table on next run
  (briefing skill's grounding pass should now find this spec
  and elide the item).

### Out of band

There's nothing to build. This is a documentation spec that
closes a recurring item. The architecture analysis IS the
deliverable.

---

## Phase 2: Design

**Status:** N/A — no implementation work.

This spec doesn't move past Phase 1; the analysis itself is
the artifact. See [decisions.md](./decisions.md) for the
resolution.

---

## Phase 3: Tasks

**Status:** N/A — no implementation work.

If the remediation-pattern question ever surfaces with concrete
appetite, draft a NEW spec (`remediation-agent-pattern` or
similar) — not a Phase 3 of this one. The shape is too
different.
