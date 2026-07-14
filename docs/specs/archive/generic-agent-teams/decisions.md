# Decisions: Generic parallel agent teams

**Status:** complete (2026-06-26) — shipped in PR #1098 (src/attune/agents/team.py verified on disk 2026-07-14); reconciled at 2026-07-14 triage (was: APPROVED)
**Requirements:** [requirements.md](requirements.md) ·
**Design:** [design.md](design.md)

---

## Decision log

### D1 — Agent unit of work is a `BaseWorkflow` (decided 2026-06-26)

Each team agent wraps a registered `BaseWorkflow`; its job is to run
that workflow over a target and surface a 0–100 score.

**Why:** maximum leverage — reuses all existing workflow infra
(tiering, output, cost) and matches what the fixed `/spec` gate
already does ad-hoc with `CodeReviewWorkflow` + `SecurityAuditWorkflow`.

**Rejected:** arbitrary callable/tool (rebuilds result/score
conventions per tool); prompt+role LLM-native (needs the real
execution backend `StubAgent` never had — the thing #1096 deleted).

### D2 — Parallel fan-out only for v1 (decided 2026-06-26)

`asyncio.gather` over independent agents, then aggregate + gate.
No sequential stages, no DAG.

**Why:** it is the proven `ReleasePrepTeam` shape and covers both
live consumers. Sequential/DAG needs a plan representation that adds
design surface and slows the first dogfood. Deferred to a follow-up.

### D3 — First consumer is the `/spec` quality gate (decided 2026-06-26)

`_run_quality_gate` is re-seated onto `AgentTeam`.

**Why:** it is live, dogfooded on every `/spec` run, and already the
exact two-agent parallel-review shape — zero orphaned-motivation risk
(the failure mode that reversed #1093/#1096). A user-facing `/team`
CLI is explicitly a non-goal for the same reason.

---

## Resolved open questions

### OQ1 → D4 — Home is `attune.agents`, not `attune.orchestration`

New module `src/attune/agents/team.py` houses `WorkflowAgent`,
`AgentTeam`, `GateSpec`, `AgentResult`, `TeamReport`.

**Why:** the working base it generalizes (`ReleaseAgent`,
`ReleasePrepTeam`, `AgentStateStore`) already lives in
`attune.agents`. `attune.orchestration` was just pruned to
agent-templates + execution-strategies (#1096) and is semantically
the dead-engine namespace; re-introducing "team" there invites
confusion with the symbols we deleted. Keep the generalization next to
the code it lifts from.

### OQ2 → D5 — One canonical score extractor, overridable

`WorkflowAgent` owns a default `extract_score(result) -> float` that
mirrors the existing gate logic: `findings["score"]` →
`metadata["score"]` → the `score:\s*N/100` regex fallback
(`_SCORE_RE`) → a configured default. A `WorkflowAgent` may pass a
`score_fn` override for workflows that report differently.

**Why:** de-duplicating this is half the point of the abstraction —
today the logic is inline in `pipeline/orchestrator.py`
(`_extract_score`/`_SCORE_RE`) and again, differently, in
`ReleasePrepTeam._evaluate_quality_gates` (`findings["coverage_percent"]`
etc.). One shared extractor with a per-agent escape hatch covers both
without forcing every workflow into one score shape.

### OQ3 → D6 — Reuse `QualityGate`; add a thin `GateSpec` input

Input: `GateSpec(name, agent_key, threshold, critical=True)`.
Evaluated output: the existing `QualityGate(name, threshold, actual,
passed, critical, message)` dataclass (lift it to a shared location).

**Why:** `QualityGate` already carries the critical-vs-warning flag the
team needs to split blockers from warnings; a slimmer spec would lose
it. The declarative `GateSpec` (which agent, what threshold) is the
only new shape, and it is what lets one team config differ from
another without code.

### OQ4 → D7 — The team contract is **async**; sync agents adapt internally

`AgentTeam.run()` does `await asyncio.gather(*[a.run(path) for a in
agents])`. `WorkflowAgent.run()` is natively async (it `await`s the
workflow). Sync agents (the subprocess-based release agents) implement
the same async `run()` by offloading their existing sync `process()`
via `loop.run_in_executor` — the shim moves *into* the agent, out of
the coordinator.

**Why:** workflows are async, so a natively-async team avoids the
executor round-trip for the primary (D1) case. Making the *contract*
async and letting sync agents adapt keeps the coordinator uniform and
still satisfies R6 (re-seat `ReleasePrepTeam`) without rewriting its
subprocess agents.

---

## D8 — Escalation and Redis/state opt-in, off by default (2026-06-26)

`WorkflowAgent` does not escalate tiers or require Redis/`AgentStateStore`
by default. Escalation is `escalate=False`; `state_store`/`redis` default
`None` (no-op, as in the base).

**Why:** the `/spec` consumer's wrapped workflows already self-tier, so
re-running them at a higher tier on a low score is redundant for v1. The
escalation/heartbeat/state machinery is preserved in the base for the
release-team case and future consumers, but kept off the v1 critical path
to keep the first dogfood small. Revisit if a consumer wants score-driven
escalation.

---

## D9 — ReleasePrepTeam re-seat: take the R6 fallback (2026-06-26, execution)

`ReleasePrepTeam` keeps its bespoke `_evaluate_quality_gates` /
`_identify_issues` and is **not** re-seated onto `AgentTeam`. It already
shares the single `QualityGate` definition (see the D6 clarification
below). R6's documented fallback is exercised.

**Why:** the release team's four gates are heterogeneous in a way the
slim v1 `GateSpec` (D6: `actual >= threshold`) does not model:

- **Security** is a *max* gate — `critical_issues <= max_critical_issues`
  (lower is better), not a min-score threshold.
- **Quality** is on a **0–10** scale (`min_quality_score = 7.0`), not the
  0–100 the team scorer assumes.
- Each gate reads a **different findings key** (`critical_issues`,
  `coverage_percent`, `quality_score`), not a uniform `score`.

Re-seating faithfully would require expanding `GateSpec` with a
comparison direction and per-agent finding extractors — adding v1 design
surface the primary consumer (`/spec`) never needed, and risking drift on
a **working, fully-tested** release path (`test_release_prep_team.py`,
`test_release_prep_team_report.py`) for **zero behavior change**. That is
precisely the risk R6's fallback clause guards against. The richer
comparator model is deferred to a follow-up if a second consumer needs it.

**Realized D6 — shared home is `release_models`, not `team.py`.** D6/design
proposed moving `QualityGate` into `team.py` with `release_models`
re-exporting. Realized the other way: `QualityGate` stays defined in
`agents/release/release_models.py` and `agents/team.py` imports it from
there. Moving it into `team.py` would make `release_models` import from
`team.py` while `team.py` imports from `release_models` — a circular
import. Keeping the definition in `release_models` gives the single shared
source D6 wanted with no cycle and no churn to the widely-imported
release module.

---

## Cross-references

- `.claude/rules/attune/removing-dead-code.md` — generalize the working
  sibling; never revive `SDKAgent`/`StubAgent` (R7 guard).
- `docs/specs/spec-gate-real-review/decisions.md` — the #1096 reversal
  and the deferred non-goal this spec fulfills.
- Lift sources: `agents/release/base_agent.py` (`ReleaseAgent`),
  `agents/release/release_prep_team.py` (`ReleasePrepTeam`,
  `QualityGate` via `release_models`), `pipeline/orchestrator.py`
  (`_run_quality_gate`, `_extract_score`, `_SCORE_RE`).
