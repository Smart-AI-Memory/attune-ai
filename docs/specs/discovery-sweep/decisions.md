# discovery-sweep — decisions

Mirror of key design decisions from
`.claude/plans/discovery-sweep.md`. The plan is the executable
spec; this file is the durable record of *why* the design landed
where it did.

## Status

- **Phase 1 shipped:** 2026-05-13 — engine as Python API, six
  tasks complete, 105 tests passing.
- **Phase 2A shipped:** 2026-05-13 — `PatternScanSource`
  deterministic adapter (no LLM cost), `DiscoverySweepWorkflow`
  BaseWorkflow CLI wrapper, registered in the workflow
  registry. `attune workflow run discovery-sweep --path
  <module>` now produces real findings end-to-end. 127 tests
  total (105 Phase 1 + 22 Phase 2A).
- **Phase 2B planned:** see [phase-2.md](phase-2.md).

## Decision 1 — Discovery and resolution are split

Discovery (read-only scan, verification, queue write) runs
autonomously. Resolution (actually fixing the bug) stays
interactive with Patrick.

**Why:** Agents are reliable at pattern-matching at scale,
unreliable at judgment calls on fixes. Existing autonomous
workflows (bug_predict, security_audit, deep_review) have
documented false-positive patterns (perf-audit on `dirs[:]`,
bug-predict on `subprocess_exec`, deep-review fabrication). The
discovery half scales; the resolution half doesn't.

**How to apply:** Anything that mutates code, commits, pushes,
or otherwise leaves the read-only boundary belongs in
resolution, not discovery.

## Decision 2 — Verification rules grounded in CLAUDE.md lessons

REJECT rules in the verification engine target false positives
documented in `CLAUDE.md` lessons — not theoretical false
positives, but ones already hit in production sessions.

**Why:** Theoretical rules accumulate maintenance cost and
risk false REJECTs. Documented lessons are pre-validated by
historical pain.

**How to apply:** When adding a REJECT rule, cite the
`CLAUDE.md` lesson it grounds in. When a verification rule
proves wrong in dogfood, fix the rule OR remove it; do not
silently widen its guards.

## Decision 3 — Resolution complexity is a tag, not a queue-entry gate

`needs_patrick` is metadata on ACCEPTed findings (Patrick's
triage filter), not a discovery-time decision to escalate.

**Why:** Original framing had ESCALATE blocking sweep
progression. Patrick clarified the trigger criteria were about
the *resolution* decision (we know it's real but want
judgment on the fix), not the *queue-entry* decision (whether
the agent is sure it's a real bug). With that clarification:

- The discovery agent's only job is real-vs-false-positive
- Real findings always enter the queue
- The complexity tag tells Patrick which queue items deserve
  more attention at triage time

**How to apply:** The verification engine decides
REJECT/ACCEPT/UNSURE. The complexity classifier only runs on
ACCEPT and only sets `routine` or `needs_patrick`. Never use
complexity as a gate.

## Decision 4 — File formats: JSONL + Markdown, by audience

- Queue (`<sweep_id>.jsonl`) — JSONL, tool consumption (jq /
  streaming)
- Rejected (`<sweep_id>.rejected.jsonl`) — JSONL, audit log
- Questions (`<sweep_id>.questions.md`) — Markdown,
  human-reviewable cold

**Why:** JSONL streams and pipes well for tooling; markdown
reads well for humans without rendering. UNSURE findings need
to be reviewable a day later without context — markdown carries
the surrounding reasoning naturally.

**How to apply:** Don't unify the three files into one format.
The audience asymmetry is load-bearing.

## Decision 5 — Output is gitignored by default

`.claude/discovery-queue/` is in `.gitignore`.

**Why:** Sweep output is ephemeral triage state. Most queues
don't need durable history; the ones that do can be committed
by-path. Tracking every sweep would bloat the repo.

**How to apply:** If Patrick wants the audit trail of a
specific sweep in git, `git add -f .claude/discovery-queue/<file>`.

## Decision 6 — Phase 1 ships engine-only; CLI deferred to Phase 2

`attune workflow run discovery-sweep` is NOT registered in
Phase 1. The engine is a Python API. Real `FindingSource`
adapters (wrapping bug_predict, security_audit, etc.) are
Phase 2 work, and registering an empty CLI workflow that
produces zero findings would be more confusing than not
registering it at all.

**Why:** Phase 1's intent was always the verification + queue
logic. Adapter implementations are independent work and gate
on the engine being stable.

**How to apply:** Phase 2A brings up both CLI registration and
the first adapter together. Until then, the documented entry
point is `DiscoverySweepEngine(sources=[...])` Python
instantiation.

**Phase 2A outcome (2026-05-13):** CLI registration shipped
alongside the `PatternScanSource` adapter — a deterministic,
zero-LLM-cost scanner that emits Findings for canonical bug
patterns (bare except, eval/exec, subprocess shell=True, TODO
markers). The verification engine then filters its raw output.
LLM-wrapping adapters (bug_predict, security_audit, code_review,
perf_audit, deep_review) remain Phase 2B work — they have a
different cost/budget profile that warrants per-adapter design.

## Decision 8 — Engine vs CLI workflow split (Phase 2A rename)

The Phase 1 class previously named `DiscoverySweepWorkflow`
was renamed to `DiscoverySweepEngine` and is the pure
orchestrator (no BaseWorkflow inheritance). A new
`DiscoverySweepWorkflow(BaseWorkflow)` in
`cli_workflow.py` is a thin wrapper that the workflow
registry sees, parses `**kwargs`, and delegates to the engine.

**Why:** `BaseWorkflow`'s mixin-heavy constructor is the right
shape for LLM-routed workflows but heavy for an orchestrator
that owns no LLM cost itself. Splitting keeps the engine's
constructor clean (sources, output_dir, project_root) while
still letting the CLI workflow runner dispatch normally.

**How to apply:** Engine for programmatic use; CLI workflow
for `attune workflow run discovery-sweep` and any future
registry-driven dispatch.

## Decision 7 — Budgets: $10 per sub-workflow, $40 per sweep, hard ceilings

Configurable via constructor or env vars
(`ATTUNE_DISCOVERY_SUBWORKFLOW_BUDGET_USD`,
`ATTUNE_DISCOVERY_SWEEP_BUDGET_USD`).

**Why:** "Standard" depth on a single sub-workflow runs ~$8–10
empirically. Multi-workflow sweeps add up fast; $40 keeps a
five-workflow sweep tractable without hard-stopping mid-run on
typical scopes. Hard ceiling (not warning) matches the SDK's
existing behavior — `Reached maximum budget` is an error, not
a soft signal.

**How to apply:** If a real sweep regularly hits the ceiling,
either narrow the scope or raise the cap — but the cap should
stay opinionated, not be auto-lifted on every overrun.

## Phase 2 commitments

Repeated here for visibility — see [phase-2.md](phase-2.md):

- CLI registration (`attune workflow run discovery-sweep`)
- Real `FindingSource` adapters (bug_predict, security_audit,
  code_review, perf_audit, deep_review)
- Auto-fix for `routine`-tagged items
- Workflow retirement evaluation (test_audit prime candidate)
- Multi-module parallelism
- RAG-grounded verification (use attune-help / attune-rag to
  check findings against documented patterns)
