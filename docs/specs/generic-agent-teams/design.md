# Design: Generic parallel agent teams

**Status:** complete (2026-06-26) — shipped in PR #1098: WorkflowAgent + AgentTeam in src/attune/agents/team.py; ReleasePrepTeam re-seat deliberately skipped per R6 fallback (see decisions.md)
**Requirements:** [requirements.md](requirements.md) ·
**Decisions:** [decisions.md](decisions.md)

---

## Architecture

A team is an explicit list of agents plus a declarative gate spec. The
coordinator fans out, aggregates, and gates. Nothing more — no plan,
no DAG (D2).

```text
AgentTeam(agents=[...], gates=[GateSpec, ...])
  .run(target) -> TeamReport
    await gather(agent.run(target) for agent in agents)   # D7 async
      WorkflowAgent.run(target) -> AgentResult            # D1 wraps a BaseWorkflow
        run wrapped workflow over target's file(s),
        extract 0-100 score (D5), sum cost
    evaluate GateSpecs against AgentResults -> QualityGate[] (D6)
    split critical-fail -> blockers, non-critical -> warnings
    verdict = no blockers and no critical gate failures
```

### The contract (async, D7)

```python
class TeamAgent(Protocol):
    key: str
    async def run(self, target: TeamTarget) -> AgentResult: ...
```

`WorkflowAgent` implements it natively async. A sync agent (the
subprocess release agents) implements the same `run` by offloading its
existing `process()` via `loop.run_in_executor` — the shim lives in the
agent, not the coordinator.

### Data classes (new, in `agents/team.py`)

```python
@dataclass
class AgentResult:
    key: str            # "code-review"
    score: float        # 0-100 (min across files for multi-file targets)
    cost: float
    success: bool       # False if the wrapped workflow errored
    details: dict[str, Any]

@dataclass
class GateSpec:         # declarative input
    name: str           # "Code Quality"
    agent_key: str      # "code-review"
    threshold: float    # 70.0
    critical: bool = True

@dataclass
class TeamReport:
    passed: bool
    gates: list[QualityGate]      # reuse existing dataclass (D6)
    results: list[AgentResult]
    blockers: list[str]
    warnings: list[str]
    cost: float
```

`QualityGate` (name, threshold, actual, passed, critical, message) is
**lifted** from `agents/release/release_models.py` to a shared home so
both the team and the release models import it from one place.

### Shared score extractor (D5)

Lift `_extract_score` / `_SCORE_RE` out of `pipeline/orchestrator.py`
into `agents/team.py` as the default `WorkflowAgent` scorer:
`findings["score"]` → `metadata["score"]` → `score:\s*N/100` regex →
configured default. A `WorkflowAgent(score_fn=...)` overrides it.

---

## Seam 1 — `/spec` quality gate (D3, the first consumer)

`_run_quality_gate` today: per-file fan-out of two workflows, min per
dimension, threshold 70. It becomes an `AgentTeam` of two agents, each
running its workflow over the file set and returning the **min** score
(behavior-preserving — R4):

```python
team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=files),
        WorkflowAgent("security-audit", SecurityAuditWorkflow, files=files),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", self._GATE_THRESHOLD),
        GateSpec("Security", "security-audit", self._GATE_THRESHOLD),
    ],
)
report = await team.run(files)
return (report.passed, report_to_gate_details(report), report.cost)
```

The empty-file trivial-pass, the `_GATE_MAX_FILES` cap, and the
fail-closed-on-error semantics are preserved — the per-file min and the
try/except move into `WorkflowAgent.run`.

## Seam 2 — `ReleasePrepTeam` re-seat (R6)

`ReleasePrepTeam` keeps its four subprocess agents but builds an
`AgentTeam` to run them: each release agent gains an async `run()`
shim around its sync `process()`, and `_evaluate_quality_gates`
becomes a list of `GateSpec`s. Observable `release-prep` output is
unchanged (R6 verifies via the existing report). If the re-seat proves
to add risk for no behavior change, the fallback is to document why
`ReleasePrepTeam` stays as-is and have it merely *import* the shared
`QualityGate` — but the default is to re-seat.

