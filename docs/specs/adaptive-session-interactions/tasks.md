# Adaptive session interactions — Tasks

**Status:** parked (2026-09-05) — five proposed tasks preserved for later
execution; 0 started, 0 completed, no execution go, no auto-run authority.

Resume-Trigger: Patrick explicitly resumes this feature for execution after
coordination with Claude's active repository work and review of the task scope.

[Requirements](requirements.md) are approved. The [design](design.md) and
this implementation ladder are proposals. Saving or committing them is not
approval to execute them. A go on one task is not a go on subsequent tasks.

## Future session entry

1. Read [decisions](decisions.md), [evidence](evidence.md), and the approved
   requirements. Run the repository collaboration preflight and inspect
   current Git state and in-flight work before adopting historical claims.
2. Ask for the execution go on the selected task only when it has not
   already been explicitly granted. T1 establishes exact owners, consumer,
   source paths and baseline; later tasks derive their file scope from it.
3. Run the existing tasks/execution lifecycle gates against the actual
   changed paths at those boundaries. BLOCKED stops progression;
   CHAIR_REQUIRED needs the explicit bound acknowledgment. The preservation
   checks in evidence.md are document checks, not future execution receipts.
4. Only after the applicable go and gates, resume this repository-relative
   plan: docs/specs/adaptive-session-interactions/tasks.md. The existing
   spec workspace's resume route enters execution; do not open it as a
   substitute for read-only review.
5. Keep one canonical task plan here. Persist actual results with the
   existing attune.spec state mechanism; completed remains empty until a
   task actually completes and receives its required approval.

The parsed objectives repeat each original context constraint because the
existing task reader ignores the context element. Dependencies use the
reader's supported dependencies/dep shape. File lists remain deliberately
unset until T1; do not infer permission to modify an arbitrary path from an
empty list. No runtime or API invocation is needed to load this plan.

| Task | Scope | Dependency | Required receipt |
| --- | --- | --- | --- |
| T1 | Reconcile and characterize | Explicit task go | Evidence-chain and current-behavior probes |
| T2 | Need selection and preference | T1 acceptance and own go | Behavioral |
| T3 | Host readiness and pending interaction | T2 acceptance and own go | Behavioral and actual host round trip |
| T4 | Bounded comparative trial | T3 acceptance and own go | Metric and completed outcomes |
| T5 | Review and promote bounded default | T4 acceptance and own go | Evidence-chain and explicit default scope ruling |

```xml
<task id="1" name="reconcile-and-characterize">
  <objective>Derive the actual consumer, selection, preference, host, and action paths from the execution checkout and reconcile active work. Execution constraints: Requirements ASI-1 through ASI-7. Read source and existing specs; do not infer implementation from task status prose.</objective>
  <context>Requirements ASI-1 through ASI-7. Read source and existing specs; do not infer implementation from task status prose.</context>
  <validation><check>Produce a source-backed inventory and current-behavior probes; record the exact host/runtime and baseline tree. Select one consumer and record existing capabilities versus demonstrated gaps.</check></validation>
</task>
```

```xml
<task id="2" name="need-selection-and-preference">
  <dependencies><dep>1</dep></dependencies>
  <objective>Tighten guidance at the selected schema-bounded workspace choice for ASI-1, ASI-2, and ASI-5; add code only for a demonstrated remaining gap. Execution constraints: Files derive from T1. Prefer existing guidance/caller wiring over a new service or duplicate selector. If characterization already satisfies the requirement, evidence and documentation complete this task.</objective>
  <context>Files derive from T1. Prefer existing guidance/caller wiring over a new service or duplicate selector. If characterization already satisfies the requirement, evidence and documentation complete this task.</context>
  <validation><check>Behavioral cases cover phase-independent choices, no redundant questions, genuine alternatives, and persistent versus one-time overrides. Changed-code coverage meets the owning spec and repository gates.</check></validation>
</task>
```

```xml
<task id="3" name="host-readiness-and-pending-interaction">
  <dependencies><dep>2</dep></dependencies>
  <objective>Connect the selected interaction to existing capability and canonical-state boundaries for ASI-3 and ASI-4. Execution constraints: Do not reinvent workspace authority or use instance correlation as authorization.</objective>
  <context>Do not reinvent workspace authority or use instance correlation as authorization.</context>
  <validation><check>Complete actual-host and equivalent fallback round trips for the chosen consumer before usefulness measurement. Probe stale/repeated actions, unavailable surfaces, canonical answer preservation, and progress without approval. Verify client draft recovery before promising it. Human-observed usability and unmeasured paint timing remain separately labelled.</check></validation>
</task>
```

```xml
<task id="4" name="bounded-comparative-trial">
  <dependencies><dep>3</dep></dependencies>
  <objective>Run a preregistered small comparison of automatic decisions and conversation using ASI-6. Execution constraints: Freeze scenarios, order, sample count, and acceptance targets after the baseline and before collection. User participation and any paid operations need their applicable authorization.</objective>
  <context>Freeze scenarios, order, sample count, and acceptance targets after the baseline and before collection. User participation and any paid operations need their applicable authorization.</context>
  <validation><check>Retain raw outcomes, overrides, clarification turns, system timing boundaries and unknowns; report usefulness and failure evidence separately from latency.</check></validation>
</task>
```

```xml
<task id="5" name="review-and-promote-bounded-default">
  <dependencies><dep>4</dep></dependencies>
  <objective>Present the evidence and strongest counter-case; promote only the chair-approved default scope and documentation. Execution constraints: A wider rollout, renderer work, or later construct is a separate evidence-based decision.</objective>
  <context>A wider rollout, renderer work, or later construct is a separate evidence-based decision.</context>
  <validation><check>Verify selected source/projection consistency, actual-host receipts, outstanding risks, and explicit scope. Keep unruled requirements and host paths excluded from completion claims.</check></validation>
</task>
```