---

## File plan

### Create

- `src/attune/agents/team.py` — `TeamAgent` protocol, `WorkflowAgent`,
  `AgentTeam`, `GateSpec`, `AgentResult`, `TeamReport`, default scorer.
- `tests/unit/agents/test_team.py` — unit coverage for the scorer,
  gate evaluation (critical vs warning split), parallel run, and
  fail-closed on a raising workflow.
- `tests/integration/test_agent_team_dogfood.py` — **non-mocked** R5
  receipt.

### Modify

- `src/attune/agents/release/release_models.py` — `QualityGate` moves
  to the shared home; re-export here for back-compat.
- `src/attune/pipeline/orchestrator.py` — `_run_quality_gate` re-seated
  onto `AgentTeam`; `_extract_score`/`_SCORE_RE`/`_min_score`/
  `_result_cost` delegate to the shared scorer (or are removed once
  lifted).
- `src/attune/agents/release/release_prep_team.py` — build an
  `AgentTeam`; release agents gain async `run()` shims.
- `CHANGELOG.md` — `### Added` generic agent-team infrastructure.

---

## Tasks

```xml
<task id="1" name="generic-team-module">
  <objective>
    Create the generic parallel agent-team abstraction: a BaseWorkflow-
    wrapping agent and an async coordinator that fans out, aggregates,
    and gates. No consumer rewired yet — pure new infrastructure.
  </objective>
  <context>
    <existing-code path="src/attune/agents/release/base_agent.py">
      ReleaseAgent — the working escalation/LLM/state/heartbeat base to
      generalize from. Do NOT revive StubAgent/SDKAgent.
    </existing-code>
    <existing-code path="src/attune/pipeline/orchestrator.py">
      _extract_score / _SCORE_RE / _min_score / _result_cost — the score
      logic to lift into the shared default scorer (D5).
    </existing-code>
    <existing-code path="src/attune/agents/release/release_models.py">
      QualityGate dataclass — lift to a shared home, re-export here.
    </existing-code>
  </context>
  <files-to-create>
    <file path="src/attune/agents/team.py">
      TeamAgent (Protocol, async run), WorkflowAgent(key, workflow_cls,
      *, files=None, score_fn=None, escalate=False), AgentTeam(agents,
      gates), GateSpec, AgentResult, TeamReport, default extract_score().
      WorkflowAgent.run runs the workflow over each file, mins scores,
      sums cost, fails closed on exception (success=False, score=0).
    </file>
    <file path="tests/unit/agents/test_team.py">
      Scorer precedence; GateSpec eval splits blockers (critical) vs
      warnings (non-critical); AgentTeam.run gathers in parallel; a
      raising workflow -> success=False, gate fails closed.
    </file>
  </files-to-create>
  <validation>
    <check>pytest tests/unit/agents/test_team.py green</check>
    <check>AgentTeam with a fake passing + fake failing agent yields
      passed=False with the failing one in blockers</check>
    <check>grep -rn "StubAgent|DynamicTeam|SDKAgent" src/attune/agents/team.py
      is empty (R7)</check>
  </validation>
  <risks>
    <risk severity="low">Score-shape variance across workflows — mitigated
      by the regex fallback + score_fn override (D5).</risk>
  </risks>
</task>

<task id="2" name="reseat-spec-gate">
  <objective>
    Re-seat /spec's _run_quality_gate onto AgentTeam, preserving the
    empty-file trivial pass, the file cap, the per-dimension min, and
    fail-closed-on-error. Ship the non-mocked dogfood receipt (R5).
  </objective>
  <context>
    <existing-code path="src/attune/pipeline/orchestrator.py">
      _run_quality_gate (post-#1094). Behavior to preserve exactly;
      only the mechanism changes from inline gather to AgentTeam.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/pipeline/orchestrator.py">
      <change location="_run_quality_gate">
        BEFORE: inline jobs = [_review(cr, p)...] + [_review(sa, p)...]
        AFTER: build AgentTeam([WorkflowAgent code-review, security-audit],
        gates) and await team.run(files); map TeamReport -> existing
        (passed, details, cost) tuple shape.
      </change>
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="tests/integration/test_agent_team_dogfood.py">
      Non-mocked: AgentTeam of real CodeReviewWorkflow + SecurityAuditWorkflow
      over a deliberately-bad temp file (eval() / hardcoded secret) returns
      passed=False, a score < 70, cost > 0. Gated/skipped per the keyless-CI
      convention if it needs a key.
    </file>
  </files-to-create>
  <validation>
    <check>Existing /spec gate tests still green (behavior parity)</check>
    <check>A trivial task with no files still trivially passes</check>
    <check>The dogfood test produces a blocked verdict with real scores</check>
  </validation>
  <risks>
    <risk severity="medium">Behavior drift from the per-file min when it
      moves into the agent — covered by the parity tests + dogfood.</risk>
  </risks>
</task>

<task id="3" name="reseat-release-team">
  <objective>
    Re-seat ReleasePrepTeam onto AgentTeam (R6): its four subprocess
    agents gain async run() shims; quality gates become GateSpecs.
    release-prep observable output unchanged.
  </objective>
  <context>
    <existing-code path="src/attune/agents/release/release_prep_team.py">
      assess_readiness (run_in_executor fan-out) and
      _evaluate_quality_gates (four hardcoded gates) to express via
      AgentTeam + GateSpec.
    </existing-code>
  </context>
  <files-to-modify>
    <file path="src/attune/agents/release/release_prep_team.py">
      <change location="ReleasePrepTeam.assess_readiness">
        Build an AgentTeam from the four agents (async run() shim around
        sync process()) and GateSpecs; keep the bespoke
        ReleaseReadinessReport conversion.
      </change>
    </file>
    <file path="src/attune/agents/release/base_agent.py">
      <change location="ReleaseAgent">
        Add async run(target) -> AgentResult that offloads process()
        via run_in_executor and maps ReleaseAgentResult -> AgentResult.
      </change>
    </file>
  </files-to-modify>
  <validation>
    <check>release-prep workflow output unchanged (existing tests green)</check>
    <check>ReleasePrepTeam builds and runs via AgentTeam</check>
  </validation>
  <risks>
    <risk severity="low">If re-seat adds risk with zero behavior change,
      fall back to importing the shared QualityGate only and document it
      in decisions.md.</risk>
  </risks>
</task>

<task id="4" name="finalize-docs-guard">
  <objective>
    Lock the spec: decisions.md final, CHANGELOG entry, and a guard test
    asserting no deleted-engine symbol returns (R7).
  </objective>
  <files-to-modify>
    <file path="CHANGELOG.md">
      <change location="[Unreleased] ### Added">
        Generic parallel agent-team infrastructure (attune.agents.team);
        /spec quality gate re-seated onto it.
      </change>
    </file>
  </files-to-modify>
  <files-to-create>
    <file path="tests/unit/agents/test_no_revived_dead_code.py">
      Assert grep of src/ for StubAgent|DynamicTeam|SDKAgent stays empty
      (regression guard for the generalize-not-revive constraint).
    </file>
  </files-to-create>
  <validation>
    <check>Full suite green; import attune.orchestration clean (R8)</check>
    <check>health-check workflow still runs (R8 no collateral damage)</check>
  </validation>
</task>
```

---

## Sequencing

T1 (abstraction) → T2 (first consumer + R5 dogfood, the keystone) →
T3 (generalization proof) → T4 (lock). T1+T2 alone deliver a real,
dogfooded capability; T3+T4 prove and seal it.
